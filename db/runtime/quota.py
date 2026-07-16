"""Quota and token usage limits checking for AI Hub CRM."""

from __future__ import annotations

import logging
from typing import Any

from db.core.schema import _connect, init_admin_schema

logger = logging.getLogger(__name__)

TOKEN_CHAR_RATIO = 4
DEFAULT_CLIENT_TOKEN_LIMIT = 5000
DEFAULT_SESSION_TOKEN_LIMIT = 1000
MAX_CLIENT_TOKEN_LIMIT = 1_000_000_000
MAX_SESSION_TOKEN_LIMIT = 1_000_000


class TokenQuotaExceededError(RuntimeError):
    """Raised when a client or session has exhausted its token budget."""


def estimate_tokens(text: str) -> int:
    """Return a rough token estimate for providers that do not expose usage."""
    clean_text = str(text or "").strip()
    if not clean_text:
        return 0
    return max(1, len(clean_text) // TOKEN_CHAR_RATIO)


def assert_usage_allowed(site_id: str, session_id: str = "") -> None:
    """Raise when the client or current session has no token budget left."""
    quota = quota_status(site_id, session_id)
    if quota["client"]["remaining"] <= 0:
        raise TokenQuotaExceededError("Client token quota is exhausted.")
    if quota["session"]["remaining"] <= 0:
        raise TokenQuotaExceededError("Session token quota is exhausted.")


def quota_status(site_id: str, session_id: str = "") -> dict[str, Any]:
    """Return client and session token quota state."""
    from db.client_domain.client_facade import _client_row, _safe_site_id, _safe_session_id

    clean_site_id = _safe_site_id(site_id)
    client = _client_row(clean_site_id)
    client_limit = int(client.get("token_limit") or DEFAULT_CLIENT_TOKEN_LIMIT) if client else DEFAULT_CLIENT_TOKEN_LIMIT
    session_limit = (
        int(client.get("session_token_limit") or DEFAULT_SESSION_TOKEN_LIMIT)
        if client
        else DEFAULT_SESSION_TOKEN_LIMIT
    )
    clean_session_id = _safe_session_id(session_id, clean_site_id) if session_id else ""
    if clean_session_id:
        _ensure_conversation_session(clean_site_id, clean_session_id, token_limit=session_limit)
    client_used = _usage_summary(clean_site_id)["tokens_estimated"]
    session_used = _session_token_total(clean_site_id, clean_session_id) if clean_session_id else 0
    return {
        "site_id": clean_site_id,
        "session_id": clean_session_id,
        "client": _quota_part(client_used, client_limit),
        "session": _quota_part(session_used, session_limit),
    }


def _usage_summary(site_id: str | None = None) -> dict[str, Any]:
    from db.client_domain.client_facade import _safe_site_id

    init_admin_schema()
    where_clause = "WHERE site_id = %s" if site_id else ""
    params = (_safe_site_id(site_id),) if site_id else ()
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_turns,
                COUNT(*) FILTER (WHERE created_at >= date_trunc('day', now())) AS turns_today,
                COALESCE(SUM(input_tokens + output_tokens), 0) AS tokens_estimated,
                COALESCE(ROUND(AVG(NULLIF(latency_ms, 0))::numeric, 0), 0) AS avg_latency_ms
            FROM hub_usage_events
            {where_clause}
            """,
            params,
        ).fetchone()
    return {
        "total_turns": int(row["total_turns"] if row else 0),
        "turns_today": int(row["turns_today"] if row else 0),
        "tokens_estimated": int(row["tokens_estimated"] if row else 0),
        "avg_latency_ms": int(row["avg_latency_ms"] if row else 0),
    }


def _quota_part(used: int, limit: int) -> dict[str, int]:
    clean_limit = max(int(limit or 0), 0)
    clean_used = max(int(used or 0), 0)
    return {
        "used": clean_used,
        "limit": clean_limit,
        "remaining": max(clean_limit - clean_used, 0),
    }


def _session_token_total(site_id: str, session_id: str) -> int:
    from db.client_domain.client_facade import _safe_site_id, _safe_session_id

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(input_tokens + output_tokens), 0) AS total
            FROM hub_usage_events
            WHERE site_id = %s AND session_id = %s
            """,
            (_safe_site_id(site_id), _safe_session_id(session_id, _safe_site_id(site_id))),
        ).fetchone()
    return int(row["total"] if row else 0)


def _client_session_limit(site_id: str) -> int:
    from db.client_domain.client_facade import _client_row

    client = _client_row(site_id)
    if not client:
        return DEFAULT_SESSION_TOKEN_LIMIT
    return int(client.get("session_token_limit") or DEFAULT_SESSION_TOKEN_LIMIT)


def _ensure_conversation_session(site_id: str, session_id: str, token_limit: int | None = None) -> None:
    from db.client_domain.client_facade import _safe_site_id, _safe_session_id

    clean_site_id = _safe_site_id(site_id)
    clean_session_id = _safe_session_id(session_id, clean_site_id)
    limit = int(token_limit or _client_session_limit(clean_site_id))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_conversation_sessions (site_id, session_id, token_limit)
            VALUES (%s, %s, %s)
            ON CONFLICT (site_id, session_id) DO UPDATE SET
                token_limit = EXCLUDED.token_limit,
                last_seen_at = hub_conversation_sessions.last_seen_at
            """,
            (clean_site_id, clean_session_id, limit),
        )
        conn.commit()
