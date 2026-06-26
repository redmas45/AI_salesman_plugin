import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from agent.verticals.registry import DEFAULT_VERTICAL_KEY, get_vertical, list_verticals
from api import crm
from api.main import app


def test_vertical_registry_lists_core_domains():
    verticals = {vertical.key: vertical for vertical in list_verticals()}

    assert DEFAULT_VERTICAL_KEY == "ecommerce"
    assert verticals["ecommerce"].label == "E-commerce"
    assert verticals["insurance"].risk_level == "high"
    assert verticals["travel"].entity_label_plural == "travel items"
    assert verticals["generic"].default_plan_label == "Generic AI plan"


def test_vertical_registry_rejects_unknown_key():
    try:
        get_vertical("unknown-domain")
    except ValueError as exc:
        assert "Unsupported vertical" in str(exc)
    else:
        raise AssertionError("unknown vertical should be rejected")


def test_crm_verticals_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    res = TestClient(app).get(
        "/v1/admin/verticals",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["default_vertical_key"] == "ecommerce"
    assert any(vertical["key"] == "insurance" for vertical in body["verticals"])


def test_crm_create_client_passes_vertical_key(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_create_client(**kwargs):
        captured.update(kwargs)
        return {
            "site_id": kwargs["site_id"] or "demo_insurance",
            "name": kwargs["name"],
            "store_url": kwargs["store_url"],
            "vertical_key": kwargs["vertical_key"],
            "vertical_label": "Insurance",
            "risk_level": "high",
        }

    monkeypatch.setattr(crm.admin_db, "create_client", fake_create_client)

    res = TestClient(app).post(
        "/v1/admin/clients",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={
            "name": "Demo Insurance",
            "store_url": "https://example.com",
            "site_id": "demo_insurance",
            "deploy_mode": "public-ip",
            "plan": "Insurance plan",
            "adapter_name": "generic_adapter.js",
            "vertical_key": "insurance",
        },
    )

    assert res.status_code == 201
    assert captured["vertical_key"] == "insurance"
    assert res.json()["client"]["vertical_key"] == "insurance"


def test_crm_updates_client_vertical(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_update_client_vertical(site_id: str, vertical_key: str):
        captured.update({"site_id": site_id, "vertical_key": vertical_key})
        return {
            "site_id": site_id,
            "vertical_key": vertical_key,
            "vertical_label": "Travel",
            "risk_level": "medium",
        }

    monkeypatch.setattr(crm.admin_db, "update_client_vertical", fake_update_client_vertical)

    res = TestClient(app).patch(
        "/v1/admin/clients/demo/vertical",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"vertical_key": "travel"},
    )

    assert res.status_code == 200
    assert captured == {"site_id": "demo", "vertical_key": "travel"}
    assert res.json()["client"]["vertical_label"] == "Travel"
