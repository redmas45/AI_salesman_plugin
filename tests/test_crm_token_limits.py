import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from api import client_panel
from api import crm
from api.main import app
from db import clients as client_db

INTERNAL_CLIENT_PANEL_FIELDS = {
    "readiness_report",
    "vertical_config",
    "script_tag",
    "adapter_name",
    "catalog_preview",
    "sync_runs",
    "prompt_profile_id",
}


def test_crm_updates_client_token_limits(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_update(site_id: str, token_limit: int, session_token_limit: int):
        captured.update(
            {
                "site_id": site_id,
                "token_limit": token_limit,
                "session_token_limit": session_token_limit,
            }
        )
        return {
            "site_id": site_id,
            "token_limit": token_limit,
            "session_token_limit": session_token_limit,
        }

    monkeypatch.setattr(crm.admin_db, "update_client_token_limits", fake_update)

    res = TestClient(app).patch(
        "/v1/admin/clients/ai_kart/token-limits",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"token_limit": 10000, "session_token_limit": 750},
    )

    assert res.status_code == 200
    assert captured == {
        "site_id": "ai_kart",
        "token_limit": 10000,
        "session_token_limit": 750,
    }
    assert res.json()["client"]["token_limit"] == 10000


def test_crm_rejects_session_limit_above_client_limit(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    res = TestClient(app).patch(
        "/v1/admin/clients/ai_kart/token-limits",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"token_limit": 5000, "session_token_limit": 5001},
    )

    assert res.status_code == 400
    assert "Session token limit" in res.json()["detail"]


def test_crm_auto_generates_client_panel_password(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_generate():
        return "generated-password-strong"

    def fake_update(site_id: str, password: str):
        captured.update({"site_id": site_id, "password": password})
        return {
            "site_id": site_id,
            "panel_password_configured": True,
            "panel_password_status": "configured",
        }

    monkeypatch.setattr(crm.admin_db, "generate_client_panel_password", fake_generate)
    monkeypatch.setattr(crm.admin_db, "update_client_panel_password", fake_update)

    res = TestClient(app).patch(
        "/v1/admin/clients/ai_kart/panel-password",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"auto_generate": True},
    )

    assert res.status_code == 200
    assert captured == {"site_id": "ai_kart", "password": "generated-password-strong"}
    assert res.json()["generated_password"] == "generated-password-strong"
    assert res.json()["client"]["panel_password_status"] == "configured"


def test_crm_sets_manual_client_panel_password(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_update(site_id: str, password: str):
        captured.update({"site_id": site_id, "password": password})
        return {"site_id": site_id, "panel_password_status": "configured"}

    monkeypatch.setattr(crm.admin_db, "update_client_panel_password", fake_update)

    res = TestClient(app).patch(
        "/v1/admin/clients/ai_kart/panel-password",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"password": "manual-password-strong"},
    )

    assert res.status_code == 200
    assert captured == {"site_id": "ai_kart", "password": "manual-password-strong"}
    assert res.json()["generated_password"] == ""


def test_crm_rejects_short_client_panel_password(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    res = TestClient(app).patch(
        "/v1/admin/clients/ai_kart/panel-password",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"password": "short"},
    )

    assert res.status_code == 422


def test_client_panel_login_rejects_short_password():
    res = TestClient(app).post(
        "/v1/client-panel/login",
        json={"site_id": "ai_kart", "password": "admin123"},
    )

    assert res.status_code == 422


