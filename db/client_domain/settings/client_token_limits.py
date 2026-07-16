"""Client token-limit update workflows."""

from __future__ import annotations

from typing import Any, Callable

from db.runtime.quota import MAX_CLIENT_TOKEN_LIMIT, MAX_SESSION_TOKEN_LIMIT


ConnectFactory = Callable[[], Any]


def update_client_session_token_limit(
    site_id: str,
    limit: int,
    *,
    safe_site_id: Callable[[str], str],
    init_schema: Callable[[], None],
    connect: ConnectFactory,
    deleted_status: str,
    get_client_detail: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    clean_site_id = safe_site_id(site_id)
    clean_limit = max(1, min(int(limit), MAX_SESSION_TOKEN_LIMIT))
    init_schema()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET session_token_limit = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (clean_limit, clean_site_id, deleted_status),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    return get_client_detail(clean_site_id)


def update_client_token_limits(
    site_id: str,
    token_limit: int,
    session_token_limit: int,
    *,
    safe_site_id: Callable[[str], str],
    init_schema: Callable[[], None],
    connect: ConnectFactory,
    deleted_status: str,
    get_client_detail: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    clean_site_id = safe_site_id(site_id)
    clean_token_limit = max(1, min(int(token_limit), MAX_CLIENT_TOKEN_LIMIT))
    clean_session_limit = max(1, min(int(session_token_limit), MAX_SESSION_TOKEN_LIMIT))
    if clean_session_limit > clean_token_limit:
        raise ValueError("Session token limit cannot be greater than the client token limit.")

    init_schema()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET token_limit = %s,
                session_token_limit = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (clean_token_limit, clean_session_limit, clean_site_id, deleted_status),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    return get_client_detail(clean_site_id)
