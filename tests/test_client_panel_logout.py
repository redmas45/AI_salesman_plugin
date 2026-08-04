"""Client-panel logout must end the session on the server, not just locally.

Before this change, "Log out" only removed the token from browser storage. The
token itself stayed valid until it expired, so anyone who had captured it (shared
machine, copied header, browser history) kept full access to the panel after the
owner believed they had signed out.

Revocation is per session: signing out on a laptop must not sign the same owner
out on their phone, and must never affect a different client.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import config  # noqa: E402
from api.client_panels import panel_routes  # noqa: E402

SECURE_SECRET = "unit-test-client-panel-secret-value"


@pytest.fixture
def signing(monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PANEL_TOKEN_SECRET", SECURE_SECRET)


@pytest.fixture
def revocations(monkeypatch):
    """In-memory stand-in for the revocation store (the store itself is DB-backed)."""
    revoked: set[tuple[str, str]] = set()
    monkeypatch.setattr(
        panel_routes,
        "panel_session_is_revoked",
        lambda site_id, session_id: (site_id, session_id) in revoked,
    )
    monkeypatch.setattr(
        panel_routes,
        "revoke_panel_session",
        lambda site_id, session_id, expires_at=None: revoked.add((site_id, session_id)),
    )
    return revoked


def _client(site_id: str = "unit_site") -> dict:
    return {
        "site_id": site_id,
        "name": "Unit Site",
        "panel_password_configured": True,
        "panel_auth_version": "version-one",
    }


@pytest.fixture
def lookup(monkeypatch):
    monkeypatch.setattr(
        panel_routes.admin_db,
        "get_client_detail",
        lambda site_id: _client(site_id),
    )


def test_token_carries_a_per_login_session_id(signing):
    token = panel_routes._encode_token(_client())
    payload = panel_routes._token_payload(token)
    assert payload["sid"]


def test_two_logins_get_different_session_ids(signing):
    first = panel_routes._token_payload(panel_routes._encode_token(_client()))
    second = panel_routes._token_payload(panel_routes._encode_token(_client()))
    assert first["sid"] != second["sid"]


def test_token_is_valid_before_logout(signing, lookup, revocations):
    token = panel_routes._encode_token(_client())
    assert panel_routes._decode_token(token) is not None


def test_token_is_rejected_after_its_session_is_revoked(signing, lookup, revocations):
    token = panel_routes._encode_token(_client())
    payload = panel_routes._token_payload(token)
    panel_routes.revoke_panel_session("unit_site", payload["sid"])
    assert panel_routes._decode_token(token) is None, "a revoked session must not authenticate"


def test_logout_endpoint_revokes_the_calling_session(signing, lookup, revocations):
    token = panel_routes._encode_token(_client())

    result = asyncio.run(panel_routes.client_panel_logout(f"Bearer {token}"))

    assert result == {"status": "signed_out"}
    assert panel_routes._decode_token(token) is None


def test_revoking_one_session_leaves_other_sessions_working(signing, lookup, revocations):
    laptop = panel_routes._encode_token(_client())
    phone = panel_routes._encode_token(_client())
    panel_routes.revoke_panel_session("unit_site", panel_routes._token_payload(laptop)["sid"])
    assert panel_routes._decode_token(laptop) is None
    assert panel_routes._decode_token(phone) is not None


def test_revoking_one_client_does_not_affect_another(signing, lookup, revocations):
    mine = panel_routes._encode_token(_client("site_a"))
    theirs = panel_routes._encode_token(_client("site_b"))
    panel_routes.revoke_panel_session("site_a", panel_routes._token_payload(mine)["sid"])
    assert panel_routes._decode_token(mine) is None
    assert panel_routes._decode_token(theirs) is not None


def test_a_revocation_store_failure_fails_closed(signing, lookup, monkeypatch):
    """If revocation state cannot be read, deny rather than assume "not revoked"."""

    def unavailable(site_id, session_id):
        raise RuntimeError("revocation store unavailable")

    monkeypatch.setattr(panel_routes, "panel_session_is_revoked", unavailable)
    token = panel_routes._encode_token(_client())
    assert panel_routes._decode_token(token) is None


def test_legacy_token_without_a_session_id_is_rejected(signing, lookup, revocations):
    """Pre-upgrade tokens cannot be revoked, so they must not be honoured."""
    legacy = panel_routes._encode_legacy_token_for_test(_client())
    assert panel_routes._decode_token(legacy) is None


def test_client_panel_calls_the_versioned_logout_route():
    """The UI must call the same prefixed route exposed by FastAPI."""
    api_source = (
        Path(__file__).parent.parent / "client-panel" / "src" / "api.ts"
    ).read_text(encoding="utf-8")
    assert "'/v1/client-panel/logout'" in api_source
    assert "request<{ status: string }>('/logout'" not in api_source
