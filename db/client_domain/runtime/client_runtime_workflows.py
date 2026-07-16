"""Client runtime config, action review, and validation workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from agent.adapters.adapter_repair import build_action_repair_proposals


@dataclass(frozen=True)
class ClientRuntimeWorkflows:
    safe_site_id: Callable[[str], str]
    safe_action_text: Callable[[Any], str]
    required_text: Callable[[Any, str], str]
    validated_vertical: Callable[[str | None], Any]
    client_vertical: Callable[[str | None], Any]
    json_object: Callable[[Any], dict[str, Any]]
    client_row: Callable[[str], dict[str, Any] | None]
    client_vertical_config: Callable[[str], dict[str, Any]]
    write_client_vertical_config: Callable[[str, dict[str, Any]], None]
    get_client_detail: Callable[[str], dict[str, Any]]
    get_client_vertical_key: Callable[[str], str]
    merge_discovery_vertical_config: Callable[..., dict[str, Any]]
    validated_action_map: Callable[[Any], dict[str, Any]]
    validated_adapter_validation: Callable[[Any], dict[str, Any]]
    action_candidate_review: Callable[..., dict[str, Any]]
    approve_action_candidate: Callable[[dict[str, Any], dict[str, Any], str], None]
    action_proposal_review: Callable[..., dict[str, Any]]
    approve_action_proposal: Callable[[dict[str, Any], dict[str, Any], str], None]
    flow_repair_review: Callable[..., dict[str, Any]]
    approve_flow_repair_proposal: Callable[[dict[str, Any], dict[str, Any]], None]
    merge_action_reviews: Callable[[dict[str, Any], Any], list[dict[str, Any]]]
    apply_validation_repairs: Callable[[dict[str, Any], dict[str, Any]], None]
    refresh_action_health: Callable[..., None]
    refresh_flow_repair_proposals: Callable[[str, dict[str, Any]], None]
    list_client_action_events: Callable[..., dict[str, list[dict[str, Any]]]]
    record_audit_event_safely: Callable[..., None]
    init_admin_schema: Callable[[], None]
    connect: Callable[[], Any]
    deleted_status: str
    action_health_event_window: int


def update_client_discovery_config(
    site_id: str,
    *,
    vertical_key: str,
    vertical_config: dict[str, Any],
    adapter_name: str,
    deps: ClientRuntimeWorkflows,
) -> dict[str, Any]:
    """Persist generated runtime config from one-line installer discovery."""
    clean_site_id = deps.safe_site_id(site_id)
    vertical = deps.validated_vertical(vertical_key)
    existing_client = deps.client_row(clean_site_id)
    existing_config = deps.json_object((existing_client or {}).get("vertical_config_json"))
    existing_vertical = deps.client_vertical((existing_client or {}).get("vertical_key")).key if existing_client else vertical.key
    merged_config = deps.merge_discovery_vertical_config(
        existing_config,
        vertical_config,
        vertical_changed=existing_vertical != vertical.key,
    )
    deps.init_admin_schema()
    with deps.connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET vertical_key = %s,
                vertical_config_json = %s,
                adapter_name = %s,
                risk_level = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (
                vertical.key,
                json.dumps(merged_config, ensure_ascii=False, default=str),
                deps.required_text(adapter_name, "Adapter name is required."),
                vertical.risk_level,
                clean_site_id,
                deps.deleted_status,
            ),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    deps.record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="widget",
        event_type="discovery_config_updated",
        event_scope="discovery",
        status="ok",
        message="Widget discovery config updated.",
        metadata={"vertical_key": vertical.key, "adapter_name": adapter_name},
    )
    return deps.get_client_detail(clean_site_id)


def update_client_adapter_actions(site_id: str, actions: dict[str, Any], deps: ClientRuntimeWorkflows) -> dict[str, Any]:
    """Replace a client's generated action map with a validated CRM override."""
    clean_site_id = deps.safe_site_id(site_id)
    vertical_config = deps.client_vertical_config(clean_site_id)
    vertical_config["actions"] = deps.validated_action_map(actions)
    vertical_config.setdefault("overrides", {})["actions"] = {
        "source": "crm",
        "updated": True,
    }
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    deps.record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="crm_admin",
        event_type="adapter_actions_updated",
        event_scope="adapter",
        status="ok",
        message="Adapter action map updated.",
        metadata={"action_count": len(vertical_config["actions"]), "actions": sorted(vertical_config["actions"])},
    )
    return deps.get_client_detail(clean_site_id)


