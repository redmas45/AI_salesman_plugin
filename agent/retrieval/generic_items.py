"""Knowledge item decoding and text formatting helpers."""

from __future__ import annotations

import json
from typing import Any


JSON_FIELD_NAMES = (
    "attributes_json",
    "pricing_json",
    "availability_json",
    "location_json",
    "contact_json",
    "policy_json",
    "risk_tags_json",
)

PRICE_FIELD_NAMES = (
    "price",
    "amount",
    "premium",
    "premium_min",
    "monthly_premium",
    "annual_premium",
    "min_price",
    "starting_price",
)


def decode_item(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for key in JSON_FIELD_NAMES:
        if key in item:
            item[key.replace("_json", "")] = json_or_text(item.pop(key))
    item["name"] = item.get("title", "")
    item["category_name"] = item.get("entity_type", "")
    item["price"] = price_value(item.get("pricing"))
    return item


def knowledge_item_to_text(item: dict[str, Any]) -> str:
    attributes = json_or_text(item.get("attributes_json"))
    pricing = json_or_text(item.get("pricing_json"))
    availability = json_or_text(item.get("availability_json"))
    location = json_or_text(item.get("location_json"))
    contact = json_or_text(item.get("contact_json"))
    policy = json_or_text(item.get("policy_json"))
    risk_tags = json_or_text(item.get("risk_tags_json"))
    return " ".join(
        text_part(part)
        for part in (
            item.get("title"),
            item.get("subtitle"),
            item.get("entity_type"),
            item.get("summary"),
            item.get("body"),
            attributes,
            pricing,
            availability,
            location,
            contact,
            policy,
            risk_tags,
        )
        if text_part(part)
    )


def json_or_text(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return str(value)


def text_part(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value or "").strip()


def optional_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def price_value(pricing: Any) -> float:
    if not isinstance(pricing, dict):
        return 0.0
    for key in PRICE_FIELD_NAMES:
        value = pricing.get(key)
        if value in (None, "", 0, 0.0, "0", "0.0"):
            continue
        number = optional_number(value)
        if number is not None and number > 0:
            return number
    return 0.0
