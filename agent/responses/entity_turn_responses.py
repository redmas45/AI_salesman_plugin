"""Entity response formatting helpers for non-product retrieved records."""

from __future__ import annotations

from agent.products.product_response import ProductCatalogFormatter, normalize_lookup_text, phrase_in_text


def answer_fallback_text(items: list[dict], formatter: ProductCatalogFormatter) -> str:
    if len(items) == 1:
        title = display_name(items[0])
        detail = fact_text(items[0], formatter)
        return f"Based on the website data, {title}: {detail}"

    bullets = [f"- {display_name(item)}: {fact_text(item, formatter)}" for item in items[:4]]
    return "Based on the website data, these records are relevant:\n" + "\n".join(bullets)


def display_name(item: dict) -> str:
    return str(item.get("title") or item.get("name") or "This record")


def fact_text(item: dict, formatter: ProductCatalogFormatter) -> str:
    summary = str(item.get("summary") or item.get("body") or "").strip()
    price = formatter.price(item)
    availability = availability_text(item)
    location = location_text(item)
    parts: list[str] = []
    if price is not None and price > 0:
        parts.append(f"published price or premium {price:g}")
    elif looks_priced(item):
        parts.append("price or premium not published in retrieved data")
    if availability:
        parts.append(availability)
    if location:
        parts.append(location)
    if summary:
        parts.append(summary[:220])
    if not parts:
        parts.append("source-backed record; confirm final fit with the website or provider")
    return "; ".join(parts)


def comparison_fact_text(item: dict, formatter: ProductCatalogFormatter) -> str:
    entity_type = str(item.get("entity_type") or item.get("category_name") or item.get("category") or "").strip()
    detail = fact_text(item, formatter)
    if entity_type:
        return f"Type: {entity_type}. {detail}"
    return detail


def availability_text(item: dict) -> str:
    availability = item.get("availability") if isinstance(item.get("availability"), dict) else {}
    if availability.get("in_stock") is True:
        return "availability marked available"
    if availability.get("in_stock") is False:
        return "availability marked unavailable"
    status = str(availability.get("status") or availability.get("availability") or item.get("availability_status") or "").strip()
    return f"availability: {status}" if status else ""


def location_text(item: dict) -> str:
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    values = [
        location.get("city"),
        location.get("area"),
        location.get("country"),
        item.get("city"),
        item.get("location_name"),
    ]
    text = ", ".join(str(value).strip() for value in values if str(value or "").strip())
    return f"location: {text}" if text else ""


def looks_priced(item: dict) -> bool:
    text = normalize_lookup_text(
        " ".join(
            str(value or "")
            for value in (
                item.get("entity_type"),
                item.get("category_name"),
                item.get("summary"),
                item.get("body"),
            )
        )
    )
    return any(phrase_in_text(token, text) for token in ("premium", "price", "pricing", "cost", "fare", "fee", "rate"))


def comparison_fallback_text(items: list[dict], formatter: ProductCatalogFormatter) -> str:
    bullets = []
    for item in items[:4]:
        title = item.get("title") or item.get("name") or "Option"
        bullets.append(f"- {title}: {comparison_fact_text(item, formatter)}")
    return "I found matching records to compare from the website data:\n" + "\n".join(bullets)
