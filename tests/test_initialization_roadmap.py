import pytest

from agent.adapters.shopify import ShopifyAdapter
from agent.adapters.woocommerce import WooCommerceAdapter
from agent.adapter_repair import build_action_repair_proposals
from agent.extractor import extract_selectors_from_html
from agent.client_initialization import run_widget_initialization
from agent.scanner import (
    SiteCapability,
    _barrier_capabilities,
    _check_cart,
    _check_checkout,
    _client_hook_capabilities,
    _flow_capabilities,
    _is_client_hook_adapter,
    _rehearsal_capabilities,
    _vertical_data_capabilities,
    _vertical_expected_action_capabilities,
)
from agent.tenant_isolation import build_tenant_isolation_audit
from agent.verticals.registry import list_verticals
from db.admin import _validated_settings

def test_auto_initialization_runs_readiness_stage(monkeypatch) -> None:
    saved_reports = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._crawl_stage",
        lambda *args, **kwargs: {"name": "crawl", "status": "ok", "message": "done"},
    )
    monkeypatch.setattr(
        "agent.client_initialization._flow_stage",
        lambda *args, **kwargs: (
            {"summary": {"pages": 2}},
            {"name": "flow_discovery", "status": "ok", "message": "done"},
        ),
    )
    monkeypatch.setattr(
        "agent.client_initialization._rehearsal_stage",
        lambda *args, **kwargs: (
            {"summary": {"verified": 1}},
            {"name": "flow_rehearsal", "status": "ok", "message": "done"},
        ),
    )
    monkeypatch.setattr(
        "agent.client_initialization._regression_stage",
        lambda *args, **kwargs: {"name": "flow_regression", "status": "ok", "message": "done"},
    )
    monkeypatch.setattr(
        "agent.client_initialization._readiness_stage",
        lambda *args, **kwargs: {"name": "readiness_scan", "status": "ok", "message": "done"},
    )

    report = run_widget_initialization(
        "policy_site",
        "https://policy.example.com",
        vertical_key="insurance",
        run_crawl=True,
        run_flow=True,
        run_rehearsal=True,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=True,
    )

    assert report["status"] == "ok"
    assert [stage["name"] for stage in report["stages"]] == [
        "crawl",
        "flow_discovery",
        "flow_rehearsal",
        "flow_regression",
        "readiness_scan",
    ]
    assert saved_reports[0]["status"] == "running"


def test_auto_initialization_persists_live_stage_progress(monkeypatch) -> None:
    saved_reports = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._crawl_stage",
        lambda *args, **kwargs: {"name": "crawl", "status": "ok", "message": "crawl done"},
    )
    monkeypatch.setattr(
        "agent.client_initialization._readiness_stage",
        lambda *args, **kwargs: {"name": "readiness_scan", "status": "ok", "message": "ready"},
    )

    report = run_widget_initialization(
        "policy_site",
        "https://policy.example.com",
        vertical_key="insurance",
        run_crawl=True,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=True,
    )

    running_crawl = next(
        saved
        for saved in saved_reports
        if saved.get("stages") and saved["stages"][-1]["name"] == "crawl" and saved["stages"][-1]["status"] == "running"
    )
    completed_crawl = next(
        saved
        for saved in saved_reports
        if saved.get("stages") and saved["stages"][-1]["name"] == "crawl" and saved["stages"][-1]["status"] == "ok"
    )
    running_readiness = next(
        saved
        for saved in saved_reports
        if saved.get("stages")
        and saved["stages"][-1]["name"] == "readiness_scan"
        and saved["stages"][-1]["status"] == "running"
    )

    assert report["status"] == "ok"
    assert running_crawl["stages"][-1]["completed_at"] == ""
    assert running_crawl["stages"][-1]["started_at"]
    assert completed_crawl["stages"][-1]["message"] == "crawl done"
    assert running_readiness["stages"][0]["status"] == "ok"


