"""Compatibility exports for client-panel password helper functions."""

from __future__ import annotations

from typing import Any


def exports(runtime: Any) -> dict[str, Any]:
    def set_default_panel_password(site_id: str) -> str:
        return runtime.client_panel_password_workflows.set_default_panel_password(
            site_id,
            default_password=runtime.DEFAULT_CLIENT_PANEL_PASSWORD,
            default_panel_password_hash=runtime._default_panel_password_hash,
            safe_site_id=runtime._safe_site_id,
            connect=runtime._connect,
        )

    def default_panel_password_hash() -> str:
        return runtime.client_panel_password_workflows.configured_default_panel_password_hash(
            runtime.DEFAULT_CLIENT_PANEL_PASSWORD
        )

    def hash_panel_password(password: str) -> str:
        return runtime.client_panel_password_workflows.configured_panel_password_hash(password)

    def verify_panel_password(password: str, password_hash: str) -> bool:
        return runtime.client_panel_password_workflows.verify_panel_password(password, password_hash)

    def panel_password_configured(password_hash: str) -> bool:
        return runtime.client_panel_password_workflows.is_panel_password_configured(password_hash)

    def panel_password_status(password_hash: str) -> str:
        return runtime.client_panel_password_workflows.configured_panel_password_status(password_hash)

    def b64(value: bytes) -> str:
        return runtime._password_b64(value)

    def unb64(value: str) -> bytes:
        return runtime._password_unb64(value)

    return {
        "_set_default_panel_password": set_default_panel_password,
        "_default_panel_password_hash": default_panel_password_hash,
        "_hash_panel_password": hash_panel_password,
        "_verify_panel_password": verify_panel_password,
        "_panel_password_configured": panel_password_configured,
        "_panel_password_status": panel_password_status,
        "_b64": b64,
        "_unb64": unb64,
    }
