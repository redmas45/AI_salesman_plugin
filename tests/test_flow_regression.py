import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from agent import adapter_repair
from agent.adapter_repair import build_flow_repair_proposals
from agent.flow_regression import build_flow_regression_report
from agent.scanner import _regression_capabilities
from api import crm
from api.main import app


def test_flow_regression_detects_removed_changed_and_blocked_actions() -> None:
    report = build_flow_regression_report(
        {
            "site_id": "builder_demo",
            "site_url": "https://builder.example.com",
            "vertical_key": "construction",
            "routes": {"projects": "/projects", "contact": "/contact"},
            "adapter_actions": {
                "REQUEST_ESTIMATE": {"type": "form", "input": "input[name='phone']"},
                "REQUEST_SITE_VISIT": {"type": "click", "selector": "button.visit"},
            },
        },
        {
            "site_id": "builder_demo",
            "site_url": "https://builder.example.com",
            "vertical_key": "construction",
            "routes": {"projects": "/our-work"},
            "adapter_actions": {
                "REQUEST_ESTIMATE": {"type": "form", "input": "input[name='mobile']"},
                "OPEN_PROJECTS": {"type": "navigate", "path": "/our-work"},
            },
        },
        previous_rehearsal={
            "steps": [{"action_name": "REQUEST_ESTIMATE", "supported": True}],
        },
        current_rehearsal={
            "steps": [{"action_name": "REQUEST_ESTIMATE", "supported": False}],
        },
    ).to_dict()

    kinds = {change["kind"] for change in report["changes"]}

    assert report["status"] == "changed"
    assert report["summary"]["high"] >= 2
    assert "route_removed" in kinds
    assert "route_changed" in kinds
    assert "action_removed" in kinds
    assert "action_changed" in kinds
    assert "action_now_blocked" in kinds


def test_flow_regression_baseline_when_no_previous_flow() -> None:
    report = build_flow_regression_report(
        {},
        {
            "site_id": "demo",
            "site_url": "https://demo.example.com",
            "routes": {"home": "/"},
            "adapter_actions": {"OPEN_CONTACT": {"type": "navigate", "path": "/contact"}},
        },
    ).to_dict()

    assert report["status"] == "baseline"
    assert report["summary"]["baseline"] is True
    assert report["changes"] == []


def test_flow_repair_proposals_group_route_and_action_drift() -> None:
    regression = build_flow_regression_report(
        {
            "site_id": "builder_demo",
            "site_url": "https://builder.example.com",
            "vertical_key": "construction",
            "routes": {"projects": "/projects"},
            "adapter_actions": {
                "REQUEST_ESTIMATE": {"type": "click", "selector": "button.old"},
            },
        },
        {
            "site_id": "builder_demo",
            "site_url": "https://builder.example.com",
            "vertical_key": "construction",
            "routes": {"projects": "/our-work"},
            "adapter_actions": {
                "REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"},
            },
        },
    ).to_dict()
    proposals = build_flow_repair_proposals(
        vertical_key="construction",
        vertical_config={
            "routes": {"projects": "/our-work"},
            "actions": {
                "REQUEST_ESTIMATE": {
                    "type": "click",
                    "selector": "button.estimate",
                    "confidence": 0.87,
                },
            },
            "regression": regression,
        },
    )

    by_key = {proposal["key"]: proposal for proposal in proposals}

    assert by_key["route:projects"]["patch"]["routes"]["projects"] == "/our-work"
    assert by_key["action:REQUEST_ESTIMATE"]["patch"]["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.estimate"
    assert by_key["action:REQUEST_ESTIMATE"]["review_required"] is True


def test_llm_flow_repair_proposal_is_validated_and_preferred(monkeypatch) -> None:
    monkeypatch.setattr("config.LLM_EXTRACTOR_ENABLED", True)
    monkeypatch.setattr("config.AZURE_OPENAI_API_KEY", "test-key")

    def fake_flow_repairs(payload: dict, site_id: str) -> dict:
        return {
            "proposals": [
                {
                    "scope": "action",
                    "item": "REQUEST_ESTIMATE",
                    "confidence": 0.93,
                    "reason": "Button label moved after redesign.",
                    "patch": {
                        "actions": {
                            "REQUEST_ESTIMATE": {
                                "type": "click",
                                "selector": "button.estimate-now",
                                "confidence": 0.93,
                            }
                        }
                    },
                }
            ]
        }

    monkeypatch.setattr(adapter_repair, "_request_flow_repairs", fake_flow_repairs)

    proposals = build_flow_repair_proposals(
        vertical_key="construction",
        vertical_config={
            "flow": {
                "site_id": "builder_demo",
                "pages": [{"url": "https://builder.example.com", "title": "Builder", "text_sample": "Get estimate"}],
                "actions": [{"action_name": "REQUEST_ESTIMATE", "label": "Estimate"}],
            },
            "actions": {
                "REQUEST_ESTIMATE": {
                    "type": "click",
                    "selector": "button.old",
                    "confidence": 0.8,
                },
            },
            "regression": {
                "site_id": "builder_demo",
                "status": "changed",
                "changes": [
                    {
                        "kind": "action_now_blocked",
                        "item": "REQUEST_ESTIMATE",
                        "severity": "high",
                        "previous": "supported",
                        "current": "blocked",
                        "evidence": "Previously rehearsed action is now blocked.",
                    }
                ],
            },
        },
    )

    by_key = {proposal["key"]: proposal for proposal in proposals}

    repair = by_key["action:REQUEST_ESTIMATE"]
    assert repair["kind"] == "llm_action_repair"
    assert repair["source"] == "llm_flow_repair"
    assert repair["patch"]["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.estimate-now"
    assert repair["patch"]["actions"]["REQUEST_ESTIMATE"]["source"] == "llm_flow_repair"


def test_llm_flow_repair_rejects_external_routes(monkeypatch) -> None:
    monkeypatch.setattr("config.LLM_EXTRACTOR_ENABLED", True)
    monkeypatch.setattr("config.AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        adapter_repair,
        "_request_flow_repairs",
        lambda payload, site_id: {
            "proposals": [
                {
                    "scope": "route",
                    "item": "projects",
                    "confidence": 0.95,
                    "patch": {"routes": {"projects": "https://external.example.com/projects"}},
                }
            ]
        },
    )

    proposals = build_flow_repair_proposals(
        vertical_key="construction",
        vertical_config={
            "regression": {
                "changes": [
                    {
                        "kind": "route_removed",
                        "item": "projects",
                        "severity": "high",
                        "previous": "/projects",
                        "current": "",
                    }
                ],
            }
        },
    )

    assert all(proposal["source"] != "llm_flow_repair" for proposal in proposals)


def test_scanner_regression_capability_flags_high_severity_drift() -> None:
    caps = {
        cap.name: cap
        for cap in _regression_capabilities(
            {
                "regression": {
                    "status": "changed",
                    "summary": {"changes": 3, "high": 1, "medium": 1},
                }
            }
        )
    }

    assert not caps["flow_regression"].supported
    assert "1 high" in caps["flow_regression"].evidence


def test_crm_regression_endpoint_returns_saved_report(monkeypatch) -> None:
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "vertical_config": {
                "regression": {
                    "site_id": site_id,
                    "site_url": "https://builder.example.com",
                    "status": "stable",
                    "summary": {"changes": 0, "high": 0},
                    "changes": [],
                    "compared_at": "now",
                }
            },
        },
    )

    res = TestClient(app).get(
        "/v1/admin/clients/builder_demo/flows/regression",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["regression"]["status"] == "stable"
