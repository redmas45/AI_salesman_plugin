"""
Catalog ingestion utilities for crawler-based sources.

Each source is normalized into tenant-specific PostgreSQL tables and then vectorized
for RAG.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
from collections import deque
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

import httpx

from agent.rag import _embed, _product_to_text
from db.database import get_db, init_tenant_schema

logger = logging.getLogger(__name__)

PRICE_RE = re.compile(r"(?:₹|rs\.?|inr|\$)\s*([0-9]+(?:[.,][0-9]{1,2})?)", re.IGNORECASE)
SPACES_RE = re.compile(r"\s+")
NEXT_FLIGHT_SCRIPT_RE = re.compile(
    r"self\.__next_f\.push\(\[\s*1,\s*(\"(?:\\.|[^\"\\])+\")\s*\]\)",
    flags=re.IGNORECASE | re.DOTALL,
)
NEXT_DATA_SCRIPT_RE = re.compile(
    r"<script[^>]*id=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>",
    flags=re.IGNORECASE | re.DOTALL,
)


def sanitize_site_id(raw: str) -> str:
    text = (raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        return "site"
    if text[0].isdigit():
        text = f"site_{text}"
    return text[:50]


def _stable_id(*parts: str) -> int:
    seed = "|".join(parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return int(digest, 16) % (2**63 - 1) or 1


def _clean_text(raw: Any) -> str:
    if raw is None:
        return ""
    return SPACES_RE.sub(" ", html.unescape(str(raw))).strip()


def _first(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, tuple, dict)) and not value:
            continue
        return value
    return default


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return 0.0
    text = str(value).replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        return float(match.group(1)) if match else 0.0


def _parse_price(text: str) -> float:
    match = PRICE_RE.search(_clean_text(text))
    if not match:
        return 0.0
    return _to_float(match.group(1))


def _normalized_candidate_name(value: str) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"(?:\s+|^)(?:₹|rs\.?|inr|\$)\s*[0-9]+(?:[.,][0-9]{1,2})?\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_noise_name(value: str) -> bool:
    lowered = _normalized_candidate_name(value)
    if not lowered:
        return True

    utility_tokens = {
        "relative",
        "block",
        "inline-block",
        "h-full",
        "w-full",
        "aspect-square",
        "sr-only",
        "pointer-events-none",
    }
    tokens = set(lowered.split())
    if len(tokens & utility_tokens) >= 2:
        return True

    if lowered.startswith(("relative ", "block ", "inline-block ")):
        return True

    if "," in lowered and float(_parse_price(lowered)) <= 0:
        return True

    return False


def _decode_next_payload(raw: str) -> Any | None:
    if not raw:
        return None

    candidate = raw.strip()
    if not candidate:
        return None

    attempts: list[str] = [candidate]
    if (candidate.startswith('"') and candidate.endswith('"')) or (
        candidate.startswith("'") and candidate.endswith("'")
    ):
        attempts.append(candidate[1:-1])
        try:
            attempts.append(bytes(candidate[1:-1], "utf-8").decode("unicode_escape"))
        except Exception:
            pass

    for attempt in attempts:
        try:
            return json.loads(attempt)
        except Exception:
            continue
    return None


def _collect_react_node_texts(node: Any, texts: list[str], images: list[str], prices: list[float]) -> None:
    if isinstance(node, str):
        text = _clean_text(node)
        if not text:
            return
        texts.append(text)
        value = _parse_price(text)
        if value > 0:
            prices.append(value)
        return

    if isinstance(node, list):
        for item in node:
            _collect_react_node_texts(item, texts, images, prices)
        return

    if isinstance(node, dict):
        for key, value in node.items():
            if key == "src" and isinstance(value, str):
                value_clean = value.strip()
                if value_clean.startswith("http://") or value_clean.startswith("https://"):
                    images.append(value_clean)
                continue

            if key == "children":
                _collect_react_node_texts(value, texts, images, prices)
                continue

            if key in {"name", "alt", "title"} and isinstance(value, str):
                texts.append(_clean_text(value))
                continue

            _collect_react_node_texts(value, texts, images, prices)


def _extract_product_from_react_payload(node: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    if not isinstance(node, dict):
        return None

    href = node.get("href")
    if not (isinstance(href, str) and "/product/" in href.lower()):
        return None

    texts: list[str] = []
    images: list[str] = []
    prices: list[float] = []
    _collect_react_node_texts(node, texts, images, prices)

    if not texts:
        return None

    candidate_names = [t for t in texts if not t.startswith("$$") and len(_clean_text(t).split()) >= 2]
    if not candidate_names:
        return None

    name = candidate_names[0]
    # Prefer names that look like product names, not site chrome/navigation labels
    for item in candidate_names:
        lowered = item.lower()
        if "acme store" not in lowered and "shop" not in lowered and "search" not in lowered:
            name = item
            break

    description = _clean_text(" | ".join(texts[:10]))
    description = description if description else name
    price = max(prices) if prices else 0.0

    if price <= 0:
        for item in texts:
            value = _parse_price(item)
            if value > 0:
                price = value
                break
    if not href.startswith("http"):
        href = urljoin(source_url, href)

    return _normalize_product_row(
        {
            "name": name,
            "description": description,
            "price": price,
            "image": _clean_text(images[0]) if images else None,
            "category": _derive_category_from_url(href),
            "brand": "Unknown Brand",
        },
        fallback_category=_derive_category_from_url(href),
        source_url=source_url,
    )


def _extract_nextjs_flight_products(html_text: str, source_url: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    def _collect_from_payload(payload: Any) -> None:
        if not isinstance(payload, (dict, list)):
            return
        stack: list[Any] = [payload]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                product = _extract_product_from_react_payload(item, source_url)
                if product:
                    product_id = int(product["id"])
                    if product_id not in seen_ids:
                        seen_ids.add(product_id)
                        results.append(product)
                for value in item.values():
                    if isinstance(value, (dict, list)):
                        stack.append(value)
            elif isinstance(item, list):
                for value in item:
                    if isinstance(value, (dict, list)):
                        stack.append(value)

    for match in NEXT_FLIGHT_SCRIPT_RE.finditer(html_text):
        payload_raw = match.group(1)
        decoded = _decode_next_payload(payload_raw)
        if decoded is None:
            continue

        if isinstance(decoded, str) and ":" in decoded[:40]:
            try:
                decoded = decoded.split(":", 1)[1]
            except Exception:
                continue
        elif isinstance(decoded, str) and decoded.startswith("[") is False:
            continue

        if isinstance(decoded, str):
            try:
                payload = json.loads(decoded)
            except json.JSONDecodeError:
                continue
        else:
            payload = decoded

        _collect_from_payload(payload)

    for match in NEXT_DATA_SCRIPT_RE.finditer(html_text):
        payload = _decode_next_payload(match.group(1))
        if payload is None:
            continue
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                continue
        _collect_from_payload(payload)

    return results


def _to_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        if "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value)]


def _normalize_product_row(row: dict[str, Any], fallback_category: str, source_url: str) -> dict[str, Any] | None:
    name = _clean_text(_first(row.get("name"), row.get("title"), row.get("product_name"), default=""))
    if not name:
        return None

    description = _clean_text(
        _first(row.get("description"), row.get("summary"), row.get("body"), default=name)
    )
    category = _clean_text(_first(row.get("category"), row.get("type"), row.get("group"), default=fallback_category))
    brand = _clean_text(_first(row.get("brand"), row.get("vendor"), row.get("maker"), default="Unknown Brand"))

    raw_id = _first(row.get("id"), row.get("product_id"), row.get("_id"), default=None)
    if raw_id is None:
        stable_id = _stable_id(source_url, name, description)
        product_id = int(stable_id)
    else:
        try:
            product_id = int(raw_id)
        except (TypeError, ValueError):
            product_id = _stable_id(source_url, str(raw_id), name)

    variant = row.get("variant_id")
    variant_id = int(_to_float(variant)) if variant not in (None, "") else None
    color = _first(row.get("color"), default=None)
    size_raw = _first(row.get("size_options"), row.get("sizes"), default="[]")
    size_options = (
        json.dumps(_to_tags(size_raw))
        if not isinstance(size_raw, str)
        else (size_raw if size_raw else "[]")
    )
    tags = _to_tags(_first(row.get("tags"), row.get("labels"), default=[]))
    price = _to_float(_first(row.get("price"), row.get("amount"), row.get("cost"), default=0.0))
    original_price = _to_float(_first(row.get("original_price"), row.get("list_price"), default=price or 0.0))
    rating = _to_float(_first(row.get("rating"), row.get("score"), default=0.0))
    review_count = int(_to_float(_first(row.get("review_count"), row.get("reviewCount"), default=0)))
    stock = int(_to_float(_first(row.get("stock"), row.get("quantity"), default=100)))
    image = _first(row.get("image"), row.get("image_url"), row.get("thumbnail"), default=None)
    is_active = int(_first(row.get("is_active"), 1))

    return {
        "id": int(product_id),
        "variant_id": variant_id,
        "name": name,
        "brand": brand or "Unknown Brand",
        "category": category or fallback_category,
        "description": description or name,
        "price": price,
        "original_price": original_price,
        "color": color,
        "size_options": size_options,
        "tags": tags,
        "rating": rating,
        "review_count": review_count,
        "stock": stock,
        "image_url": image,
        "is_active": is_active,
    }


class _HtmlHarvest(HTMLParser):
    BLOCK_TAGS = {"title", "h1", "h2", "h3", "p", "li", "section", "article"}
    IGNORE_TAGS = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.links: list[str] = []
        self._stack: list[str] = []
        self._buffers: list[list[str]] = []
        self._ignore_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.IGNORE_TAGS:
            self._ignore_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self._stack.append(tag)
            self._buffers.append([])
        if tag == "a":
            href = dict(attrs).get("href")
            if href and not href.startswith("javascript:") and href != "#":
                self.links.append(href)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.IGNORE_TAGS:
            self._ignore_depth = max(0, self._ignore_depth - 1)
            return
        if tag in self.BLOCK_TAGS and self._stack and self._stack[-1] == tag:
            idx = len(self._buffers) - 1
            if idx >= 0:
                text = _clean_text(" ".join(self._buffers[idx]))
                if text:
                    self.blocks.append(text)
                self._buffers.pop()
            self._stack.pop()

    def handle_data(self, data):
        if self._ignore_depth:
            return
        text = data.strip()
        if not text:
            return
        for idx in range(len(self._buffers)):
            self._buffers[idx].append(text)


def _extract_jsonld_products(html_text: str, source_url: str) -> list[dict[str, Any]]:
    raw_json = re.findall(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    results = []
    for entry in raw_json:
        try:
            payload = json.loads(entry.strip())
        except json.JSONDecodeError:
            continue

        queue: list[Any] = [payload] if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])
        while queue:
            item = queue.pop()
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "Product":
                row = _normalize_jsonld_item(item, source_url)
                if row:
                    results.append(row)

            graph = item.get("@graph")
            if isinstance(graph, list):
                queue.extend(graph)
            elif isinstance(graph, dict):
                queue.append(graph)
    return results


def _normalize_jsonld_item(raw: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    name = _clean_text(_first(raw.get("name"), raw.get("headline"), default=""))
    if not name:
        return None

    description = _clean_text(_first(raw.get("description"), raw.get("summary"), default=name))
    category = _clean_text(_first(raw.get("category"), "Products"))
    brand = raw.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")

    offers = raw.get("offers") or {}
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if not isinstance(offers, dict):
        offers = {}

    rating = 0.0
    review_count = 0
    aggregate = raw.get("aggregateRating")
    if isinstance(aggregate, dict):
        rating = _to_float(aggregate.get("ratingValue"))
        review_count = int(_to_float(aggregate.get("reviewCount")))

    availability = _clean_text(_first(raw.get("availability"), offers.get("availability"), default="")).lower()
    stock = 100 if ("in stock" in availability or availability == "instock") else 100

    return _normalize_product_row(
        {
            "id": _first(raw.get("product_id"), raw.get("sku"), _stable_id(source_url, name, description)),
            "name": name,
            "brand": _first(brand, "Unknown Brand"),
            "category": _first(category, "Products"),
            "description": description,
            "price": _to_float(_first(offers.get("price"), offers.get("lowPrice"), offers.get("highPrice"), 0)),
            "original_price": _to_float(_first(offers.get("highPrice"), offers.get("price"), offers.get("lowPrice"), 0)),
            "color": _first(raw.get("color"), default=None),
            "size_options": _first(raw.get("size"), raw.get("size_options"), "[]"),
            "tags": _to_tags(raw.get("keywords")),
            "rating": rating,
            "review_count": review_count,
            "stock": stock,
            "image": _first(raw.get("image"), default=None),
            "is_active": 1,
        },
        fallback_category="Products",
        source_url=source_url,
    )


def _derive_category_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    for part in reversed(parts):
        lowered = part.lower()
        if lowered not in {"product", "products", "item", "items", "shop", "category", "categories"}:
            return part.replace("-", " ").replace("_", " ").title()
    return "Products"


def _build_candidates_from_html(url: str, html_text: str) -> list[dict[str, Any]]:
    parser = _HtmlHarvest()
    parser.feed(html_text)

    all_products = []
    all_products.extend(_extract_jsonld_products(html_text, url))
    all_products.extend(_extract_nextjs_flight_products(html_text, url))

    category_hint = _derive_category_from_url(url)
    for block in parser.blocks:
        text = _clean_text(block)
        if len(text) < 45:
            continue
        lowered = text.lower()
        has_price_signal = _parse_price(text) > 0
        has_shop_signal = any(token in lowered for token in ("add to cart", "buy", "price", "₹", "rs", "inr", "$"))
        if not has_price_signal and not has_shop_signal:
            continue

        row = _normalize_product_row(
            {
                "name": text.split(".")[0][:90],
                "description": text,
                "category": category_hint,
                "price": _parse_price(text),
            },
            fallback_category=category_hint,
            source_url=url,
        )
        if row:
            all_products.append(row)

    unique: dict[int, dict[str, Any]] = {}
    for item in all_products:
        if isinstance(item, dict):
            unique[int(item["id"])] = item

    return _dedupe_products(list(unique.values()))


def _candidate_score(product: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        1 if float(product.get("price") or 0.0) > 0 else 0,
        1 if _is_present(product.get("image_url")) else 0,
        1 if _clean_text(product.get("brand")) not in {"", "Unknown Brand"} else 0,
        1 if _clean_text(product.get("category")) not in {"", "Products", "Uncategorized"} else 0,
        len(_clean_text(product.get("description"))),
    )


def _merge_product_candidates(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    preferred = incoming if _candidate_score(incoming) > _candidate_score(existing) else existing
    other = existing if preferred is incoming else incoming
    merged = dict(preferred)

    if float(merged.get("price") or 0.0) <= 0 and float(other.get("price") or 0.0) > 0:
        merged["price"] = other["price"]
        merged["original_price"] = other.get("original_price", other["price"])
    if not _is_present(merged.get("image_url")) and _is_present(other.get("image_url")):
        merged["image_url"] = other["image_url"]
    if _clean_text(merged.get("brand")) in {"", "Unknown Brand"} and _clean_text(other.get("brand")) not in {"", "Unknown Brand"}:
        merged["brand"] = other["brand"]
    if _clean_text(merged.get("category")) in {"", "Products", "Uncategorized"} and _clean_text(other.get("category")) not in {"", "Products", "Uncategorized"}:
        merged["category"] = other["category"]
    if len(_clean_text(other.get("description"))) > len(_clean_text(merged.get("description"))):
        merged["description"] = other["description"]

    preferred_name = _clean_text(merged.get("name"))
    other_name = _clean_text(other.get("name"))
    if _normalized_candidate_name(other_name) == _normalized_candidate_name(preferred_name) and len(other_name) < len(preferred_name):
        merged["name"] = other_name

    return merged


def _dedupe_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_name: dict[str, dict[str, Any]] = {}
    for item in products:
        if _looks_like_noise_name(str(item.get("name") or "")):
            continue
        normalized_name = _normalized_candidate_name(str(item.get("name") or ""))
        if not normalized_name:
            merged_by_name[str(item["id"])] = item
            continue
        existing = merged_by_name.get(normalized_name)
        merged_by_name[normalized_name] = _merge_product_candidates(existing, item) if existing else item
    return list(merged_by_name.values())


def _ensure_category(conn, category_name: str, site_id: str) -> int:
    safe_name = _clean_text(category_name) or "Products"
    slug = re.sub(r"[^a-z0-9]+", "-", safe_name.lower()).strip("-") or "products"

    existing = conn.execute(
        "SELECT id FROM categories WHERE name = %s OR slug = %s",
        (safe_name, slug),
    ).fetchone()
    if existing:
        return existing["id"]

    category_id = _stable_id(site_id, safe_name, slug)
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


def _vectorize(site_id: str) -> int:
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
    return len(rows)


def _persist_catalog(
    site_id: str,
    products: list[dict[str, Any]],
    reconcile_missing: bool,
    source_name: str,
) -> int:
    init_tenant_schema(site_id)

    incoming_ids: list[int] = []
    incoming_source_ids: list[str] = []
    changed = 0
    deactivated = 0
    with get_db(site_id) as conn:
        for product in products:
            product_id = int(product["id"])
            incoming_ids.append(product_id)
            source_product_id = str(product_id)
            incoming_source_ids.append(source_product_id)
            category_id = _ensure_category(conn, _first(product.get("category"), "Products"), site_id)
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
                    _first(product.get("category"), "Products"),
                    float(product["price"]),
                    int(product.get("stock", 0)),
                    product.get("image_url"),
                    json.dumps(product, ensure_ascii=False),
                    int(product.get("is_active", 1)),
                ),
            )
            row = conn.execute(
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
            if row:
                changed += 1

        if reconcile_missing and incoming_ids:
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
                """,
                (incoming_ids,),
            )
            deactivated = result.rowcount

    vectorized = _vectorize(site_id)
    with get_db(site_id) as conn:
        conn.execute(
            """
            INSERT INTO catalog_sync_runs
              (source_name, source_count, changed_count, deactivated_count, vectorized_count)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (source_name, len(incoming_ids), changed, deactivated, vectorized),
        )
    logger.info(
        "Catalog sync for %s/%s: source=%s changed=%s deactivated=%s vectorized=%s",
        site_id,
        source_name,
        len(incoming_ids),
        changed,
        deactivated,
        vectorized,
    )
    print(
        f"Catalog sync ({source_name}): {len(incoming_ids)} source products, "
        f"{changed} changed/new, {deactivated} deactivated, {vectorized} vectorized"
    )
    return changed

async def async_web_crawl(
    start_url: str,
    *,
    max_pages: int = 60,
    max_depth: int = 3,
    site_id: str | None = None,
    reconcile_missing: bool = True,
    source_name: str = "custom_url_crawler",
    timeout: int = 12,
) -> str:
    from crawl4ai import AsyncWebCrawler
    if not start_url:
        raise ValueError("Start URL is required.")
    if max_pages <= 0 or max_depth < 0:
        raise ValueError("max_pages and max_depth must be positive.")

    resolved_site_id = sanitize_site_id(site_id or start_url)
    seed = urldefrag(start_url)[0]
    parsed_seed = urlparse(seed)
    if not parsed_seed.netloc:
        raise ValueError("Start URL must include a host.")

    allowed_host = parsed_seed.netloc.lower()
    allowed_scheme = parsed_seed.scheme or "https"

    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    visited: set[str] = set()
    extracted_products: list[dict[str, Any]] = []
    pages_seen = 0
    product_links: set[str] = set()
    stopped_by_limit = False

    async with AsyncWebCrawler(verbose=False) as crawler:
        while queue and len(visited) < max_pages:
            page_url, depth = queue.popleft()
            page_url = urldefrag(page_url)[0]
            if page_url in visited:
                continue
            visited.add(page_url)

            result = await crawler.arun(url=page_url)
            if not result.success:
                continue

            text = result.html
            if not text:
                continue

            parser = _HtmlHarvest()
            parser.feed(text)
            pages_seen += 1

            for link in parser.links:
                next_url = urldefrag(urljoin(page_url, link))[0]
                parsed = urlparse(next_url)
                if not parsed.netloc:
                    continue
                if parsed.scheme != allowed_scheme or parsed.netloc.lower() != allowed_host:
                    continue
                if next_url in visited or depth >= max_depth:
                    continue
                if "/admin" in next_url.lower():
                    continue
                if next_url.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js", ".pdf", ".xml")):
                    continue
                queue.append((next_url, depth + 1))

            candidates = _build_candidates_from_html(page_url, text)
            for link in parser.links:
                if link and "/product/" in link.lower():
                    product_links.add(urldefrag(urljoin(page_url, link))[0])
            extracted_products.extend(candidates)

        if len(visited) >= max_pages:
            stopped_by_limit = True

    if not extracted_products:
        logger.warning("Crawler did not extract any product-like records.")

    deduped_products = _dedupe_products(extracted_products)
    print(f"Crawler summary: visited {pages_seen} pages, extracted {len(extracted_products)} raw candidates, deduped to {len(deduped_products)}.")

    import json
    from pathlib import Path
    crawl_json_path = Path(__file__).resolve().parent.parent / "crawl.json"
    with open(crawl_json_path, "w", encoding="utf-8") as f:
        json.dump(deduped_products, f, indent=2, ensure_ascii=False)

    import asyncio
    await asyncio.to_thread(
        _persist_catalog,
        resolved_site_id,
        deduped_products,
        reconcile_missing=reconcile_missing,
        source_name=source_name,
    )
    return resolved_site_id

def sync_web_crawl(*args, **kwargs) -> str:
    import asyncio
    return asyncio.run(async_web_crawl(*args, **kwargs))
