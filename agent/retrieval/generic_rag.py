"""Generic knowledge-item retrieval for non-commerce verticals."""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg

import config
from agent.rag import _embed
from db.database import get_db, init_tenant_schema

logger = logging.getLogger(__name__)
DEFAULT_RETRIEVAL_LIMIT = 8
VECTORIZE_BATCH_SIZE = 256
SEMANTIC_SCORE_FLOOR = 0.22


def retrieve_knowledge(
    query: str,
    *,
    site_id: str,
    entity_types: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve source-backed knowledge items for a non-ecommerce client."""
    init_tenant_schema(site_id)
    safe_limit = max(1, min(int(limit or config.RAG_TOP_N or DEFAULT_RETRIEVAL_LIMIT), 20))
    clean_types = [item for item in (entity_types or []) if item]
    try:
        results = _semantic_search(query, site_id, clean_types, safe_limit)
    except (RuntimeError, psycopg.Error) as exc:
        logger.warning("Generic RAG semantic search failed for %s: %s", site_id, exc)
        results = []
    if results:
        return results
    return _recent_active_items(site_id, clean_types, safe_limit)


def vectorize_missing_knowledge(site_id: str) -> int:
    """Embed knowledge rows that are missing vectors."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT id, entity_type, title, subtitle, summary, body, attributes_json,
                   pricing_json, availability_json
            FROM knowledge_items
            WHERE is_active = 1 AND embedding IS NULL
            ORDER BY updated_at DESC, id
            LIMIT %s
            """,
            (VECTORIZE_BATCH_SIZE,),
        ).fetchall()
    if not rows:
        return 0

    texts = [_knowledge_item_to_text(dict(row)) for row in rows]
    embeddings = _embed(texts)
    with get_db(site_id) as conn:
        for index, row in enumerate(rows):
            conn.execute(
                "UPDATE knowledge_items SET embedding = %s WHERE id = %s",
                (embeddings[index], row["id"]),
            )
    return len(rows)


def _semantic_search(
    query: str,
    site_id: str,
    entity_types: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    query_vec = _embed([query])[0]
    type_clause = ""
    params: list[Any] = [query_vec]
    if entity_types:
        type_clause = "AND entity_type = ANY(%s)"
        params.append(entity_types)
    params.extend([query_vec, limit * 2])

    with get_db(site_id) as conn:
        rows = conn.execute(
            f"""
            SELECT *,
                   1 - (embedding <=> %s) AS _semantic_score
            FROM knowledge_items
            WHERE is_active = 1
              AND embedding IS NOT NULL
              {type_clause}
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            params,
        ).fetchall()
    items = [_decode_item(row) for row in rows]
    filtered = [item for item in items if float(item.get("_semantic_score") or 0) >= SEMANTIC_SCORE_FLOOR]
    return filtered[:limit]


def _recent_active_items(site_id: str, entity_types: list[str], limit: int) -> list[dict[str, Any]]:
    type_clause = ""
    params: list[Any] = []
    if entity_types:
        type_clause = "AND entity_type = ANY(%s)"
        params.append(entity_types)
    params.append(limit)
    with get_db(site_id) as conn:
        rows = conn.execute(
            f"""
            SELECT *, 0.0 AS _semantic_score
            FROM knowledge_items
            WHERE is_active = 1
              {type_clause}
            ORDER BY updated_at DESC, title ASC
            LIMIT %s
            """,
            params,
        ).fetchall()
    return [_decode_item(row) for row in rows]


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
    item["price"] = _price_value(item.get("pricing"))
    return item


def _knowledge_item_to_text(item: dict[str, Any]) -> str:
    attributes = _json_or_text(item.get("attributes_json"))
    pricing = _json_or_text(item.get("pricing_json"))
    availability = _json_or_text(item.get("availability_json"))
    return " ".join(
        str(part or "").strip()
        for part in (
            item.get("title"),
            item.get("subtitle"),
            item.get("entity_type"),
            item.get("summary"),
            item.get("body"),
            attributes,
            pricing,
            availability,
        )
        if str(part or "").strip()
    )


def _json_or_text(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return str(value)


def _price_value(pricing: Any) -> float:
    if not isinstance(pricing, dict):
        return 0.0
    try:
        return float(pricing.get("price") or 0)
    except (TypeError, ValueError):
        return 0.0
