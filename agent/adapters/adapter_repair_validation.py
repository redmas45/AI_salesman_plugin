"""Validation helpers shared by adapter action and flow repair."""

from __future__ import annotations

import json
import re
from typing import Any

REPAIR_MAX_ACTIONS = 40
REPAIR_MIN_CONFIDENCE = 0.7
ACTION_TYPES = frozenset({"navigate", "click", "form"})
CSS_SELECTOR_PATTERN = re.compile(r'^[a-zA-Z#.\[\]:\-_\s>+~*="\'^$|,()0-9]+$')


def repair_action_payload(actions: dict[str, Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for action_name, action_config in list(actions.items())[:REPAIR_MAX_ACTIONS]:
        payload.append({"action": action_name, "config": action_config})
    return payload


def json_response(raw_response: str) -> Any:
    cleaned = str(raw_response or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def validated_repair(raw_repair: Any) -> dict[str, Any]:
    repair = raw_repair if isinstance(raw_repair, dict) else {}
    repair_confidence = confidence(repair.get("confidence"))
    action_type = str(repair.get("type") or "").strip().lower()
    if repair_confidence < REPAIR_MIN_CONFIDENCE or action_type not in ACTION_TYPES:
        return {}

    clean: dict[str, Any] = {"type": action_type, "confidence": repair_confidence}
    for key in ("path", "selector", "form", "input", "submit", "label"):
        value = clean_target(repair.get(key))
        if value:
            clean[key] = value
    if has_required_target(clean):
        return clean
    return {}


def has_required_target(repair: dict[str, Any]) -> bool:
    action_type = repair.get("type")
    if action_type == "navigate":
        return bool(str(repair.get("path") or "").startswith("/"))
    if action_type == "click":
        return valid_selector(repair.get("selector"))
    if action_type == "form":
        return valid_selector(repair.get("input"))
    return False


def valid_selector(value: Any) -> bool:
    selector = str(value or "").strip()
    return bool(selector and len(selector) <= 240 and CSS_SELECTOR_PATTERN.match(selector))


def clean_target(value: Any) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if text.lower().startswith(("javascript:", "data:", "http://", "https://")):
        return ""
    if any(key in text for key in ("<script", "</")):
        return ""
    return text[:500]


def confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(number, 1.0)), 2)
