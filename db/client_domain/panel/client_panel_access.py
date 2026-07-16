"""Client panel password access workflows."""

from __future__ import annotations

from typing import Any, Callable


ConnectFactory = Callable[[], Any]


def verify_client_panel_password(
    site_id: str,
    password: str,
    *,
    safe_site_id: Callable[[str], str],
    client_row: Callable[[str], dict[str, Any] | None],
    set_default_panel_password: Callable[[str], str],
    verify_panel_password: Callable[[str, str], bool],
    get_client_detail: Callable[[str], dict[str, Any]],
    disabled_marker: str,
) -> dict[str, Any]:
    clean_site_id = safe_site_id(site_id)
    client = client_row(clean_site_id)
    if not client:
        raise LookupError(f"Client {clean_site_id} was not found.")
    password_hash = client.get("panel_password_hash") or ""
    if password_hash == disabled_marker:
        raise PermissionError("Client panel password is disabled.")
    if not password_hash:
        password_hash = set_default_panel_password(clean_site_id)
    if not verify_panel_password(password, password_hash):
        raise PermissionError("Invalid client panel credentials.")
    return get_client_detail(clean_site_id)


def update_client_panel_password(
    site_id: str,
    password: str,
    *,
    safe_site_id: Callable[[str], str],
    min_password_length: int,
    hash_panel_password: Callable[[str], str],
    init_schema: Callable[[], None],
    connect: ConnectFactory,
    deleted_status: str,
    record_audit_event_safely: Callable[..., None],
    get_client_detail: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    clean_site_id = safe_site_id(site_id)
    clean_password = str(password or "")
    if len(clean_password) < min_password_length:
        raise ValueError(f"Client panel password must be at least {min_password_length} characters.")
    password_hash = hash_panel_password(clean_password)
    init_schema()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET panel_password_hash = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (password_hash, clean_site_id, deleted_status),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="crm_admin",
        event_type="client_panel_password_updated",
        event_scope="security",
        status="ok",
        message="Client panel password updated.",
        metadata={"password_configured": True},
    )
    return get_client_detail(clean_site_id)


def revoke_client_panel_password(
    site_id: str,
    *,
    safe_site_id: Callable[[str], str],
    init_schema: Callable[[], None],
    connect: ConnectFactory,
    disabled_marker: str,
    deleted_status: str,
    get_client_detail: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    clean_site_id = safe_site_id(site_id)
    init_schema()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET panel_password_hash = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (disabled_marker, clean_site_id, deleted_status),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    return get_client_detail(clean_site_id)


def set_default_panel_password(
    site_id: str,
    *,
    default_password: str,
    min_password_length: int,
    default_panel_password_hash: Callable[[], str],
    safe_site_id: Callable[[str], str],
    connect: ConnectFactory,
) -> str:
    if len(default_password) < min_password_length:
        raise PermissionError("Client panel default password is not configured securely.")
    password_hash = default_panel_password_hash()
    if not password_hash:
        raise PermissionError("Client panel default password is not configured securely.")
    with connect() as conn:
        conn.execute(
            """
            UPDATE hub_clients
            SET panel_password_hash = %s,
                updated_at = now()
            WHERE site_id = %s
            """,
            (password_hash, safe_site_id(site_id)),
        )
        conn.commit()
    return password_hash
