"""Sanitizers for client setup, discovery, and smoke-test reports."""

from __future__ import annotations

from typing import Any

from db.client_domain.core.client_serialization import (
    dict_config,
    safe_action_text,
    safe_confidence,
    safe_flow_list,
    safe_route_map,
    safe_text_list,
)

REPORT_ITEM_LIMIT: int = 100
SMOKE_TEST_LIMIT = 20
SETUP_STATUS_RUNNING = "running"


def validated_flow_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": safe_action_text(report.get("site_id")),
        "site_url": safe_action_text(report.get("site_url")),
        "vertical_key": safe_action_text(report.get("vertical_key")),
        "detected_vertical_key": safe_action_text(report.get("detected_vertical_key")),
        "confidence": safe_confidence(report.get("confidence"), 0.0),
        "engine": safe_action_text(report.get("engine")),
        "summary": dict_config(report.get("summary")),
        "routes": safe_route_map(report.get("routes")),
        "actions": safe_flow_list(report.get("actions"), REPORT_ITEM_LIMIT),
        "pages": safe_flow_list(report.get("pages"), REPORT_ITEM_LIMIT),
        "prompt_suggestions": safe_text_list(report.get("prompt_suggestions"), 20),
        "barriers": validated_barrier_report(report.get("barriers")),
        "discovered_at": safe_action_text(report.get("discovered_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
    }


def validated_barrier_report(raw_report: Any) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": safe_action_text(report.get("site_id")),
        "site_url": safe_action_text(report.get("site_url")),
        "summary": dict_config(report.get("summary")),
        "findings": safe_flow_list(report.get("findings"), REPORT_ITEM_LIMIT),
        "detected_at": safe_action_text(report.get("detected_at")),
    }


def validated_rehearsal_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": safe_action_text(report.get("site_id")),
        "site_url": safe_action_text(report.get("site_url")),
        "engine": safe_action_text(report.get("engine")),
        "summary": dict_config(report.get("summary")),
        "steps": safe_flow_list(report.get("steps"), REPORT_ITEM_LIMIT),
        "rehearsed_at": safe_action_text(report.get("rehearsed_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
    }


def validated_regression_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": safe_action_text(report.get("site_id")),
        "site_url": safe_action_text(report.get("site_url")),
        "status": safe_action_text(report.get("status")) or "unknown",
        "summary": dict_config(report.get("summary")),
        "changes": safe_flow_list(report.get("changes"), REPORT_ITEM_LIMIT),
        "compared_at": safe_action_text(report.get("compared_at")),
    }


def validated_initialization_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "source": safe_action_text(report.get("source")) or "widget_registration",
        "status": safe_action_text(report.get("status")) or "unknown",
        "run_id": safe_action_text(report.get("run_id")),
        "site_id": safe_action_text(report.get("site_id")),
        "site_url": safe_action_text(report.get("site_url")),
        "vertical_key": safe_action_text(report.get("vertical_key")),
        "started_at": safe_action_text(report.get("started_at")),
        "completed_at": safe_action_text(report.get("completed_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
        "timeout_seconds": max(0, int(report.get("timeout_seconds") or 0)),
        "cancel_requested": bool(report.get("cancel_requested")),
        "cancel_requested_at": safe_action_text(report.get("cancel_requested_at")),
        "stages": safe_flow_list(report.get("stages"), REPORT_ITEM_LIMIT),
        "error": safe_action_text(report.get("error")),
    }


def validated_assistant_smoke_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "source": safe_action_text(report.get("source")) or "crm_assistant_smoke_tests",
        "status": safe_action_text(report.get("status")) or "unknown",
        "site_id": safe_action_text(report.get("site_id")),
        "vertical_key": safe_action_text(report.get("vertical_key")),
        "started_at": safe_action_text(report.get("started_at")),
        "completed_at": safe_action_text(report.get("completed_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
        "message": safe_action_text(report.get("message")),
        "total": max(0, int(report.get("total") or 0)),
        "passed": max(0, int(report.get("passed") or 0)),
        "failed": max(0, int(report.get("failed") or 0)),
        "tests": safe_flow_list(report.get("tests"), SMOKE_TEST_LIMIT),
    }


def same_setup_run(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_run_id = safe_action_text(left.get("run_id"))
    right_run_id = safe_action_text(right.get("run_id"))
    return bool(left_run_id and right_run_id and left_run_id == right_run_id)


def setup_stages_with_stop_status(
    raw_stages: Any,
    status: str,
    message: str,
    completed_at: str,
    *,
    limit: int = REPORT_ITEM_LIMIT,
) -> list[dict[str, Any]]:
    stages = safe_flow_list(raw_stages, limit)
    if stages:
        updated = [dict(stage) for stage in stages]
        if str(updated[-1].get("status") or "").lower() == SETUP_STATUS_RUNNING:
            updated[-1] = {
                **updated[-1],
                "status": status,
                "message": message,
                "completed_at": completed_at,
            }
        elif not any(str(stage.get("status") or "").lower() in {status, "failed"} for stage in updated):
            updated.append({
                "name": "setup_stopped",
                "status": status,
                "message": message,
                "started_at": completed_at,
                "completed_at": completed_at,
            })
        return updated[:limit]
    return [{
        "name": "setup_stopped",
        "status": status,
        "message": message,
        "started_at": completed_at,
        "completed_at": completed_at,
    }]
