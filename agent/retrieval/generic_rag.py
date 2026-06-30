"""Generic knowledge-item retrieval for non-commerce verticals."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import psycopg

import config
from agent.rag import _embed
from db.database import get_db, init_tenant_schema

logger = logging.getLogger(__name__)
DEFAULT_RETRIEVAL_LIMIT = 8
VECTORIZE_BATCH_SIZE = 256
SEMANTIC_SCORE_FLOOR = 0.22
LEXICAL_SCAN_LIMIT = 250
LEXICAL_SCORE_FLOOR = 4
LEXICAL_STOPWORDS = {
    "a",
    "am",
    "and",
    "are",
    "between",
    "for",
    "from",
    "i",
    "is",
    "me",
    "my",
    "of",
    "old",
    "please",
    "show",
    "the",
    "to",
    "with",
    "year",
    "years",
}
LEXICAL_ALIASES = {
    "compare": {"compare", "comparison", "premium", "coverage", "features", "rating"},
    "health": {"health", "medical", "hospital", "hospitalization", "cashless", "illness", "opd"},
    "insurance": {"insurance", "policy", "policies", "plan", "plans", "premium", "coverage", "cover", "claim"},
    "policy": {"insurance", "policy", "policies", "plan", "plans", "coverage", "premium"},
    "plan": {"plan", "plans", "policy", "coverage", "premium"},
}


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
    lexical_results = _lexical_search(query, site_id, clean_types, safe_limit)
    if lexical_results:
        return lexical_results
    return _recent_active_items(site_id, clean_types, safe_limit)


def vectorize_missing_knowledge(site_id: str, *, max_batches: int | None = None) -> int:
    """Embed all active knowledge rows that are missing vectors."""
    total = 0
    batches = 0
    while max_batches is None or batches < max_batches:
        vectorized = _vectorize_missing_knowledge_batch(site_id)
        if vectorized <= 0:
            break
        total += vectorized
        batches += 1
    return total


def _vectorize_missing_knowledge_batch(site_id: str) -> int:
    """Embed one bounded batch of active knowledge rows."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT id, entity_type, title, subtitle, summary, body, attributes_json,
                   pricing_json, availability_json, location_json, contact_json,
                   policy_json, risk_tags_json
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


def _lexical_search(
    query: str,
    site_id: str,
    entity_types: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    type_clause = ""
    params: list[Any] = []
    if entity_types:
        type_clause = "AND entity_type = ANY(%s)"
        params.append(entity_types)
    params.append(LEXICAL_SCAN_LIMIT)
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
    ranked = _rank_lexical_items(query, [dict(row) for row in rows], limit)
    return [_decode_item(row) for row in ranked]


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


def _rank_lexical_items(query: str, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    terms = _query_terms(query)
    if not terms:
        return []
    age = _age_from_query(query)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row in rows:
        text = _normalize_text(_knowledge_item_to_text(row))
        score = _lexical_score(text, terms)
        if age is not None and _age_matches_item(age, row):
            score += 5
        if score < LEXICAL_SCORE_FLOOR:
            continue
        item = dict(row)
        item["_semantic_score"] = max(float(item.get("_semantic_score") or 0.0), min(score / 30, 0.95))
        scored.append((score, str(item.get("title") or ""), item))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item for _score, _title, item in scored[:limit]]


def _query_terms(query: str) -> set[str]:
    tokens = {
        _singularize(token)
        for token in _normalize_text(query).split()
        if len(token) > 1 and token not in LEXICAL_STOPWORDS
    }
    expanded = set(tokens)
    for token in tokens:
        expanded.update(LEXICAL_ALIASES.get(token, set()))
    if "20" in tokens or "age" in tokens:
        expanded.update({"age", "eligible", "adult"})
    return {term for term in expanded if term}


def _lexical_score(text: str, terms: set[str]) -> int:
    score = 0
    for term in terms:
        if not term:
            continue
        if _phrase_in_text(term, text):
            score += 3 if len(term) > 3 else 2
    if _phrase_in_text("health", text) and {"health", "medical", "hospital"} & terms:
        score += 6
    if _phrase_in_text("insurance", text) and {"insurance", "policy", "plan"} & terms:
        score += 6
    if _phrase_in_text("insurance plan", text) or _phrase_in_text("health insurance", text):
        score += 4
    return score


def _age_from_query(query: str) -> int | None:
    match = re.search(r"\b(?:age\s*)?(\d{1,3})(?:\s*(?:year|years|yr|yrs)\s*old)?\b", str(query or "").lower())
    if not match:
        return None
    try:
        age = int(match.group(1))
    except (TypeError, ValueError):
        return None
    return age if 0 < age < 120 else None


def _age_matches_item(age: int, row: dict[str, Any]) -> bool:
    candidates = [
        _json_or_text(row.get("policy_json")),
        _json_or_text(row.get("attributes_json")),
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        age_min = _optional_number(candidate.get("age_min") or candidate.get("min_age"))
        age_max = _optional_number(candidate.get("age_max") or candidate.get("max_age"))
        if age_min is not None and age < age_min:
            continue
        if age_max is not None and age > age_max:
            continue
        if age_min is not None or age_max is not None:
            return True
    return False


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
    location = _json_or_text(item.get("location_json"))
    contact = _json_or_text(item.get("contact_json"))
    policy = _json_or_text(item.get("policy_json"))
    risk_tags = _json_or_text(item.get("risk_tags_json"))
    return " ".join(
        _text_part(part)
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
        if _text_part(part)
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


def _text_part(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value or "").strip()


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())).strip()


def _phrase_in_text(phrase: str, text: str) -> bool:
    return f" {phrase} " in f" {text} "


def _singularize(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _optional_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _price_value(pricing: Any) -> float:
    if not isinstance(pricing, dict):
        return 0.0
    for key in (
        "price",
        "amount",
        "premium",
        "premium_min",
        "monthly_premium",
        "annual_premium",
        "min_price",
        "starting_price",
    ):
        value = pricing.get(key)
        if value in (None, "", 0, 0.0, "0", "0.0"):
            continue
        try:
            number = float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return 0.0
