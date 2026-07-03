"""Admin-schema rolling session memory for runtime conversations."""

from __future__ import annotations

import logging
from typing import Any

from agent.context_budget import summarize_turns
from db.clients import _safe_session_id, _safe_site_id
from db.quota import _ensure_conversation_session
from db.schema import _connect, init_admin_schema

logger = logging.getLogger(__name__)


def get_session_summary(site_id: str, session_id: str) -> str:
    clean_session_id = str(session_id or "").strip()
    if not clean_session_id:
        return ""
    clean_site_id = _safe_site_id(site_id)
    clean_session_id = _safe_session_id(clean_session_id, clean_site_id)
    try:
        init_admin_schema()
        _ensure_conversation_session(clean_site_id, clean_session_id)
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT summary_text
                FROM hub_conversation_sessions
                WHERE site_id = %s AND session_id = %s
                """,
                (clean_site_id, clean_session_id),
            ).fetchone()
        return str(row.get("summary_text") or "") if row else ""
    except Exception as exc:
        logger.warning("Session summary lookup failed for %s/%s: %s", clean_site_id, clean_session_id, exc)
        return ""


def update_session_summary(
    site_id: str,
    session_id: str,
    *,
    history: list[dict[str, Any]] | None = None,
    transcript: str = "",
    response_text: str = "",
) -> str:
    clean_session_id = str(session_id or "").strip()
    if not clean_session_id:
        return ""
    clean_site_id = _safe_site_id(site_id)
    clean_session_id = _safe_session_id(clean_session_id, clean_site_id)
    try:
        existing = get_session_summary(clean_site_id, clean_session_id)
        summary = summarize_turns(existing, history or [], transcript, response_text)
        init_admin_schema()
        _ensure_conversation_session(clean_site_id, clean_session_id)
        with _connect() as conn:
            conn.execute(
                """
                UPDATE hub_conversation_sessions
                SET summary_text = %s,
                    summary_updated_at = now(),
                    last_seen_at = now()
                WHERE site_id = %s AND session_id = %s
                """,
                (summary, clean_site_id, clean_session_id),
            )
            conn.commit()
        return summary
    except Exception as exc:
        logger.warning("Session summary update failed for %s/%s: %s", clean_site_id, clean_session_id, exc)
        return ""
