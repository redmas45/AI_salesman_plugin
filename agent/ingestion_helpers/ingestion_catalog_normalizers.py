"""Catalog payload normalizers for storefront and vertical API ingestion."""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any, Callable
from urllib.parse import urljoin

from agent.ingestion_helpers.ingestion_normalization import clean_text, first, strip_html, to_float, to_positive_int_id
from agent.ingestion_helpers.ingestion_generic_product_details import (
    enriched_product_description,
    generic_color,
    generic_product_tags,
    generic_size_options,
)
from agent.ingestion_helpers.ingestion_product_rows import (
    derive_category_from_url,
    image_url_from_value,
    normalize_product_row,
    optional_int,
    term_names,
    to_tags,
)
from agent.verticals.discovery_profiles import high_value_url_keywords_for

logger = logging.getLogger(__name__)

SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", flags=re.IGNORECASE | re.DOTALL)


def looks_like_shopify_product(raw: dict[str, Any]) -> bool:
    variants = raw.get("variants") if isinstance(raw.get("variants"), list) else []
    has_shopify_variant = any(
        isinstance(variant, dict)
        and variant.get("id") not in (None, "")
        and any(key in variant for key in ("price", "sku", "inventory_quantity"))
        for variant in variants
    )
    return has_shopify_variant and (
        "handle" in raw or "body_html" in raw or "product_type" in raw or "vendor" in raw
    )


def normalize_shopify_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    variants = raw.get("variants") if isinstance(raw.get("variants"), list) else []
    selected_variant = next(
        (variant for variant in variants if isinstance(variant, dict) and variant.get("available") is not False),
        {},
    )
    if not selected_variant and variants and isinstance(variants[0], dict):
        selected_variant = variants[0]

    image = image_url_from_value(first(raw.get("image"), raw.get("images"), raw.get("featured_image"), default=None))
    available = first(selected_variant.get("available"), raw.get("available"), default=True)
    stock = first(selected_variant.get("inventory_quantity"), raw.get("stock"), default=None)
    if stock in (None, ""):
        stock = 100 if available is not False else 0

    return normalize_product_row(
        {
            "id": first(raw.get("id"), raw.get("handle"), raw.get("sku"), default=None),
            "variant_id": to_positive_int_id(selected_variant.get("id")),
            "name": first(raw.get("title"), raw.get("name"), raw.get("handle")),
            "description": first(strip_html(raw.get("body_html")), raw.get("description"), raw.get("title")),
            "category": first(raw.get("product_type"), raw.get("category"), "Products"),
            "brand": first(raw.get("vendor"), raw.get("brand"), "Unknown Brand"),
            "price": first(selected_variant.get("price"), raw.get("price"), 0),
            "original_price": first(
                selected_variant.get("compare_at_price"),
                raw.get("compare_at_price"),
                selected_variant.get("price"),
                raw.get("price"),
                0,
            ),
            "image": image,
            "stock": stock,
            "tags": to_tags(raw.get("tags")),
            "is_active": 1 if available is not False and int(to_float(stock)) > 0 else 0,
        },
        fallback_category=clean_text(first(raw.get("product_type"), "Products")),
        source_url=api_url,
    )


def woocommerce_price(raw_prices: Any, *keys: str) -> float:
    if not isinstance(raw_prices, dict):
        return 0.0
    minor_units = int(to_float(raw_prices.get("currency_minor_unit") or 0))
    for key in keys:
        value = raw_prices.get(key)
        if value in (None, ""):
            continue
        amount = to_float(value)
        if minor_units > 0 and isinstance(value, str) and value.isdigit():
            amount = amount / (10**minor_units)
        if amount > 0:
            return amount
    return 0.0


def looks_like_woocommerce_product(raw: dict[str, Any]) -> bool:
    return isinstance(raw.get("prices"), dict) or "is_in_stock" in raw or "stock_status" in raw


