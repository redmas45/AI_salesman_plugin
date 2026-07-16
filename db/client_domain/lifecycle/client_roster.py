"""CRM client roster read model and status transitions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable


# Roster dependencies isolate the CRM read model from persistence globals.
@dataclass(frozen=True)
class ClientRosterWorkflows:
    safe_site_id: Callable[[str], str]
    visible_client_rows: Callable[[Any], list[dict[str, Any]]]
    client_vertical: Callable[[str | None], Any]
    risk_level_text: Callable[[str | None, str], str]
    json_object: Callable[[Any], dict[str, Any]]
    script_tag_for_site: Callable[[str], str]
    runtime_status: Callable[[list[str]], dict[str, Any]]
    runtime_status_source_urls: Callable[[dict[str, Any]], list[str]]
    safe_catalog_summary: Callable[[str], dict[str, Any]]
    safe_catalog_preview: Callable[[str], list[dict[str, Any]]]
    safe_sync_history: Callable[[str], list[dict[str, Any]]]
    safe_answer_cache_summary: Callable[[str], dict[str, Any]]
    usage_summary: Callable[[str], dict[str, Any]]
    quota_status: Callable[[str], dict[str, Any]]
    panel_password_configured: Callable[[str], bool]
    panel_password_status: Callable[[str], str]
    ensure_default_client: Callable[[], None]
    init_admin_schema: Callable[[], None]
    connect: Callable[[], Any]
    deleted_status: str
    live_status: str
    disabled_status: str
    available_status: str


def list_clients(deps: ClientRosterWorkflows) -> list[dict[str, Any]]:
    """Return CRM clients with catalog and usage summaries."""
    deps.ensure_default_client()
    with deps.connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM hub_clients
            WHERE status <> %s
            ORDER BY created_at ASC
            """,
            (deps.deleted_status,),
        ).fetchall()
    visible_rows = deps.visible_client_rows(dict(row) for row in rows)
    return [client_summary(row, deps) for row in visible_rows]


def get_client_detail(site_id: str, deps: ClientRosterWorkflows) -> dict[str, Any]:
    """Return one client with full CRM-facing details."""
    deps.ensure_default_client()
    client = client_row(site_id, deps)
    if not client:
        raise LookupError(f"Client {site_id} was not found.")
    detail = client_summary(client, deps)
    detail["catalog_preview"] = deps.safe_catalog_preview(client["site_id"])
    detail["sync_runs"] = deps.safe_sync_history(client["site_id"])
    return detail


def remove_client(site_id: str, deps: ClientRosterWorkflows) -> None:
    """Hide a client from CRM lists while keeping tenant data for traceability."""
    update_client_status(site_id, deps.deleted_status, deps)


def move_client_to_available(site_id: str, deps: ClientRosterWorkflows) -> dict[str, Any]:
    """Move a current/disabled client back to the Available board."""
    update_client_status(site_id, deps.available_status, deps)
    return get_client_detail(site_id, deps)


def activate_client(site_id: str, deps: ClientRosterWorkflows) -> dict[str, Any]:
    """Promote an available/discovered client into the current live roster."""
    update_client_status(site_id, deps.live_status, deps)
    return get_client_detail(site_id, deps)


def set_client_enabled(site_id: str, enabled: bool, deps: ClientRosterWorkflows) -> dict[str, Any]:
    """Enable or disable a client widget from the CRM."""
    status = deps.live_status if enabled else deps.disabled_status
    update_client_status(site_id, status, deps)
    return get_client_detail(site_id, deps)


def client_summary(client: dict[str, Any], deps: ClientRosterWorkflows) -> dict[str, Any]:
    site_id = client["site_id"]
    panel_password_hash = client.get("panel_password_hash") or ""
    public_client = {key: value for key, value in client.items() if key != "panel_password_hash"}
    vertical = deps.client_vertical(public_client.get("vertical_key"))
    public_client["vertical_key"] = vertical.key
    public_client["vertical_label"] = vertical.label
    public_client["risk_level"] = deps.risk_level_text(public_client.get("risk_level"), vertical.risk_level)
    public_client["vertical_config"] = deps.json_object(public_client.pop("vertical_config_json", "{}"))
    panel_is_configured = deps.panel_password_configured(panel_password_hash)
    return {
        **public_client,
        "script_tag": deps.script_tag_for_site(site_id),
        "runtime_status": deps.runtime_status(deps.runtime_status_source_urls(public_client)),
        "catalog": deps.safe_catalog_summary(site_id),
        "answer_cache": deps.safe_answer_cache_summary(site_id),
        "usage": deps.usage_summary(site_id),
        "quota": deps.quota_status(site_id),
        "panel_password_configured": panel_is_configured,
        "panel_password_status": deps.panel_password_status(panel_password_hash),
        "panel_auth_version": _panel_auth_version(panel_password_hash) if panel_is_configured else "",
    }


def _panel_auth_version(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def client_row(site_id: str, deps: ClientRosterWorkflows) -> dict[str, Any] | None:
    deps.init_admin_schema()
    with deps.connect() as conn:
        row = conn.execute(
            "SELECT * FROM hub_clients WHERE site_id = %s AND status <> %s",
            (deps.safe_site_id(site_id), deps.deleted_status),
        ).fetchone()
    return dict(row) if row else None


def update_client_status(site_id: str, status: str, deps: ClientRosterWorkflows) -> None:
    deps.init_admin_schema()
    with deps.connect() as conn:
        cursor = conn.execute(
            "UPDATE hub_clients SET status = %s, updated_at = now() WHERE site_id = %s",
            (status, deps.safe_site_id(site_id)),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {site_id} was not found.")
