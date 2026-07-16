"""Action-health and runtime-repair helpers for client adapter configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agent.actions.registry import is_supported_action, normalize_action_name
from agent.adapters.adapter_interaction_learning import action_config_from_interaction
from db.client_domain.actions.client_action_configs import validated_action_config
from db.client_domain.events.client_events import safe_action_status, validated_action_event
from db.client_domain.core.client_serialization import (
    dict_config,
    safe_action_stage,
    safe_action_text,
    safe_confidence,
    safe_flow_list,
    safe_int,
    safe_text_list,
)

VALIDATION_REPAIR_THRESHOLD = 0.65
ACTION_HEALTH_FAILURE_THRESHOLD = 3
ACTION_HEALTH_EVENT_WINDOW = 12
ACTION_HEALTH_FAILURE_STATUSES = frozenset({"failed", "error"})


def has_crm_action_override(vertical_config: dict[str, Any]) -> bool:
    overrides = dict_config(vertical_config.get("overrides"))
    action_override = dict_config(overrides.get("actions"))
    return safe_action_text(action_override.get("source")).lower() == "crm"


def refresh_action_health(vertical_config: dict[str, Any], *, events: list[dict[str, Any]] | None = None) -> None:
    action_events = safe_flow_list(events, 50)
    validation = dict_config(vertical_config.get("validation"))
    repair_candidates = runtime_repair_candidates(vertical_config)
    health = action_health_from_events(action_events, validation, repair_candidates)
    applied_repairs = apply_action_health_repairs(vertical_config, health)
    if applied_repairs:
        health = mark_action_health_repairs_applied(health, applied_repairs)
        vertical_config["action_repairs"] = merge_action_repairs(
            applied_repairs,
            vertical_config.get("action_repairs"),
        )
    vertical_config["action_health"] = health


def action_health_from_events(
    events: list[dict[str, Any]],
    validation: dict[str, Any],
    repair_candidates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw_event in events[:ACTION_HEALTH_EVENT_WINDOW]:
        event = validated_action_event(raw_event)
        action_name = event["action"]
        if not action_name or not is_supported_action(action_name):
            continue
        grouped.setdefault(action_name, []).append(event)

    action_rows = {
        action_name: action_health_row(
            action_name,
            action_events,
            validation,
            repair_candidates.get(action_name),
        )
        for action_name, action_events in grouped.items()
    }
    needs_repair = [row for row in action_rows.values() if row["status"] in {"needs_repair", "blocked"}]
    blocked_actions = sorted(row["action"] for row in needs_repair if row["status"] == "blocked")
    return {
        "summary": {
            "tracked": len(action_rows),
            "needs_repair": len(needs_repair),
            "blocked": len(blocked_actions),
        },
        "actions": action_rows,
        "needs_repair": sorted(needs_repair, key=lambda row: (-int(row["failure_count"]), row["action"]))[:20],
        "blocked_actions": blocked_actions,
    }


def action_health_row(
    action_name: str,
    events: list[dict[str, Any]],
    validation: dict[str, Any],
    repair_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    latest = events[0]
    validation_state = validation_health_state(action_name, latest, validation, repair_candidate)
    if validation_state:
        return validation_state

    failure_count = consecutive_failure_count(events)
    status = action_health_status(latest["status"], failure_count)
    return action_health_payload(action_name, latest, status, failure_count, repair_candidate)


def validation_health_state(
    action_name: str,
    latest_event: dict[str, Any],
    validation: dict[str, Any],
    repair_candidate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not validation_is_newer(latest_event, validation):
        return None
    evidence = dict_config(dict_config(validation.get("actions")).get(action_name))
    if bool(evidence.get("supported")):
        return action_health_payload(action_name, latest_event, "validated", 0, repair_candidate)
    repair = dict_config(evidence.get("repair"))
    if safe_confidence(repair.get("confidence"), 0.0) >= VALIDATION_REPAIR_THRESHOLD:
        return action_health_payload(action_name, latest_event, "repair_applied", 0, repair_candidate)
    return None


def validation_is_newer(latest_event: dict[str, Any], validation: dict[str, Any]) -> bool:
    validated_at = timestamp_value(validation.get("validated_at"))
    event_at = timestamp_value(latest_event.get("occurred_at"))
    return validated_at > 0 and validated_at >= event_at


def consecutive_failure_count(events: list[dict[str, Any]]) -> int:
    failures = 0
    for event in events:
        status = safe_action_status(event.get("status"))
        if status in ACTION_HEALTH_FAILURE_STATUSES:
            failures += 1
            continue
        if status == "blocked":
            continue
        break
    return failures


def action_health_status(latest_status: str, failure_count: int) -> str:
    if latest_status in {"ok", "succeeded"}:
        return "healthy"
    if latest_status == "blocked":
        return "policy_blocked"
    if latest_status == "needs_handoff":
        return "handoff_required"
    if failure_count >= ACTION_HEALTH_FAILURE_THRESHOLD:
        return "blocked"
    if failure_count > 0:
        return "needs_repair"
    return "unknown"


def action_health_payload(
    action_name: str,
    latest_event: dict[str, Any],
    status: str,
    failure_count: int,
    repair_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "action": action_name,
        "status": status,
        "failure_count": failure_count,
        "last_status": safe_action_status(latest_event.get("status")),
        "last_stage": safe_action_stage(latest_event.get("stage")),
        "last_reason": safe_action_text(latest_event.get("reason")),
        "last_url": safe_action_text(latest_event.get("final_url")) or safe_action_text(latest_event.get("url")),
        "last_request_id": safe_action_text(latest_event.get("request_id")),
        "last_seen_at": safe_action_text(latest_event.get("occurred_at")),
    }
    if status in {"needs_repair", "blocked"}:
        clean_candidate = validated_repair_candidate(repair_candidate)
        if clean_candidate:
            payload["repair_candidate"] = clean_candidate
    return payload


def runtime_repair_candidates(vertical_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for event in safe_flow_list(vertical_config.get("interaction_events"), 50):
        action_name, action_config = action_config_from_interaction(event)
        if not action_name or not action_config:
            continue
        repair_candidate = validated_repair_candidate(
            {
                **action_config,
                "source": "runtime_interaction_repair",
                "reason": "matched_recent_browser_interaction",
            }
        )
        if not repair_candidate:
            continue
        existing = candidates.get(action_name)
        if safe_confidence(repair_candidate.get("confidence"), 0.0) <= safe_confidence(
            dict_config(existing).get("confidence"),
            0.0,
        ):
            continue
        candidates[action_name] = repair_candidate
    return candidates


def validated_repair_candidate(raw_candidate: Any) -> dict[str, Any]:
    candidate = raw_candidate if isinstance(raw_candidate, dict) else {}
    try:
        clean_config = validated_action_config(candidate)
    except ValueError:
        return {}
    if safe_confidence(clean_config.get("confidence"), 0.0) < VALIDATION_REPAIR_THRESHOLD:
        return {}
    clean_config["source"] = safe_action_text(candidate.get("source")) or "runtime_repair_candidate"
    reason = safe_action_text(candidate.get("reason"))
    if reason:
        clean_config["reason"] = reason
    return clean_config


def apply_action_health_repairs(vertical_config: dict[str, Any], health: dict[str, Any]) -> list[dict[str, Any]]:
    if has_crm_action_override(vertical_config):
        return []
    actions = dict_config(vertical_config.get("actions")).copy()
    applied: list[dict[str, Any]] = []
    for row in safe_flow_list(health.get("needs_repair"), 20):
        action_name = normalize_action_name(safe_action_text(row.get("action")))
        repair_candidate = validated_repair_candidate(row.get("repair_candidate"))
        if not action_name or not repair_candidate:
            continue
        current = dict_config(actions.get(action_name))
        if safe_action_text(current.get("source")).lower() == "crm":
            continue
        repaired_config = validated_action_config(
            {
                **current,
                **repair_candidate,
                "source": "runtime_repair",
                "confidence": max(
                    safe_confidence(current.get("confidence"), 0.0),
                    safe_confidence(repair_candidate.get("confidence"), 0.0),
                ),
            }
        )
        if same_action_target(current, repaired_config):
            continue
        actions[action_name] = repaired_config
        applied.append(
            {
                "action": action_name,
                "status": "applied",
                "source": "runtime_repair",
                "reason": safe_action_text(repair_candidate.get("reason")) or "matched_recent_browser_interaction",
                "repair": repaired_config,
                "failure_count": safe_int(row.get("failure_count")),
                "last_url": safe_action_text(row.get("last_url")),
                "applied_at": utc_timestamp(),
            }
        )
    if applied:
        vertical_config["actions"] = actions
    return applied


def same_action_target(current: dict[str, Any], repaired: dict[str, Any]) -> bool:
    if safe_action_text(current.get("type")) != safe_action_text(repaired.get("type")):
        return False
    target_keys = ("path", "selector", "form", "input", "submit")
    return all(safe_action_text(current.get(key)) == safe_action_text(repaired.get(key)) for key in target_keys)


def mark_action_health_repairs_applied(health: dict[str, Any], repairs: list[dict[str, Any]]) -> dict[str, Any]:
    repaired_actions = {normalize_action_name(repair.get("action")) for repair in repairs}
    actions = dict_config(health.get("actions")).copy()
    for action_name in repaired_actions:
        row = dict_config(actions.get(action_name))
        if not row:
            continue
        row["status"] = "repair_applied"
        row["runtime_repair_applied"] = True
        row["failure_count"] = 0
        actions[action_name] = row
    needs_repair = [
        row
        for row in safe_flow_list(health.get("needs_repair"), 20)
        if normalize_action_name(row.get("action")) not in repaired_actions
    ]
    blocked_actions = [
        action
        for action in safe_text_list(health.get("blocked_actions"), 20)
        if normalize_action_name(action) not in repaired_actions
    ]
    summary = dict_config(health.get("summary")).copy()
    summary["needs_repair"] = len(needs_repair)
    summary["blocked"] = len(blocked_actions)
    return {
        **health,
        "summary": summary,
        "actions": actions,
        "needs_repair": needs_repair,
        "blocked_actions": blocked_actions,
        "repairs_applied": safe_flow_list(repairs, 20),
    }


def merge_action_repairs(new_repairs: list[dict[str, Any]], old_repairs: Any) -> list[dict[str, Any]]:
    rows = [*safe_flow_list(new_repairs, 20), *safe_flow_list(old_repairs, 30)]
    return rows[:30]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_value(value: Any) -> float:
    text = safe_action_text(value)
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0
