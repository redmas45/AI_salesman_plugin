"""Catalog persistence and crawl report helpers for ingestion."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Protocol

from agent.ingestion_helpers.ingestion_coverage import count_product_variants, coverage_score
from agent.retrieval.product_rag import _embed, _product_to_text
from agent.verticals.discovery_profiles import knowledge_entity_type_for
from agent.verticals.registry import DEFAULT_VERTICAL_KEY
from db.core.database import get_db, init_tenant_schema, upsert_variants

logger = logging.getLogger(__name__)


class CrawlReportFactory(Protocol):
    def __call__(
        self,
        site_id: str,
        site_url: str,
        source_type: str,
        pages_visited: int,
        pages_failed: int,
        pages_blocked: int,
        product_count: int,
        variant_count: int,
        category_count: int,
        failed_urls: list[str],
        blocked_urls: list[str],
        coverage_score: float,
        duration_ms: float,
        stopped_by_limit: bool,
        created_at: str,
    ) -> Any: ...


TextCleaner = Callable[[Any], str]
StableIdBuilder = Callable[..., int]
FirstValue = Callable[..., Any]
ConsolePrinter = Callable[[str], None]


def ensure_category(
    conn: Any,
    category_name: str,
    site_id: str,
    *,
    clean_text: TextCleaner,
    stable_id: StableIdBuilder,
) -> int:
    safe_name = clean_text(category_name) or "Products"
    slug = re.sub(r"[^a-z0-9]+", "-", safe_name.lower()).strip("-") or "products"

    existing = conn.execute(
        "SELECT id FROM categories WHERE name = %s OR slug = %s",
        (safe_name, slug),
    ).fetchone()
    if existing:
        return existing["id"]

    category_id = stable_id(site_id, safe_name, slug)
    try:
        conn.execute(
            "INSERT INTO categories (id, name, slug) VALUES (%s, %s, %s)",
            (category_id, safe_name, slug),
        )
        return category_id
    except Exception:
        existing = conn.execute(
            "SELECT id FROM categories WHERE name = %s OR slug = %s",
            (safe_name, slug),
        ).fetchone()
        if existing:
            return existing["id"]
        raise


def vectorize(site_id: str) -> int:
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT p.*, c.name AS category_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.embedding IS NULL
            ORDER BY p.id
            """
        ).fetchall()

    if not rows:
        return 0

    texts = [_product_to_text(dict(row)) for row in rows]
    embeddings = _embed(texts)
    with get_db(site_id) as conn:
        for index, row in enumerate(rows):
            conn.execute(
                "UPDATE products SET embedding = %s WHERE id = %s",
                (embeddings[index], row["id"]),
            )
    try:
        from db.core.database import rebuild_search_vectors

        rebuild_search_vectors(site_id)
    except Exception as exc:
        logger.warning("Ingestion | search_vector rebuild after vectorize failed: %s", exc)
    return len(rows)


def persist_catalog(
    site_id: str,
    products: list[dict[str, Any]],
    reconcile_missing: bool,
    source_name: str,
    *,
    clean_text: TextCleaner,
    stable_id: StableIdBuilder,
    first_value: FirstValue,
    console_print: ConsolePrinter,
    crawl_report: dict[str, Any] | None = None,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
) -> int:
    init_tenant_schema(site_id)
    start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    incoming_ids: list[int] = []
    incoming_source_ids: list[str] = []
    changed_names: list[str] = []
    changed = 0
    deactivated = 0
    deactivated_names: list[str] = []
    variant_batches: list[tuple[int, list[dict[str, Any]]]] = []
    with get_db(site_id) as conn:
        for product in products:
            product_id = int(product["id"])
            incoming_ids.append(product_id)
            source_product_id = str(product_id)
            incoming_source_ids.append(source_product_id)
            category_id = ensure_category(
                conn,
                first_value(product.get("category"), "Products"),
                site_id,
                clean_text=clean_text,
                stable_id=stable_id,
            )
            _upsert_source_product(conn, source_name, source_product_id, product_id, product, first_value)
            row = _upsert_product(conn, product_id, product, category_id)
            if row:
                changed += 1
                changed_names.append(product["name"])
            variants = product.get("variants")
            if isinstance(variants, list) and variants:
                variant_batches.append((product_id, variants))

        if reconcile_missing and incoming_ids:
            deactivated, deactivated_names = _deactivate_missing_products(conn, source_name, incoming_source_ids, incoming_ids)

    variant_count = sum(upsert_variants(site_id, product_id, variants) for product_id, variants in variant_batches)
    vectorized = vectorize(site_id)
    knowledge_vectorized = sync_catalog_knowledge(site_id, source_name, vertical_key=vertical_key)
    if changed or deactivated or variant_count or vectorized or knowledge_vectorized:
        _bump_catalog_data_version(site_id, source_name)
    _record_catalog_sync_run(
        site_id,
        source_name,
        len(incoming_ids),
        changed,
        deactivated,
        vectorized + knowledge_vectorized,
        crawl_report,
    )
    _log_catalog_sync(
        site_id,
        source_name,
        start_timestamp,
        len(incoming_ids),
        changed,
        deactivated,
        variant_count,
        vectorized,
        knowledge_vectorized,
        changed_names,
        deactivated_names,
        console_print,
    )
    return changed


