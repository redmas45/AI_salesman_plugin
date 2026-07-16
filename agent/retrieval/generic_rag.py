"""Generic knowledge-item retrieval for non-commerce verticals."""

from __future__ import annotations

import logging
import re
from typing import Any

import psycopg

import config
from agent.retrieval.product_rag import _embed, _clean_query_for_fts, _build_tsquery
from agent.retrieval.generic_items import (
    decode_item as _decode_item,
    json_or_text as _json_or_text,
    knowledge_item_to_text as _knowledge_item_to_text,
    optional_number as _optional_number,
    price_value as _price_value,
    text_part as _text_part,
)
from agent.retrieval.generic_lexical import (
    LEXICAL_ALIASES,
    LEXICAL_SCORE_FLOOR,
    LEXICAL_STOPWORDS,
    age_from_query as _age_from_query,
    age_matches_item as _age_matches_item,
    lexical_score as _lexical_score,
    normalize_text as _normalize_text,
    phrase_in_text as _phrase_in_text,
    query_terms as _query_terms,
    rank_lexical_items as _rank_lexical_items,
    singularize as _singularize,
)
from db.core.database import get_db, init_tenant_schema

logger = logging.getLogger(__name__)
DEFAULT_RETRIEVAL_LIMIT = 50
MAX_RETRIEVAL_LIMIT = 100
VECTORIZE_BATCH_SIZE = 256
SEMANTIC_SCORE_FLOOR = 0.22
LEXICAL_SCAN_LIMIT = 250


def retrieve_knowledge(
    query: str,
    *,
    site_id: str,
    entity_types: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve source-backed knowledge items for a non-ecommerce client using hybrid search."""
    init_tenant_schema(site_id)
    safe_limit = max(1, min(int(limit or config.RAG_TOP_N or DEFAULT_RETRIEVAL_LIMIT), MAX_RETRIEVAL_LIMIT))
    clean_types = [item for item in (entity_types or []) if item]

    # 1. Lexical search via FTS
    fts_results = _fts_knowledge_search(query, site_id, clean_types, safe_limit * 2)

    # 2. Semantic search
    try:
        semantic_results = _semantic_search(query, site_id, clean_types, safe_limit * 2)
    except (RuntimeError, psycopg.Error) as exc:
        logger.warning("Generic RAG semantic search failed for %s: %s", site_id, exc)
        semantic_results = []

    # 3. Fuzzy search
    fuzzy_results = _fuzzy_knowledge_search(query, site_id, clean_types, safe_limit * 2)
    # Merge via RRF
    merged = _rrf_merge_knowledge(fts_results, semantic_results, fuzzy_results, safe_limit)
    if merged:
        return merged

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
    try:
        from db.core.database import rebuild_knowledge_search_vectors
        rebuild_knowledge_search_vectors(site_id)
    except Exception as exc:
        logger.warning("Generic RAG | knowledge search_vector rebuild failed: %s", exc)
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


def _fts_knowledge_search(
    query: str,
    site_id: str,
    entity_types: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    """Full-text search using PostgreSQL tsvector/tsquery on knowledge items."""
    clean = _clean_query_for_fts(query)
    if not clean:
        return []
    try:
        tsquery = _build_tsquery(clean)
        type_clause = ""
        params = [tsquery, tsquery]
        if entity_types:
            type_clause = "AND entity_type = ANY(%s)"
            params.append(entity_types)
        params.append(limit)
        with get_db(site_id) as conn:
            rows = conn.execute(
                f"""
                SELECT *,
                       ts_rank_cd(search_vector, to_tsquery('english', %s), 32) AS _fts_rank
                FROM knowledge_items
                WHERE is_active = 1
                  AND search_vector IS NOT NULL
                  AND search_vector @@ to_tsquery('english', %s)
                  {type_clause}
                ORDER BY _fts_rank DESC
                LIMIT %s
                """,
                params,
            ).fetchall()
        results = [_decode_item(row) for row in rows]
        for r in results:
            r["_search_method"] = "lexical"
            r["_semantic_score"] = max(float(r.get("_fts_rank") or 0.0) * 2, 0.5)
        return results
    except Exception as exc:
        logger.warning("Generic RAG | Lexical FTS search failed: %s", exc)
        return []


def _fuzzy_knowledge_search(
    query: str,
    site_id: str,
    entity_types: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    """Fuzzy trigram search using pg_trgm for typo tolerance on knowledge item titles."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", query).strip()
    if len(clean) < 3:
        return []
    try:
        type_clause = ""
        params = [clean, clean, 0.15]
        if entity_types:
            type_clause = "AND entity_type = ANY(%s)"
            params.append(entity_types)
        params.extend([clean, limit])
        with get_db(site_id) as conn:
            rows = conn.execute(
                f"""
                SELECT *,
                       similarity(title, %s) AS _trgm_score
                FROM knowledge_items
                WHERE is_active = 1
                  AND similarity(title, %s) >= %s
                  {type_clause}
                ORDER BY similarity(title, %s) DESC
                LIMIT %s
                """,
                params,
            ).fetchall()
        results = [_decode_item(row) for row in rows]
        for r in results:
            r["_search_method"] = "fuzzy"
            r["_semantic_score"] = max(float(r.get("_trgm_score") or 0.0), 0.3)
        return results
    except Exception as exc:
        logger.warning("Generic RAG | Fuzzy search failed: %s", exc)
        return []


def _rrf_merge_knowledge(
    fts_res: list[dict[str, Any]],
    semantic_res: list[dict[str, Any]],
    fuzzy_res: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Merge results from multiple search strategies via Reciprocal Rank Fusion for knowledge items."""
    RRF_K = 60
    scores: dict[str, float] = {}
    item_map: dict[str, dict] = {}

    def _add_ranked(results: list[dict], weight: float) -> None:
        for rank, item in enumerate(results):
            iid = item.get("id")
            if iid is None:
                continue
            rrf_score = weight / (RRF_K + rank + 1)
            scores[iid] = scores.get(iid, 0.0) + rrf_score
            if iid not in item_map:
                item_map[iid] = item

    _add_ranked(fts_res, 1.2)
    _add_ranked(semantic_res, 1.0)
    _add_ranked(fuzzy_res, 0.6)

    sorted_ids = sorted(scores, key=lambda iid: scores[iid], reverse=True)

    result = []
    for iid in sorted_ids[:limit]:
        item = item_map[iid]
        item["_rrf_score"] = round(scores[iid], 4)
        if "_semantic_score" not in item or item.get("_search_method") == "lexical":
            item["_semantic_score"] = max(float(item.get("_semantic_score") or 0.0), 0.5)
        result.append(item)
    return result
