"""Shared product row normalization helpers for catalog ingestion."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from agent.ingestion_helpers.ingestion_normalization import (
    clean_text,
    first,
    stable_id,
    to_float,
    to_positive_int_id,
)


MIN_RATING = 0.0
MAX_RATING = 5.0


def optional_rating(row: dict[str, Any]) -> float | None:
    """Return a usable 0-5 score, or ``None`` when the source has not rated it.

    A missing, blank, zero, or out-of-range value all mean "no score to show".
    Coercing any of them to ``0.0`` would publish the worst possible rating for a
    product nobody has reviewed.
    """
    raw = first(row.get("rating"), row.get("score"), default=None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    value = to_float(raw)
    if value <= MIN_RATING or value > MAX_RATING:
        return None
    return value


def optional_review_count(row: dict[str, Any]) -> int | None:
    """Return a non-negative review count, or ``None`` when the source omits it."""
    raw = first(row.get("review_count"), row.get("reviewCount"), default=None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    value = int(to_float(raw))
    return value if value >= 0 else None


def image_url_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = clean_text(value)
        return text or None
    if isinstance(value, dict):
        return image_url_from_value(
            first(
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
            result = image_url_from_value(item)
            if result:
                return result
    return None


def term_names(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return to_tags(value)
    if isinstance(value, dict):
        name = first(value.get("name"), value.get("title"), value.get("slug"), default=None)
        return [clean_text(name)] if name else []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            for name in term_names(item):
                if name and name not in names:
                    names.append(name)
        return names
    return [clean_text(value)]


def to_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value)]


def normalize_product_row(
    row: dict[str, Any],
    fallback_category: str,
    source_url: str,
) -> dict[str, Any] | None:
    name = clean_text(first(row.get("name"), row.get("title"), row.get("product_name"), default=""))
    if not name:
        return None

    description = clean_text(
        first(row.get("description"), row.get("summary"), row.get("body"), default=name)
    )
    category = clean_text(first(row.get("category"), row.get("type"), row.get("group"), default=fallback_category))
    subcategory = published_subcategory(row)
    brand = clean_text(first(row.get("brand"), row.get("vendor"), row.get("maker"), default="Unknown Brand"))

    raw_id = first(row.get("id"), row.get("product_id"), row.get("_id"), default=None)
    if raw_id is None:
        product_id = int(stable_id(source_url, name, description))
    else:
        try:
            product_id = int(raw_id)
        except (TypeError, ValueError):
            product_id = stable_id(source_url, str(raw_id))

    variant_id = to_positive_int_id(row.get("variant_id"))
    color = first(row.get("color"), default=None)
    size_raw = first(row.get("size_options"), row.get("sizes"), default="[]")
    size_options = (
        json.dumps(to_tags(size_raw))
        if not isinstance(size_raw, str)
        else (size_raw if size_raw else "[]")
    )
    tags = to_tags(first(row.get("tags"), row.get("labels"), default=[]))
    price = to_float(first(row.get("price"), row.get("amount"), row.get("cost"), default=0.0))
    original_price = to_float(first(row.get("original_price"), row.get("list_price"), default=price or 0.0))
    # "Unrated" and "rated zero" are different claims about a product, so a
    # missing score stays NULL instead of collapsing into a real 0/5.
    rating = optional_rating(row)
    review_count = optional_review_count(row)
    stock = int(to_float(first(row.get("stock"), row.get("quantity"), default=100)))
    image = first(row.get("image"), row.get("image_url"), row.get("thumbnail"), default=None)
    is_active = int(first(row.get("is_active"), 1))

    return {
        "id": int(product_id),
        "variant_id": variant_id,
        "name": name,
        "brand": brand or "Unknown Brand",
        "category": category or fallback_category,
        "subcategory": subcategory,
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


def published_subcategory(row: dict[str, Any]) -> str | None:
    """The leaf of the narrowest grouping the source publishes for this record.

    Catalogues publish a path ("Electronics > Smartphones > Android Budget") or a
    plain label. The whole path is kept, because a customer may name any level of
    it: "electronics", "phones", or "android budget" all identify the same
    records, and keeping only the leaf loses the level people usually say.
    """
    raw = first(
        row.get("subcategory"),
        row.get("sub_category"),
        row.get("product_type"),
        row.get("category_path"),
        default=None,
    )
    segments = [clean_text(part) for part in str(raw or "").split(">")]
    path = " > ".join(part for part in segments if part)
    return path or None


def derive_category_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    for part in reversed(parts):
        lowered = part.lower()
        if lowered not in {"product", "products", "item", "items", "shop", "category", "categories"}:
            return part.replace("-", " ").replace("_", " ").title()
    return "Products"


def optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