def test_auto_initialization_stops_when_cancel_requested(monkeypatch) -> None:
    from agent import client_initialization

    saved_reports = []
    cancel_requested = {"value": False}

    monkeypatch.setattr(client_initialization, "_save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr(client_initialization, "_client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(client_initialization.admin_db, "setup_cancel_requested", lambda site_id, run_id="": cancel_requested["value"])
    monkeypatch.setattr(client_initialization.admin_db, "update_client_crawl_status", lambda *args, **kwargs: None)

    def fake_crawl(*args, **kwargs):
        cancel_requested["value"] = True
        return {"name": "crawl", "status": "ok", "message": "crawl done"}

    monkeypatch.setattr(client_initialization, "_crawl_stage", fake_crawl)
    monkeypatch.setattr(
        client_initialization,
        "_readiness_stage",
        lambda *args, **kwargs: {"name": "readiness_scan", "status": "ok", "message": "should not run"},
    )

    report = run_widget_initialization(
        "policy_site",
        "https://policy.example.com",
        vertical_key="insurance",
        run_crawl=True,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=True,
    )

    assert report["status"] == "canceled"
    assert report["error"] == "Setup run canceled by admin."
    assert [stage["name"] for stage in report["stages"]] == ["crawl", "setup_stopped"]
    assert saved_reports[-1]["run_id"]
    assert saved_reports[-1]["timeout_seconds"] > 0


def test_initialization_save_does_not_overwrite_terminal_same_run(monkeypatch) -> None:
    from db import clients as clients_db

    writes = []
    monkeypatch.setattr(
        clients_db,
        "_client_vertical_config",
        lambda site_id: {"initialization": {"status": "timed_out", "run_id": "run-1", "error": "old timeout"}},
    )
    monkeypatch.setattr(clients_db, "_write_client_vertical_config", lambda site_id, vertical_config: writes.append(vertical_config))
    monkeypatch.setattr(clients_db, "get_client_detail", lambda site_id: {"site_id": site_id, "status": "live"})

    result = clients_db.save_client_initialization_report(
        "demo_site",
        {
            "status": "running",
            "run_id": "run-1",
            "site_id": "demo_site",
            "stages": [{"name": "crawl", "status": "ok", "message": "late write"}],
        },
    )

    assert result == {"site_id": "demo_site", "status": "live"}
    assert writes == []


def test_auto_initialization_runs_assistant_smoke_stage_when_requested(monkeypatch) -> None:
    saved_reports = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._assistant_smoke_stage",
        lambda *args, **kwargs: {
            "name": "assistant_smoke_tests",
            "status": "ok",
            "message": "2/2 assistant smoke tests passed.",
            "total": 2,
            "passed": 2,
            "failed": 0,
        },
    )

    report = run_widget_initialization(
        "ai_kart",
        "https://shop.example.com",
        vertical_key="ecommerce",
        run_crawl=False,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=False,
        run_smoke_tests=True,
    )

    running_smoke = next(
        saved
        for saved in saved_reports
        if saved.get("stages")
        and saved["stages"][-1]["name"] == "assistant_smoke_tests"
        and saved["stages"][-1]["status"] == "running"
    )

    assert report["status"] == "ok"
    assert [stage["name"] for stage in report["stages"]] == ["assistant_smoke_tests"]
    assert running_smoke["stages"][-1]["message"] == "Assistant prompt smoke tests are running."


def test_auto_initialization_clears_setup_when_only_prompt_checks_need_repair(monkeypatch) -> None:
    setup_updates = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: None)
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._crawl_stage",
        lambda *args, **kwargs: {"name": "crawl", "status": "ok", "message": "Content crawl completed."},
    )
    monkeypatch.setattr(
        "agent.client_initialization._assistant_smoke_stage",
        lambda *args, **kwargs: {
            "name": "assistant_smoke_tests",
            "status": "failed",
            "message": "0/1 assistant smoke tests passed.",
            "total": 1,
            "passed": 0,
            "failed": 1,
        },
    )
    monkeypatch.setattr(
        "agent.client_initialization.admin_db.update_client_setup_status",
        lambda site_id, **kwargs: setup_updates.append((site_id, kwargs)),
    )

    report = run_widget_initialization(
        "ai_kart",
        "https://shop.example.com",
        vertical_key="ecommerce",
        run_crawl=True,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=False,
        run_smoke_tests=True,
    )

    assert report["status"] == "partial"
    assert setup_updates
    assert setup_updates[-1][0] == "ai_kart"
    assert setup_updates[-1][1]["needs_setup"] is False


def test_operation_status_does_not_mark_setup_failed_for_prompt_repair_only() -> None:
    from api import crm

    operation_status = crm._client_operation_status(
        {
            "site_id": "ai_kart",
            "vertical_config": {
                "initialization": {
                    "status": "partial",
                    "started_at": "2026-07-06T10:00:00+00:00",
                    "completed_at": "2026-07-06T10:05:00+00:00",
                    "duration_ms": 300000,
                    "stages": [
                        {"name": "crawl", "status": "ok", "message": "Content crawl completed."},
                        {"name": "readiness_scan", "status": "ok", "message": "Readiness scan completed."},
                        {
                            "name": "assistant_smoke_tests",
                            "status": "failed",
                            "message": "0/1 assistant smoke tests passed.",
                            "total": 1,
                            "passed": 0,
                            "failed": 1,
                        },
                    ],
                }
            },
        }
    )

    integration = operation_status["operations"]["integration"]

    assert integration["status"] == "complete"
    assert "Prompt checks found repair items" in integration["message"]
    assert integration["stages"][2]["status"] == "failed"



