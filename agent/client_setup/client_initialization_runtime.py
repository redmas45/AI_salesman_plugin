"""Automatic one-script client initialization jobs."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import config
import psycopg
from agent.client_setup import client_initialization_smoke
from agent.flows.flow_discovery import DEFAULT_FLOW_MAX_PAGES, discover_site_flows
from agent.flows.flow_regression import build_flow_regression_report
from agent.flows.flow_rehearsal import DEFAULT_REHEARSAL_MAX_STEPS, rehearse_site_flows
from agent.ingestion_helpers.ingestion_facade import sync_web_crawl
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)

INITIALIZATION_SOURCE = "widget_registration"
NON_BLOCKING_SETUP_FAILURE_STAGES = frozenset({"assistant_smoke_tests"})
SMOKE_MAX_ATTEMPTS = 1


class SetupRunStopped(Exception):
    """Raised when a setup run should stop at the next safe checkpoint."""

    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def run_widget_initialization(
    site_id: str,
    site_url: str,
    *,
    vertical_key: str,
    run_crawl: bool,
    run_flow: bool,
    run_rehearsal: bool,
    crawl_max_pages: int,
    crawl_max_depth: int,
    flow_max_pages: int = DEFAULT_FLOW_MAX_PAGES,
    rehearsal_max_steps: int = DEFAULT_REHEARSAL_MAX_STEPS,
    run_readiness: bool = True,
    run_smoke_tests: bool = False,
) -> dict[str, Any]:
    """Run automatic onboarding after the universal script registers."""
    run_id = uuid.uuid4().hex
    timeout_seconds = max(1, int(getattr(config, "SETUP_RUN_TIMEOUT_SECONDS", 7200) or 7200))
    started = time.monotonic()
    started_at = _utc_now()
    stages: list[dict[str, Any]] = []
    stop_check_failed = False

    def save_running() -> None:
        _save_report(
            site_id,
            _report(
                site_id,
                site_url,
                vertical_key,
                "running",
                stages,
                started_at,
                started,
                run_id=run_id,
                timeout_seconds=timeout_seconds,
            ),
        )

    def stop_if_requested() -> None:
        nonlocal stop_check_failed
        elapsed = time.monotonic() - started
        if elapsed > timeout_seconds:
            raise SetupRunStopped("timed_out", f"Setup run timed out after {timeout_seconds} seconds.")
        if stop_check_failed:
            return
        try:
            if admin_db.setup_cancel_requested(site_id, run_id):
                raise SetupRunStopped("canceled", "Setup run canceled by admin.")
        except SetupRunStopped:
            raise
        except Exception as exc:
            stop_check_failed = True
            logger.warning("Setup cancel check failed for %s: %s", site_id, exc)

    def stopped_report(stop: SetupRunStopped) -> dict[str, Any]:
        if stages and stages[-1].get("status") == "running":
            stages[-1] = {
                **stages[-1],
                "status": stop.status,
                "message": stop.message,
                "completed_at": _utc_now(),
            }
        else:
            stages.append(_stage("setup_stopped", stop.status, stop.message))
        final_report = _report(
            site_id,
            site_url,
            vertical_key,
            stop.status,
            stages,
            started_at,
            started,
            run_id=run_id,
            timeout_seconds=timeout_seconds,
            error=stop.message,
        )
        _save_report(site_id, final_report)
        _update_crawl_status_safe(site_id, admin_db.CRAWL_STATUS_ERROR, stop.message)
        return final_report

    save_running()

    previous_client = _client_detail(site_id)
    flow_report: dict[str, Any] = {}
    rehearsal_report: dict[str, Any] = {}

    try:
        stop_if_requested()
        if run_crawl:
            _start_stage(stages, "crawl", "Content crawl is running.")
            save_running()
            stages[-1] = _crawl_stage(site_id, site_url, crawl_max_pages, crawl_max_depth)
            save_running()
            stop_if_requested()
        if run_flow:
            stop_if_requested()
            _start_stage(stages, "flow_discovery", "Adapter flow discovery is running.")
            save_running()
            flow_report, flow_stage = _flow_stage(site_id, site_url, vertical_key, flow_max_pages)
            stages[-1] = flow_stage
            save_running()
            stop_if_requested()
        rehearsal_flow_report = flow_report or _existing_flow_report(site_id)
        if run_rehearsal and rehearsal_flow_report:
            stop_if_requested()
            _start_stage(stages, "flow_rehearsal", "Safe action rehearsal is running.")
            save_running()
            rehearsal_report, rehearsal_stage = _rehearsal_stage(site_id, site_url, rehearsal_flow_report, rehearsal_max_steps)
            stages[-1] = rehearsal_stage
            save_running()
            stop_if_requested()
        elif run_rehearsal:
            stages.append(_stage("flow_rehearsal", "skipped", "No flow report is available to rehearse."))
            save_running()
            stop_if_requested()
        if flow_report:
            stop_if_requested()
            _start_stage(stages, "flow_regression", "Flow regression comparison is running.")
            save_running()
            stages[-1] = _regression_stage(site_id, site_url, previous_client, flow_report, rehearsal_report)
            save_running()
            stop_if_requested()
        if run_readiness:
            stop_if_requested()
            _start_stage(stages, "readiness_scan", "Readiness scan is running.")
            save_running()
            stages[-1] = _readiness_stage(site_id, site_url, vertical_key)
            save_running()
            stop_if_requested()
        if run_smoke_tests:
            stop_if_requested()
            _start_stage(stages, "assistant_smoke_tests", "Assistant prompt smoke tests are running.")
            save_running()
            stages[-1] = _assistant_smoke_stage(site_id, vertical_key)
            save_running()
            stop_if_requested()
    except SetupRunStopped as stop:
        return stopped_report(stop)

    status = _overall_status(stages)
    final_report = _report(
        site_id,
        site_url,
        vertical_key,
        status,
        stages,
        started_at,
        started,
        run_id=run_id,
        timeout_seconds=timeout_seconds,
    )
    _save_report(site_id, final_report)

    if status == "ok" or _setup_evidence_ready(stages):
        _update_setup_status_safe(site_id, needs_setup=False, last_setup_at=_utc_now())

    return final_report


def _crawl_stage(site_id: str, site_url: str, max_pages: int, max_depth: int) -> dict[str, Any]:
    try:
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_RUNNING, "Auto initialization crawl started.")
        sync_web_crawl(
            site_url,
            max_pages=max_pages,
            max_depth=max_depth,
            site_id=site_id,
            reconcile_missing=True,
            source_name="widget_initialization_crawler",
        )
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_OK, "Auto initialization crawl completed.")
        return _stage("crawl", "ok", "Content crawl completed.")
    except Exception as exc:
        logger.error("Auto initialization crawl failed for %s: %s", site_id, exc)
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_ERROR, str(exc))
        return _stage("crawl", "failed", str(exc))


def _flow_stage(site_id: str, site_url: str, vertical_key: str, max_pages: int) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        flow_report = asyncio.run(
            discover_site_flows(site_url, site_id, vertical_key=vertical_key, max_pages=max_pages)
        ).to_dict()
        admin_db.save_client_flow_report(site_id, flow_report)
        summary = flow_report.get("summary") if isinstance(flow_report.get("summary"), dict) else {}
        return flow_report, _stage("flow_discovery", "ok", "Flow discovery completed.", summary=summary)
    except Exception as exc:
        logger.error("Auto flow discovery failed for %s: %s", site_id, exc)
        return {}, _stage("flow_discovery", "failed", str(exc))


def _rehearsal_stage(
    site_id: str,
    site_url: str,
    flow_report: dict[str, Any],
    max_steps: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        rehearsal_report = asyncio.run(
            rehearse_site_flows(site_url, site_id, flow_report, max_steps=max_steps)
        ).to_dict()
        admin_db.save_client_rehearsal_report(site_id, rehearsal_report)
        summary = rehearsal_report.get("summary") if isinstance(rehearsal_report.get("summary"), dict) else {}
        return rehearsal_report, _stage("flow_rehearsal", "ok", "Flow rehearsal completed.", summary=summary)
    except Exception as exc:
        logger.error("Auto flow rehearsal failed for %s: %s", site_id, exc)
        return {}, _stage("flow_rehearsal", "failed", str(exc))


def _regression_stage(
    site_id: str,
    site_url: str,
    previous_client: dict[str, Any],
    flow_report: dict[str, Any],
    rehearsal_report: dict[str, Any],
) -> dict[str, Any]:
    try:
        previous_config = previous_client.get("vertical_config") if isinstance(previous_client.get("vertical_config"), dict) else {}
        regression = build_flow_regression_report(
            previous_config.get("flow") if isinstance(previous_config.get("flow"), dict) else {},
            flow_report,
            previous_rehearsal=previous_config.get("rehearsal") if isinstance(previous_config.get("rehearsal"), dict) else {},
            current_rehearsal=rehearsal_report,
            site_id=site_id,
            site_url=site_url,
        ).to_dict()
        admin_db.save_client_regression_report(site_id, regression)
        return _stage(
            "flow_regression",
            "ok",
            "Flow regression snapshot saved.",
            regression_status=regression.get("status"),
        )
    except Exception as exc:
        logger.error("Auto flow regression failed for %s: %s", site_id, exc)
        return _stage("flow_regression", "failed", str(exc))


def _readiness_stage(site_id: str, site_url: str, vertical_key: str) -> dict[str, Any]:
    try:
        client = _client_detail(site_id)
        vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
        from agent.scanning.scanner import scan_site

        report = asyncio.run(
            scan_site(
                site_url,
                site_id,
                adapter_name=str(client.get("adapter_name") or ""),
                vertical_key=str(client.get("vertical_key") or vertical_key),
                vertical_config=vertical_config,
            )
        ).to_dict()
        admin_db.save_readiness_report(site_id, report)
        supported = sum(
            1
            for capability in report.get("capabilities", [])
            if capability.get("supported") or capability.get("blocking") is False
        )
        total = len(report.get("capabilities", []))
        return _stage(
            "readiness_scan",
            "ok",
            "Readiness scan completed.",
            supported=supported,
            total=total,
            platform=report.get("platform"),
            platform_confidence=report.get("platform_confidence"),
        )
    except Exception as exc:
        logger.error("Auto readiness scan failed for %s: %s", site_id, exc)
        return _stage("readiness_scan", "failed", str(exc))


def _initialization_runtime() -> Any:
    import sys

    return sys.modules[__name__]


globals().update(client_initialization_smoke.exports(_initialization_runtime()))


def _client_detail(site_id: str) -> dict[str, Any]:
    try:
        return admin_db.get_client_detail(site_id)
    except LookupError:
        return {"site_id": site_id, "vertical_config": {}}
    except psycopg.Error as exc:
        logger.warning("Client detail unavailable for %s during setup initialization: %s", site_id, exc)
        return {"site_id": site_id, "vertical_config": {}}


def _existing_flow_report(site_id: str) -> dict[str, Any]:
    client = _client_detail(site_id)
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    flow_report = vertical_config.get("flow")
    return flow_report if isinstance(flow_report, dict) else {}


def _save_report(site_id: str, report: dict[str, Any]) -> None:
    try:
        admin_db.save_client_initialization_report(site_id, report)
    except (LookupError, ValueError) as exc:
        logger.warning("Initialization report could not be saved for %s: %s", site_id, exc)


def _update_crawl_status_safe(site_id: str, status: str, message: str) -> None:
    try:
        admin_db.update_client_crawl_status(site_id, status, message)
    except Exception as exc:
        logger.warning("Setup crawl status could not be updated for %s: %s", site_id, exc)


def _update_setup_status_safe(site_id: str, *, needs_setup: bool, last_setup_at: str) -> None:
    try:
        admin_db.update_client_setup_status(site_id, needs_setup=needs_setup, last_setup_at=last_setup_at)
    except psycopg.Error as exc:
        logger.warning("Setup status could not be updated for %s: %s", site_id, exc)


def _report(
    site_id: str,
    site_url: str,
    vertical_key: str,
    status: str,
    stages: list[dict[str, Any]],
    started_at: str,
    started: float,
    *,
    run_id: str = "",
    timeout_seconds: int = 0,
    error: str = "",
) -> dict[str, Any]:
    return {
        "source": INITIALIZATION_SOURCE,
        "status": status,
        "run_id": run_id,
        "site_id": site_id,
        "site_url": site_url,
        "vertical_key": vertical_key,
        "started_at": started_at,
        "completed_at": _utc_now() if status != "running" else "",
        "duration_ms": (time.monotonic() - started) * 1000,
        "timeout_seconds": max(0, int(timeout_seconds or 0)),
        "error": error,
        "stages": [dict(stage) for stage in stages],
    }


def _stage(name: str, status: str, message: str, **extra: Any) -> dict[str, Any]:
    started_at = str(extra.pop("started_at", "") or "")
    completed_at = str(extra.pop("completed_at", "") or "")
    return {
        "name": name,
        "status": status,
        "message": message,
        "started_at": started_at,
        "completed_at": completed_at if status == "running" else completed_at or _utc_now(),
        **extra,
    }


def _start_stage(stages: list[dict[str, Any]], name: str, message: str) -> None:
    stages.append(_stage(name, "running", message, started_at=_utc_now(), completed_at=""))


def _overall_status(stages: list[dict[str, Any]]) -> str:
    failed = [stage for stage in stages if stage.get("status") in {"failed", "canceled", "timed_out"}]
    succeeded = [stage for stage in stages if stage.get("status") == "ok"]
    if failed and succeeded:
        return "partial"
    if failed:
        return "error"
    return "ok"


def _setup_evidence_ready(stages: list[dict[str, Any]]) -> bool:
    return bool(_successful_setup_evidence_stages(stages)) and not _blocking_setup_failures(stages)


def _successful_setup_evidence_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        stage
        for stage in stages
        if stage.get("status") == "ok" and str(stage.get("name") or "") not in NON_BLOCKING_SETUP_FAILURE_STAGES
    ]


def _blocking_setup_failures(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        stage
        for stage in stages
        if stage.get("status") in {"failed", "canceled", "timed_out"}
        and str(stage.get("name") or "") not in NON_BLOCKING_SETUP_FAILURE_STAGES
    ]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
