"""Tenant knowledge-item persistence for generic vertical RAG."""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg

from db.core.database import get_db, init_tenant_schema

DEFAULT_SOURCE_ID = "source:catalog_products"
DEFAULT_SOURCE_NAME = "catalog_products"
DEFAULT_SOURCE_TYPE = "product_catalog"
KNOWLEDGE_PREVIEW_LIMIT = 50
logger = logging.getLogger(__name__)


def sync_products_to_knowledge(
    site_id: str,
    source_name: str = DEFAULT_SOURCE_NAME,
    *,
    entity_type: str = "product",
    source_type: str = DEFAULT_SOURCE_TYPE,
) -> int:
    """Mirror catalog rows into generic knowledge_items."""
    init_tenant_schema(site_id)
    source_id = _source_id(source_name)
    with get_db(site_id) as conn:
        _upsert_source(conn, source_id, source_name, source_type=source_type)
        rows = conn.execute(
            """
            SELECT p.*, c.name AS category_name, c.slug AS category_slug,
                   csp.raw_product AS source_raw_product
            FROM products p
            JOIN categories c ON p.category_id = c.id
            LEFT JOIN catalog_source_products csp
              ON csp.product_id = p.id
             AND csp.source_name = %s
             AND csp.is_active = 1
            ORDER BY p.id
            """,
            (source_name,),
        ).fetchall()

    changed = 0
    with get_db(site_id) as conn:
        for row in rows:
            changed += _upsert_product_knowledge_item(conn, dict(row), source_id, entity_type=entity_type)
    if changed:
        try:
            from db.cache.answer_cache import bump_data_version

            bump_data_version(site_id, reason="knowledge_sync")
        except psycopg.Error:
            raise
        except Exception as exc:
            logger.warning("Answer cache invalidation skipped for %s/%s: %s", site_id, source_name, exc)
    return changed


def knowledge_stats(site_id: str) -> dict[str, Any]:
    """Return tenant knowledge counts for CRM/API surfaces."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_items,
                COUNT(*) FILTER (WHERE is_active = 1) AS active_items,
                COUNT(*) FILTER (WHERE is_active = 1 AND embedding IS NULL) AS missing_embeddings,
                COUNT(DISTINCT entity_type) FILTER (WHERE is_active = 1) AS entity_types
            FROM knowledge_items
            """
        ).fetchone()
    return dict(row or {})


def knowledge_preview(site_id: str, limit: int = KNOWLEDGE_PREVIEW_LIMIT) -> list[dict[str, Any]]:
    """Return a small active knowledge sample for CRM review."""
    init_tenant_schema(site_id)
    safe_limit = max(1, min(int(limit), 500))
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT
                id, external_id, entity_type, title, subtitle, summary, body,
                url, image_url, source_id, attributes_json, pricing_json,
                availability_json, is_active,
                CASE WHEN embedding IS NULL THEN 0 ELSE 1 END AS has_embedding,
                updated_at::TEXT AS updated_at
            FROM knowledge_items
            WHERE is_active = 1
            ORDER BY updated_at DESC, title ASC
            LIMIT %s
            """,
            (safe_limit,),
        ).fetchall()
    return [_decode_item(row) for row in rows]


def get_knowledge_items_by_ids(site_id: str, item_ids: list[str]) -> list[dict[str, Any]]:
    """Return active knowledge items by exact string IDs."""
    clean_ids = [str(item_id).strip() for item_id in item_ids if str(item_id).strip()]
    if not clean_ids:
        return []
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM knowledge_items
            WHERE id = ANY(%s) AND is_active = 1
            """,
            (clean_ids,),
        ).fetchall()
    return [_decode_item(row) for row in rows]