def _upsert_source_product(
    conn: Any,
    source_name: str,
    source_product_id: str,
    product_id: int,
    product: dict[str, Any],
    first_value: FirstValue,
) -> None:
    conn.execute(
        """
        INSERT INTO catalog_source_products
          (source_name, source_product_id, product_id, name, brand, category,
           price, stock, image_url, raw_product, is_active, last_seen_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (source_name, source_product_id) DO UPDATE SET
          product_id = EXCLUDED.product_id,
          name = EXCLUDED.name,
          brand = EXCLUDED.brand,
          category = EXCLUDED.category,
          price = EXCLUDED.price,
          stock = EXCLUDED.stock,
          image_url = EXCLUDED.image_url,
          raw_product = EXCLUDED.raw_product,
          is_active = EXCLUDED.is_active,
          last_seen_at = CURRENT_TIMESTAMP
        """,
        (
            source_name,
            source_product_id,
            product_id,
            product["name"],
            product["brand"],
            first_value(product.get("category"), "Products"),
            float(product["price"]),
            int(product.get("stock", 0)),
            product.get("image_url"),
            json.dumps(product, ensure_ascii=False),
            int(product.get("is_active", 1)),
        ),
    )


def _upsert_product(conn: Any, product_id: int, product: dict[str, Any], category_id: int) -> Any:
    return conn.execute(
        """
        INSERT INTO products
          (id, variant_id, name, brand, category_id, description, price,
           original_price, color, size_options, tags, rating, review_count, stock,
           image_url, is_active, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
        ON CONFLICT (id) DO UPDATE SET
          variant_id = EXCLUDED.variant_id,
          name = EXCLUDED.name,
          brand = EXCLUDED.brand,
          category_id = EXCLUDED.category_id,
          description = EXCLUDED.description,
          price = EXCLUDED.price,
          original_price = EXCLUDED.original_price,
          color = EXCLUDED.color,
          size_options = EXCLUDED.size_options,
          tags = EXCLUDED.tags,
          rating = EXCLUDED.rating,
          review_count = EXCLUDED.review_count,
          stock = EXCLUDED.stock,
          image_url = EXCLUDED.image_url,
          is_active = EXCLUDED.is_active,
          embedding = CASE
            WHEN products.name IS DISTINCT FROM EXCLUDED.name
              OR products.brand IS DISTINCT FROM EXCLUDED.brand
              OR products.category_id IS DISTINCT FROM EXCLUDED.category_id
              OR products.description IS DISTINCT FROM EXCLUDED.description
              OR products.price IS DISTINCT FROM EXCLUDED.price
              OR products.original_price IS DISTINCT FROM EXCLUDED.original_price
              OR products.color IS DISTINCT FROM EXCLUDED.color
              OR products.size_options IS DISTINCT FROM EXCLUDED.size_options
              OR products.tags IS DISTINCT FROM EXCLUDED.tags
              OR products.image_url IS DISTINCT FROM EXCLUDED.image_url
            THEN NULL
            ELSE products.embedding
          END
        WHERE products.variant_id IS DISTINCT FROM EXCLUDED.variant_id
           OR products.name IS DISTINCT FROM EXCLUDED.name
           OR products.brand IS DISTINCT FROM EXCLUDED.brand
           OR products.category_id IS DISTINCT FROM EXCLUDED.category_id
           OR products.description IS DISTINCT FROM EXCLUDED.description
           OR products.price IS DISTINCT FROM EXCLUDED.price
           OR products.original_price IS DISTINCT FROM EXCLUDED.original_price
           OR products.color IS DISTINCT FROM EXCLUDED.color
           OR products.size_options IS DISTINCT FROM EXCLUDED.size_options
           OR products.tags IS DISTINCT FROM EXCLUDED.tags
           OR products.rating IS DISTINCT FROM EXCLUDED.rating
           OR products.review_count IS DISTINCT FROM EXCLUDED.review_count
           OR products.stock IS DISTINCT FROM EXCLUDED.stock
           OR products.image_url IS DISTINCT FROM EXCLUDED.image_url
           OR products.is_active IS DISTINCT FROM EXCLUDED.is_active
        RETURNING id
        """,
        (
            product_id,
            product.get("variant_id"),
            product["name"],
            product["brand"],
            category_id,
            product["description"],
            float(product["price"]),
            float(product["original_price"]),
            product.get("color"),
            product.get("size_options") or "[]",
            json.dumps(product.get("tags") or []),
            float(product.get("rating", 0.0)),
            int(product.get("review_count", 0)),
            int(product.get("stock", 0)),
            product.get("image_url"),
            int(product.get("is_active", 1)),
        ),
    ).fetchone()


