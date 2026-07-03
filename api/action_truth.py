"""Action request identifiers for browser execution truth loops."""

from __future__ import annotations

import re
import uuid
from typing import Any

MAX_ACTION_REQUEST_ID_LENGTH = 80


def new_action_turn_id() -> str:
    """Return a short unique turn ID used to correlate UI actions and browser acks."""
    return f"turn_{uuid.uuid4().hex[:12]}"


def annotate_ui_actions(actions: Any, *, turn_id: str | None = None) -> list[dict[str, Any]]:
    """Attach stable request IDs to action dicts without changing action params."""
    if not isinstance(actions, list):
        return []
    clean_turn_id = _safe_request_id(turn_id or new_action_turn_id())
    annotated: list[dict[str, Any]] = []
    for index, raw_action in enumerate(actions, start=1):
        if not isinstance(raw_action, dict):
            continue
        action = dict(raw_action)
        request_id = _safe_request_id(
            action.get("request_id")
            or action.get("action_request_id")
            or f"{clean_turn_id}_{index}"
        )
        action["request_id"] = request_id
        action["turn_id"] = clean_turn_id
        action["sequence"] = index
        annotated.append(action)
    return annotated


def _safe_request_id(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", str(value or "").strip())
    return text[:MAX_ACTION_REQUEST_ID_LENGTH] or f"action_{uuid.uuid4().hex[:12]}"
