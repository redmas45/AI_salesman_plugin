"""Audit helpers for setup assistant smoke tests."""

from __future__ import annotations

from typing import Any, Protocol


class SmokeAuditRecorder(Protocol):
    def record_audit_event(self, **kwargs: Any) -> Any: ...


def record_smoke_repair_need(
    site_id: str,
    case: dict[str, Any],
    test_result: dict[str, Any],
    audit_recorder: SmokeAuditRecorder,
    logger: Any,
) -> None:
    """Log deterministic smoke repair evidence without mutating prompts blindly."""
    try:
        audit_recorder.record_audit_event(
            site_id=site_id,
            actor_type="setup_runner",
            actor_id="assistant_smoke_tests",
            event_type="assistant_smoke_repair_needed",
            status=str(test_result.get("failure_kind") or "failed"),
            message=str(test_result.get("recommended_fix") or test_result.get("reason") or "Smoke test repair needed."),
            metadata={
                "case": str(case.get("name") or ""),
                "prompt": str(case.get("prompt") or ""),
                "expected_actions": test_result.get("expected_actions") or [],
                "actual_actions": test_result.get("actual_actions") or [],
                "filtered_actions": test_result.get("filtered_actions") or [],
            },
        )
    except Exception as exc:
        logger.warning("Smoke repair audit write failed for %s/%s: %s", site_id, case.get("name"), exc)