def _upsert_source(
    conn: psycopg.Connection,
    source_id: str,
    source_name: str,
    *,
    source_type: str = DEFAULT_SOURCE_TYPE,
) -> None:
    conn.execute(
        """
        INSERT INTO knowledge_sources
            (id, source_type, source_name, status, metadata_json, updated_at)
        VALUES (%s, %s, %s, 'active', '{}', CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
            source_name = EXCLUDED.source_name,
            status = EXCLUDED.status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (source_id, source_type, source_name),
    )


def _upsert_product_knowledge_item(
    conn: psycopg.Connection,
    product: dict[str, Any],
    source_id: str,
    *,
    entity_type: str = "product",
) -> int:
    item = _product_to_knowledge_item(product, source_id, entity_type=entity_type)
    row = conn.execute(
        """
        INSERT INTO knowledge_items
            (
                id, external_id, entity_type, title, subtitle, summary, body,
                url, image_url, source_id, attributes_json, pricing_json,
                availability_json, policy_json, risk_tags_json,
                is_active, last_seen_at, updated_at, embedding
            )
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
        ON CONFLICT (id) DO UPDATE SET
            external_id = EXCLUDED.external_id,
            entity_type = EXCLUDED.entity_type,
            title = EXCLUDED.title,
            subtitle = EXCLUDED.subtitle,
            summary = EXCLUDED.summary,
            body = EXCLUDED.body,
            url = EXCLUDED.url,
            image_url = EXCLUDED.image_url,
            source_id = EXCLUDED.source_id,
            attributes_json = EXCLUDED.attributes_json,
            pricing_json = EXCLUDED.pricing_json,
            availability_json = EXCLUDED.availability_json,
            policy_json = EXCLUDED.policy_json,
            risk_tags_json = EXCLUDED.risk_tags_json,
            is_active = EXCLUDED.is_active,
            last_seen_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            embedding = CASE
                WHEN knowledge_items.title IS DISTINCT FROM EXCLUDED.title
                  OR knowledge_items.summary IS DISTINCT FROM EXCLUDED.summary
                  OR knowledge_items.body IS DISTINCT FROM EXCLUDED.body
                  OR knowledge_items.attributes_json IS DISTINCT FROM EXCLUDED.attributes_json
                  OR knowledge_items.pricing_json IS DISTINCT FROM EXCLUDED.pricing_json
                  OR knowledge_items.policy_json IS DISTINCT FROM EXCLUDED.policy_json
                  OR knowledge_items.risk_tags_json IS DISTINCT FROM EXCLUDED.risk_tags_json
                THEN NULL
                ELSE knowledge_items.embedding
            END
        WHERE knowledge_items.external_id IS DISTINCT FROM EXCLUDED.external_id
           OR knowledge_items.entity_type IS DISTINCT FROM EXCLUDED.entity_type
           OR knowledge_items.title IS DISTINCT FROM EXCLUDED.title
           OR knowledge_items.subtitle IS DISTINCT FROM EXCLUDED.subtitle
           OR knowledge_items.summary IS DISTINCT FROM EXCLUDED.summary
           OR knowledge_items.body IS DISTINCT FROM EXCLUDED.body
           OR knowledge_items.url IS DISTINCT FROM EXCLUDED.url
           OR knowledge_items.image_url IS DISTINCT FROM EXCLUDED.image_url
           OR knowledge_items.source_id IS DISTINCT FROM EXCLUDED.source_id
           OR knowledge_items.attributes_json IS DISTINCT FROM EXCLUDED.attributes_json
           OR knowledge_items.pricing_json IS DISTINCT FROM EXCLUDED.pricing_json
           OR knowledge_items.availability_json IS DISTINCT FROM EXCLUDED.availability_json
           OR knowledge_items.policy_json IS DISTINCT FROM EXCLUDED.policy_json
           OR knowledge_items.risk_tags_json IS DISTINCT FROM EXCLUDED.risk_tags_json
           OR knowledge_items.is_active IS DISTINCT FROM EXCLUDED.is_active
        RETURNING id
        """,
        (
            item["id"],
            item["external_id"],
            item["entity_type"],
            item["title"],
            item["subtitle"],
            item["summary"],
            item["body"],
            item["url"],
            item["image_url"],
            item["source_id"],
            item["attributes_json"],
            item["pricing_json"],
            item["availability_json"],
            item["policy_json"],
            item["risk_tags_json"],
            item["is_active"],
        ),
    ).fetchone()
    return 1 if row else 0


def _product_to_knowledge_item(
    product: dict[str, Any],
    source_id: str,
    *,
    entity_type: str = "product",
) -> dict[str, Any]:
    product_id = str(product.get("id") or "")
    title = _text(product.get("name"), f"Item {product_id}")
    category = _text(product.get("category_name"), product.get("category"), "Knowledge")
    brand = _text(product.get("brand"))
    summary = _knowledge_summary(product, brand, category, entity_type)
    source_payload = _source_product_payload(product)
    return {
        "id": f"product:{product_id}",
        "external_id": product_id,
        "entity_type": _safe_entity_type(entity_type),
        "title": title,
        "subtitle": " | ".join(part for part in (brand, category) if part),
        "summary": summary,
        "body": _knowledge_body(product, summary),
        "url": _text(product.get("url")),
        "image_url": _text(product.get("image_url")),
        "source_id": source_id,
        "attributes_json": _json_text(_product_attributes(product, category, brand)),
        "pricing_json": _json_text(_product_pricing(product, source_payload)),
        "availability_json": _json_text(_product_availability(product)),
        "policy_json": _json_text(_product_policy(source_payload)),
        "risk_tags_json": _json_text(_product_risk_tags(source_payload)),
        "is_active": int(product.get("is_active", 1) or 0),
    }


def _product_attributes(product: dict[str, Any], category: str, brand: str) -> dict[str, Any]:
    return {
        "product_id": str(product.get("id") or ""),
        "brand": brand,
        "category": category,
        "category_slug": _text(product.get("category_slug")),
        "color": _text(product.get("color")),
        "size_options": _json_or_text(product.get("size_options")),
        "tags": _json_or_text(product.get("tags")),
        "rating": float(product.get("rating") or 0),
        "review_count": int(product.get("review_count") or 0),
    }


def _product_pricing(product: dict[str, Any], source_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    pricing = {
        "price": float(product.get("price") or 0),
        "original_price": _optional_float(product.get("original_price")),
        "currency": "INR",
    }
    source_pricing = source_payload.get("pricing_json") if isinstance(source_payload, dict) else None
    if isinstance(source_pricing, dict):
        for key in ("premium_monthly", "premium_annual", "currency"):
            if source_pricing.get(key) not in (None, ""):
                pricing[key] = source_pricing[key]
    return pricing


def _product_availability(product: dict[str, Any]) -> dict[str, Any]:
    stock = int(product.get("stock") or 0)
    return {"stock": stock, "in_stock": stock > 0, "is_active": bool(product.get("is_active", 1))}


def _source_product_payload(product: dict[str, Any]) -> dict[str, Any]:
    raw = product.get("source_raw_product")
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        value = json.loads(str(raw))
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _product_policy(source_payload: dict[str, Any]) -> dict[str, Any]:
    raw_policy = source_payload.get("policy_json") if isinstance(source_payload, dict) else None
    if not isinstance(raw_policy, dict):
        return {}
    return {key: value for key, value in raw_policy.items() if value not in ("", None, [], {})}


def _product_risk_tags(source_payload: dict[str, Any]) -> list[str]:
    raw_tags = source_payload.get("risk_tags") if isinstance(source_payload, dict) else None
    tags = raw_tags if isinstance(raw_tags, list) else []
    return [str(tag).strip() for tag in tags if str(tag or "").strip()]


def _knowledge_summary(product: dict[str, Any], brand: str, category: str, entity_type: str) -> str:
    price = float(product.get("price") or 0)
    type_label = _safe_entity_type(entity_type).replace("_", " ")
    owner = f"{brand} " if brand else ""
    if price > 0:
        return f"{owner}{category} {type_label} priced at INR {price:,.0f}.".strip()
    return f"{owner}{category} {type_label}.".strip()


def _knowledge_body(product: dict[str, Any], summary: str) -> str:
    description = _text(product.get("description"))
    parts = [summary, description]
    return " ".join(part for part in parts if part)


def _safe_entity_type(value: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(value or "").strip().lower())
    clean = "_".join(part for part in clean.split("_") if part)
    return clean or "knowledge_item"


def _decode_item(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for key in (
        "attributes_json",
        "pricing_json",
        "availability_json",
        "location_json",
        "contact_json",
        "policy_json",
        "risk_tags_json",
    ):
        if key in item:
            item[key.replace("_json", "")] = _json_or_text(item.pop(key))
    item["name"] = item.get("title", "")
    item["category_name"] = item.get("entity_type", "")
    return item


def _source_id(source_name: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in source_name)
    return f"source:{clean or DEFAULT_SOURCE_NAME}"


def _text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_or_text(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return str(value)


def _optional_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None