def _deactivate_missing_products(
    conn: Any,
    source_name: str,
    incoming_source_ids: list[str],
    incoming_ids: list[int],
) -> tuple[int, list[str]]:
    conn.execute(
        """
        UPDATE catalog_source_products
        SET is_active = 0
        WHERE source_name = %s
          AND is_active = 1
          AND NOT (source_product_id = ANY(%s))
        """,
        (source_name, incoming_source_ids),
    )
    result = conn.execute(
        """
        UPDATE products
        SET is_active = 0,
            embedding = NULL
        WHERE is_active = 1
          AND NOT (id = ANY(%s))
        RETURNING name
        """,
        (incoming_ids,),
    )
    deactivated_rows = result.fetchall()
    return len(deactivated_rows), [row["name"] for row in deactivated_rows]


def _bump_catalog_data_version(site_id: str, source_name: str) -> None:
    try:
        from db.cache.answer_cache import bump_data_version

        bump_data_version(site_id, reason="catalog_sync")
    except Exception as exc:
        logger.warning("Answer cache invalidation skipped for %s/%s: %s", site_id, source_name, exc)


def _record_catalog_sync_run(
    site_id: str,
    source_name: str,
    source_count: int,
    changed_count: int,
    deactivated_count: int,
    vectorized_count: int,
    crawl_report: dict[str, Any] | None,
) -> None:
    with get_db(site_id) as conn:
        conn.execute(
            """
            INSERT INTO catalog_sync_runs
              (source_name, source_count, changed_count, deactivated_count, vectorized_count, report_json)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                source_name,
                source_count,
                changed_count,
                deactivated_count,
                vectorized_count,
                json.dumps(crawl_report or {}, ensure_ascii=False),
            ),
        )


def _log_catalog_sync(
    site_id: str,
    source_name: str,
    start_timestamp: str,
    source_count: int,
    changed: int,
    deactivated: int,
    variant_count: int,
    vectorized: int,
    knowledge_vectorized: int,
    changed_names: list[str],
    deactivated_names: list[str],
    console_print: ConsolePrinter,
) -> None:
    logger.info(
        "Catalog sync for %s/%s: source=%s changed=%s deactivated=%s vectorized=%s knowledge_vectorized=%s",
        site_id,
        source_name,
        source_count,
        changed,
        deactivated,
        vectorized,
        knowledge_vectorized,
    )
    console_print(
        f"[{start_timestamp}] Catalog sync ({source_name}): {source_count} source products, "
        f"{changed} changed/new, {deactivated} deactivated, {variant_count} variants, "
        f"{vectorized} product vectors, {knowledge_vectorized} knowledge vectors"
    )
    if changed_names:
        console_print(f"  -> Added/Changed: {', '.join(changed_names)}")
    if deactivated_names:
        console_print(f"  -> Deactivated/Removed: {', '.join(deactivated_names)}")


def sync_catalog_knowledge(site_id: str, source_name: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> int:
    try:
        from agent.retrieval.generic_rag import vectorize_missing_knowledge
        from db.knowledge_base.knowledge_items import sync_products_to_knowledge

        entity_type = knowledge_entity_type_for(vertical_key)
        source_type = "product_catalog" if entity_type == "product" else "website_crawl"
        sync_products_to_knowledge(site_id, source_name, entity_type=entity_type, source_type=source_type)
        return vectorize_missing_knowledge(site_id)
    except Exception as exc:
        logger.warning("Knowledge sync skipped for %s/%s: %s", site_id, source_name, exc)
        return 0


def build_crawl_report(
    *,
    site_id: str,
    site_url: str,
    source_type: str,
    pages_visited: int,
    pages_failed: int,
    pages_blocked: int,
    products: list[dict[str, Any]],
    failed_urls: list[str],
    blocked_urls: list[str],
    stopped_by_limit: bool,
    duration_ms: float,
    report_factory: CrawlReportFactory,
    clean_text: TextCleaner,
) -> Any:
    variant_count = count_product_variants(products)
    category_count = len({
        clean_text(product.get("category"))
        for product in products
        if clean_text(product.get("category"))
    })
    return report_factory(
        site_id=site_id,
        site_url=site_url,
        source_type=source_type,
        pages_visited=pages_visited,
        pages_failed=pages_failed,
        pages_blocked=pages_blocked,
        product_count=len(products),
        variant_count=variant_count,
        category_count=category_count,
        failed_urls=failed_urls[:50],
        blocked_urls=blocked_urls[:50],
        coverage_score=coverage_score(
            stopped_by_limit=stopped_by_limit,
            pages_visited=pages_visited,
            pages_failed=pages_failed,
            product_count=len(products),
            variant_count=variant_count,
            source_type=source_type,
        ),
        duration_ms=duration_ms,
        stopped_by_limit=stopped_by_limit,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