def test_client_panel_dashboard_exposes_integration_summary(monkeypatch):
    monkeypatch.setattr(client_panel.config, "CLIENT_PANEL_TOKEN_SECRET", "test-client-panel-secret")
    readiness_report = {
        "capabilities": [
            {
                "name": "domain_action_coverage",
                "supported": True,
                "confidence": 0.9,
                "evidence": "6/6 expected E-commerce action(s) are covered. Missing: none.",
            },
            {
                "name": "expected_action:SHOW_PRODUCTS",
                "supported": True,
                "confidence": 0.8,
                "evidence": "SHOW_PRODUCTS can use AI Hub product rendering with 25 active products.",
            },
            {
                "name": "flow_graph",
                "supported": False,
                "confidence": 0.35,
                "evidence": "Discovery mapped 6 page(s) and 0 action candidate(s).",
            },
            {
                "name": "variants",
                "supported": False,
                "confidence": 0.4,
                "evidence": "No variant data detected in product API responses.",
            },
        ]
    }
    client = {
        "site_id": "ai_kart",
        "name": "AI Kart",
        "store_url": "https://shop.example",
        "status": "live",
        "plan": "Commerce plan",
        "session_token_limit": 1000,
        "usage": {},
        "quota": {},
        "panel_password_configured": True,
        "script_tag": "<script>internal</script>",
        "adapter_name": "generated_adapter.js",
        "prompt_profile_id": "prompt_internal",
        "catalog_preview": [{"id": "hidden"}],
        "sync_runs": [{"id": "hidden"}],
        "catalog": {"active_products": 25, "missing_embeddings": 0},
        "readiness_report": json.dumps(readiness_report),
        "vertical_config": {
            "assistant_smoke_tests": {
                "status": "ok",
                "passed": 2,
                "failed": 0,
                "total": 2,
                "message": "2/2 assistant smoke tests passed.",
            },
            "action_health": {"summary": {"needs_repair": 0}},
        },
    }

    monkeypatch.setattr(client_panel.admin_db, "verify_client_panel_password", lambda site_id, password: client)
    monkeypatch.setattr(client_panel.admin_db, "get_client_detail", lambda site_id: client)
    monkeypatch.setattr(client_panel.admin_db, "analytics_snapshot", lambda range, site_id: {"metrics": {}, "summary": "", "top_products": [], "top_intents": [], "series": []})
    monkeypatch.setattr(client_panel.admin_db, "conversation_log", lambda range, site_id: {"groups": []})

    api = TestClient(app)
    login = api.post("/v1/client-panel/login", json={"site_id": "ai_kart", "password": "admin12345678"})
    assert INTERNAL_CLIENT_PANEL_FIELDS.isdisjoint(login.json()["client"])
    auth = {"Authorization": f"Bearer {login.json()['token']}"}
    me = api.get("/v1/client-panel/me", headers=auth)
    assert me.status_code == 200
    assert INTERNAL_CLIENT_PANEL_FIELDS.isdisjoint(me.json()["client"])
    res = api.get("/v1/client-panel/dashboard", headers={"Authorization": f"Bearer {login.json()['token']}"})

    assert res.status_code == 200
    assert INTERNAL_CLIENT_PANEL_FIELDS.isdisjoint(res.json()["client"])
    assert res.json()["client"]["site_id"] == "ai_kart"
    integration = res.json()["integration"]
    assert integration["score"] >= 80
    assert integration["score"] < 100
    assert integration["domain_actions"]["covered"] == 1
    assert integration["domain_actions"]["evidence"].startswith("6/6 expected")
    assert integration["prompt_tests"]["passed"] == 2
    assert integration["readiness"]["needs_work"] == 1
    assert integration["readiness"]["unsupported"][0]["name"] == "flow_graph"
    assert integration["readiness"]["informational"][0]["name"] == "variants"
    assert "flow_graph" in integration["next_action"]

    monkeypatch.setattr(client_panel.admin_db, "update_client_session_token_limit", lambda site_id, limit: {**client, "session_token_limit": limit})
    updated = api.patch("/v1/client-panel/token-policy", headers=auth, json={"session_token_limit": 750})
    assert updated.status_code == 200
    assert updated.json()["client"]["session_token_limit"] == 750
    assert INTERNAL_CLIENT_PANEL_FIELDS.isdisjoint(updated.json()["client"])


