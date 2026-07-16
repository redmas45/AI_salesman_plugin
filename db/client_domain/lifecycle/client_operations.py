"""Operational client helpers for widget state, setup status, and usage events."""

from __future__ import annotations

import config
from db.client_domain.core.client_identity import safe_session_id, safe_site_id
from db.core.schema import _connect, init_admin_schema
from db.settings.settings_manager import _public_hub_origin

CLIENT_STATUS_LIVE = "live"


def is_client_widget_enabled(site_id: str) -> bool:
    """Return whether the public widget should boot for this client."""
    row = client_status_row(site_id)
    if row is None:
        return True
    return row["status"] == CLIENT_STATUS_LIVE


def client_status_row(site_id: str) -> dict[str, object] | None:
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT status FROM hub_clients WHERE site_id = %s",
            (safe_site_id(site_id),),
        ).fetchone()
    return dict(row) if row else None


def update_client_crawl_status(site_id: str, status: str, message: str = "") -> None:
    """Persist crawler state for a client row."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE hub_clients
            SET last_crawl_status = %s,
                last_crawl_message = %s,
                last_crawl_at = now(),
                updated_at = now()
            WHERE site_id = %s
            """,
            (status, message[:500], safe_site_id(site_id)),
        )
        conn.commit()


def update_client_setup_status(site_id: str, needs_setup: bool, last_setup_at: str | None = None) -> None:
    """Persist setup state and drift flagging for a client row."""
    init_admin_schema()
    with _connect() as conn:
        if last_setup_at:
            conn.execute(
                """
                UPDATE hub_clients
                SET needs_setup = %s,
                    last_setup_at = %s,
                    updated_at = now()
                WHERE site_id = %s
                """,
                (needs_setup, last_setup_at, safe_site_id(site_id)),
            )
        else:
            conn.execute(
                """
                UPDATE hub_clients
                SET needs_setup = %s,
                    updated_at = now()
                WHERE site_id = %s
                """,
                (needs_setup, safe_site_id(site_id)),
            )
        conn.commit()


def script_tag_for_site(site_id: str) -> str:
    """Build the one-line script tag for a client site."""
    clean_site_id = safe_site_id(site_id)
    origin = _public_hub_origin()
    return (
        f'<script defer src="{origin}/install.js?site={clean_site_id}" '
        f'data-site-id="{clean_site_id}"></script>'
    )


def record_usage_event(
    *,
    site_id: str,
    session_id: str = "",
    transport: str,
    status: str,
    transcript: str,
    response_text: str,
    intent: str,
    action_count: int,
    latency_ms: float,
) -> None:
    """Store one customer turn for CRM usage reporting."""
    init_admin_schema()
    clean_site_id = safe_site_id(site_id)
    clean_session_id = safe_session_id(session_id, clean_site_id)

    from db.runtime.quota import estimate_tokens, _ensure_conversation_session

    input_tokens = estimate_tokens(transcript)
    output_tokens = estimate_tokens(response_text)
    total_tokens = input_tokens + output_tokens
    _ensure_conversation_session(clean_site_id, clean_session_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_usage_events
                (
                    site_id, session_id, transport, status, input_tokens, output_tokens,
                    latency_ms, intent, action_count, transcript, response_text
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                clean_site_id,
                clean_session_id,
                transport,
                status,
                input_tokens,
                output_tokens,
                max(float(latency_ms or 0), 0.0),
                intent[:100],
                max(int(action_count), 0),
                str(transcript or "")[: config.MAX_TRANSCRIPT_CHARS],
                str(response_text or "")[: config.MAX_RESPONSE_CHARS],
            ),
        )
        conn.execute(
            """
            UPDATE hub_conversation_sessions
            SET token_used = token_used + %s,
                turn_count = turn_count + 1,
                last_seen_at = now()
            WHERE site_id = %s AND session_id = %s
            """,
            (total_tokens, clean_site_id, clean_session_id),
        )
        conn.commit()
