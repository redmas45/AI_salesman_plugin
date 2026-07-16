"""Validation helpers for persisted adapter action configuration."""

from __future__ import annotations

from typing import Any

from agent.actions.registry import is_supported_action, normalize_action_name
from db.client_domain.core.client_serialization import (
    safe_action_page_path,
    safe_action_text,
    safe_confidence,
    safe_int,
    safe_text_list,
)

ADAPTER_ACTION_TYPES = frozenset({"navigate", "click", "form", "sequence", "handoff"})
ADAPTER_FORM_SUBMIT_MODES = frozenset({"submit", "auto_submit", "fill_only", "prepare_only"})
ADAPTER_SEQUENCE_OPERATIONS = frozenset({
    "check",
    "click",
    "fill",
    "focus",
    "navigate",
    "scroll",
    "select",
    "set_value",
    "submit",
    "uncheck",
    "wait",
    "wait_for",
})
MAX_ADAPTER_ACTIONS = 100
MAX_ADAPTER_SEQUENCE_STEPS = 30


def validated_action_config(raw_config: Any) -> dict[str, Any]:
    if not isinstance(raw_config, dict):
        raise ValueError("Adapter action config must be a JSON object.")
    action_type = str(raw_config.get("type") or "").strip().lower()
    if action_type not in ADAPTER_ACTION_TYPES:
        raise ValueError("Adapter action type must be navigate, click, form, sequence, or handoff.")
    clean_config = {"type": action_type}
    for key in ("path", "selector", "form", "input", "submit", "submit_mode", "label", "source", "note", "message", "reason"):
        value = safe_action_text(raw_config.get(key))
        if key == "submit_mode" and value not in ADAPTER_FORM_SUBMIT_MODES:
            continue
        if value:
            clean_config[key] = value
    for raw_key, clean_key in (
        ("page_path", "page_path"),
        ("pagePath", "page_path"),
        ("source_path", "source_path"),
        ("sourcePath", "source_path"),
    ):
        if clean_key in clean_config:
            continue
        value = safe_action_page_path(raw_config.get(raw_key))
        if value:
            clean_config[clean_key] = value
    fields = safe_text_list(raw_config.get("fields"), 20)
    if fields and action_type in {"form", "sequence"}:
        clean_config["fields"] = fields
    required_fields = safe_text_list(raw_config.get("required_fields"), 20)
    if action_type in {"form", "sequence"} and ("required_fields" in raw_config or raw_config.get("required_fields_known") is True):
        clean_config["required_fields"] = required_fields
        clean_config["required_fields_known"] = True
    field_schema = validated_field_schema(raw_config.get("field_schema"))
    if field_schema and action_type in {"form", "sequence"}:
        clean_config["field_schema"] = field_schema
    if action_type == "sequence":
        clean_config["steps"] = validated_adapter_sequence(raw_config.get("steps"))
    clean_config["confidence"] = safe_confidence(raw_config.get("confidence"), 0.7)
    return clean_config


def validated_action_map(raw_actions: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_actions, dict):
        raise ValueError("Adapter actions must be a JSON object.")
    clean_actions: dict[str, Any] = {}
    for raw_name, raw_config in list(raw_actions.items())[:MAX_ADAPTER_ACTIONS]:
        action_name = normalize_action_name(str(raw_name))
        if not is_supported_action(action_name):
            raise ValueError(f"Unsupported adapter action: {raw_name}.")
        clean_actions[action_name] = validated_action_config(raw_config)
    return clean_actions


def validated_field_schema(raw_schema: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_schema, list):
        return []
    rows = [validated_field_schema_item(item) for item in raw_schema[:20]]
    return [row for row in rows if row]


def validated_field_schema_item(raw_item: Any) -> dict[str, Any]:
    if not isinstance(raw_item, dict):
        return {}
    param = safe_action_text(raw_item.get("param"))[:80]
    if not param:
        return {}
    row: dict[str, Any] = {"param": param, "required": bool(raw_item.get("required") is True)}
    for key in ("label", "type", "autocomplete"):
        value = safe_action_text(raw_item.get(key))[:120]
        if value:
            row[key] = value
    options = validated_field_options(raw_item.get("options"))
    if options:
        row["options"] = options
    return row


def validated_field_options(raw_options: Any) -> list[dict[str, str]]:
    if not isinstance(raw_options, list):
        return []
    rows = [validated_field_option(option) for option in raw_options[:20]]
    return [row for row in rows if row]


