"""Client vertical persistence workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ClientVerticalUpdateWorkflows:
    safe_site_id: Callable[[str], str]
    validated_vertical: Callable[[str | None], Any]
    init_schema: Callable[[], None]
    connect: Callable[[], Any]
    record_audit_event_safely: Callable[..., None]
    get_client_detail: Callable[[str], dict[str, Any]]
    deleted_status: str


def update_client_vertical(
    site_id: str,
    vertical_key: str,
    workflows: ClientVerticalUpdateWorkflows,
) -> dict[str, Any]:
    """Change a client's vertical without touching tenant data."""
    clean_site_id = workflows.safe_site_id(site_id)
    vertical = workflows.validated_vertical(vertical_key)
    workflows.init_schema()
    with workflows.connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET vertical_key = %s,
                risk_level = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (vertical.key, vertical.risk_level, clean_site_id, workflows.deleted_status),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    workflows.record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="crm_admin",
        event_type="client_vertical_updated",
        event_scope="client_config",
        status="ok",
        message=f"Vertical changed to {vertical.key}.",
        metadata={"vertical_key": vertical.key, "risk_level": vertical.risk_level},
    )
    return workflows.get_client_detail(clean_site_id)