def normalize_woocommerce_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    prices = raw.get("prices") if isinstance(raw.get("prices"), dict) else {}
    category_names = term_names(raw.get("categories"))
    tag_names = term_names(raw.get("tags"))
    in_stock = first(raw.get("is_in_stock"), raw.get("in_stock"), default=True)
    stock = first(raw.get("stock_quantity"), raw.get("stock"), default=None)
    if stock in (None, ""):
        stock = 100 if in_stock is not False else 0

    price = woocommerce_price(prices, "price", "sale_price", "regular_price")
    if price <= 0:
        price = first(raw.get("price"), raw.get("sale_price"), raw.get("regular_price"), 0)
    regular_price = woocommerce_price(prices, "regular_price", "price")
    if regular_price <= 0:
        regular_price = first(raw.get("regular_price"), price)

    return normalize_product_row(
        {
            "id": first(raw.get("id"), raw.get("sku"), raw.get("slug"), default=None),
            "name": first(raw.get("name"), raw.get("title"), raw.get("slug")),
            "description": first(strip_html(raw.get("description")), strip_html(raw.get("short_description")), raw.get("name")),
            "category": first(category_names[0] if category_names else None, raw.get("category"), "Products"),
            "brand": first(raw.get("brand"), raw.get("vendor"), "Unknown Brand"),
            "price": price,
            "original_price": regular_price,
            "image": image_url_from_value(raw.get("images")),
            "stock": stock,
            "tags": tag_names,
            "rating": raw.get("average_rating"),
            "review_count": raw.get("review_count"),
            "is_active": 1 if in_stock is not False and int(to_float(stock)) > 0 else 0,
        },
        fallback_category=clean_text(first(category_names[0] if category_names else None, "Products")),
        source_url=api_url,
    )


def extract_platform_variants(raw: dict[str, Any], product: dict[str, Any], source_url: str) -> list[dict[str, Any]]:
    try:
        product_id = int(product["id"])
        if looks_like_shopify_product(raw):
            from agent.adapters.shopify import ShopifyAdapter

            return ShopifyAdapter().extract_variants(raw, product_id, source_url)
        if looks_like_woocommerce_product(raw):
            from agent.adapters.woocommerce import WooCommerceAdapter

            return WooCommerceAdapter().extract_variants(raw, product_id, source_url)
    except (ImportError, TypeError, ValueError, KeyError) as exc:
        logger.info("Variant extraction skipped for %s: %s", source_url, exc)
    return []


