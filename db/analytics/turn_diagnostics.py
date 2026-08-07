"""The safe, structured record of what one turn decided.

A support case asks whether Maya's speech, the records she chose, the page the
customer saw and the action that ran all agreed. Answering it needs the turn's
own decisions - which ids were selected, how many matched, what was planned, what
the model cost - and until now none of that was stored. The CRM's full log had
fields for them and read `null` from every one.

What is stored here is deliberately narrow. Nothing that could authenticate as
anyone and nothing that identifies a person beyond the session id is kept: see
``REDACTED_KEY_PATTERN``. Sizes are bounded so a runaway payload cannot turn a
usage row into a blob.

Nothing here knows a vertical. Every field is one the runtime already computes.
"""

from __future__ import annotations

import re
from typing import Any

# Keys whose values are never stored, matched case-insensitively anywhere in the
# key name. This mirrors the CRM's own export filter so a value cannot become
# visible by taking a different route to the screen.
REDACTED_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|auth|cookie|"
    r"session[_-]?key|credential|bearer|signature|private|env|audio|raw_audio|"
    r"payload_raw|card|cvv|iban|ssn|email|phone_number|address)",
    re.IGNORECASE,
)

REDACTED = "[redacted]"
MAX_STRING_LENGTH = 2000
MAX_ARRAY_LENGTH = 50
MAX_DEPTH = 5
MAX_IDS = 50


def sanitize(value: Any, depth: int = 0) -> Any:
    """Copy a value, dropping anything sensitive and bounding its size."""
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return value if len(value) <= MAX_STRING_LENGTH else f"{value[:MAX_STRING_LENGTH]}...[truncated]"
    if depth >= MAX_DEPTH:
        return REDACTED
    if isinstance(value, (list, tuple)):
        return [sanitize(item, depth + 1) for item in list(value)[:MAX_ARRAY_LENGTH]]
    if isinstance(value, dict):
        return {
            str(key): REDACTED if REDACTED_KEY_PATTERN.search(str(key)) else sanitize(item, depth + 1)
            for key, item in list(value.items())[:MAX_ARRAY_LENGTH]
        }
    return REDACTED


def _ids(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value[:MAX_IDS] if item is not None and str(item)]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def turn_id_of(result: dict[str, Any]) -> str:
    """The turn id the runtime stamped onto this turn's actions.

    Actions carry it so their browser outcomes can be joined back to the turn
    that planned them. Reading it from the actions keeps one source of truth
    rather than minting a second id that would never match.
    """
    for action in result.get("ui_actions") or []:
        if isinstance(action, dict) and action.get("turn_id"):
            return str(action["turn_id"])
    return ""


def planned_actions(result: dict[str, Any]) -> list[dict[str, Any]]:
    """What the turn intended the browser to do, before it did it."""
    planned: list[dict[str, Any]] = []
    for action in (result.get("ui_actions") or [])[:MAX_ARRAY_LENGTH]:
        if not isinstance(action, dict):
            continue
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        planned.append(
            {
                "action": str(action.get("action") or ""),
                "request_id": str(action.get("request_id") or ""),
                "sequence": _int_or_none(action.get("sequence")),
                "params": sanitize(params),
            }
        )
    return planned


def build_turn_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    """Everything the full log needs about one turn, safe to store as-is.

    ``spoken_text`` is kept only when it differs from the written answer, because
    that difference is exactly what a reviewer is looking for when a customer
    reports hearing something other than what the transcript shows.
    """
    if not isinstance(result, dict):
        return {}

    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    response_text = str(result.get("response_text") or "")
    spoken_text = str(result.get("spoken_text") or "")

    diagnostics: dict[str, Any] = {
        "turn_id": turn_id_of(result),
        "confidence": result.get("confidence"),
        "answer_scope": str(result.get("answer_scope") or ""),
        "spoken_text": sanitize(spoken_text) if spoken_text and spoken_text != response_text else None,
        "selected_ids": _ids(result.get("selected_ids") or retrieval.get("selected_ids")),
        "selected_names": _ids(result.get("selected_names") or retrieval.get("selected_names")),
        "retrieved_ids": _ids(retrieval.get("source_ids") or result.get("source_ids")),
        "matching_total": _int_or_none(result.get("matching_total") or retrieval.get("matching_total")),
        "displayed_count": _int_or_none(result.get("displayed_count") or retrieval.get("displayed_count")),
        "requested_count": _int_or_none(result.get("requested_count") or retrieval.get("requested_count")),
        "constraints": sanitize(result.get("constraints") or retrieval.get("constraints")),
        "planned_actions": planned_actions(result),
        "cache": {
            "hit": bool(retrieval.get("cache_hit")),
            "match_type": str(retrieval.get("match_type") or ""),
            "data_version": _int_or_none(retrieval.get("data_version")),
        },
        "model": {
            "name": str(result.get("model") or ""),
            "provider": str(result.get("provider") or ""),
        },
        "latency_ms": sanitize(result.get("latency_ms") if isinstance(result.get("latency_ms"), dict) else {}),
    }
    return {key: value for key, value in diagnostics.items() if value not in (None, "", [], {})}