def test_crm_revokes_client_panel_password(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_revoke(site_id: str):
        captured["site_id"] = site_id
        return {
            "site_id": site_id,
            "panel_password_configured": False,
            "panel_password_status": "revoked",
        }

    monkeypatch.setattr(crm.admin_db, "revoke_client_panel_password", fake_revoke)

    res = TestClient(app).delete(
        "/v1/admin/clients/ai_kart/panel-password",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert captured == {"site_id": "ai_kart"}
    assert res.json()["client"]["panel_password_status"] == "revoked"


def test_crm_operation_status_projects_backend_evidence(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    client = {
        "site_id": "ai_kart",
        "status": "live",
        "last_crawl_status": client_db.CRAWL_STATUS_OK,
        "last_crawl_message": "Crawler completed.",
        "last_crawl_at": "2026-06-28T12:00:00+00:00",
        "vertical_config": {
            "initialization": {
                "status": "ok",
                "started_at": "2026-06-28T11:58:00+00:00",
                "completed_at": "2026-06-28T12:01:00+00:00",
                "duration_ms": 180000,
                "stages": [
                    {"name": "crawl", "status": "ok", "message": "Content crawl completed."},
                    {"name": "flow_discovery", "status": "ok", "message": "Flow discovery completed."},
                    {"name": "readiness_scan", "status": "ok", "message": "Readiness scan completed."},
                ],
            }
        },
    }
    readiness_report = {
        "scanned_at": "2026-06-28T12:02:00+00:00",
        "capabilities": [
            {"name": "catalog", "supported": True},
            {"name": "checkout", "supported": False},
        ],
    }
    crawl_report = {
        "created_at": "2026-06-28T12:00:30+00:00",
        "duration_ms": 30000,
        "pages_visited": 7,
        "product_count": 42,
    }

    monkeypatch.setattr(crm.admin_db, "get_client_detail", lambda site_id: client)
    monkeypatch.setattr(crm.admin_db, "get_readiness_report", lambda site_id: readiness_report)
    monkeypatch.setattr(crm.admin_db, "get_latest_crawl_report", lambda site_id: crawl_report)

    res = TestClient(app).get(
        "/v1/admin/clients/ai_kart/operation-status",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    operations = res.json()["operations"]
    assert operations["crawl"]["status"] == "complete"
    assert operations["crawl"]["stages"][2]["message"] == "7 pages visited."
    assert operations["readiness"]["status"] == "complete"
    assert operations["readiness"]["message"] == "1/2 readiness checks supported."
    assert operations["integration"]["status"] == "complete"
    assert operations["integration"]["stages"][1]["label"] == "Discovering routes and actions"


def test_crm_operation_status_marks_crawl_running(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    client = {
        "site_id": "ai_kart",
        "status": "live",
        "last_crawl_status": client_db.CRAWL_STATUS_RUNNING,
        "last_crawl_message": "Crawler queued.",
        "last_crawl_at": "2026-06-28T12:00:00+00:00",
        "vertical_config": {},
    }

    monkeypatch.setattr(crm.admin_db, "get_client_detail", lambda site_id: client)
    monkeypatch.setattr(crm.admin_db, "get_readiness_report", lambda site_id: None)
    monkeypatch.setattr(crm.admin_db, "get_latest_crawl_report", lambda site_id: None)

    res = TestClient(app).get(
        "/v1/admin/clients/ai_kart/operation-status",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    operations = res.json()["operations"]
    assert operations["crawl"]["status"] == "running"
    assert operations["crawl"]["stages"][1]["status"] == "running"
    assert operations["integration"]["status"] == "pending"


def test_short_default_client_panel_password_is_not_auto_configured(monkeypatch):
    monkeypatch.setattr(client_db, "DEFAULT_CLIENT_PANEL_PASSWORD", "admin123")

    assert client_db._default_panel_password_hash() == ""


def test_missing_default_client_panel_password_is_not_auto_configured(monkeypatch):
    monkeypatch.setattr(client_db, "DEFAULT_CLIENT_PANEL_PASSWORD", "")

    assert client_db._default_panel_password_hash() == ""


def test_strong_default_client_panel_password_hashes_for_local_testing(monkeypatch):
    monkeypatch.setattr(client_db, "DEFAULT_CLIENT_PANEL_PASSWORD", "admin12345678")

    password_hash = client_db._default_panel_password_hash()

    assert password_hash
    assert client_db._verify_panel_password("admin12345678", password_hash)


def test_crm_admin_api_fails_closed_without_configured_token(monkeypatch):
    monkeypatch.delenv("CRM_ADMIN_TOKEN", raising=False)

    res = TestClient(app).get("/v1/admin/overview")

    assert res.status_code == 503
    assert "not configured" in res.json()["detail"]


def test_crm_admin_api_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    res = TestClient(app).get(
        "/v1/admin/overview",
        headers={"x-crm-admin-token": "wrong-token"},
    )

    assert res.status_code == 401
