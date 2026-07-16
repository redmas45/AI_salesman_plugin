"""Persistence workflows for client flow, setup, and smoke-test reports."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

import config


# Persistence dependencies are explicit so report merging can be tested without a database.
@dataclass(frozen=True)
class ClientReportPersistence:
    safe_site_id: Callable[[str], str]
    safe_action_text: Callable[[Any], str]
    client_vertical_config: Callable[[str], dict[str, Any]]
    write_client_vertical_config: Callable[[str, dict[str, Any]], None]
    get_client_detail: Callable[[str], dict[str, Any]]
    record_audit_event_safely: Callable[..., None]
    init_admin_schema: Callable[[], None]
    connect: Callable[[], Any]
    deleted_status: str
    crawl_status_error: str
    utc_timestamp: Callable[[], str]
    json_object: Callable[[Any], dict[str, Any]]
    dict_config: Callable[[Any], dict[str, Any]]
    safe_route_map: Callable[[Any], dict[str, str]]
    safe_flow_list: Callable[[Any, int], list[dict[str, Any]]]
    validated_action_map: Callable[[Any], dict[str, Any]]
    validated_assistant_smoke_report: Callable[[Any], dict[str, Any]]
    validated_barrier_report: Callable[[Any], list[dict[str, Any]]]
    validated_flow_report: Callable[[Any], dict[str, Any]]
    validated_regression_report: Callable[[Any], dict[str, Any]]
    validated_rehearsal_report: Callable[[Any], dict[str, Any]]
    merged_initialization_report: Callable[[Any, dict[str, Any]], tuple[dict[str, Any], bool]]
    setup_cancel_requested: Callable[[Any, str], bool]
    setup_cancel_update: Callable[[Any, str], tuple[dict[str, Any], bool]]
    expired_initialization_update: Callable[..., tuple[dict[str, Any], str] | None]
    refresh_flow_repair_proposals: Callable[[str, dict[str, Any]], None]


def save_client_flow_report(site_id: str, flow_report: dict[str, Any], deps: ClientReportPersistence) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(flow_report, dict):
        raise ValueError("Flow report must be a JSON object.")
    vertical_config = deps.client_vertical_config(clean_site_id)
    vertical_config["flow"] = deps.validated_flow_report(flow_report)
    vertical_config["barriers"] = deps.validated_barrier_report(flow_report.get("barriers"))
    vertical_config["routes"] = {
        **deps.dict_config(vertical_config.get("routes")),
        **deps.safe_route_map(flow_report.get("routes")),
    }
    vertical_config["actions"] = {
        **deps.dict_config(vertical_config.get("actions")),
        **deps.validated_action_map(deps.dict_config(flow_report.get("adapter_actions"))),
    }
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def save_client_rehearsal_report(
    site_id: str,
    rehearsal_report: dict[str, Any],
    deps: ClientReportPersistence,
) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(rehearsal_report, dict):
        raise ValueError("Flow rehearsal report must be a JSON object.")
    vertical_config = deps.client_vertical_config(clean_site_id)
    vertical_config["rehearsal"] = deps.validated_rehearsal_report(rehearsal_report)
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def save_client_regression_report(
    site_id: str,
    regression_report: dict[str, Any],
    deps: ClientReportPersistence,
) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(regression_report, dict):
        raise ValueError("Flow regression report must be a JSON object.")
    vertical_config = deps.client_vertical_config(clean_site_id)
    vertical_config["regression"] = deps.validated_regression_report(regression_report)
    deps.refresh_flow_repair_proposals(clean_site_id, vertical_config)
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    return deps.get_client_detail(clean_site_id)


def save_client_initialization_report(
    site_id: str,
    initialization_report: dict[str, Any],
    deps: ClientReportPersistence,
) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(initialization_report, dict):
        raise ValueError("Initialization report must be a JSON object.")
    vertical_config = deps.client_vertical_config(clean_site_id)
    next_initialization, should_write = deps.merged_initialization_report(
        vertical_config.get("initialization"),
        initialization_report,
    )
    if not should_write:
        return deps.get_client_detail(clean_site_id)
    vertical_config["initialization"] = next_initialization
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    deps.record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="setup_runner",
        event_type="setup_run_status",
        event_scope="setup",
        status=next_initialization["status"],
        request_id=next_initialization["run_id"],
        message=next_initialization["error"] or next_initialization["status"],
        metadata={
            "stage_count": len(next_initialization["stages"]),
            "duration_ms": next_initialization["duration_ms"],
            "cancel_requested": next_initialization["cancel_requested"],
        },
    )
    return deps.get_client_detail(clean_site_id)


def setup_cancel_requested(site_id: str, run_id: str, deps: ClientReportPersistence) -> bool:
    initialization = deps.client_vertical_config(deps.safe_site_id(site_id)).get("initialization")
    return deps.setup_cancel_requested(initialization, run_id)


def request_client_setup_cancel(site_id: str, deps: ClientReportPersistence) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    vertical_config = deps.client_vertical_config(clean_site_id)
    initialization, should_write = deps.setup_cancel_update(
        vertical_config.get("initialization"),
        requested_at=deps.utc_timestamp(),
    )
    if should_write:
        vertical_config["initialization"] = initialization
        deps.write_client_vertical_config(clean_site_id, vertical_config)
        deps.record_audit_event_safely(
            site_id=clean_site_id,
            actor_type="crm_admin",
            event_type="setup_cancel_requested",
            event_scope="setup",
            status="requested",
            request_id=deps.safe_action_text(initialization.get("run_id")),
            message="Setup stop requested from CRM.",
        )
    return deps.get_client_detail(clean_site_id)


def expire_stale_client_initialization_runs(max_age_seconds: int, deps: ClientReportPersistence) -> int:
    max_age = max(60, int(max_age_seconds or config.SETUP_RUN_TIMEOUT_SECONDS or 7200))
    now_epoch = time.time()
    now_text = deps.utc_timestamp()
    expired = 0
    deps.init_admin_schema()
    with deps.connect() as conn:
        rows = conn.execute(
            """
            SELECT site_id, vertical_config_json
            FROM hub_clients
            WHERE status <> %s
            """,
            (deps.deleted_status,),
        ).fetchall()
        for row in rows:
            site_id = deps.safe_site_id(row.get("site_id"))
            vertical_config = deps.json_object(row.get("vertical_config_json"))
            expired_update = deps.expired_initialization_update(
                vertical_config,
                max_age=max_age,
                now_epoch=now_epoch,
                now_text=now_text,
            )
            if expired_update is None:
                continue
            vertical_config, message = expired_update
            _write_expired_initialization(conn, site_id, vertical_config, message, deps)
            expired += 1
        conn.commit()
    return expired


def _write_expired_initialization(
    conn: Any,
    site_id: str,
    vertical_config: dict[str, Any],
    message: str,
    deps: ClientReportPersistence,
) -> None:
    conn.execute(
        """
        UPDATE hub_clients
        SET vertical_config_json = %s,
            last_crawl_status = %s,
            last_crawl_message = %s,
            updated_at = now()
        WHERE site_id = %s AND status <> %s
        """,
        (
            json.dumps(vertical_config, ensure_ascii=False, default=str),
            deps.crawl_status_error,
            message[:500],
            site_id,
            deps.deleted_status,
        ),
    )


def save_client_assistant_smoke_report(
    site_id: str,
    smoke_report: dict[str, Any],
    deps: ClientReportPersistence,
) -> dict[str, Any]:
    clean_site_id = deps.safe_site_id(site_id)
    if not isinstance(smoke_report, dict):
        raise ValueError("Assistant smoke report must be a JSON object.")
    vertical_config = deps.client_vertical_config(clean_site_id)
    vertical_config["assistant_smoke_tests"] = deps.validated_assistant_smoke_report(smoke_report)
    deps.write_client_vertical_config(clean_site_id, vertical_config)
    report = vertical_config["assistant_smoke_tests"]
    deps.record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="setup_runner",
        event_type="assistant_smoke_report",
        event_scope="prompt_checks",
        status=report["status"],
        message=report["message"],
        metadata={"total": report["total"], "passed": report["passed"], "failed": report["failed"]},
    )
    return deps.get_client_detail(clean_site_id)