def normalize_with_platform_adapter(raw: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    try:
        if looks_like_shopify_product(raw):
            from agent.adapters.shopify import ShopifyAdapter

            return ShopifyAdapter().normalize_product(raw, source_url) or normalize_shopify_product(raw, source_url)
        if looks_like_woocommerce_product(raw):
            from agent.adapters.woocommerce import WooCommerceAdapter

            return WooCommerceAdapter().normalize_product(raw, source_url) or normalize_woocommerce_product(raw, source_url)
    except (ImportError, TypeError, ValueError, KeyError) as exc:
        logger.info("Platform normalization skipped for %s: %s", source_url, exc)
        if looks_like_shopify_product(raw):
            return normalize_shopify_product(raw, source_url)
        if looks_like_woocommerce_product(raw):
            return normalize_woocommerce_product(raw, source_url)
    return None


def with_platform_variants(raw: dict[str, Any], product: dict[str, Any] | None, source_url: str) -> dict[str, Any] | None:
    if not product:
        return None
    variants = extract_platform_variants(raw, product, source_url)
    if variants:
        product = dict(product)
        product["variants"] = variants
    return product


def normalize_embedded_json_product(raw: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    if looks_like_shopify_product(raw) or looks_like_woocommerce_product(raw):
        return with_platform_variants(raw, normalize_with_platform_adapter(raw, source_url), source_url)

    name = clean_text(first(raw.get("name"), raw.get("title"), raw.get("product_name"), default=""))
    if not name or len(name) > 180:
        return None

    offers = raw.get("offers")
    if isinstance(offers, list) and offers:
        offers = offers[0]
    offers = offers if isinstance(offers, dict) else {}
    prices = raw.get("prices") if isinstance(raw.get("prices"), dict) else {}
    image = image_url_from_value(
        first(raw.get("image"), raw.get("images"), raw.get("image_url"), raw.get("thumbnail"), raw.get("featured_image"), default=None)
    )
    url_value = first(raw.get("url"), raw.get("href"), raw.get("permalink"), raw.get("product_url"), default=None)
    absolute_url = urljoin(source_url, str(url_value)) if url_value else source_url
    price = first(
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

    signal_score = product_signal_score(raw, image, price, url_value)
    if signal_score < 2:
        return None

    categories = term_names(raw.get("categories"))
    tags = term_names(raw.get("tags"))
    in_stock = first(raw.get("in_stock"), raw.get("is_in_stock"), raw.get("available"), default=True)
    stock = first(raw.get("stock"), raw.get("quantity"), raw.get("stock_quantity"), default=None)
    if stock in (None, ""):
        stock = 100 if in_stock is not False else 0

    return normalize_product_row(
        {
            "id": first(raw.get("id"), raw.get("product_id"), raw.get("_id"), raw.get("sku"), raw.get("handle"), default=None),
            "name": name,
            "description": first(strip_html(raw.get("description")), strip_html(raw.get("summary")), strip_html(raw.get("short_description")), name),
            "category": first(raw.get("category"), categories[0] if categories else None, "Products"),
            "brand": first(raw.get("brand"), raw.get("vendor"), raw.get("maker"), "Unknown Brand"),
            "price": price,
            "original_price": first(raw.get("original_price"), raw.get("regular_price"), raw.get("compare_at_price"), price),
            "image": image,
            "stock": stock,
            "tags": tags,
            "rating": first(raw.get("rating"), raw.get("average_rating"), default=0),
            "review_count": first(raw.get("review_count"), raw.get("reviewCount"), default=0),
            "is_active": 1 if in_stock is not False and int(to_float(stock)) > 0 else 0,
        },
        fallback_category=derive_category_from_url(absolute_url),
        source_url=absolute_url,
    )


def product_signal_score(raw: dict[str, Any], image: str | None, price: Any, url_value: Any) -> int:
    score = 0
    if to_float(price) > 0:
        score += 2
    if image:
        score += 1
    if any(raw.get(key) not in (None, "") for key in ("id", "product_id", "sku", "handle", "_id")):
        score += 1
    if url_value and any(token in str(url_value).lower() for token in high_value_url_keywords_for("ecommerce")):
        score += 1
    if any(key in raw for key in ("variants", "offers", "prices", "inventory", "stock", "stock_quantity")):
        score += 1
    if any(raw.get(key) not in (None, "") for key in ("brand", "vendor", "category", "categories")):
        score += 1
    return score


def extract_products_from_json_tree(payload: Any, source_url: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    stack: list[Any] = [payload]
    nodes_seen = 0
    while stack and nodes_seen < 5000:
        item = stack.pop()
        nodes_seen += 1
        if isinstance(item, dict):
            product = normalize_embedded_json_product(item, source_url)
            if product:
                product_id = int(product["id"])
                if product_id not in seen_ids:
                    seen_ids.add(product_id)
                    results.append(product)
            stack.extend(value for value in item.values() if isinstance(value, (dict, list)))
        elif isinstance(item, list):
            stack.extend(value for value in item if isinstance(value, (dict, list)))
    return results


def iter_script_json_payloads(script_text: str) -> list[Any]:
    text = html.unescape(script_text or "").strip()
    if not text or len(text) > 2_000_000:
        return []

    decoder = json.JSONDecoder()
    payloads: list[Any] = []
    if text[0] in "[{":
        try:
            payload, _index = decoder.raw_decode(text)
            payloads.append(payload)
        except json.JSONDecodeError as exc:
            logger.debug("Embedded JSON raw decode failed: %s", exc)

    for match in re.finditer(r"=\s*([\{\[])", text):
        if len(payloads) >= 25:
            break
        try:
            payload, _index = decoder.raw_decode(text[match.start(1):])
        except json.JSONDecodeError:
            continue
        payloads.append(payload)
    return payloads


def extract_embedded_json_products(
    html_text: str,
    source_url: str,
    *,
    dedupe_products: Callable[..., list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for match in SCRIPT_TAG_RE.finditer(html_text):
        for payload in iter_script_json_payloads(match.group(1)):
            products.extend(extract_products_from_json_tree(payload, source_url))
    return dedupe_products(products)


def normalize_api_catalog_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    if looks_like_insurance_policy_api(raw):
        return normalize_policy_catalog_product(raw, api_url)

    categories = raw.get("categories") if isinstance(raw.get("categories"), list) else []
    category = first(raw.get("category"), categories[0] if categories else None, "Products")
    stock = raw.get("stock")
    in_stock = raw.get("in_stock")
    if stock in (None, ""):
        stock = 100 if in_stock is not False else 0

    tags = list(categories)
    for tag in generic_product_tags(raw):
        if tag not in tags:
            tags.append(tag)

    normalized = normalize_product_row(
        {
            "id": first(raw.get("rag_id"), raw.get("id"), raw.get("handle"), raw.get("sku")),
            "name": first(raw.get("name"), raw.get("title"), raw.get("handle")),
            "description": enriched_product_description(raw, first(raw.get("name"), raw.get("title"))),
            "category": category,
            "brand": first(raw.get("brand"), raw.get("vendor"), "Unknown Brand"),
            "price": first(raw.get("price"), raw.get("amount"), raw.get("cost"), 0),
            "original_price": first(raw.get("original_price"), raw.get("compare_at_price"), raw.get("price"), 0),
            "image": first(raw.get("image_url"), raw.get("image"), raw.get("thumbnail")),
            "stock": stock,
            "tags": tags,
            "rating": first(raw.get("rating"), raw.get("average_rating"), default=0),
            "review_count": first(raw.get("review_count"), raw.get("reviewCount"), default=0),
            "color": generic_color(raw),
            "size_options": generic_size_options(raw),
            "is_active": 1 if in_stock is not False and int(to_float(stock)) > 0 else 0,
        },
        fallback_category=clean_text(category) or "Products",
        source_url=api_url,
    )
    if not normalized:
        return None
    for key in ("specs", "specifications", "variants", "highlights", "url", "sku", "currency"):
        if raw.get(key) not in (None, "", [], {}):
            normalized[key] = raw[key]
    return normalized


def looks_like_insurance_policy_api(raw: dict[str, Any]) -> bool:
    keys = ("premium_monthly", "premium_annual", "sum_insured", "insurer", "claim_process", "waiting_period")
    return any(key in raw for key in keys)


def normalize_policy_catalog_product(raw: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    category_id = clean_text(raw.get("category_id"))
    category = insurance_category_label(category_id)
    monthly_premium = to_float(raw.get("premium_monthly"))
    annual_premium = to_float(raw.get("premium_annual"))
    price = monthly_premium or annual_premium
    normalized = normalize_product_row(
        {
            "id": first(raw.get("id"), raw.get("policy_id")),
            "name": first(raw.get("name"), raw.get("title")),
            "description": policy_catalog_description(raw, category),
            "category": category,
            "brand": first(raw.get("insurer"), raw.get("brand"), "Insurance Provider"),
            "price": price,
            "original_price": annual_premium or price,
            "stock": 100,
            "tags": policy_catalog_tags(raw, category),
            "rating": raw.get("rating"),
            "review_count": raw.get("review_count"),
            "is_active": 1,
        },
        fallback_category=category or "Insurance Plans",
        source_url=api_url,
    )
    if not normalized:
        return None
    normalized["policy_json"] = policy_catalog_policy_payload(raw, category)
    normalized["risk_tags"] = policy_catalog_risk_tags(raw, category)
    normalized["pricing_json"] = {"premium_monthly": monthly_premium, "premium_annual": annual_premium, "currency": "INR"}
    return normalized


def insurance_category_label(category_id: str) -> str:
    labels = {
        "health": "Health Insurance",
        "life": "Life Insurance",
        "motor": "Motor Insurance",
        "travel": "Travel Insurance",
        "home": "Home Insurance",
        "business": "Business Insurance",
    }
    return labels.get(category_id.lower(), "Insurance Plans")


def policy_catalog_description(raw: dict[str, Any], category: str) -> str:
    features = to_tags(raw.get("features"))
    parts = [
        clean_text(raw.get("name")),
        category,
        clean_text(raw.get("type")),
        clean_text(raw.get("insurer")),
        f"monthly premium INR {to_float(raw.get('premium_monthly')):g}" if to_float(raw.get("premium_monthly")) else "",
        f"annual premium INR {to_float(raw.get('premium_annual')):g}" if to_float(raw.get("premium_annual")) else "",
        f"sum insured INR {to_float(raw.get('sum_insured')):g}" if to_float(raw.get("sum_insured")) else "",
        f"age {clean_text(raw.get('age_min'))} to {clean_text(raw.get('age_max'))}" if raw.get("age_min") or raw.get("age_max") else "",
        f"waiting period {clean_text(raw.get('waiting_period'))}" if raw.get("waiting_period") else "",
        f"claim process {clean_text(raw.get('claim_process'))}" if raw.get("claim_process") else "",
        f"renewability {clean_text(raw.get('renewability'))}" if raw.get("renewability") else "",
        f"tax benefit {clean_text(raw.get('tax_benefit'))}" if raw.get("tax_benefit") else "",
        "Features: " + "; ".join(features[:8]) if features else "",
    ]
    return ". ".join(part for part in parts if part)


def policy_catalog_tags(raw: dict[str, Any], category: str) -> list[str]:
    tags = ["insurance", "policy", "plan", category, raw.get("category_id"), raw.get("type"), raw.get("insurer"), "premium", "coverage", "claim"]
    tags.extend(to_tags(raw.get("features"))[:10])
    if raw.get("age_min") or raw.get("age_max"):
        tags.append(f"age {raw.get('age_min') or ''} {raw.get('age_max') or ''}".strip())
    return [str(tag).strip() for tag in tags if str(tag or "").strip()]


def policy_catalog_policy_payload(raw: dict[str, Any], category: str) -> dict[str, Any]:
    payload = {
        "category": category,
        "category_id": clean_text(raw.get("category_id")),
        "policy_type": clean_text(raw.get("type")),
        "sum_insured": to_float(raw.get("sum_insured")),
        "age_min": optional_int(raw.get("age_min")),
        "age_max": optional_int(raw.get("age_max")),
        "claim_process": clean_text(raw.get("claim_process")),
        "waiting_period": clean_text(raw.get("waiting_period")),
        "renewability": clean_text(raw.get("renewability")),
        "tax_benefit": clean_text(raw.get("tax_benefit")),
    }
    return {key: value for key, value in payload.items() if value not in ("", None, 0.0)}


def policy_catalog_risk_tags(raw: dict[str, Any], category: str) -> list[str]:
    tags = ["regulated_insurance", "insurance_plan"]
    category_text = f"{category} {clean_text(raw.get('category_id'))}".lower()
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


def normalize_catalog_payload(
    payload: Any,
    api_url: str,
    *,
    dedupe_products: Callable[..., list[dict[str, Any]]],
    merge_same_name: bool = True,
) -> list[dict[str, Any]]:
    raw_products = first(payload.get("products"), payload.get("data"), payload.get("items"), payload.get("results"), default=None) if isinstance(payload, dict) else payload
    if not isinstance(raw_products, list):
        return dedupe_products(extract_products_from_json_tree(payload, api_url), merge_same_name=merge_same_name)

    products = []
    for raw in raw_products:
        if not isinstance(raw, dict):
            continue
        if looks_like_shopify_product(raw) or looks_like_woocommerce_product(raw):
            normalized = with_platform_variants(raw, normalize_with_platform_adapter(raw, api_url), api_url)
        else:
            normalized = normalize_api_catalog_product(raw, api_url)
        if normalized:
            products.append(normalized)
    return dedupe_products(products, merge_same_name=merge_same_name)
