import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from api import crm
from api.main import app


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
