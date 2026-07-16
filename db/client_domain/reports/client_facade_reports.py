"""Report and event facade exports for db.clients."""

from __future__ import annotations

from typing import Any

from db.client_domain.reports import client_report_persistence
from db.client_domain.events import client_event_persistence


def exports(runtime: Any) -> dict[str, Any]:
    def save_client_flow_report(site_id: str, flow_report: dict[str, Any]) -> dict[str, Any]:
        return client_report_persistence.save_client_flow_report(
            site_id,
            flow_report,
            runtime._report_persistence(),
        )

    def save_client_rehearsal_report(site_id: str, rehearsal_report: dict[str, Any]) -> dict[str, Any]:
        return client_report_persistence.save_client_rehearsal_report(
            site_id,
            rehearsal_report,
            runtime._report_persistence(),
        )

    def save_client_regression_report(site_id: str, regression_report: dict[str, Any]) -> dict[str, Any]:
        return client_report_persistence.save_client_regression_report(
            site_id,
            regression_report,
            runtime._report_persistence(),
        )

    def save_client_initialization_report(site_id: str, initialization_report: dict[str, Any]) -> dict[str, Any]:
        return client_report_persistence.save_client_initialization_report(
            site_id,
            initialization_report,
            runtime._report_persistence(),
        )

    def setup_cancel_requested(site_id: str, run_id: str = "") -> bool:
        return client_report_persistence.setup_cancel_requested(
            site_id,
            run_id,
            runtime._report_persistence(),
        )

    def request_client_setup_cancel(site_id: str) -> dict[str, Any]:
        return client_report_persistence.request_client_setup_cancel(
            site_id,
            runtime._report_persistence(),
        )

    def expire_stale_client_initialization_runs(max_age_seconds: int) -> int:
        return client_report_persistence.expire_stale_client_initialization_runs(
            max_age_seconds,
            runtime._report_persistence(),
        )

    def save_client_assistant_smoke_report(site_id: str, smoke_report: dict[str, Any]) -> dict[str, Any]:
        return client_report_persistence.save_client_assistant_smoke_report(
            site_id,
            smoke_report,
            runtime._report_persistence(),
        )

    def save_client_policy_event(site_id: str, event: dict[str, Any]) -> dict[str, Any]:
        return client_event_persistence.save_client_policy_event(site_id, event, runtime._event_persistence())

    def save_client_action_event(site_id: str, event: dict[str, Any]) -> dict[str, Any]:
        return client_event_persistence.save_client_action_event(site_id, event, runtime._event_persistence())

    def save_client_interaction_event(site_id: str, event: dict[str, Any]) -> dict[str, Any]:
        return client_event_persistence.save_client_interaction_event(site_id, event, runtime._event_persistence())

    return {
        "save_client_flow_report": save_client_flow_report,
        "save_client_rehearsal_report": save_client_rehearsal_report,
        "save_client_regression_report": save_client_regression_report,
        "save_client_initialization_report": save_client_initialization_report,
        "setup_cancel_requested": setup_cancel_requested,
        "request_client_setup_cancel": request_client_setup_cancel,
        "expire_stale_client_initialization_runs": expire_stale_client_initialization_runs,
        "save_client_assistant_smoke_report": save_client_assistant_smoke_report,
        "save_client_policy_event": save_client_policy_event,
        "save_client_action_event": save_client_action_event,
        "save_client_interaction_event": save_client_interaction_event,
    }
