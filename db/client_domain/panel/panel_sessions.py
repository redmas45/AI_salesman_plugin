"""Server-side revocation for client-panel sessions.

Signing out used to be a browser-only act: the token was dropped from local
storage but stayed valid until expiry, so a captured token still worked. This
store records revoked session ids so a signed-out token is rejected on the
server.

Revocation is keyed by (site_id, session_id), so signing out one device never
disturbs the owner's other sessions or any other client. Rows are pruned once the
token they refer to could no longer be valid anyway.
"""

from __future__ import annotations

import logging
import time

from db.core.schema import _connect, init_admin_schema

logger = logging.getLogger(__name__)

MAX_SESSION_ID_CHARS = 128


def _clean(value: str, limit: int = MAX_SESSION_ID_CHARS) -> str:
    return str(value or "").strip()[:limit]


def revoke_panel_session(site_id: str, session_id: str, expires_at: int | None = None) -> bool:
    """Mark one client-panel session as signed out. Idempotent."""
    safe_site_id = _clean(site_id)
    safe_session_id = _clean(session_id)
    if not safe_site_id or not safe_session_id:
        return False

    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_client_panel_revoked_sessions (site_id, session_id, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (site_id, session_id) DO NOTHING
            """,
            (safe_site_id, safe_session_id, int(expires_at) if expires_at else None),
        )
        conn.commit()
    return True


def panel_session_is_revoked(site_id: str, session_id: str) -> bool:
    """True when this session was signed out.

    Raises on storage failure so the caller can fail closed: silently returning
    False here would let a signed-out token keep working during an outage.
    """
    safe_site_id = _clean(site_id)
    safe_session_id = _clean(session_id)
    if not safe_site_id or not safe_session_id:
        return True

    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT 1 AS revoked
            FROM hub_client_panel_revoked_sessions
            WHERE site_id = %s AND session_id = %s
            LIMIT 1
            """,
            (safe_site_id, safe_session_id),
        ).fetchone()
    return bool(row)


def purge_expired_revocations(now: int | None = None) -> int:
    """Drop revocations whose tokens have expired anyway. Best-effort."""
    cutoff = int(now if now is not None else time.time())
    try:
        init_admin_schema()
        with _connect() as conn:
            deleted = conn.execute(
                "DELETE FROM hub_client_panel_revoked_sessions WHERE expires_at IS NOT NULL AND expires_at < %s",
                (cutoff,),
            ).rowcount
            conn.commit()
        return int(deleted or 0)
    except Exception as exc:
        logger.warning("Client panel revocation purge failed: %s", exc)
        return 0
