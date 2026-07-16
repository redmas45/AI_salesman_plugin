"""CRM operation-status projections."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import psycopg

from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)


def client_operation_status(client: dict[str, Any]) -> dict[str, Any]:
    site_id = str(client.get("site_id") or "")
    vertical_config = dict_value(client.get("vertical_config"))
    return {
        "site_id": site_id,
        "generated_at": utc_now(),
        "operations": {
            "crawl": crawl_operation_status(client),
            "readiness": readiness_operation_status(client),
            "integration": integration_operation_status(client, vertical_config),
        },
    }


def crawl_operation_status(client: dict[str, Any]) -> dict[str, Any]:
    site_id = str(client.get("site_id") or "")
    raw_status = str(client.get("last_crawl_status") or admin_db.CRAWL_STATUS_NOT_STARTED).lower()
    message = str(client.get("last_crawl_message") or "")
    updated_at = str(client.get("last_crawl_at") or "")
    report = latest_crawl_report(site_id)
    status = {
        admin_db.CRAWL_STATUS_RUNNING: "running",
        admin_db.CRAWL_STATUS_OK: "complete",
        admin_db.CRAWL_STATUS_ERROR: "failed",
    }.get(raw_status, "pending")
    stages = [
        operation_stage("crawl_queue", "Queueing crawl job", "pending", "Waiting for crawl request."),
        operation_stage("crawl_connect", "Connecting to website", "pending", "Waiting for crawler."),
        operation_stage("crawl_pages", "Reading pages and routes", "pending", "Waiting for crawler."),
        operation_stage("crawl_extract", "Extracting records and metadata", "pending", "Waiting for crawler."),
        operation_stage("crawl_store", "Updating knowledge store", "pending", "Waiting for crawler."),
        operation_stage("crawl_report", "Refreshing crawl report", "pending", "Waiting for crawler."),
    ]
    if status == "running":
        stages[0] = operation_stage(
            "crawl_queue",
            "Queueing crawl job",
            "complete",
            "Crawler accepted the request.",
            completed_at=updated_at,
        )
        stages[1] = operation_stage(
            "crawl_connect",
            "Connecting to website",
            "running",
            message or "Crawler is connecting to the source website.",
            started_at=updated_at,
        )
    elif status == "complete":
        pages = int(report.get("pages_visited") or 0)
        products = int(report.get("product_count") or 0)
        duration = float(report.get("duration_ms") or 0.0)
        stages = [
            operation_stage("crawl_queue", "Queueing crawl job", "complete", "Crawler accepted the request.", completed_at=updated_at),
            operation_stage("crawl_connect", "Connecting to website", "complete", "Website connection completed.", completed_at=updated_at),
            operation_stage("crawl_pages", "Reading pages and routes", "complete", f"{pages} pages visited.", completed_at=updated_at),
            operation_stage("crawl_extract", "Extracting records and metadata", "complete", f"{products} records extracted.", completed_at=updated_at),
            operation_stage("crawl_store", "Updating knowledge store", "complete", "Knowledge/catalog data refreshed.", completed_at=updated_at),
            operation_stage(
                "crawl_report",
                "Refreshing crawl report",
                "complete",
                "Crawl report saved.",
                completed_at=str(report.get("created_at") or updated_at),
                duration_ms=duration,
            ),
        ]
    elif status == "failed":
        stages[0] = operation_stage(
            "crawl_queue",
            "Queueing crawl job",
            "complete",
            "Crawler accepted the request.",
            completed_at=updated_at,
        )
        stages[1] = operation_stage(
            "crawl_connect",
            "Connecting to website",
            "failed",
            message or "Crawler failed.",
            completed_at=updated_at,
        )
    return operation(
        "crawl",
        "Crawler run",
        status,
        message or operation_message(status, "Crawler"),
        stages,
        result_tab="crawl",
        started_at=updated_at if raw_status == admin_db.CRAWL_STATUS_RUNNING else "",
        completed_at=updated_at if status in {"complete", "failed"} else "",
        logs=stage_logs(stages),
    )


def readiness_operation_status(client: dict[str, Any]) -> dict[str, Any]:
    site_id = str(client.get("site_id") or "")
    report = readiness_report(site_id)
    scanned_at = str(report.get("scanned_at") or "")
    capabilities = report.get("capabilities") if isinstance(report.get("capabilities"), list) else []
    supported = sum(
        1
        for item in capabilities
        if isinstance(item, dict) and item.get("supported")
    )
    total = len(capabilities)
    blockers = [
        item
        for item in capabilities
        if isinstance(item, dict) and item.get("blocking") is not False and not item.get("supported")
    ]
    if not report:
        return operation(
            "readiness",
            "Readiness scan",
            "pending",
            "No readiness scan has been saved yet.",
            [
                operation_stage("readiness_context", "Preparing client context", "pending", "Waiting for scan."),
                operation_stage("readiness_evidence", "Loading latest adapter evidence", "pending", "Waiting for scan."),
                operation_stage("readiness_scan", "Scanning website capabilities", "pending", "Waiting for scan."),
                operation_stage("readiness_compare", "Comparing domain action contract", "pending", "Waiting for scan."),
                operation_stage("readiness_save", "Saving readiness report", "pending", "Waiting for scan."),
            ],
            result_tab="readiness",
        )
    scan_status = "failed" if not capabilities or blockers or report.get("platform") == "unreachable" else "complete"
    if not capabilities:
        scan_message = "No readiness capabilities were verified."
        compare_message = "No capability evidence was available to compare."
    elif blockers:
        scan_message = f"{len(blockers)} blocking readiness check(s) require attention."
        compare_message = "Blocking action gaps found."
    else:
        scan_message = f"{supported}/{total} checks supported."
        compare_message = "Action contract compared."
    stages = [
        operation_stage("readiness_context", "Preparing client context", "complete", "Client context loaded.", completed_at=scanned_at),
        operation_stage("readiness_evidence", "Loading latest adapter evidence", "complete", "Adapter evidence loaded.", completed_at=scanned_at),
        operation_stage("readiness_scan", "Scanning website capabilities", scan_status, scan_message, completed_at=scanned_at),
        operation_stage("readiness_compare", "Comparing domain action contract", scan_status, compare_message, completed_at=scanned_at),
        operation_stage("readiness_save", "Saving readiness report", "complete", "Readiness report saved.", completed_at=scanned_at),
    ]
    return operation(
        "readiness",
        "Readiness scan",
        scan_status,
        scan_message,
        stages,
        result_tab="readiness",
        completed_at=scanned_at,
        logs=stage_logs(stages),
    )


def integration_operation_status(client: dict[str, Any], vertical_config: dict[str, Any]) -> dict[str, Any]:
    initialization = dict_value(vertical_config.get("initialization"))
    raw_stages = initialization.get("stages") if isinstance(initialization.get("stages"), list) else []
    if not initialization:
        stages = [
            operation_stage("integration_queue", "Queueing setup run", "pending", "Waiting for setup run."),
            operation_stage("crawl", "Crawling source website", "pending", "Waiting for setup run."),
            operation_stage("flow_discovery", "Discovering routes and actions", "pending", "Waiting for setup run."),
            operation_stage("flow_rehearsal", "Validating adapter behavior", "pending", "Waiting for setup run."),
            operation_stage("assistant_smoke_tests", "Running prompt checks", "pending", "Waiting for setup run."),
            operation_stage("integration_save", "Saving evidence", "pending", "Waiting for setup run."),
        ]
        return operation(
            "integration",
            "Setup run",
            "pending",
            "No setup run has been saved yet.",
            stages,
            result_tab="integration",
        )
    stages = [integration_stage_from_saved(stage) for stage in raw_stages if isinstance(stage, dict)]
    if not stages:
        stages = [operation_stage("integration_queue", "Queueing setup run", "running", "Setup run accepted.")]
    if all(stage["status"] != "running" for stage in stages):
        stages.append(
            operation_stage(
                "integration_save",
                "Saving evidence",
                "complete",
                "Setup evidence saved.",
                completed_at=str(initialization.get("completed_at") or ""),
            )
        )
    status = normalize_operation_status(str(initialization.get("status") or "unknown"), stages)
    message = str(initialization.get("error") or "") or operation_message(status, "Setup run")
    if only_prompt_checks_failed(stages):
        message = "Assistant smoke tests failed. Open the prompt checks for exact evidence before enabling this client."
    if status == "running" and initialization.get("cancel_requested"):
        message = "Setup stop requested. Waiting for the current stage checkpoint."
    return operation(
        "integration",
        "Setup run",
        status,
        message,
        stages,
        result_tab="integration",
        started_at=str(initialization.get("started_at") or ""),
        completed_at=str(initialization.get("completed_at") or ""),
        duration_ms=float(initialization.get("duration_ms") or 0.0),
        logs=stage_logs(stages),
    )


def integration_stage_from_saved(stage: dict[str, Any]) -> dict[str, Any]:
    name = str(stage.get("name") or "stage")
    return operation_stage(
        name,
        integration_stage_label(name),
        normalize_stage_status(str(stage.get("status") or "unknown")),
        str(stage.get("message") or ""),
        started_at=str(stage.get("started_at") or ""),
        completed_at=str(stage.get("completed_at") or ""),
        duration_ms=float(stage.get("duration_ms") or 0.0),
        detail={key: value for key, value in stage.items() if key not in {"name", "status", "message", "started_at", "completed_at", "duration_ms"}},
    )


def integration_stage_label(name: str) -> str:
    return {
        "crawl": "Crawling source website",
        "flow_discovery": "Discovering routes and actions",
        "flow_rehearsal": "Validating adapter behavior",
        "flow_regression": "Comparing flow changes",
        "readiness_scan": "Scanning readiness",
        "assistant_smoke_tests": "Running prompt checks",
        "integration_save": "Saving evidence",
        "integration_queue": "Queueing setup run",
    }.get(name, name.replace("_", " ").title())


def only_prompt_checks_failed(stages: list[dict[str, Any]]) -> bool:
    failed = [stage for stage in stages if stage["status"] == "failed"]
    return bool(failed) and all(stage["name"] == "assistant_smoke_tests" for stage in failed)


def normalize_stage_status(status: str) -> str:
    normalized = status.lower()
    if normalized in {"ok", "complete", "completed", "success", "passed"}:
        return "complete"
    if normalized in {"failed", "error", "canceled", "cancelled", "timed_out", "timeout"}:
        return "failed"
    if normalized == "running":
        return "running"
    if normalized == "skipped":
        return "skipped"
    return "pending"


def normalize_operation_status(raw_status: str, stages: list[dict[str, Any]]) -> str:
    normalized = raw_status.lower()
    if any(stage["status"] == "running" for stage in stages) or normalized == "running":
        return "running"
    if any(stage["status"] == "failed" for stage in stages) or normalized in {"failed", "error", "canceled", "cancelled", "timed_out", "timeout"}:
        return "failed"
    if stages and all(stage["status"] in {"complete", "skipped"} for stage in stages):
        return "complete"
    if normalized in {"ok", "complete", "completed", "success"}:
        return "complete"
    return "pending"


def operation(
    kind: str,
    label: str,
    status: str,
    message: str,
    stages: list[dict[str, Any]],
    *,
    result_tab: str,
    started_at: str = "",
    completed_at: str = "",
    duration_ms: float = 0.0,
    logs: list[str] | None = None,
) -> dict[str, Any]:
    progress = operation_progress(stages)
    return {
        "kind": kind,
        "label": label,
        "status": status,
        "message": message,
        "progress": progress,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": max(0.0, float(duration_ms or 0.0)),
        "result_tab": result_tab,
        "stages": stages,
        "logs": logs or [],
    }


def operation_stage(
    name: str,
    label: str,
    status: str,
    message: str,
    *,
    started_at: str = "",
    completed_at: str = "",
    duration_ms: float = 0.0,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "status": status,
        "message": message,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": max(0.0, float(duration_ms or 0.0)),
        "detail": detail or {},
    }


def operation_progress(stages: list[dict[str, Any]]) -> int:
    if not stages:
        return 0
    complete_weight = sum(1 for stage in stages if stage.get("status") in {"complete", "skipped"})
    running_weight = 0.5 if any(stage.get("status") == "running" for stage in stages) else 0
    return min(100, int(((complete_weight + running_weight) / len(stages)) * 100))


def operation_message(status: str, label: str) -> str:
    if status == "running":
        return f"{label} is running."
    if status == "complete":
        return f"{label} completed."
    if status == "failed":
        return f"{label} failed."
    return f"{label} has not started."


def stage_logs(stages: list[dict[str, Any]]) -> list[str]:
    logs: list[str] = []
    for stage in stages:
        status = str(stage.get("status") or "unknown")
        label = str(stage.get("label") or stage.get("name") or "Stage")
        message = str(stage.get("message") or "")
        logs.append(f"{label}: {status}{f' - {message}' if message else ''}")
    return logs


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_crawl_report(site_id: str) -> dict[str, Any]:
    try:
        return dict_value(admin_db.get_latest_crawl_report(site_id))
    except psycopg.Error:
        logger.warning("Unable to load latest crawl report for %s", site_id, exc_info=True)
        return {}


def readiness_report(site_id: str) -> dict[str, Any]:
    try:
        return dict_value(admin_db.get_readiness_report(site_id))
    except psycopg.Error:
        logger.warning("Unable to load readiness report for %s", site_id, exc_info=True)
        return {}