def validated_field_option(raw_option: Any) -> dict[str, str]:
    if isinstance(raw_option, dict):
        label = safe_action_text(raw_option.get("label"))[:120]
        value = safe_action_text(raw_option.get("value"))[:120]
    else:
        label = safe_action_text(raw_option)[:120]
        value = label
    if not label and not value:
        return {}
    return {"label": label or value, "value": value or label}


def validated_adapter_sequence(raw_steps: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_steps, list):
        raise ValueError("Sequence adapter actions require steps.")
    steps = [validated_adapter_sequence_step(step) for step in raw_steps[:MAX_ADAPTER_SEQUENCE_STEPS]]
    clean_steps = [step for step in steps if step]
    if not clean_steps:
        raise ValueError("Sequence adapter actions require at least one valid step.")
    return clean_steps


def validated_adapter_sequence_step(raw_step: Any) -> dict[str, Any]:
    if not isinstance(raw_step, dict):
        return {}
    operation = safe_action_text(raw_step.get("op") or raw_step.get("type") or raw_step.get("action")).lower()
    if operation not in ADAPTER_SEQUENCE_OPERATIONS:
        return {}
    step: dict[str, Any] = {"op": operation}
    for key in ("selector", "label", "text", "name", "param", "parameter", "value", "path", "to"):
        value = safe_action_text(raw_step.get(key))
        if value:
            step[key] = value
    if raw_step.get("optional") is True:
        step["optional"] = True
    if raw_step.get("ms") is not None:
        step["ms"] = safe_wait_ms(raw_step.get("ms"))
    for key in ("x", "y"):
        if raw_step.get(key) is not None:
            step[key] = safe_int(raw_step.get(key))
    return step


def safe_wait_ms(value: Any) -> int:
    return max(0, min(safe_int(value), 5000))


def validated_adapter_validation(raw_report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_report, dict):
        raise ValueError("Adapter validation report must be a JSON object.")
    actions = raw_report.get("actions")
    if not isinstance(actions, dict):
        actions = {}
    clean_actions = {
        normalize_action_name(name): validated_action_evidence(evidence)
        for name, evidence in list(actions.items())[:MAX_ADAPTER_ACTIONS]
        if is_supported_action(normalize_action_name(name))
    }
    return {
        "source": safe_action_text(raw_report.get("source")) or "browser_runtime",
        "origin": safe_action_text(raw_report.get("origin")),
        "url": safe_action_text(raw_report.get("url")),
        "validated_at": safe_action_text(raw_report.get("validated_at")),
        "summary": validation_summary(clean_actions),
        "actions": clean_actions,
    }


def validated_action_evidence(raw_evidence: Any) -> dict[str, Any]:
    evidence = raw_evidence if isinstance(raw_evidence, dict) else {}
    clean_evidence = {
        "type": safe_action_text(evidence.get("type")),
        "status": safe_action_text(evidence.get("status")) or "unknown",
        "target": safe_action_text(evidence.get("target")),
        "evidence": safe_action_text(evidence.get("evidence")),
        "supported": bool(evidence.get("supported")),
        "confidence": safe_confidence(evidence.get("confidence"), 0.0),
    }
    repair = repair_config(evidence.get("repair"))
    if repair:
        clean_evidence["repair"] = repair
    return clean_evidence


def repair_config(raw_repair: Any) -> dict[str, Any]:
    if not isinstance(raw_repair, dict):
        return {}
    clean_repair: dict[str, Any] = {}
    for key in ("selector", "form", "input", "submit", "path", "label"):
        value = safe_action_text(raw_repair.get(key))
        if value:
            clean_repair[key] = value
    repair_type = safe_action_text(raw_repair.get("type"))
    if repair_type in ADAPTER_ACTION_TYPES:
        clean_repair["type"] = repair_type
    clean_repair["confidence"] = safe_confidence(raw_repair.get("confidence"), 0.0)
    return clean_repair


def validation_summary(actions: dict[str, dict[str, Any]]) -> dict[str, int]:
    supported = sum(1 for action in actions.values() if action.get("supported"))
    repaired = sum(1 for action in actions.values() if action.get("repair"))
    return {
        "total": len(actions),
        "supported": supported,
        "needs_repair": max(0, len(actions) - supported),
        "repair_suggestions": repaired,
    }
