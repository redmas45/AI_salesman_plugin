import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from agent.flow_rehearsal import build_rehearsal_report_from_flow
from agent.scanner import _rehearsal_capabilities
from api import crm
from api.main import app


def test_static_rehearsal_marks_routes_selectors_and_confirmation_policy() -> None:
    report = build_rehearsal_report_from_flow(
        {
            "site_id": "builder_demo",
            "site_url": "https://builder.example.com",
            "actions": [
                {
                    "action_name": "REQUEST_ESTIMATE",
                    "action_type": "form",
                    "page_url": "https://builder.example.com/contact",
                    "input": "input[name='phone']",
                }
            ],
            "adapter_actions": {
                "OPEN_PROJECTS": {"type": "navigate", "path": "/projects"},
                "REQUEST_ESTIMATE": {
                    "type": "form",
                    "form": "form.estimate",
                    "input": "input[name='phone']",
                    "submit": "button.estimate",
                },
                "REQUEST_SITE_VISIT": {"type": "click", "selector": "button.visit"},
            },
        },
        site_id="builder_demo",
        site_url="https://builder.example.com",
    ).to_dict()

    assert report["summary"]["total"] == 3
    assert report["summary"]["supported"] == 3
    assert report["summary"]["needs_confirmation"] == 2
    by_name = {step["action_name"]: step for step in report["steps"]}
    assert by_name["OPEN_PROJECTS"]["status"] == "static_route_recorded"
    assert by_name["REQUEST_ESTIMATE"]["status"] == "static_prepare_only"
    assert by_name["REQUEST_ESTIMATE"]["requires_confirmation"] is True


def test_scanner_rehearsal_capabilities_reflect_saved_rehearsal() -> None:
    caps = {
        cap.name: cap
        for cap in _rehearsal_capabilities(
            {
                "rehearsal": {
                    "engine": "playwright",
                    "summary": {"total": 4, "supported": 3, "blocked": 1, "needs_confirmation": 2},
                }
            }
        )
    }

    assert caps["flow_rehearsal"].supported
    assert "3/4" in caps["flow_rehearsal"].evidence
    assert caps["flow_confirmation_policy"].supported
    assert "2 rehearsed action" in caps["flow_confirmation_policy"].evidence


def test_crm_flow_rehearsal_endpoint_persists_and_returns_runtime(monkeypatch) -> None:
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    saved = {}

    class FakeRehearsal:
        def to_dict(self):
            return {
                "site_id": "builder_demo",
                "site_url": "https://builder.example.com",
                "engine": "test",
                "steps": [],
                "summary": {"total": 1, "supported": 1, "blocked": 0, "needs_confirmation": 1},
                "rehearsed_at": "now",
                "duration_ms": 1,
            }

    async def fake_rehearse_site_flows(*args, **kwargs):
        return FakeRehearsal()

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://builder.example.com",
            "vertical_key": "construction",
            "vertical_config": {
                "flow": {
                    "site_id": site_id,
                    "site_url": "https://builder.example.com",
                    "summary": {"pages": 1, "actions": 1},
                    "adapter_actions": {"REQUEST_ESTIMATE": {"type": "form", "input": "input[name='phone']"}},
                }
            },
        },
    )
    monkeypatch.setattr(
        crm.admin_db,
        "save_client_rehearsal_report",
        lambda site_id, report: saved.update({site_id: report}),
    )
    monkeypatch.setattr(crm.admin_db, "save_client_regression_report", lambda site_id, report: None)
    monkeypatch.setattr("agent.flow_rehearsal.rehearse_site_flows", fake_rehearse_site_flows)
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {
            "site_id": site,
            "enabled": True,
            "vertical": {},
            "adapter": {"rehearsal": saved[site]},
        },
    )
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")
    monkeypatch.setattr(crm, "render_adapter_code", lambda runtime_config: "// adapter")

    res = TestClient(app).post(
        "/v1/admin/clients/builder_demo/flows/rehearse",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"max_steps": 3},
    )

    assert res.status_code == 200
    assert saved["builder_demo"]["summary"]["supported"] == 1
    assert res.json()["runtime_config"]["adapter"]["rehearsal"]["engine"] == "test"
