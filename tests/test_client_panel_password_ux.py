"""Regression tests for client-panel password handling and login diagnostics.

Reproduced defects:
  * A correct password could still fail sign-in with 503 because the token secret
    was missing/short, and the panel reported it like a credential problem.
  * The CRM dialog persisted a generated password immediately and then labelled a
    locally held value "Current password", although only a hash is stored.

These tests pin the security invariants: the minimum secret length is never
relaxed, no default/fallback secret exists, rotation and revocation invalidate
tokens, and no secret value is ever returned by the readiness surface.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import config  # noqa: E402
from api.client_panels import panel_routes  # noqa: E402

SECURE_SECRET = "unit-test-client-panel-secret-value"


@pytest.fixture
def restore_secret():
    original = config.CLIENT_PANEL_TOKEN_SECRET
    yield
    config.CLIENT_PANEL_TOKEN_SECRET = original


# --- Token signing: correct password must still fail loudly, not silently ---


def test_missing_token_secret_reports_not_ready(restore_secret):
    config.CLIENT_PANEL_TOKEN_SECRET = ""
    status = panel_routes.token_signing_status()
    assert status["ready"] is False
    assert status["configured"] is False
    assert "administrator" in status["message"].lower()


def test_short_token_secret_reports_not_ready(restore_secret):
    config.CLIENT_PANEL_TOKEN_SECRET = "tooshort"
    status = panel_routes.token_signing_status()
    assert status["ready"] is False
    assert status["configured"] is True
    assert str(panel_routes.MIN_TOKEN_SECRET_LENGTH) in status["message"]


def test_secure_token_secret_reports_ready(restore_secret):
    config.CLIENT_PANEL_TOKEN_SECRET = SECURE_SECRET
    assert panel_routes.token_signing_status()["ready"] is True


def test_readiness_never_exposes_the_secret(restore_secret):
    config.CLIENT_PANEL_TOKEN_SECRET = SECURE_SECRET
    serialized = repr(panel_routes.token_signing_status())
    assert SECURE_SECRET not in serialized
    # The exact length is also withheld so the value cannot be narrowed down.
    assert str(len(SECURE_SECRET)) not in serialized


def test_minimum_secret_length_is_not_weakened():
    assert panel_routes.MIN_TOKEN_SECRET_LENGTH >= 16


def test_no_default_or_fallback_signing_secret(restore_secret):
    """An unset secret must fail closed, never fall back to a built-in value."""
    config.CLIENT_PANEL_TOKEN_SECRET = ""
    with pytest.raises(Exception) as excinfo:
        panel_routes._sign("payload")
    assert getattr(excinfo.value, "status_code", None) == 503


def test_signing_succeeds_with_a_secure_secret(restore_secret):
    config.CLIENT_PANEL_TOKEN_SECRET = SECURE_SECRET
    assert panel_routes._sign("payload")


# --- Rotation and revocation invalidate previously issued tokens ---


def _client(auth_version: str, configured: bool = True) -> dict:
    return {
        "site_id": "unit_site",
        "name": "Unit Site",
        "panel_password_configured": configured,
        "panel_auth_version": auth_version,
    }


def test_token_is_invalid_after_password_rotation(restore_secret, monkeypatch):
    config.CLIENT_PANEL_TOKEN_SECRET = SECURE_SECRET
    token = panel_routes._encode_token(_client("version-one"))
    monkeypatch.setattr(panel_routes.admin_db, "get_client_detail", lambda site_id: _client("version-one"))
    assert panel_routes._decode_token(token) is not None
    monkeypatch.setattr(panel_routes.admin_db, "get_client_detail", lambda site_id: _client("version-two"))
    assert panel_routes._decode_token(token) is None


def test_token_is_invalid_after_password_revocation(restore_secret, monkeypatch):
    config.CLIENT_PANEL_TOKEN_SECRET = SECURE_SECRET
    token = panel_routes._encode_token(_client("version-one"))
    monkeypatch.setattr(
        panel_routes.admin_db,
        "get_client_detail",
        lambda site_id: _client("", configured=False),
    )
    assert panel_routes._decode_token(token) is None


# --- CRM generation is local-only: the generator never persists anything ---


def test_generated_password_meets_the_stored_minimum_length():
    """The CRM generator length must satisfy the server-side minimum."""
    from db.client_domain.panel.client_passwords import MIN_CLIENT_PANEL_PASSWORD_LENGTH

    generator = (Path(__file__).parent.parent / "crm" / "src" / "utils" / "password.ts").read_text(encoding="utf-8")
    assert "crypto.getRandomValues" in generator
    assert "GENERATED_PASSWORD_LENGTH = 20" in generator
    assert 20 >= MIN_CLIENT_PANEL_PASSWORD_LENGTH


def test_crm_dialog_generates_without_calling_the_update_api():
    """"Generate password" must fill the field only - no persistence call."""
    dialog = (
        Path(__file__).parent.parent / "crm" / "src" / "components" / "shared" / "dialogs" / "Dialogs.tsx"
    ).read_text(encoding="utf-8")
    generate_body = dialog.split("function generatePassword()", 1)[1].split("}", 1)[0]
    assert "onUpdatePassword" not in generate_body
    assert "generateSecurePassword()" in generate_body
    # The CRM no longer asks the server to auto-generate.
    assert "onUpdatePassword(activeClient.site_id, '', true)" not in dialog


def test_crm_dialog_labels_the_value_shown_once_and_saves_explicitly():
    dialog = (
        Path(__file__).parent.parent / "crm" / "src" / "components" / "shared" / "dialogs" / "Dialogs.tsx"
    ).read_text(encoding="utf-8")
    assert "Saved password (shown once)" in dialog
    assert "Save password" in dialog
    assert "Generate password" in dialog
    # The misleading label is gone.
    assert "Current password is visible below" not in dialog
    assert "Generate and set" not in dialog


def test_client_panel_ui_separates_credentials_from_service_failure():
    api_source = (Path(__file__).parent.parent / "client-panel" / "src" / "api.ts").read_text(encoding="utf-8")
    assert "response.status === 503" in api_source
    assert "response.status === 401" in api_source
    assert "password may be correct" in api_source
    assert "administrator" in api_source
