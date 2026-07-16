import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from agent.verticals.registry import DEFAULT_VERTICAL_KEY, get_vertical, list_verticals
from api import crm
from api.main import app, _allowed_cors_origins
from db import clients as client_db
from db.clients import _default_client_adapter_name, _default_client_vertical_key
from db.seed import DEFAULT_SEED_SITE_IDS


def test_remove_client_marks_deleted_not_available(monkeypatch):
    updates = []

    monkeypatch.setattr(client_db, "_update_client_status", lambda site_id, status: updates.append((site_id, status)))

    client_db.remove_client("old_auto_install")

    assert updates == [("old_auto_install", client_db.CLIENT_STATUS_DELETED)]


def test_crm_remove_client_uses_delete_semantics(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    removed = []

    monkeypatch.setattr(crm.admin_db, "remove_client", lambda site_id: removed.append(site_id))

    res = TestClient(app).delete(
        "/v1/admin/clients/old_auto_install",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert removed == ["old_auto_install"]


def test_crm_move_client_to_available_has_separate_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    moved = []

    def fake_move(site_id: str):
        moved.append(site_id)
        return {"site_id": site_id, "status": client_db.CLIENT_STATUS_AVAILABLE}

    monkeypatch.setattr(crm.admin_db, "move_client_to_available", fake_move)

    res = TestClient(app).post(
        "/v1/admin/clients/current_site/available",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == client_db.CLIENT_STATUS_AVAILABLE
    assert res.json()["client"]["status"] == client_db.CLIENT_STATUS_AVAILABLE
    assert moved == ["current_site"]


def test_crm_crawl_rejects_available_client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://policy.example.com",
            "status": client_db.CLIENT_STATUS_AVAILABLE,
        },
    )
    monkeypatch.setattr(
        crm.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not crawl")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/demo_policy/crawl",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 409
    assert "Move this client to Current" in res.json()["detail"]


def test_crm_auto_integration_rejects_available_client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://policy.example.com",
            "status": client_db.CLIENT_STATUS_AVAILABLE,
        },
    )
    monkeypatch.setattr(
        crm.admin_db,
        "activate_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not auto-activate")),
    )
    monkeypatch.setattr(
        crm.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not auto-integrate")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/demo_policy/auto-integrate",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 409
    assert "Move this client to Current" in res.json()["detail"]


def test_crm_auto_integration_queues_assistant_smoke_tests(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://shop.example.com",
            "status": client_db.CLIENT_STATUS_LIVE,
            "vertical_key": "ecommerce",
        },
    )
    monkeypatch.setattr(crm.admin_db, "update_client_crawl_status", lambda *args, **kwargs: None)

    def fake_run_widget_initialization(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(crm, "run_widget_initialization", fake_run_widget_initialization)

    res = TestClient(app).post(
        "/v1/admin/clients/ai_kart/auto-integrate",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "queued"
    assert "assistant smoke tests" in res.json()["message"]
    assert captured["args"][0] == "ai_kart"
    assert captured["kwargs"]["run_smoke_tests"] is True


def test_crm_assistant_smoke_tests_runs_without_crawl(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://shop.example.com",
            "status": client_db.CLIENT_STATUS_LIVE,
            "vertical_key": "ecommerce",
        },
    )
    monkeypatch.setattr(
        crm,
        "run_assistant_smoke_tests",
        lambda site_id, vertical_key: {
            "source": "crm_assistant_smoke_tests",
            "status": "ok",
            "site_id": site_id,
            "vertical_key": vertical_key,
            "message": "2/2 assistant smoke tests passed.",
            "tests": [],
        },
    )

    def fake_save(site_id: str, report: dict[str, object]):
        saved.update({"site_id": site_id, "report": report})
        return {"site_id": site_id, "vertical_config": {"assistant_smoke_tests": report}}

    monkeypatch.setattr(crm.admin_db, "save_client_assistant_smoke_report", fake_save)
    monkeypatch.setattr(
        crm.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("smoke tests must not crawl")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/ai_kart/assistant-smoke-tests",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert saved["site_id"] == "ai_kart"
    assert saved["report"]["source"] == "crm_assistant_smoke_tests"


def test_crm_assistant_smoke_tests_rejects_available_client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://shop.example.com",
            "status": client_db.CLIENT_STATUS_AVAILABLE,
            "vertical_key": "ecommerce",
        },
    )
    monkeypatch.setattr(
        crm,
        "run_assistant_smoke_tests",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not run smoke tests")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/ai_kart/assistant-smoke-tests",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 409
    assert "Move this client to Current" in res.json()["detail"]


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

