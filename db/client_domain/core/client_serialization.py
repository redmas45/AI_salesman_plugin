"""JSON-safe serialization and sanitizer helpers for client persistence."""

from __future__ import annotations

import json
import re
from typing import Any

MAX_SAFE_ACTION_TEXT_LENGTH = 500


def safe_action_text(value: Any) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if text.lower().startswith(("javascript:", "data:")):
        return ""
    return text[:MAX_SAFE_ACTION_TEXT_LENGTH]


def safe_action_page_path(value: Any) -> str:
    path = safe_action_text(value)
    if not path or not path.startswith("/") or path.startswith("//"):
        return ""
    if path.lower().startswith(("/javascript:", "/data:")):
        return ""
    return path


def safe_confidence(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return round(max(0.0, min(number, 1.0)), 2)


def safe_audit_status(value: Any) -> str:
    status = re.sub(r"[^a-z0-9_]+", "_", safe_action_text(value).lower()).strip("_")
    if not status:
        return "unknown"
    return status[:80]


def safe_action_stage(value: Any) -> str:
    stage = re.sub(r"[^a-z0-9_]+", "_", safe_action_text(value).lower()).strip("_")
    return stage[:80]


def safe_duration_ms(value: Any) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, number), 2)


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def safe_flow_list(value: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        rows.append({str(key)[:80]: safe_json_value(raw_value) for key, raw_value in item.items()})
    return rows


def safe_text_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [safe_action_text(item) for item in value[:limit] if safe_action_text(item)]


def safe_route_map(value: Any) -> dict[str, str]:
    routes = dict_config(value)
    safe_routes: dict[str, str] = {}
    for raw_key, raw_value in routes.items():
        key = re.sub(r"[^a-z0-9_]+", "_", str(raw_key or "").strip().lower()).strip("_")[:80]
        path = safe_action_text(raw_value)
        if key and path.startswith("/"):
            safe_routes[key] = path
    return safe_routes


def dict_config(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_json_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        return [safe_json_value(item) for item in value[:20]]
    if isinstance(value, dict):
        return {str(key)[:80]: safe_json_value(item) for key, item in list(value.items())[:40]}
    return safe_action_text(value)


def json_object(raw: Any) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def json_list(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        data = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []
