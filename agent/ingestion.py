"""
Catalog ingestion utilities for crawler-based sources.

Each source is normalized into tenant-specific PostgreSQL tables and then vectorized
for RAG.
"""

from __future__ import annotations

import hashlib
import gzip
import html
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from time import monotonic
from typing import Any
from urllib.parse import parse_qsl, urlencode, urldefrag, urljoin, urlparse, urlunparse

import httpx

from agent.local_urls import local_runtime_url_candidates
from agent.rag import _embed, _product_to_text
from agent.verticals.discovery_profiles import (
    discovery_paths_for,
    get_discovery_profile,
    high_value_url_keywords_for,
    knowledge_entity_type_for,
)
from agent.verticals.registry import DEFAULT_VERTICAL_KEY
from db.database import get_db, init_tenant_schema, upsert_variants

logger = logging.getLogger(__name__)


def _safe_console_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_message = str(message).encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_message)

PRICE_RE = re.compile(r"(?:₹|rs\.?|inr|\$)\s*([0-9]+(?:[.,][0-9]{1,2})?)", re.IGNORECASE)
SPACES_RE = re.compile(r"\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", flags=re.IGNORECASE | re.DOTALL)
NEXT_FLIGHT_SCRIPT_RE = re.compile(
    r"self\.__next_f\.push\(\[\s*1,\s*(\"(?:\\.|[^\"\\])+\")\s*\]\)",
    flags=re.IGNORECASE | re.DOTALL,
)
NEXT_DATA_SCRIPT_RE = re.compile(
    r"<script[^>]*id=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>",
    flags=re.IGNORECASE | re.DOTALL,
)
CATALOG_ENDPOINT_PATHS = (
    "/api/products",
    "/api/policies",
    "/api/products.json",
    "/products.json",
    "/collections/all/products.json",
    "/wp-json/wc/store/products?per_page=100",
    "/wp-json/wc/store/v1/products?per_page=100",
)
SHOPIFY_CATALOG_PAGE_LIMIT = 250
SHOPIFY_CATALOG_MAX_PAGES = 20
WOO_CATALOG_MAX_PAGES = 20
GENERIC_API_CATALOG_PAGE_SIZE = 96
GENERIC_API_CATALOG_MAX_PAGES = 100
PRODUCT_URL_KEYWORDS = (
    "/product/",
    "/products/",
    "/item/",
    "/items/",
    "/p/",
    "product_id=",
    "variant=",
    "sku=",
)
LOW_VALUE_URL_KEYWORDS = (
    "/blog",
    "/news",
    "/about",
    "/contact",
    "/privacy",
    "/terms",
    "/support",
    "/faq",
)
SKIP_PATH_MARKERS = (
    "/admin",
    "/wp-admin",
    "/account",
    "/login",
    "/logout",
    "/register",
    "/checkout",
    "/cart",
    "/wishlist",
    "/auth",
)
SKIP_URL_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".pdf",
    ".zip",
    ".mp4",
    ".mp3",
    ".woff",
    ".woff2",
    ".ttf",
    ".xml",
)


@dataclass
class CrawlReport:
    site_id: str
    site_url: str
    source_type: str
    pages_visited: int
    pages_failed: int
    pages_blocked: int
    product_count: int
    variant_count: int
    category_count: int
    failed_urls: list[str] = field(default_factory=list)
    blocked_urls: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    duration_ms: float = 0.0
    stopped_by_limit: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["coverage_score"] = round(float(self.coverage_score), 2)
        data["duration_ms"] = round(float(self.duration_ms), 1)
        return data


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


def _strip_html(raw: Any) -> str:
    return _clean_text(HTML_TAG_RE.sub(" ", str(raw or "")))


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


def _to_positive_int_id(value: Any) -> int | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"\d+", text):
        return None
    parsed = int(text)
    return parsed if parsed > 0 else None


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
        except UnicodeDecodeError as exc:
            logger.debug("Embedded JSON unicode escape decode failed: %s", exc)

    for attempt in attempts:
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
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
            decoded = decoded.split(":", 1)[1]
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


def _image_url_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = _clean_text(value)
        return text or None
    if isinstance(value, dict):
        return _image_url_from_value(
            _first(
                value.get("src"),
                value.get("url"),
                value.get("image"),
                value.get("image_url"),
                value.get("thumbnail"),
                value.get("originalSrc"),
                default=None,
            )
        )
    if isinstance(value, list):
        for item in value:
            result = _image_url_from_value(item)
            if result:
                return result
    return None


