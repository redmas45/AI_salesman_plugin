"""Tenant-local answer cache and data-version helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg

from db.database import get_db, init_tenant_schema

RUNTIME_DATA_SCOPE = "runtime_data"
DEFAULT_CACHE_TTL_DAYS = 30
SEMANTIC_CACHE_THRESHOLD = 0.88
MAX_CACHE_QUESTION_CHARS = 500
MAX_CACHE_ANSWER_CHARS = 3000
MAX_CACHE_ACTIONS = 5


def normalize_question(text: str) -> str:
    """Normalize a customer question for exact cache matching."""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()
    return re.sub(r"\s+", " ", normalized)[:MAX_CACHE_QUESTION_CHARS]


def current_data_version(site_id: str) -> int:
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        row = conn.execute(
            """
            INSERT INTO tenant_data_versions (scope, version, reason)
            VALUES (%s, 1, 'initial')
            ON CONFLICT (scope) DO UPDATE SET scope = EXCLUDED.scope
            RETURNING version
            """,
            (RUNTIME_DATA_SCOPE,),
        ).fetchone()
    return int(row["version"] if row else 1)


def bump_data_version(site_id: str, reason: str = "data_changed") -> int:
    """Bump the tenant runtime-data version and mark cached answers stale."""
    init_tenant_schema(site_id)
    clean_reason = str(reason or "data_changed")[:200]
    with get_db(site_id) as conn:
        row = conn.execute(
            """
            INSERT INTO tenant_data_versions (scope, version, reason, updated_at)
            VALUES (%s, 2, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (scope) DO UPDATE SET
                version = tenant_data_versions.version + 1,
                reason = EXCLUDED.reason,
                updated_at = CURRENT_TIMESTAMP
            RETURNING version
            """,
            (RUNTIME_DATA_SCOPE, clean_reason),
        ).fetchone()
        conn.execute(
            """
            UPDATE answer_cache
            SET is_stale = 1,
                stale_reason = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE is_stale = 0
            """,
            (clean_reason,),
        )
    return int(row["version"] if row else 1)


def lookup_answer_cache(site_id: str, question: str) -> dict[str, Any] | None:
    """Return a fresh exact or semantic cached answer for this tenant."""
    normalized = normalize_question(question)
    if not normalized:
        return None
    data_version = current_data_version(site_id)
    exact = _exact_cache_match(site_id, normalized, data_version)
    if exact:
        return _record_cache_hit(site_id, exact, match_type="exact", score=1.0)
    semantic = _semantic_cache_match(site_id, question, data_version)
    if semantic:
        return _record_cache_hit(
            site_id,
            semantic["row"],
            match_type="semantic",
            score=float(semantic.get("score") or 0.0),
        )
    return None


def store_answer_cache(
    site_id: str,
    *,
    question: str,
    answer_text: str,
    answer_scope: str,
    cache_type: str,
    source_ids: list[str] | None = None,
    source_urls: list[str] | None = None,
    ui_actions: list[dict[str, Any]] | None = None,
    confidence: float = 0.0,
    ttl_days: int = DEFAULT_CACHE_TTL_DAYS,
) -> dict[str, Any] | None:
    """Upsert a safe answer into the tenant-local cache."""
    normalized = normalize_question(question)
    answer = str(answer_text or "").strip()[:MAX_CACHE_ANSWER_CHARS]
    if not normalized or not answer:
        return None
    data_version = current_data_version(site_id)
    embedding = _embed_question(question)
    expires_at = datetime.now(timezone.utc) + timedelta(days=max(1, int(ttl_days)))
    payload = (
        normalized,
        str(question or "").strip()[:MAX_CACHE_QUESTION_CHARS],
        embedding,
        answer,
        str(answer_scope or "grounded_fact")[:80],
        str(cache_type or "llm")[:80],
        json.dumps(_safe_text_list(source_ids), ensure_ascii=False),
        json.dumps(_safe_text_list(source_urls), ensure_ascii=False),
        json.dumps((ui_actions or [])[:MAX_CACHE_ACTIONS], ensure_ascii=False, default=str),
        max(0.0, min(float(confidence or 0.0), 1.0)),
        data_version,
        expires_at,
    )
    with get_db(site_id) as conn:
        row = conn.execute(
            """
            INSERT INTO answer_cache
                (
                    normalized_question, question, question_embedding, answer_text,
                    answer_scope, cache_type, source_ids_json, source_urls_json,
                    ui_actions_json, confidence, data_version, expires_at
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (normalized_question, data_version) DO UPDATE SET
                question = EXCLUDED.question,
                question_embedding = EXCLUDED.question_embedding,
                answer_text = EXCLUDED.answer_text,
                answer_scope = EXCLUDED.answer_scope,
                cache_type = EXCLUDED.cache_type,
                source_ids_json = EXCLUDED.source_ids_json,
                source_urls_json = EXCLUDED.source_urls_json,
                ui_actions_json = EXCLUDED.ui_actions_json,
                confidence = EXCLUDED.confidence,
                is_stale = 0,
                stale_reason = '',
                expires_at = EXCLUDED.expires_at,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            payload,
        ).fetchone()
    return _decode_cache_row(dict(row)) if row else None


def answer_cache_summary(site_id: str, limit: int = 10) -> dict[str, Any]:
    """Return CRM-safe cache stats for one tenant."""
    init_tenant_schema(site_id)
    data_version = current_data_version(site_id)
    safe_limit = max(1, min(int(limit or 10), 100))
    with get_db(site_id) as conn:
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE is_stale = 0 AND data_version = %s) AS fresh,
                COUNT(*) FILTER (WHERE is_stale = 1 OR data_version <> %s) AS stale,
                COALESCE(SUM(hit_count), 0) AS hits
            FROM answer_cache
            """,
            (data_version, data_version),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT *
            FROM answer_cache
            ORDER BY hit_count DESC, updated_at DESC
            LIMIT %s
            """,
            (safe_limit,),
        ).fetchall()
    items = [_decode_cache_row(dict(row), current_version=data_version) for row in rows]
    token_savings = sum(int(item.get("hit_count") or 0) * _estimated_tokens(item.get("answer_text")) for item in items)
    return {
        "site_id": site_id,
        "data_version": data_version,
        "total": int(stats["total"] if stats else 0),
        "fresh": int(stats["fresh"] if stats else 0),
        "stale": int(stats["stale"] if stats else 0),
        "hits": int(stats["hits"] if stats else 0),
        "estimated_tokens_saved": token_savings,
        "items": items,
    }


