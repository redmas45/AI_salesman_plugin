"""DOM sequence parameter validation for output guardrails."""

from __future__ import annotations

import logging
from typing import Any

STEPS_PARAM = "steps"
MAX_STEPS = 30
MAX_STRING_LENGTH = 500
MAX_WAIT_MS = 5000
ALLOWED_OPERATIONS = {
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
}
SELECTOR_OPERATIONS = {
    "check",
    "fill",
    "focus",
    "select",
    "set_value",
    "submit",
    "uncheck",
    "wait_for",
}


def validate_dom_sequence_params(params: dict, logger: logging.Logger) -> dict | None:
    """Validate a generated same-origin DOM operation sequence."""
    raw_steps = params.get(STEPS_PARAM)
    if not isinstance(raw_steps, list):
        logger.warning("Guardrail | RUN_DOM_SEQUENCE steps must be a list.")
        return None

    steps = []
    for raw_step in raw_steps[:MAX_STEPS]:
        step = validate_dom_sequence_step(raw_step)
        if step is not None:
            steps.append(step)

    if not steps:
        logger.warning("Guardrail | RUN_DOM_SEQUENCE had no valid steps.")
        return None
    return {STEPS_PARAM: steps}


def validate_dom_sequence_step(raw_step: Any) -> dict | None:
    if not isinstance(raw_step, dict):
        return None

    operation = clean_dom_sequence_text(
        raw_step.get("op") or raw_step.get("type") or raw_step.get("action"),
        limit=40,
    ).lower()
    if operation not in ALLOWED_OPERATIONS:
        return None

    step = {"op": operation}
    copy_dom_sequence_common_fields(raw_step, step)
    if not copy_dom_sequence_operation_fields(raw_step, step):
        return None
    return step


def copy_dom_sequence_common_fields(raw_step: dict, step: dict) -> None:
    if raw_step.get("optional") is True:
        step["optional"] = True
    for key in ("label", "text", "name", "param", "parameter"):
        value = clean_dom_sequence_text(raw_step.get(key))
        if value:
            step[key] = value


def copy_dom_sequence_operation_fields(raw_step: dict, step: dict) -> bool:
    operation = step["op"]
    if operation == "navigate":
        return copy_dom_sequence_path(raw_step, step)
    if operation == "wait":
        step["ms"] = clean_dom_sequence_wait(raw_step.get("ms") or raw_step.get("timeout_ms"))
        return True
    if operation in {"click", "scroll"}:
        return copy_dom_sequence_target(raw_step, step, require_selector=False)

    return copy_dom_sequence_target(raw_step, step, require_selector=operation in SELECTOR_OPERATIONS)


def copy_dom_sequence_target(raw_step: dict, step: dict, require_selector: bool) -> bool:
    selector = clean_dom_sequence_selector(raw_step.get("selector"))
    if selector:
        step["selector"] = selector
    if require_selector and not selector:
        return False

    value = clean_dom_sequence_text(raw_step.get("value"))
    if value:
        step["value"] = value
    if step["op"] == "wait_for" and selector:
        step["ms"] = clean_dom_sequence_wait(raw_step.get("ms") or raw_step.get("timeout_ms"))
    if step["op"] == "scroll":
        copy_dom_sequence_scroll_fields(raw_step, step)
    return bool(selector or step.get("label") or step.get("text") or step["op"] == "scroll")


def copy_dom_sequence_scroll_fields(raw_step: dict, step: dict) -> None:
    target = clean_dom_sequence_text(raw_step.get("to"), limit=20).lower()
    if target in {"top", "bottom"}:
        step["to"] = target
    for key in ("x", "y"):
        if raw_step.get(key) is not None:
            step[key] = clean_dom_sequence_number(raw_step.get(key))


def copy_dom_sequence_path(raw_step: dict, step: dict) -> bool:
    path = clean_dom_sequence_path(raw_step.get("path") or raw_step.get("url") or raw_step.get("href"))
    if not path:
        return False
    step["path"] = path
    return True


def clean_dom_sequence_path(value: Any) -> str:
    path = clean_dom_sequence_text(value)
    lowered = path.lower()
    if not path or lowered.startswith(("http://", "https://", "javascript:", "data:")):
        return ""
    return path


def clean_dom_sequence_selector(value: Any) -> str:
    selector = clean_dom_sequence_text(value)
    if not selector or has_control_characters(selector):
        return ""
    return selector


def clean_dom_sequence_text(value: Any, limit: int = MAX_STRING_LENGTH) -> str:
    text = str(value or "").strip()
    return text[:limit]


def clean_dom_sequence_wait(value: Any) -> int:
    try:
        wait_ms = int(value)
    except (TypeError, ValueError):
        return 100
    return max(0, min(wait_ms, MAX_WAIT_MS))


def clean_dom_sequence_number(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def has_control_characters(value: str) -> bool:
    return any(ord(char) < 32 for char in value)
