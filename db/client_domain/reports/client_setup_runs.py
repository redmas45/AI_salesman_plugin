"""Setup-run state transitions for client initialization."""

from __future__ import annotations

from typing import Any

from db.client_domain.actions.client_action_health import timestamp_value
from db.client_domain.reports.client_reports import (
    same_setup_run,
    setup_stages_with_stop_status,
    validated_initialization_report,
)
from db.client_domain.core.client_serialization import dict_config, safe_action_text

SETUP_STATUS_RUNNING = "running"
SETUP_STATUS_CANCELED = "canceled"
SETUP_STATUS_TIMED_OUT = "timed_out"


def merged_initialization_report(
    existing_raw: Any,
    report: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    existing_initialization = dict_config(existing_raw)
    next_initialization = validated_initialization_report(report)
    if _same_terminal_setup_run(existing_initialization, next_initialization):
        return next_initialization, False
    if _same_cancel_requested_setup_run(existing_initialization, next_initialization):
        next_initialization["cancel_requested"] = True
        next_initialization["cancel_requested_at"] = safe_action_text(
            existing_initialization.get("cancel_requested_at")
        )
    return next_initialization, True


def setup_cancel_requested(initialization_raw: Any, run_id: str = "") -> bool:
    initialization = dict_config(initialization_raw)
    if not initialization.get("cancel_requested"):
        return False
    return not run_id or same_setup_run(initialization, {"run_id": run_id})


def setup_cancel_update(
    initialization_raw: Any,
    *,
    requested_at: str,
) -> tuple[dict[str, Any], bool]:
    initialization = dict_config(initialization_raw).copy()
    if str(initialization.get("status") or "").lower() != SETUP_STATUS_RUNNING:
        raise ValueError("No setup run is running for this client.")
    if initialization.get("cancel_requested"):
        return initialization, False
    initialization["cancel_requested"] = True
    initialization["cancel_requested_at"] = requested_at
    return validated_initialization_report(initialization), True


def expired_initialization_update(
    vertical_config: dict[str, Any],
    *,
    max_age: int,
    now_epoch: float,
    now_text: str,
) -> tuple[dict[str, Any], str] | None:
    initialization = dict_config(vertical_config.get("initialization")).copy()
    if str(initialization.get("status") or "").lower() != SETUP_STATUS_RUNNING:
        return None
    saved_duration_ms = _saved_duration_ms(initialization.get("duration_ms"))
    age_seconds = _setup_age_seconds(
        initialization,
        saved_duration_ms=saved_duration_ms,
        max_age=max_age,
        now_epoch=now_epoch,
    )
    if age_seconds < max_age:
        return None
    message = f"Setup run timed out after {max_age} seconds."
    initialization["status"] = SETUP_STATUS_TIMED_OUT
    initialization["completed_at"] = now_text
    initialization["duration_ms"] = max(saved_duration_ms, age_seconds * 1000)
    initialization["error"] = message
    initialization["stages"] = setup_stages_with_stop_status(
        initialization.get("stages"),
        SETUP_STATUS_TIMED_OUT,
        message,
        now_text,
    )
    updated_config = vertical_config.copy()
    updated_config["initialization"] = validated_initialization_report(initialization)
    return updated_config, message


def _same_terminal_setup_run(existing: dict[str, Any], next_initialization: dict[str, Any]) -> bool:
    return (
        str(existing.get("status") or "").lower() in {SETUP_STATUS_CANCELED, SETUP_STATUS_TIMED_OUT}
        and same_setup_run(existing, next_initialization)
    )


def _same_cancel_requested_setup_run(existing: dict[str, Any], next_initialization: dict[str, Any]) -> bool:
    return (
        next_initialization.get("status") == SETUP_STATUS_RUNNING
        and bool(existing.get("cancel_requested"))
        and same_setup_run(existing, next_initialization)
    )


def _saved_duration_ms(raw_duration_ms: Any) -> float:
    try:
        return max(0.0, float(raw_duration_ms or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _setup_age_seconds(
    initialization: dict[str, Any],
    *,
    saved_duration_ms: float,
    max_age: int,
    now_epoch: float,
) -> float:
    started_epoch = timestamp_value(initialization.get("started_at"))
    if started_epoch > 0:
        return now_epoch - started_epoch
    if saved_duration_ms > 0:
        return saved_duration_ms / 1000
    return max_age + 1
