"""Security boundary tests for public runtime and operational routes."""

from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from starlette.requests import Request

import config
from api.client_panels import panel_routes
from api.main import app
from api.runtime import cors_policy, main_app, runtime_payloads, runtime_security
from api.runtime.ws_shop import WebSocketShopSession
from api.runtime.middleware import RateLimitMiddleware


def test_crawler_trigger_requires_admin_token(monkeypatch) -> None:
    monkeypatch.delenv("CRM_ADMIN_TOKEN", raising=False)

    response = TestClient(app).post("/v1/catalog/crawler/run")

    assert response.status_code == 503


def test_rate_limit_ignores_forwarded_ip_from_untrusted_peer(monkeypatch) -> None:
    monkeypatch.setattr(config, "TRUSTED_PROXY_IPS", set())
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/shop",
            "headers": [(b"x-forwarded-for", b"203.0.113.10")],
            "client": ("198.51.100.4", 1234),
        }
    )

    assert RateLimitMiddleware(app)._client_ip(request) == "198.51.100.4"


def test_rate_limit_accepts_forwarded_ip_from_trusted_peer(monkeypatch) -> None:
    monkeypatch.setattr(config, "TRUSTED_PROXY_IPS", {"10.0.0.2"})
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/shop",
            "headers": [(b"x-forwarded-for", b"203.0.113.10, 10.0.0.2")],
            "client": ("10.0.0.2", 1234),
        }
    )

    assert RateLimitMiddleware(app)._client_ip(request) == "203.0.113.10"


def test_widget_registration_uses_stricter_rate_limit_rule() -> None:
    rule = RateLimitMiddleware(app)._matching_rule("/v1/widget/register")

    assert rule == ("/v1/widget/register", 20, 60)


def test_client_panel_token_is_invalid_after_password_rotation(monkeypatch) -> None:
    monkeypatch.setattr(config, "CLIENT_PANEL_TOKEN_SECRET", "test-client-panel-secret")
    client = {
        "site_id": "policy_site",
        "panel_password_configured": True,
        "panel_auth_version": "version-one",
    }
    monkeypatch.setattr(panel_routes.admin_db, "get_client_detail", lambda site_id: dict(client))
    token = panel_routes._encode_token(client)

    assert panel_routes._decode_token(token) is not None

    client["panel_auth_version"] = "version-two"

    assert panel_routes._decode_token(token) is None


def test_client_panel_token_is_invalid_after_password_revocation(monkeypatch) -> None:
    monkeypatch.setattr(config, "CLIENT_PANEL_TOKEN_SECRET", "test-client-panel-secret")
    client = {
        "site_id": "policy_site",
        "panel_password_configured": True,
        "panel_auth_version": "version-one",
    }
    monkeypatch.setattr(panel_routes.admin_db, "get_client_detail", lambda site_id: dict(client))
    token = panel_routes._encode_token(client)
    client.update({"panel_password_configured": False, "panel_auth_version": ""})

    assert panel_routes._decode_token(token) is None


def test_runtime_origin_rejects_other_client_website(monkeypatch) -> None:
    monkeypatch.setattr(
        main_app.admin_db,
        "get_client_detail",
        lambda site_id: {"site_id": site_id, "allowed_origin": "https://client.example"},
    )

    assert runtime_security.runtime_origin_is_allowed(
        "client_site", "https://client.example", main_app.admin_db.get_client_detail
    ) is True
    assert runtime_security.runtime_origin_is_allowed(
        "client_site", "https://attacker.example", main_app.admin_db.get_client_detail
    ) is False


def test_origin_allowlist_normalizes_paths() -> None:
    client = {"allowed_origin": "https://client.example/store"}

    assert cors_policy.client_origin_is_allowed("https://client.example", client) is True
    assert cors_policy.client_origin_is_allowed("https://other.example", client) is False


@pytest.mark.asyncio
async def test_http_audio_upload_is_bounded(monkeypatch) -> None:
    monkeypatch.setattr(config, "MAX_AUDIO_UPLOAD_BYTES", 4)
    upload = UploadFile(filename="large.wav", file=BytesIO(b"12345"))

    with pytest.raises(HTTPException) as exc_info:
        await runtime_payloads.build_runtime_turn_payload(
            audio=upload,
            text=None,
            conversation_history=None,
        )

    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_websocket_audio_chunks_are_bounded(monkeypatch) -> None:
    monkeypatch.setattr(config, "MAX_AUDIO_UPLOAD_BYTES", 4)

    class FakeWebSocket:
        messages: list[dict] = []

        async def send_json(self, payload: dict) -> None:
            self.messages.append(payload)

    websocket = FakeWebSocket()
    session = WebSocketShopSession(websocket, "policy_site")

    assert await session.append_audio_chunk(b"1234") is True
    assert await session.append_audio_chunk(b"5") is False
    assert session.audio_chunks == []
    assert websocket.messages[-1]["message"] == "Audio payload is too large."
