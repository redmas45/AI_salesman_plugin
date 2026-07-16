"""Generic commerce product details preserved during API ingestion."""

from __future__ import annotations

from typing import Any

from agent.ingestion_helpers.ingestion_normalization import clean_text, strip_html
from agent.ingestion_helpers.ingestion_product_rows import term_names, to_tags

MAX_DESCRIPTION_LENGTH = 4_000
MAX_SPECIFICATIONS = 24
MAX_TAGS = 40


def enriched_product_description(raw: dict[str, Any], fallback_name: Any) -> str:
    """Build searchable buying facts from a generic product payload."""
    base = clean_text(strip_html(raw.get("description") or raw.get("summary") or fallback_name))
    parts = [base]

    subcategory = clean_text(raw.get("subcategory"))
    if subcategory and subcategory.lower() not in base.lower():
        parts.append(f"Category path: {subcategory}")

    specifications = specification_pairs(raw.get("specs") or raw.get("specifications"))
    if specifications:
        parts.append("Specifications: " + "; ".join(f"{key}: {value}" for key, value in specifications))

    highlights = term_names(raw.get("highlights"))
    if highlights:
        parts.append("Highlights: " + "; ".join(highlights[:8]))

    return ". ".join(part.rstrip(". ") for part in parts if part)[:MAX_DESCRIPTION_LENGTH]


def generic_product_tags(raw: dict[str, Any]) -> list[str]:
    """Return bounded retrieval tags from categories, tags, and specifications."""
    candidates = [*term_names(raw.get("categories")), *to_tags(raw.get("tags"))]
    subcategory = clean_text(raw.get("subcategory"))
    if subcategory:
        candidates.extend(part.strip() for part in subcategory.split(">"))
    for key, value in specification_pairs(raw.get("specs") or raw.get("specifications")):
        candidates.extend((key, value))
    return unique_text(candidates, MAX_TAGS)


def generic_size_options(raw: dict[str, Any]) -> list[str]:
    """Extract size choices without treating colors as sizes."""
    candidates = to_tags(raw.get("sizes") or raw.get("size_options"))
    specs = raw.get("specs") or raw.get("specifications")
    if isinstance(specs, dict):
        candidates.extend(to_tags(specs.get("sizes_available") or specs.get("sizes")))
    for variant in raw.get("variants") or []:
        if not isinstance(variant, dict) or clean_text(variant.get("type")).lower() != "size":
            continue
        candidates.append(clean_text(variant.get("name") or variant.get("value")))
    return unique_text(candidates, MAX_TAGS)


def generic_color(raw: dict[str, Any]) -> str | None:
    direct = clean_text(raw.get("color"))
    if direct:
        return direct
    for variant in raw.get("variants") or []:
        if not isinstance(variant, dict) or clean_text(variant.get("type")).lower() != "color":
            continue
        color = clean_text(variant.get("name") or variant.get("value"))
        if color:
            return color
    return None


def specification_pairs(value: Any) -> list[tuple[str, str]]:
    if not isinstance(value, dict):
        return []
    pairs: list[tuple[str, str]] = []
    for raw_key, raw_value in value.items():
        key = clean_text(str(raw_key).replace("_", " "))
        formatted = formatted_specification_value(raw_value)
        if key and formatted:
            pairs.append((key, formatted))
        if len(pairs) >= MAX_SPECIFICATIONS:
            break
    return pairs


def formatted_specification_value(value: Any) -> str:
    if isinstance(value, dict):
        entries = [f"{clean_text(key)} {clean_text(item)}" for key, item in value.items()]
        return ", ".join(entry for entry in entries if entry.strip())[:240]
    if isinstance(value, list):
        return ", ".join(clean_text(item) for item in value if clean_text(item))[:240]
    return clean_text(value)[:240]


def unique_text(values: list[Any], limit: int) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        results.append(text)
        if len(results) >= limit:
            break
    return results
