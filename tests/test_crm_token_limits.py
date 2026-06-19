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
