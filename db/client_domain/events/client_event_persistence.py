"""Persistence workflows for client runtime and interaction events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


# Dependency injection keeps event persistence independently testable from the facade.
@dataclass(frozen=True)
class ClientEventPersistence:
    safe_site_id: Callable[[str], str]
    client_vertical_config: Callable[[str], dict[str, Any]]
    write_client_vertical_config: Callable[[str, dict[str, Any]], None]
    get_client_detail: Callable[[str], dict[str, Any]]
    get_client_vertical_key: Callable[[str], str]
    validated_policy_event: Callable[[dict[str, Any]], dict[str, Any]]
    validated_action_event: Callable[[dict[str, Any]], dict[str, Any]]
    validated_interaction_event: Callable[[dict[str, Any]], dict[str, Any]]
    enrich_interaction_event: Callable[[dict[str, Any], str], dict[str, Any]]
    action_config_from_interaction: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]]
    safe_flow_list: Callable[[Any, int], list[dict[str, Any]]]
    merge_interaction_candidate: Callable[[Any, dict[str, Any]], list[dict[str, Any]]]
    merge_learned_action: Callable[[Any, str, dict[str, Any]], dict[str, Any]]
    insert_client_action_event: Callable[[str, dict[str, Any]], None]
    list_client_action_events: Callable[[set[str], int], dict[str, list[dict[str, Any]]]]
    record_audit_event: Callable[..., None]
    refresh_action_health: Callable[[dict[str, Any]], None]
    terminal_statuses: frozenset[str]
    action_health_event_window: int


def save_client_policy_event(site_id: str, event: dict[str, Any], deps: ClientEventPersistence) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(event, dict):
        raise ValueError("Policy event must be a JSON object.")
    clean_event = deps.validated_policy_event(event)
    deps.record_audit_event(
        site_id=clean_site_id,
        actor_type="browser_runtime",
        event_type="policy_event",
        event_scope="runtime",
        status=clean_event["status"],
        action=clean_event["action"],
        message=clean_event["reason"],
        metadata={"url": clean_event["url"], "policy": clean_event["policy"]},
    )
    vertical_config = deps.client_vertical_config(clean_site_id)
    existing = vertical_config.get("policy_events")
    events = existing if isinstance(existing, list) else []
    vertical_config["policy_events"] = [clean_event, *deps.safe_flow_list(events, 29)]
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def save_client_action_event(site_id: str, event: dict[str, Any], deps: ClientEventPersistence) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(event, dict):
        raise ValueError("Action execution event must be a JSON object.")
    clean_event = deps.validated_action_event(event)
    deps.insert_client_action_event(clean_site_id, clean_event)
    if clean_event["status"] in deps.terminal_statuses:
        _record_terminal_action_event(clean_site_id, clean_event, deps)
    vertical_config = deps.client_vertical_config(clean_site_id)
    recent_events = deps.list_client_action_events(
        {clean_site_id},
        limit=deps.action_health_event_window,
    ).get(clean_site_id, [])
    deps.refresh_action_health(vertical_config, events=recent_events or [clean_event])
    vertical_config.pop("action_events", None)
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def _record_terminal_action_event(
    clean_site_id: str,
    clean_event: dict[str, Any],
    deps: ClientEventPersistence,
) -> None:
    deps.record_audit_event(
        site_id=clean_site_id,
        actor_type="browser_runtime",
        event_type="action_terminal",
        event_scope="runtime_action",
        status=clean_event["status"],
        request_id=clean_event["request_id"],
        action=clean_event["action"],
        message=clean_event["reason"],
        metadata={
            "turn_id": clean_event["turn_id"],
            "sequence": clean_event["sequence"],
            "stage": clean_event["stage"],
            "requested_url": clean_event["requested_url"],
            "final_url": clean_event["final_url"],
        },
    )


def save_client_interaction_event(
    site_id: str,
    event: dict[str, Any],
    deps: ClientEventPersistence,
) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(event, dict):
        raise ValueError("Interaction event must be a JSON object.")
    vertical_config = deps.client_vertical_config(clean_site_id)
    existing = vertical_config.get("interaction_events")
    events = existing if isinstance(existing, list) else []
    clean_event = deps.enrich_interaction_event(
        deps.validated_interaction_event(event),
        deps.get_client_vertical_key(clean_site_id),
    )
    vertical_config["interaction_events"] = [clean_event, *deps.safe_flow_list(events, 49)]
    vertical_config["action_candidates"] = deps.merge_interaction_candidate(
        vertical_config.get("action_candidates"),
        clean_event,
    )
    action_name, action_config = deps.action_config_from_interaction(clean_event)
    if action_name and action_config:
        vertical_config["actions"] = deps.merge_learned_action(
            vertical_config.get("actions"),
            action_name,
            action_config,
        )
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)