def _exact_cache_match(site_id: str, normalized: str, data_version: int) -> dict[str, Any] | None:
    with get_db(site_id) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM answer_cache
            WHERE normalized_question = %s
              AND data_version = %s
              AND is_stale = 0
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (normalized, data_version),
        ).fetchone()
    return dict(row) if row else None


def _semantic_cache_match(site_id: str, question: str, data_version: int) -> dict[str, Any] | None:
    embedding = _embed_question(question)
    with get_db(site_id) as conn:
        row = conn.execute(
            """
            SELECT *,
                   1 - (question_embedding <=> %s) AS _semantic_score
            FROM answer_cache
            WHERE question_embedding IS NOT NULL
              AND data_version = %s
              AND is_stale = 0
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY question_embedding <=> %s
            LIMIT 1
            """,
            (embedding, data_version, embedding),
        ).fetchone()
    if not row:
        return None
    score = float(row.get("_semantic_score") or 0.0)
    if score < SEMANTIC_CACHE_THRESHOLD:
        return None
    return {"row": dict(row), "score": score}


def _record_cache_hit(site_id: str, row: dict[str, Any], *, match_type: str, score: float) -> dict[str, Any]:
    cache_id = row.get("id")
    with get_db(site_id) as conn:
        updated = conn.execute(
            """
            UPDATE answer_cache
            SET hit_count = hit_count + 1,
                last_hit_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING *
            """,
            (cache_id,),
        ).fetchone()
    result = _decode_cache_row(dict(updated or row))
    result["cache_hit"] = True
    result["match_type"] = match_type
    result["match_score"] = round(float(score or 0.0), 4)
    return result


def _decode_cache_row(row: dict[str, Any], current_version: int | None = None) -> dict[str, Any]:
    data_version = int(row.get("data_version") or 0)
    current = int(current_version if current_version is not None else data_version)
    return {
        "id": row.get("id"),
        "normalized_question": str(row.get("normalized_question") or ""),
        "question": str(row.get("question") or ""),
        "answer_text": str(row.get("answer_text") or ""),
        "answer_scope": str(row.get("answer_scope") or ""),
        "cache_type": str(row.get("cache_type") or ""),
        "source_ids": _json_list(row.get("source_ids_json")),
        "source_urls": _json_list(row.get("source_urls_json")),
        "ui_actions": _json_list(row.get("ui_actions_json")),
        "confidence": float(row.get("confidence") or 0.0),
        "data_version": data_version,
        "is_stale": bool(row.get("is_stale")) or data_version != current,
        "stale_reason": str(row.get("stale_reason") or ""),
        "hit_count": int(row.get("hit_count") or 0),
        "last_hit_at": _text(row.get("last_hit_at")),
        "updated_at": _text(row.get("updated_at")),
    }


def _embed_question(question: str) -> Any:
    from agent.rag import _embed

    return _embed([str(question or "")[:MAX_CACHE_QUESTION_CHARS]])[0]


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    try:
        decoded = json.loads(str(value or "[]"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
    return decoded if isinstance(decoded, list) else []


def _safe_text_list(values: list[str] | None) -> list[str]:
    return [str(value or "").strip()[:500] for value in (values or []) if str(value or "").strip()][:30]


def _estimated_tokens(text: Any) -> int:
    return max(1, len(str(text or "")) // 4) if str(text or "").strip() else 0


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