def _term_names(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return _to_tags(value)
    if isinstance(value, dict):
        name = _first(value.get("name"), value.get("title"), value.get("slug"), default=None)
        return [_clean_text(name)] if name else []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            for name in _term_names(item):
                if name and name not in names:
                    names.append(name)
        return names
    return [_clean_text(value)]


def _looks_like_shopify_product(raw: dict[str, Any]) -> bool:
    return isinstance(raw.get("variants"), list) and (
        "handle" in raw or "body_html" in raw or "product_type" in raw or "vendor" in raw
    )


def _normalize_shopify_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    variants = raw.get("variants") if isinstance(raw.get("variants"), list) else []
    selected_variant = {}
    for variant in variants:
        if isinstance(variant, dict) and variant.get("available") is not False:
            selected_variant = variant
            break
    if not selected_variant and variants and isinstance(variants[0], dict):
        selected_variant = variants[0]

    image = _image_url_from_value(_first(raw.get("image"), raw.get("images"), raw.get("featured_image"), default=None))
    available = _first(selected_variant.get("available"), raw.get("available"), default=True)
    stock = _first(selected_variant.get("inventory_quantity"), raw.get("stock"), default=None)
    if stock in (None, ""):
        stock = 100 if available is not False else 0

    variant_id = selected_variant.get("id")
    variant_id = _to_positive_int_id(variant_id)

    return _normalize_product_row(
        {
            "id": _first(raw.get("id"), raw.get("handle"), raw.get("sku"), default=None),
            "variant_id": variant_id,
            "name": _first(raw.get("title"), raw.get("name"), raw.get("handle")),
            "description": _first(_strip_html(raw.get("body_html")), raw.get("description"), raw.get("title")),
            "category": _first(raw.get("product_type"), raw.get("category"), "Products"),
            "brand": _first(raw.get("vendor"), raw.get("brand"), "Unknown Brand"),
            "price": _first(selected_variant.get("price"), raw.get("price"), 0),
            "original_price": _first(
                selected_variant.get("compare_at_price"),
                raw.get("compare_at_price"),
                selected_variant.get("price"),
                raw.get("price"),
                0,
            ),
            "image": image,
            "stock": stock,
            "tags": _to_tags(raw.get("tags")),
            "is_active": 1 if available is not False and int(_to_float(stock)) > 0 else 0,
        },
        fallback_category=_clean_text(_first(raw.get("product_type"), "Products")),
        source_url=api_url,
    )


def _woocommerce_price(raw_prices: Any, *keys: str) -> float:
    if not isinstance(raw_prices, dict):
        return 0.0
    minor_units = int(_to_float(raw_prices.get("currency_minor_unit") or 0))
    for key in keys:
        value = raw_prices.get(key)
        if value in (None, ""):
            continue
        amount = _to_float(value)
        if minor_units > 0 and isinstance(value, str) and value.isdigit():
            amount = amount / (10**minor_units)
        if amount > 0:
            return amount
    return 0.0


def _looks_like_woocommerce_product(raw: dict[str, Any]) -> bool:
    return isinstance(raw.get("prices"), dict) or "is_in_stock" in raw or "stock_status" in raw


def _normalize_woocommerce_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    prices = raw.get("prices") if isinstance(raw.get("prices"), dict) else {}
    category_names = _term_names(raw.get("categories"))
    tag_names = _term_names(raw.get("tags"))
    in_stock = _first(raw.get("is_in_stock"), raw.get("in_stock"), default=True)
    stock = _first(raw.get("stock_quantity"), raw.get("stock"), default=None)
    if stock in (None, ""):
        stock = 100 if in_stock is not False else 0

    price = _woocommerce_price(prices, "price", "sale_price", "regular_price")
    if price <= 0:
        price = _first(raw.get("price"), raw.get("sale_price"), raw.get("regular_price"), 0)

    regular_price = _woocommerce_price(prices, "regular_price", "price")
    if regular_price <= 0:
        regular_price = _first(raw.get("regular_price"), price)

    return _normalize_product_row(
        {
            "id": _first(raw.get("id"), raw.get("sku"), raw.get("slug"), default=None),
            "name": _first(raw.get("name"), raw.get("title"), raw.get("slug")),
            "description": _first(_strip_html(raw.get("description")), _strip_html(raw.get("short_description")), raw.get("name")),
            "category": _first(category_names[0] if category_names else None, raw.get("category"), "Products"),
            "brand": _first(raw.get("brand"), raw.get("vendor"), "Unknown Brand"),
            "price": price,
            "original_price": regular_price,
            "image": _image_url_from_value(raw.get("images")),
            "stock": stock,
            "tags": tag_names,
            "rating": raw.get("average_rating"),
            "review_count": raw.get("review_count"),
            "is_active": 1 if in_stock is not False and int(_to_float(stock)) > 0 else 0,
        },
        fallback_category=_clean_text(_first(category_names[0] if category_names else None, "Products")),
        source_url=api_url,
    )


def _extract_platform_variants(
    raw: dict[str, Any],
    product: dict[str, Any],
    source_url: str,
) -> list[dict[str, Any]]:
    """Extract variants with platform adapters while keeping ingestion deterministic."""
    try:
        product_id = int(product["id"])
        if _looks_like_shopify_product(raw):
            from agent.adapters.shopify import ShopifyAdapter

            return ShopifyAdapter().extract_variants(raw, product_id, source_url)
        if _looks_like_woocommerce_product(raw):
            from agent.adapters.woocommerce import WooCommerceAdapter

            return WooCommerceAdapter().extract_variants(raw, product_id, source_url)
    except (ImportError, TypeError, ValueError, KeyError) as exc:
        logger.info("Variant extraction skipped for %s: %s", source_url, exc)
    return []


def _normalize_with_platform_adapter(
    raw: dict[str, Any],
    source_url: str,
) -> dict[str, Any] | None:
    """Normalize known platform products through their adapter modules."""
    try:
        if _looks_like_shopify_product(raw):
            from agent.adapters.shopify import ShopifyAdapter

            return ShopifyAdapter().normalize_product(raw, source_url)
        if _looks_like_woocommerce_product(raw):
            from agent.adapters.woocommerce import WooCommerceAdapter

            return WooCommerceAdapter().normalize_product(raw, source_url)
    except (ImportError, TypeError, ValueError, KeyError) as exc:
        logger.info("Platform normalization skipped for %s: %s", source_url, exc)
    return None


def _with_platform_variants(
    raw: dict[str, Any],
    product: dict[str, Any] | None,
    source_url: str,
) -> dict[str, Any] | None:
    """Attach variant rows to a normalized product when source data has them."""
    if not product:
        return None
    variants = _extract_platform_variants(raw, product, source_url)
    if variants:
        product = dict(product)
        product["variants"] = variants
    return product


def _normalize_embedded_json_product(raw: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    if _looks_like_shopify_product(raw):
        return _with_platform_variants(raw, _normalize_with_platform_adapter(raw, source_url), source_url)
    if _looks_like_woocommerce_product(raw):
        return _with_platform_variants(raw, _normalize_with_platform_adapter(raw, source_url), source_url)

    name = _clean_text(_first(raw.get("name"), raw.get("title"), raw.get("product_name"), default=""))
    if not name or len(name) > 180:
        return None

    offers = raw.get("offers")
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if not isinstance(offers, dict):
        offers = {}

    prices = raw.get("prices") if isinstance(raw.get("prices"), dict) else {}
    image = _image_url_from_value(
        _first(
            raw.get("image"),
            raw.get("images"),
            raw.get("image_url"),
            raw.get("thumbnail"),
            raw.get("featured_image"),
            default=None,
        )
    )
    url_value = _first(raw.get("url"), raw.get("href"), raw.get("permalink"), raw.get("product_url"), default=None)
    absolute_url = urljoin(source_url, str(url_value)) if url_value else source_url
    price = _first(
        raw.get("price"),
        raw.get("amount"),
        raw.get("sale_price"),
        raw.get("regular_price"),
        raw.get("min_price"),
        offers.get("price"),
        prices.get("price"),
        prices.get("sale_price"),
        default=0,
    )

    signal_score = 0
    if _to_float(price) > 0:
        signal_score += 2
    if image:
        signal_score += 1
    if any(raw.get(key) not in (None, "") for key in ("id", "product_id", "sku", "handle", "_id")):
        signal_score += 1
    if url_value and any(token in str(url_value).lower() for token in high_value_url_keywords_for("ecommerce")):
        signal_score += 1
    if any(key in raw for key in ("variants", "offers", "prices", "inventory", "stock", "stock_quantity")):
        signal_score += 1
    if any(raw.get(key) not in (None, "") for key in ("brand", "vendor", "category", "categories")):
        signal_score += 1
    if signal_score < 2:
        return None

    categories = _term_names(raw.get("categories"))
    tags = _term_names(raw.get("tags"))
    in_stock = _first(raw.get("in_stock"), raw.get("is_in_stock"), raw.get("available"), default=True)
    stock = _first(raw.get("stock"), raw.get("quantity"), raw.get("stock_quantity"), default=None)
    if stock in (None, ""):
        stock = 100 if in_stock is not False else 0

    return _normalize_product_row(
        {
            "id": _first(raw.get("id"), raw.get("product_id"), raw.get("_id"), raw.get("sku"), raw.get("handle"), default=None),
            "name": name,
            "description": _first(
                _strip_html(raw.get("description")),
                _strip_html(raw.get("summary")),
                _strip_html(raw.get("short_description")),
                name,
            ),
            "category": _first(raw.get("category"), categories[0] if categories else None, "Products"),
            "brand": _first(raw.get("brand"), raw.get("vendor"), raw.get("maker"), "Unknown Brand"),
            "price": price,
            "original_price": _first(raw.get("original_price"), raw.get("regular_price"), raw.get("compare_at_price"), price),
            "image": image,
            "stock": stock,
            "tags": tags,
            "rating": _first(raw.get("rating"), raw.get("average_rating"), default=0),
            "review_count": _first(raw.get("review_count"), raw.get("reviewCount"), default=0),
            "is_active": 1 if in_stock is not False and int(_to_float(stock)) > 0 else 0,
        },
        fallback_category=_derive_category_from_url(absolute_url),
        source_url=absolute_url,
    )


def _extract_products_from_json_tree(payload: Any, source_url: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    stack: list[Any] = [payload]
    nodes_seen = 0

    while stack and nodes_seen < 5000:
        item = stack.pop()
        nodes_seen += 1

        if isinstance(item, dict):
            product = _normalize_embedded_json_product(item, source_url)
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

    return results


def _iter_script_json_payloads(script_text: str) -> list[Any]:
    text = html.unescape(script_text or "").strip()
    if not text or len(text) > 2_000_000:
        return []

    decoder = json.JSONDecoder()
    payloads: list[Any] = []

    if text[0] in "[{":
        try:
            payload, _ = decoder.raw_decode(text)
            payloads.append(payload)
        except json.JSONDecodeError as exc:
            logger.debug("Embedded JSON raw decode failed: %s", exc)

    for match in re.finditer(r"=\s*([\{\[])", text):
        if len(payloads) >= 25:
            break
        start = match.start(1)
        try:
            payload, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        payloads.append(payload)

    return payloads


def _extract_embedded_json_products(html_text: str, source_url: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for match in SCRIPT_TAG_RE.finditer(html_text):
        for payload in _iter_script_json_payloads(match.group(1)):
            products.extend(_extract_products_from_json_tree(payload, source_url))
    return _dedupe_products(products)


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
            product_id = _stable_id(source_url, str(raw_id))

    variant_id = _to_positive_int_id(row.get("variant_id"))
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


def _normalize_api_catalog_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    """Normalize the storefront's JSON catalog product shape for RAG ingestion."""
    if _looks_like_insurance_policy_api(raw):
        return _normalize_policy_catalog_product(raw, api_url)

    categories = raw.get("categories") if isinstance(raw.get("categories"), list) else []
    category = _first(raw.get("category"), categories[0] if categories else None, "Products")
    stock = raw.get("stock")
    in_stock = raw.get("in_stock")
    if stock in (None, ""):
        stock = 100 if in_stock is not False else 0

    tags = list(categories)
    for tag in _to_tags(raw.get("tags")):
        if tag not in tags:
            tags.append(tag)

    return _normalize_product_row(
        {
            "id": _first(raw.get("rag_id"), raw.get("id"), raw.get("handle"), raw.get("sku")),
            "name": _first(raw.get("name"), raw.get("title"), raw.get("handle")),
            "description": _first(raw.get("description"), raw.get("summary"), raw.get("name"), raw.get("title")),
            "category": category,
            "brand": _first(raw.get("brand"), raw.get("vendor"), "Unknown Brand"),
            "price": _first(raw.get("price"), raw.get("amount"), raw.get("cost"), 0),
            "original_price": _first(raw.get("original_price"), raw.get("compare_at_price"), raw.get("price"), 0),
            "image": _first(raw.get("image_url"), raw.get("image"), raw.get("thumbnail")),
            "stock": stock,
            "tags": tags,
            "is_active": 1 if in_stock is not False and int(_to_float(stock)) > 0 else 0,
        },
        fallback_category=_clean_text(category) or "Products",
        source_url=api_url,
    )


def _looks_like_insurance_policy_api(raw: dict[str, Any]) -> bool:
    return any(
        key in raw
        for key in (
            "premium_monthly",
            "premium_annual",
            "sum_insured",
            "insurer",
            "claim_process",
            "waiting_period",
        )
    )


def _normalize_policy_catalog_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    category_id = _clean_text(raw.get("category_id"))
    category = _insurance_category_label(category_id)
    monthly_premium = _to_float(raw.get("premium_monthly"))
    annual_premium = _to_float(raw.get("premium_annual"))
    price = monthly_premium or annual_premium
    tags = _policy_catalog_tags(raw, category)
    normalized = _normalize_product_row(
        {
            "id": _first(raw.get("id"), raw.get("policy_id")),
            "name": _first(raw.get("name"), raw.get("title")),
            "description": _policy_catalog_description(raw, category),
            "category": category,
            "brand": _first(raw.get("insurer"), raw.get("brand"), "Insurance Provider"),
            "price": price,
            "original_price": annual_premium or price,
            "stock": 100,
            "tags": tags,
            "rating": raw.get("rating"),
            "review_count": raw.get("review_count"),
            "is_active": 1,
        },
        fallback_category=category or "Insurance Plans",
        source_url=api_url,
    )
    if not normalized:
        return None
    normalized["policy_json"] = _policy_catalog_policy_payload(raw, category)
    normalized["risk_tags"] = _policy_catalog_risk_tags(raw, category)
    normalized["pricing_json"] = {
        "premium_monthly": monthly_premium,
        "premium_annual": annual_premium,
        "currency": "INR",
    }
    return normalized


def _insurance_category_label(category_id: str) -> str:
    labels = {
        "health": "Health Insurance",
        "life": "Life Insurance",
        "motor": "Motor Insurance",
        "travel": "Travel Insurance",
        "home": "Home Insurance",
        "business": "Business Insurance",
    }
    return labels.get(category_id.lower(), "Insurance Plans")


def _policy_catalog_description(raw: dict[str, Any], category: str) -> str:
    features = _to_tags(raw.get("features"))
    parts = [
        _clean_text(raw.get("name")),
        category,
        _clean_text(raw.get("type")),
        _clean_text(raw.get("insurer")),
        f"monthly premium INR {_to_float(raw.get('premium_monthly')):g}" if _to_float(raw.get("premium_monthly")) else "",
        f"annual premium INR {_to_float(raw.get('premium_annual')):g}" if _to_float(raw.get("premium_annual")) else "",
        f"sum insured INR {_to_float(raw.get('sum_insured')):g}" if _to_float(raw.get("sum_insured")) else "",
        f"age {_clean_text(raw.get('age_min'))} to {_clean_text(raw.get('age_max'))}" if raw.get("age_min") or raw.get("age_max") else "",
        f"waiting period {_clean_text(raw.get('waiting_period'))}" if raw.get("waiting_period") else "",
        f"claim process {_clean_text(raw.get('claim_process'))}" if raw.get("claim_process") else "",
        f"renewability {_clean_text(raw.get('renewability'))}" if raw.get("renewability") else "",
        f"tax benefit {_clean_text(raw.get('tax_benefit'))}" if raw.get("tax_benefit") else "",
        "Features: " + "; ".join(features[:8]) if features else "",
    ]
    return ". ".join(part for part in parts if part)


def _policy_catalog_tags(raw: dict[str, Any], category: str) -> list[str]:
    tags = [
        "insurance",
        "policy",
        "plan",
        category,
        raw.get("category_id"),
        raw.get("type"),
        raw.get("insurer"),
        "premium",
        "coverage",
        "claim",
    ]
    features = _to_tags(raw.get("features"))
    tags.extend(features[:10])
    if raw.get("age_min") or raw.get("age_max"):
        tags.append(f"age {raw.get('age_min') or ''} {raw.get('age_max') or ''}".strip())
    return [str(tag).strip() for tag in tags if str(tag or "").strip()]


def _policy_catalog_policy_payload(raw: dict[str, Any], category: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "category": category,
        "category_id": _clean_text(raw.get("category_id")),
        "policy_type": _clean_text(raw.get("type")),
        "sum_insured": _to_float(raw.get("sum_insured")),
        "age_min": _optional_int(raw.get("age_min")),
        "age_max": _optional_int(raw.get("age_max")),
        "claim_process": _clean_text(raw.get("claim_process")),
        "waiting_period": _clean_text(raw.get("waiting_period")),
        "renewability": _clean_text(raw.get("renewability")),
        "tax_benefit": _clean_text(raw.get("tax_benefit")),
    }
    return {key: value for key, value in payload.items() if value not in ("", None, 0.0)}


def _policy_catalog_risk_tags(raw: dict[str, Any], category: str) -> list[str]:
    tags = ["regulated_insurance", "insurance_plan"]
    category_text = f"{category} {_clean_text(raw.get('category_id'))}".lower()
    if "health" in category_text:
        tags.append("health_cover")
    if "life" in category_text:
        tags.append("life_cover")
    if "motor" in category_text:
        tags.append("motor_cover")
    if raw.get("claim_process"):
        tags.append("claim_process_available")
    if raw.get("waiting_period"):
        tags.append("waiting_period_applies")
    return sorted(set(tags))


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _site_base_url(seed_url: str) -> str:
    parsed = urlparse(seed_url)
    scheme = parsed.scheme or "https"
    return f"{scheme}://{parsed.netloc}"


def _catalog_endpoint_for(seed_url: str) -> str:
    return urljoin(_site_base_url(seed_url), "/api/products")


def _catalog_endpoints_for(seed_url: str) -> list[str]:
    base = _site_base_url(seed_url)
    urls = [urljoin(base, path) for path in CATALOG_ENDPOINT_PATHS]
    return list(dict.fromkeys(urls))


def _catalog_seed_candidates(seed_url: str) -> list[str]:
    return local_runtime_url_candidates(seed_url) or [seed_url]


def _normalize_catalog_payload(payload: Any, api_url: str, *, merge_same_name: bool = True) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        raw_products = _first(
            payload.get("products"),
            payload.get("data"),
            payload.get("items"),
            payload.get("results"),
            default=None,
        )
    else:
        raw_products = payload

    if not isinstance(raw_products, list):
        return _dedupe_products(_extract_products_from_json_tree(payload, api_url), merge_same_name=merge_same_name)

    products = []
    for raw in raw_products:
        if not isinstance(raw, dict):
            continue
        if _looks_like_shopify_product(raw):
            normalized = _with_platform_variants(
                raw,
                _normalize_with_platform_adapter(raw, api_url),
                api_url,
            )
        elif _looks_like_woocommerce_product(raw):
            normalized = _with_platform_variants(
                raw,
                _normalize_with_platform_adapter(raw, api_url),
                api_url,
            )
        else:
            normalized = _normalize_api_catalog_product(raw, api_url)
        if normalized:
            products.append(normalized)

    return _dedupe_products(products, merge_same_name=merge_same_name)


async def _fetch_api_catalog_products(seed_url: str, timeout: int) -> list[dict[str, Any]]:
    """Fetch common public commerce catalog endpoints before rendering HTML."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        for candidate_seed_url in _catalog_seed_candidates(seed_url):
            for api_url in _catalog_endpoints_for(candidate_seed_url):
                deduped = await _fetch_catalog_endpoint_pages(client, api_url)
                if deduped:
                    logger.info("API catalog at %s returned %d products.", api_url, len(deduped))
                    return deduped
                logger.warning("API catalog at %s did not contain a usable product list.", api_url)

    return []


async def _fetch_catalog_endpoint_pages(
    client: httpx.AsyncClient,
    api_url: str,
) -> list[dict[str, Any]]:
    """Fetch one catalog endpoint, including standard Shopify/Woo pagination."""
    products: list[dict[str, Any]] = []
    seen_product_ids: set[int] = set()
    page_urls = _catalog_page_urls(api_url)
    for page_url in page_urls:
        try:
            response = await client.get(page_url, headers={"Accept": "application/json"})
            if response.status_code in {401, 403, 404, 405}:
                break
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.info("No API catalog available at %s: %s", page_url, exc)
            break

        page_products = _normalize_catalog_payload(
            payload,
            _catalog_normalization_url(api_url, page_url),
            merge_same_name=False,
        )
        if not page_products:
            break
        new_products = []
        for product in page_products:
            product_id = int(product["id"])
            if product_id in seen_product_ids:
                continue
            new_products.append(product)
            seen_product_ids.add(product_id)
        if not new_products and products:
            break
        products.extend(new_products)

        if len(page_urls) == 1:
            break
        if _catalog_response_reached_last_page(payload):
            break

    return _dedupe_products(products, merge_same_name=False)


def _catalog_page_urls(api_url: str) -> list[str]:
    if "/collections/all/products.json" in api_url or api_url.endswith("/products.json"):
        separator = "&" if "?" in api_url else "?"
        return [
            f"{api_url}{separator}limit={SHOPIFY_CATALOG_PAGE_LIMIT}&page={page}"
            for page in range(1, SHOPIFY_CATALOG_MAX_PAGES + 1)
        ]
    if "/wp-json/wc/store" in api_url and "/products" in api_url:
        separator = "&" if "?" in api_url else "?"
        return [
            f"{api_url}{separator}page={page}"
            for page in range(1, WOO_CATALOG_MAX_PAGES + 1)
        ]
    if _is_generic_products_api(api_url):
        return [
            _catalog_url_with_params(
                api_url,
                {
                    "page": page,
                    "per_page": GENERIC_API_CATALOG_PAGE_SIZE,
                },
            )
            for page in range(1, GENERIC_API_CATALOG_MAX_PAGES + 1)
        ]
    return [api_url]


def _is_generic_products_api(api_url: str) -> bool:
    parsed = urlparse(api_url)
    return parsed.path.rstrip("/") == "/api/products"


def _catalog_url_with_params(api_url: str, params: dict[str, int]) -> str:
    parsed = urlparse(api_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({key: str(value) for key, value in params.items()})
    return urlunparse(parsed._replace(query=urlencode(query)))


def _catalog_response_reached_last_page(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else payload
    page = _to_positive_int_id(meta.get("page"))
    total_pages = _to_positive_int_id(meta.get("total_pages"))
    return bool(page and total_pages and page >= total_pages)


def _catalog_normalization_url(api_url: str, page_url: str) -> str:
    if _is_generic_products_api(api_url):
        return api_url
    return page_url


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


def _extract_jsonld_products(html_text: str, source_url: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[dict[str, Any]]:
    profile = get_discovery_profile(vertical_key)
    profile_types = {item.lower() for item in profile.jsonld_types}
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
            item_types = _jsonld_type_texts(item.get("@type"))
            if "product" in item_types and profile.key == "ecommerce":
                row = _normalize_jsonld_item(item, source_url)
                if row:
                    results.append(row)
            elif item_types & profile_types:
                row = _normalize_generic_jsonld_item(item, source_url, vertical_key=profile.key)
                if row:
                    results.append(row)

            graph = item.get("@graph")
            if isinstance(graph, list):
                queue.extend(graph)
            elif isinstance(graph, dict):
                queue.append(graph)
    return results


def _jsonld_type_text(value: Any) -> str:
    if isinstance(value, list):
        return _clean_text(_first(*value, default=""))
    return _clean_text(value)


def _jsonld_type_texts(value: Any) -> set[str]:
    if isinstance(value, list):
        values = value
    else:
        values = [value]
    result: set[str] = set()
    for item in values:
        text = _clean_text(item)
        if not text:
            continue
        result.add(text)
        result.add(text.rsplit("/", 1)[-1])
    return {item.lower() for item in result if item}


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


def _normalize_generic_jsonld_item(
    raw: dict[str, Any],
    source_url: str,
    *,
    vertical_key: str,
) -> dict[str, Any] | None:
    profile = get_discovery_profile(vertical_key)
    name = _clean_text(_first(raw.get("name"), raw.get("headline"), raw.get("serviceType"), raw.get("title"), default=""))
    if not name:
        return None

    description = _clean_text(_first(raw.get("description"), raw.get("summary"), default=name))
    provider = raw.get("provider") or raw.get("brand") or raw.get("seller") or raw.get("organizer")
    if isinstance(provider, dict):
        provider = provider.get("name")

    offers = raw.get("offers") or {}
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if not isinstance(offers, dict):
        offers = {}

    tags = _to_tags(_first(raw.get("keywords"), raw.get("areaServed"), raw.get("serviceType"), raw.get("@type"), default=[]))
    for tag in profile.text_signals[:4]:
        if tag not in tags:
            tags.append(tag)

    return _normalize_product_row(
        {
            "id": _first(raw.get("identifier"), raw.get("sku"), _stable_id(source_url, name, description)),
            "name": name,
            "brand": _first(provider, profile.provider_label),
            "category": _first(raw.get("category"), profile.category_label),
            "description": description,
            "price": _first(offers.get("price"), offers.get("lowPrice"), 0),
            "original_price": _first(offers.get("highPrice"), offers.get("price"), 0),
            "image": _first(raw.get("image"), default=None),
            "tags": tags,
            "stock": 100,
            "is_active": 1,
        },
        fallback_category=profile.category_label or "Knowledge",
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


def _build_candidates_from_html(url: str, html_text: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[dict[str, Any]]:
    profile = get_discovery_profile(vertical_key)
    parser = _HtmlHarvest()
    parser.feed(html_text)

    all_products = []
    all_products.extend(_extract_jsonld_products(html_text, url, vertical_key=vertical_key))
    all_products.extend(_extract_nextjs_flight_products(html_text, url))
    all_products.extend(_extract_embedded_json_products(html_text, url))

    category_hint = _derive_category_from_url(url)
    for block in parser.blocks:
        text = _clean_text(block)
        if len(text) < 45:
            continue
        lowered = text.lower()
        has_price_signal = _parse_price(text) > 0
        has_shop_signal = any(token in lowered for token in ("add to cart", "buy", "price", "₹", "rs", "inr", "$"))
        has_vertical_signal = _has_vertical_signal(text, url, vertical_key=profile.key)
        if not has_price_signal and not has_shop_signal and not has_vertical_signal:
            continue

        fallback_category = profile.category_label if has_vertical_signal else category_hint
        matched_signals = _matched_vertical_signals(text, url, vertical_key=profile.key)
        row = _normalize_product_row(
            {
                "name": _candidate_title_from_block(text, vertical_key=vertical_key),
                "description": text,
                "category": fallback_category,
                "brand": profile.provider_label if has_vertical_signal else "Unknown Brand",
                "price": _parse_price(text),
                "tags": matched_signals if has_vertical_signal else [],
            },
            fallback_category=fallback_category,
            source_url=url,
        )
        if row:
            all_products.append(row)

    unique: dict[int, dict[str, Any]] = {}
    for item in all_products:
        if isinstance(item, dict):
            unique[int(item["id"])] = item

    return _dedupe_products(list(unique.values()))


def _has_vertical_signal(text: str, url: str, *, vertical_key: str) -> bool:
    if vertical_key == "ecommerce":
        return False
    matched = _matched_vertical_signals(text, url, vertical_key=vertical_key)
    return len(matched) >= 2 or any(token in url.lower() for token in high_value_url_keywords_for(vertical_key))


def _matched_vertical_signals(text: str, url: str, *, vertical_key: str) -> list[str]:
    profile = get_discovery_profile(vertical_key)
    lowered = f"{text} {url}".lower()
    return [token for token in profile.text_signals if token in lowered]


def _candidate_title_from_block(text: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> str:
    clean = _clean_text(text)
    if vertical_key == "ecommerce":
        return clean.split(".")[0][:90]

    for separator in (".", ":", "|", "-", ","):
        first = clean.split(separator)[0].strip()
        if 8 <= len(first) <= 90:
            return first
    words = clean.split()
    return " ".join(words[:10])[:90]


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
    if not merged.get("variants") and other.get("variants"):
        merged["variants"] = other["variants"]

    preferred_name = _clean_text(merged.get("name"))
    other_name = _clean_text(other.get("name"))
    if _normalized_candidate_name(other_name) == _normalized_candidate_name(preferred_name) and len(other_name) < len(preferred_name):
        merged["name"] = other_name

    return merged


def _dedupe_products(products: list[dict[str, Any]], *, merge_same_name: bool = True) -> list[dict[str, Any]]:
    if not merge_same_name:
        unique_by_id: dict[int, dict[str, Any]] = {}
        for item in products:
            if _looks_like_noise_name(str(item.get("name") or "")):
                continue
            unique_by_id[int(item["id"])] = item
        return list(unique_by_id.values())

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


def _path_has_marker(path: str, marker: str) -> bool:
    marker = marker.rstrip("/")
    return path == marker or path.startswith(f"{marker}/") or f"{marker}/" in path


def _is_allowed_crawl_url(url: str, allowed_host: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() != allowed_host:
        return False

    path = parsed.path.lower() or "/"
    if any(_path_has_marker(path, marker) for marker in SKIP_PATH_MARKERS):
        return False
    if path.endswith(SKIP_URL_EXTENSIONS):
        return False
    return True


def _url_priority(url: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> int:
    parsed = urlparse(url)
    target = f"{parsed.path.lower()}?{parsed.query.lower()}"
    score = 0
    if any(token in target for token in PRODUCT_URL_KEYWORDS):
        score += 100
    if any(token in target for token in high_value_url_keywords_for(vertical_key)):
        score += 50
    if "page=" in target or "paged=" in target:
        score += 10
    if any(token in target for token in LOW_VALUE_URL_KEYWORDS):
        score -= 40
    return score


def _ranked_unique_urls(urls: list[str], vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for url in urls:
        clean = urldefrag(url)[0]
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return sorted(unique, key=lambda item: (-_url_priority(item, vertical_key), len(urlparse(item).path), item))


def _common_discovery_urls(seed_url: str, vertical_key: str) -> list[str]:
    base = _site_base_url(seed_url)
    return [urljoin(base, path) for path in discovery_paths_for(vertical_key)]


def _extract_sitemap_locations(xml_text: str) -> list[str]:
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return []

    locations: list[str] = []
    for element in root.iter():
        if element.tag.lower().endswith("loc") and element.text:
            loc = _clean_text(element.text)
            if loc:
                locations.append(loc)
    return locations


def _extract_robots_sitemaps(robots_text: str) -> list[str]:
    urls: list[str] = []
    for line in (robots_text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("sitemap:"):
            url = _clean_text(line.split(":", 1)[1])
            if url:
                urls.append(url)
    return urls


def _decode_sitemap_response(response: httpx.Response, sitemap_url: str) -> str:
    content = response.content
    if sitemap_url.lower().endswith(".gz"):
        try:
            return gzip.decompress(content).decode(response.encoding or "utf-8", errors="replace")
        except (gzip.BadGzipFile, OSError, UnicodeDecodeError) as exc:
            logger.debug("Sitemap gzip decode failed for %s: %s", sitemap_url, exc)
            return response.text
    return response.text


async def _fetch_sitemap_tree(
    client: httpx.AsyncClient,
    sitemap_url: str,
    allowed_host: str,
    *,
    max_urls: int,
    seen_sitemaps: set[str],
    vertical_key: str,
) -> list[str]:
    sitemap_url = urldefrag(sitemap_url)[0]
    if sitemap_url in seen_sitemaps or len(seen_sitemaps) >= 25:
        return []
    seen_sitemaps.add(sitemap_url)

    try:
        response = await client.get(sitemap_url, headers={"Accept": "application/xml,text/xml,*/*"})
        if response.status_code in {401, 403, 404, 405}:
            return []
        response.raise_for_status()
    except Exception as exc:
        logger.info("Sitemap unavailable at %s: %s", sitemap_url, exc)
        return []

    locations = _extract_sitemap_locations(_decode_sitemap_response(response, sitemap_url))
    urls: list[str] = []
    for loc in locations:
        if len(urls) >= max_urls:
            break
        loc_url = urljoin(sitemap_url, loc)
        parsed = urlparse(loc_url)
        if parsed.netloc.lower() != allowed_host:
            continue
        lower_path = parsed.path.lower()
        if lower_path.endswith((".xml", ".xml.gz")) or "sitemap" in lower_path:
            nested = await _fetch_sitemap_tree(
                client,
                loc_url,
                allowed_host,
                max_urls=max_urls - len(urls),
                seen_sitemaps=seen_sitemaps,
                vertical_key=vertical_key,
            )
            urls.extend(nested)
            continue
        if _is_allowed_crawl_url(loc_url, allowed_host):
            urls.append(urldefrag(loc_url)[0])

    return urls[:max_urls]


async def _discover_sitemap_urls(seed_url: str, timeout: int, max_urls: int, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[str]:
    allowed_host = urlparse(seed_url).netloc.lower()
    base = _site_base_url(seed_url)
    sitemap_candidates = [urljoin(base, "/sitemap.xml")]

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        try:
            robots = await client.get(urljoin(base, "/robots.txt"))
            if robots.status_code < 400:
                sitemap_candidates.extend(_extract_robots_sitemaps(robots.text))
        except Exception as exc:
            logger.info("robots.txt unavailable for %s: %s", base, exc)

        urls: list[str] = []
        seen_sitemaps: set[str] = set()
        for sitemap_url in list(dict.fromkeys(sitemap_candidates)):
            if len(urls) >= max_urls:
                break
            urls.extend(
                await _fetch_sitemap_tree(
                    client,
                    sitemap_url,
                    allowed_host,
                    max_urls=max_urls - len(urls),
                    seen_sitemaps=seen_sitemaps,
                    vertical_key=vertical_key,
                )
            )

    return _ranked_unique_urls(urls, vertical_key=vertical_key)[:max_urls]


async def _discover_crawl_entrypoints(seed_url: str, timeout: int, max_urls: int, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[str]:
    allowed_host = urlparse(seed_url).netloc.lower()
    sitemap_urls = await _discover_sitemap_urls(seed_url, timeout, max_urls=max_urls, vertical_key=vertical_key)
    candidates = [seed_url]
    candidates.extend(sitemap_urls)
    candidates.extend(_common_discovery_urls(seed_url, vertical_key))
    candidates = [url for url in candidates if _is_allowed_crawl_url(url, allowed_host)]
    return _ranked_unique_urls(candidates, vertical_key=vertical_key)[:max_urls]


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
    # Also rebuild full-text search vectors alongside embeddings
    try:
        from db.database import rebuild_search_vectors
        rebuild_search_vectors(site_id)
    except Exception as exc:
        logger.warning("Ingestion | search_vector rebuild after vectorize failed: %s", exc)
    return len(rows)


def _persist_catalog(
    site_id: str,
    products: list[dict[str, Any]],
    reconcile_missing: bool,
    source_name: str,
    crawl_report: dict[str, Any] | None = None,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
) -> int:
    init_tenant_schema(site_id)

    import datetime
    start_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                changed_names.append(product["name"])
            variants = product.get("variants")
            if isinstance(variants, list) and variants:
                variant_batches.append((product_id, variants))

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
                RETURNING name
                """,
                (incoming_ids,),
            )
            deactivated_rows = result.fetchall()
            deactivated = len(deactivated_rows)
            deactivated_names = [r["name"] for r in deactivated_rows]

    variant_count = 0
    for product_id, variants in variant_batches:
        variant_count += upsert_variants(site_id, product_id, variants)

    vectorized = _vectorize(site_id)
    knowledge_vectorized = _sync_catalog_knowledge(site_id, source_name, vertical_key=vertical_key)
    if changed or deactivated or variant_count or vectorized or knowledge_vectorized:
        try:
            from db.answer_cache import bump_data_version

            bump_data_version(site_id, reason="catalog_sync")
        except Exception as exc:
            logger.warning("Answer cache invalidation skipped for %s/%s: %s", site_id, source_name, exc)
    with get_db(site_id) as conn:
        conn.execute(
            """
            INSERT INTO catalog_sync_runs
              (source_name, source_count, changed_count, deactivated_count, vectorized_count, report_json)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                source_name,
                len(incoming_ids),
                changed,
                deactivated,
                vectorized + knowledge_vectorized,
                json.dumps(crawl_report or {}, ensure_ascii=False),
            ),
        )
    logger.info(
        "Catalog sync for %s/%s: source=%s changed=%s deactivated=%s vectorized=%s knowledge_vectorized=%s",
        site_id,
        source_name,
        len(incoming_ids),
        changed,
        deactivated,
        vectorized,
        knowledge_vectorized,
    )
    _safe_console_print(
        f"[{start_timestamp}] Catalog sync ({source_name}): {len(incoming_ids)} source products, "
        f"{changed} changed/new, {deactivated} deactivated, {variant_count} variants, "
        f"{vectorized} product vectors, {knowledge_vectorized} knowledge vectors"
    )
    if changed_names:
        _safe_console_print(f"  -> Added/Changed: {', '.join(changed_names)}")
    if deactivated_names:
        _safe_console_print(f"  -> Deactivated/Removed: {', '.join(deactivated_names)}")
    return changed


def _sync_catalog_knowledge(site_id: str, source_name: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> int:
    try:
        from db.knowledge import sync_products_to_knowledge
        from agent.retrieval.generic_rag import vectorize_missing_knowledge

        entity_type = knowledge_entity_type_for(vertical_key)
        source_type = "product_catalog" if entity_type == "product" else "website_crawl"
        sync_products_to_knowledge(site_id, source_name, entity_type=entity_type, source_type=source_type)
        return vectorize_missing_knowledge(site_id)
    except Exception as exc:
        logger.warning("Knowledge sync skipped for %s/%s: %s", site_id, source_name, exc)
        return 0


def _count_product_variants(products: list[dict[str, Any]]) -> int:
    return sum(
        len(product.get("variants") or [])
        for product in products
        if isinstance(product.get("variants"), list)
    )


def _coverage_score(
    *,
    stopped_by_limit: bool,
    pages_visited: int,
    pages_failed: int,
    product_count: int,
    variant_count: int,
    source_type: str,
) -> float:
    score = 1.0
    if product_count <= 0:
        score -= 0.55
    if stopped_by_limit:
        score -= 0.2
    total_pages = max(1, pages_visited + pages_failed)
    score -= min(0.25, (pages_failed / total_pages) * 0.25)
    if source_type == "api_catalog" and variant_count <= 0:
        score -= 0.1
    return max(0.0, min(1.0, score))


def _build_crawl_report(
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
) -> CrawlReport:
    variant_count = _count_product_variants(products)
    category_count = len({
        _clean_text(product.get("category"))
        for product in products
        if _clean_text(product.get("category"))
    })
    return CrawlReport(
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
        coverage_score=_coverage_score(
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
    crawl_started = monotonic()
    if not start_url:
        raise ValueError("Start URL is required.")
    if max_pages <= 0 or max_depth < 0:
        raise ValueError("max_pages and max_depth must be positive.")

    resolved_site_id = sanitize_site_id(site_id or start_url)
    vertical_key = _crawl_vertical_key(resolved_site_id)
    seed = urldefrag(start_url)[0]
    parsed_seed = urlparse(seed)
    if not parsed_seed.netloc:
        raise ValueError("Start URL must include a host.")

    allowed_host = parsed_seed.netloc.lower()

    visited: set[str] = set()
    api_catalog_products = await _fetch_api_catalog_products(seed, timeout)
    extracted_products: list[dict[str, Any]] = list(api_catalog_products)
    pages_seen = 0
    pages_failed = 0
    pages_blocked = 0
    failed_urls: list[str] = []
    blocked_urls: list[str] = []
    product_links: set[str] = set()
    stopped_by_limit = False

    if not api_catalog_products:
        entrypoints = await _discover_crawl_entrypoints(seed, timeout, max_urls=max_pages * 3, vertical_key=vertical_key)
        if not entrypoints:
            entrypoints = [seed]
        queue: deque[tuple[str, int]] = deque((url, 0) for url in entrypoints)
        queued: set[str] = set(entrypoints)

        async with AsyncWebCrawler(verbose=False) as crawler:
            while queue and len(visited) < max_pages:
                page_url, depth = queue.popleft()
                page_url = urldefrag(page_url)[0]
                if page_url in visited:
                    continue
                visited.add(page_url)

                try:
                    result = await crawler.arun(url=page_url)
                except Exception as exc:
                    logger.info("Crawl failed for %s: %s", page_url, exc)
                    pages_failed += 1
                    if len(failed_urls) < 50:
                        failed_urls.append(page_url)
                    continue
                if not result.success:
                    pages_failed += 1
                    if len(failed_urls) < 50:
                        failed_urls.append(page_url)
                    continue

                text = result.html
                if not text:
                    continue

                parser = _HtmlHarvest()
                parser.feed(text)
                pages_seen += 1

                discovered_links: list[str] = []
                for link in parser.links:
                    next_url = urldefrag(urljoin(page_url, link))[0]
                    if not _is_allowed_crawl_url(next_url, allowed_host):
                        pages_blocked += 1
                        if len(blocked_urls) < 50:
                            blocked_urls.append(next_url)
                        continue
                    if any(token in next_url.lower() for token in PRODUCT_URL_KEYWORDS):
                        product_links.add(next_url)
                    if next_url in visited or next_url in queued or depth >= max_depth:
                        continue
                    discovered_links.append(next_url)

                for next_url in _ranked_unique_urls(discovered_links, vertical_key=vertical_key):
                    queued.add(next_url)
                    queue.append((next_url, depth + 1))

                candidates = _build_candidates_from_html(page_url, text, vertical_key=vertical_key)
                extracted_products.extend(candidates)

            if len(visited) >= max_pages:
                stopped_by_limit = True

    if not extracted_products:
        logger.warning("Crawler did not extract any product-like records.")

    deduped_products = _dedupe_products(extracted_products)
    source_label = "api catalog" if api_catalog_products else "advanced html crawl"
    source_type = "api_catalog" if api_catalog_products else "html_crawl"
    report = _build_crawl_report(
        site_id=resolved_site_id,
        site_url=seed,
        source_type=source_type,
        pages_visited=pages_seen,
        pages_failed=pages_failed,
        pages_blocked=pages_blocked,
        products=deduped_products,
        failed_urls=failed_urls,
        blocked_urls=blocked_urls,
        stopped_by_limit=stopped_by_limit,
        duration_ms=(monotonic() - crawl_started) * 1000,
    )
    _safe_console_print(
        f"Crawler summary ({source_label}): visited {pages_seen} pages, "
        f"extracted {len(extracted_products)} raw candidates, deduped to {len(deduped_products)}."
    )

    import json
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent.parent / "data" / resolved_site_id
    data_dir.mkdir(parents=True, exist_ok=True)
    crawl_json_path = data_dir / "crawl.json"
    with open(crawl_json_path, "w", encoding="utf-8") as f:
        json.dump(deduped_products, f, indent=2, ensure_ascii=False)

    import asyncio
    await asyncio.to_thread(
        _persist_catalog,
        resolved_site_id,
        deduped_products,
        reconcile_missing=reconcile_missing,
        source_name=source_name,
        crawl_report=report.to_dict(),
        vertical_key=vertical_key,
    )
    return resolved_site_id

def sync_web_crawl(*args, **kwargs) -> str:
    import asyncio
    return asyncio.run(async_web_crawl(*args, **kwargs))


def _crawl_vertical_key(site_id: str) -> str:
    try:
        from db.clients import get_client_vertical_key

        return get_client_vertical_key(site_id)
    except Exception as exc:
        logger.debug("Crawler vertical lookup failed for %s: %s", site_id, exc)
        return DEFAULT_VERTICAL_KEY
