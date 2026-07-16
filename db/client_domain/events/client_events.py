"""Browser runtime event validation helpers for client persistence."""

from __future__ import annotations

from typing import Any

from agent.actions.registry import normalize_action_name
from db.client_domain.core.client_serialization import (
    safe_action_stage,
    safe_action_text,
    safe_duration_ms,
    safe_int,
    safe_json_value,
    safe_text_list,
)

ACTION_STATUS_VALUES: frozenset[str] = frozenset({
    "ok",
    "requested",
    "executing",
    "succeeded",
    "failed",
    "blocked",
    "needs_handoff",
    "error",
    "unknown",
})


def safe_action_status(value: Any) -> str:
    status = safe_action_text(value).lower()
    return status if status in ACTION_STATUS_VALUES else "unknown"


def validated_policy_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    event = raw_event if isinstance(raw_event, dict) else {}
    return {
        "source": safe_action_text(event.get("source")) or "browser_runtime",
        "origin": safe_action_text(event.get("origin")),
        "url": safe_action_text(event.get("url")),
        "occurred_at": safe_action_text(event.get("occurred_at")),
        "action": normalize_action_name(safe_action_text(event.get("action"))),
        "status": safe_action_text(event.get("status")) or "unknown",
        "reason": safe_action_text(event.get("reason")),
        "policy": safe_json_value(event.get("policy")),
    }


def validated_action_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    event = raw_event if isinstance(raw_event, dict) else {}
    return {
        "source": safe_action_text(event.get("source")) or "browser_runtime",
        "origin": safe_action_text(event.get("origin")),
        "url": safe_action_text(event.get("url")),
        "occurred_at": safe_action_text(event.get("occurred_at")),
        "request_id": safe_action_text(event.get("request_id")),
        "turn_id": safe_action_text(event.get("turn_id")),
        "sequence": safe_int(event.get("sequence")),
        "action": normalize_action_name(safe_action_text(event.get("action"))),
        "status": safe_action_status(event.get("status")),
        "stage": safe_action_stage(event.get("stage")),
        "reason": safe_action_text(event.get("reason")),
        "duration_ms": safe_duration_ms(event.get("duration_ms")),
        "param_keys": safe_text_list(event.get("param_keys"), 20),
        "requested_url": safe_action_text(event.get("requested_url")),
        "final_url": safe_action_text(event.get("final_url")),
        "evidence": safe_json_value(event.get("evidence")),
    }


def validated_interaction_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    event = raw_event if isinstance(raw_event, dict) else {}
    event_type = safe_action_text(event.get("event_type")).lower()
    if event_type not in {"click", "submit"}:
        event_type = "unknown"
    return {
        "source": safe_action_text(event.get("source")) or "browser_runtime",
        "origin": safe_action_text(event.get("origin")),
        "url": safe_action_text(event.get("url")),
        "occurred_at": safe_action_text(event.get("occurred_at")),
        "event_type": event_type,
        "label": safe_action_text(event.get("label")),
        "selector": safe_action_text(event.get("selector")),
        "tag": safe_action_text(event.get("tag")),
        "href": safe_action_text(event.get("href")),
        "form": validated_interaction_form(event.get("form")),
    }


def validated_interaction_form(raw_form: Any) -> dict[str, Any]:
    form = raw_form if isinstance(raw_form, dict) else {}
    return {
        "selector": safe_action_text(form.get("selector")),
        "submit_selector": safe_action_text(form.get("submit_selector")),
        "fields": validated_interaction_fields(form.get("fields")),
    }


def validated_interaction_fields(raw_fields: Any) -> list[dict[str, str]]:
    if not isinstance(raw_fields, list):
        return []
    fields: list[dict[str, str]] = []
    for raw_field in raw_fields[:12]:
        field = raw_field if isinstance(raw_field, dict) else {}
        selector = safe_action_text(field.get("selector"))
        if not selector:
            continue
        fields.append(
            {
                "selector": selector,
                "name": safe_action_text(field.get("name")),
                "type": safe_action_text(field.get("type")),
                "placeholder": safe_action_text(field.get("placeholder")),
            }
        )
    return fields
