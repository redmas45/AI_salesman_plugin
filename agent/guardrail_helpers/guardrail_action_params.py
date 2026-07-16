"""Validation helpers for generated adapter action parameters."""

from __future__ import annotations

import re
from typing import Any

MAX_ACTION_PARAM_KEYS = 20
MAX_ACTION_PARAM_VALUE_LENGTH = 500
SAFE_ACTION_PARAM_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,79}$")
BLOCKED_ACTION_PARAM_KEYS = frozenset({"__proto__", "constructor", "prototype"})


def validate_adapter_action_params(params: dict, action_config: dict[str, Any]) -> dict | None:
    """Keep privacy/safety-safe params needed by generated adapter actions."""
    action_type = str(action_config.get("type") or "").lower()
    if action_type in {"click", "navigate"}:
        return safe_action_params(params, allowed_keys=adapter_param_keys(action_config), allow_open=False)
    if action_type in {"form", "sequence"}:
        allowed_keys = adapter_param_keys(action_config)
        return safe_action_params(params, allowed_keys=allowed_keys, allow_open=not allowed_keys)
    return safe_action_params(params, allowed_keys=set(), allow_open=True)


def safe_action_params(params: dict, *, allowed_keys: set[str], allow_open: bool) -> dict | None:
    clean_params: dict[str, Any] = {}
    for raw_key, raw_value in list(params.items())[:MAX_ACTION_PARAM_KEYS]:
        key = clean_action_param_key(raw_key)
        if not key:
            continue
        if allowed_keys and normalize_action_param_key(key) not in allowed_keys:
            continue
        if not allowed_keys and not allow_open:
            continue
        value = clean_action_param_value(raw_value)
        if value is None:
            continue
        clean_params[key] = value
    return clean_params


def adapter_param_keys(action_config: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for raw_key in action_config.get("fields") or []:
        key = normalize_action_param_key(raw_key)
        if key:
            keys.add(key)
    for raw_step in action_config.get("steps") or []:
        if not isinstance(raw_step, dict):
            continue
        for field in ("param", "parameter", "name"):
            key = normalize_action_param_key(raw_step.get(field))
            if key:
                keys.add(key)
    return keys


def clean_action_param_key(value: Any) -> str:
    key = str(value or "").strip()
    if key in BLOCKED_ACTION_PARAM_KEYS or not SAFE_ACTION_PARAM_KEY.match(key):
        return ""
    return key


def normalize_action_param_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def clean_action_param_value(value: Any) -> str | int | float | bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return None
    text = value.replace("\x00", "").strip()[:MAX_ACTION_PARAM_VALUE_LENGTH]
    if text.lower().startswith(("javascript:", "data:")):
        return None
    return text
