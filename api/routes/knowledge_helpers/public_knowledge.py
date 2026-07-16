"""Public knowledge response sanitization helpers."""

from __future__ import annotations

from typing import Any

MAX_PUBLIC_KNOWLEDGE_IDS = 30
MAX_PUBLIC_KNOWLEDGE_ID_LENGTH = 180
MAX_PUBLIC_KNOWLEDGE_TEXT_CHARS = 1200


def parse_public_knowledge_ids(raw_ids: str) -> list[str]:
    seen: set[str] = set()
    parsed_ids: list[str] = []
    for raw_id in str(raw_ids or "").split(","):
        item_id = raw_id.strip().strip('"')
        if not item_id or item_id in seen:
            continue
        if len(item_id) > MAX_PUBLIC_KNOWLEDGE_ID_LENGTH:
            continue
        seen.add(item_id)
        parsed_ids.append(item_id)
        if len(parsed_ids) >= MAX_PUBLIC_KNOWLEDGE_IDS:
            break
    return parsed_ids


def short_public_text(value: Any) -> str:
    text = str(value or "").strip()
    return text[:MAX_PUBLIC_KNOWLEDGE_TEXT_CHARS]


def public_knowledge_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "external_id": str(item.get("external_id") or ""),
        "entity_type": str(item.get("entity_type") or "knowledge_item"),
        "title": short_public_text(item.get("title") or item.get("name")),
        "subtitle": short_public_text(item.get("subtitle")),
        "summary": short_public_text(item.get("summary")),
        "body": short_public_text(item.get("body")),
        "url": str(item.get("url") or ""),
        "image_url": str(item.get("image_url") or ""),
        "attributes": item.get("attributes") or {},
        "pricing": item.get("pricing") or {},
        "availability": item.get("availability") or {},
        "location": item.get("location") or {},
        "contact": item.get("contact") or {},
        "policy": item.get("policy") or {},
        "risk_tags": item.get("risk_tags") or [],
    }


def public_knowledge_items(items: list[dict[str, Any]], requested_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {str(item.get("id") or ""): public_knowledge_item(item) for item in items}
    return [by_id[item_id] for item_id in requested_ids if item_id in by_id]