def review_client_action_candidate(
    site_id: str,
    candidate: dict[str, Any],
    *,
    decision: str,
    action_name: str,
    note: str,
    deps: ClientRuntimeWorkflows,
) -> dict[str, Any]:
    """Approve or reject one discovered adapter action candidate."""
    clean_site_id = deps.safe_site_id(site_id)
    clean_decision = deps.safe_action_text(decision).lower()
    if clean_decision not in {"approve", "reject"}:
        raise ValueError("Action candidate decision must be approve or reject.")

    vertical_config = deps.client_vertical_config(clean_site_id)
    review = deps.action_candidate_review(candidate, clean_decision, action_name=action_name, note=note)
    if clean_decision == "approve":
        deps.approve_action_candidate(vertical_config, candidate, review["action"])
    vertical_config["action_reviews"] = deps.merge_action_reviews(review, vertical_config.get("action_reviews"))
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def refresh_client_action_proposals(site_id: str, deps: ClientRuntimeWorkflows) -> dict[str, Any]:
    """Rebuild CRM-reviewable adapter action repair proposals from current evidence."""
    clean_site_id = deps.safe_site_id(site_id)
    vertical_config = deps.client_vertical_config(clean_site_id)
    vertical_config["action_proposals"] = build_action_repair_proposals(
        vertical_config=vertical_config,
        vertical_key=deps.get_client_vertical_key(clean_site_id),
    )
    deps.refresh_flow_repair_proposals(clean_site_id, vertical_config)
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def review_client_action_proposal(
    site_id: str,
    proposal: dict[str, Any],
    *,
    decision: str,
    note: str,
    deps: ClientRuntimeWorkflows,
) -> dict[str, Any]:
    """Approve or reject one generated adapter repair proposal."""
    clean_site_id = deps.safe_site_id(site_id)
    clean_decision = deps.safe_action_text(decision).lower()
    if clean_decision not in {"approve", "reject"}:
        raise ValueError("Action proposal decision must be approve or reject.")

    vertical_config = deps.client_vertical_config(clean_site_id)
    review = deps.action_proposal_review(proposal, clean_decision, note=note)
    if clean_decision == "approve":
        deps.approve_action_proposal(vertical_config, proposal, review["action"])
    vertical_config["action_proposal_reviews"] = deps.merge_action_reviews(
        review,
        vertical_config.get("action_proposal_reviews"),
    )
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def review_client_flow_repair_proposal(
    site_id: str,
    proposal: dict[str, Any],
    *,
    decision: str,
    note: str,
    deps: ClientRuntimeWorkflows,
) -> dict[str, Any]:
    """Approve or reject one generated flow repair proposal."""
    clean_site_id = deps.safe_site_id(site_id)
    clean_decision = deps.safe_action_text(decision).lower()
    if clean_decision not in {"approve", "reject"}:
        raise ValueError("Flow repair proposal decision must be approve or reject.")

    vertical_config = deps.client_vertical_config(clean_site_id)
    review = deps.flow_repair_review(proposal, clean_decision, note=note)
    if clean_decision == "approve":
        deps.approve_flow_repair_proposal(vertical_config, proposal)
    vertical_config["flow_repair_reviews"] = deps.merge_action_reviews(
        review,
        vertical_config.get("flow_repair_reviews"),
    )
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def save_adapter_validation_report(
    site_id: str,
    report: dict[str, Any],
    deps: ClientRuntimeWorkflows,
) -> dict[str, Any]:
    """Persist browser runtime validation and apply high-confidence repairs."""
    clean_site_id = deps.safe_site_id(site_id)
    vertical_config = deps.client_vertical_config(clean_site_id)
    validation = deps.validated_adapter_validation(report)
    vertical_config["validation"] = validation
    deps.apply_validation_repairs(vertical_config, validation)
    deps.refresh_action_health(
        vertical_config,
        events=deps.list_client_action_events({clean_site_id}, limit=deps.action_health_event_window).get(
            clean_site_id,
            [],
        ),
    )
    deps.refresh_flow_repair_proposals(clean_site_id, vertical_config)
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)
