"""Client panel password workflows and hashing adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from db.client_domain.panel import client_panel_access
from db.client_domain.panel.client_passwords import (
    GENERATED_PANEL_PASSWORD_BYTES,
    MIN_CLIENT_PANEL_PASSWORD_LENGTH,
    PANEL_PASSWORD_DISABLED,
    PANEL_PASSWORD_ITERATIONS,
    PANEL_PASSWORD_SALT_BYTES,
    default_panel_password_hash,
    generate_panel_password,
    hash_panel_password,
    panel_password_configured,
    panel_password_status,
    verify_panel_password as password_hash_matches,
)


ConnectFactory = Callable[[], Any]


@dataclass(frozen=True)
class ClientPanelPasswordWorkflows:
    safe_site_id: Callable[[str], str]
    client_row: Callable[[str], dict[str, Any] | None]
    set_default_panel_password: Callable[[str], str]
    verify_panel_password: Callable[[str, str], bool]
    hash_panel_password: Callable[[str], str]
    get_client_detail: Callable[[str], dict[str, Any]]
    init_schema: Callable[[], None]
    connect: ConnectFactory
    record_audit_event_safely: Callable[..., None]
    deleted_status: str
    disabled_marker: str = PANEL_PASSWORD_DISABLED
    min_password_length: int = MIN_CLIENT_PANEL_PASSWORD_LENGTH


def verify_client_panel_password(
    site_id: str,
    password: str,
    workflows: ClientPanelPasswordWorkflows,
) -> dict[str, Any]:
    return client_panel_access.verify_client_panel_password(
        site_id,
        password,
        safe_site_id=workflows.safe_site_id,
        client_row=workflows.client_row,
        set_default_panel_password=workflows.set_default_panel_password,
        verify_panel_password=workflows.verify_panel_password,
        get_client_detail=workflows.get_client_detail,
        disabled_marker=workflows.disabled_marker,
    )


def generate_client_panel_password() -> str:
    return generate_panel_password(GENERATED_PANEL_PASSWORD_BYTES)


def update_client_panel_password(
    site_id: str,
    password: str,
    workflows: ClientPanelPasswordWorkflows,
) -> dict[str, Any]:
    return client_panel_access.update_client_panel_password(
        site_id,
        password,
        safe_site_id=workflows.safe_site_id,
        min_password_length=workflows.min_password_length,
        hash_panel_password=workflows.hash_panel_password,
        init_schema=workflows.init_schema,
        connect=workflows.connect,
        deleted_status=workflows.deleted_status,
        record_audit_event_safely=workflows.record_audit_event_safely,
        get_client_detail=workflows.get_client_detail,
    )


def revoke_client_panel_password(site_id: str, workflows: ClientPanelPasswordWorkflows) -> dict[str, Any]:
    return client_panel_access.revoke_client_panel_password(
        site_id,
        safe_site_id=workflows.safe_site_id,
        init_schema=workflows.init_schema,
        connect=workflows.connect,
        disabled_marker=workflows.disabled_marker,
        deleted_status=workflows.deleted_status,
        get_client_detail=workflows.get_client_detail,
    )


def set_default_panel_password(
    site_id: str,
    *,
    default_password: str,
    safe_site_id: Callable[[str], str],
    connect: ConnectFactory,
    default_panel_password_hash: Callable[[], str],
) -> str:
    return client_panel_access.set_default_panel_password(
        site_id,
        default_password=default_password,
        min_password_length=MIN_CLIENT_PANEL_PASSWORD_LENGTH,
        default_panel_password_hash=default_panel_password_hash,
        safe_site_id=safe_site_id,
        connect=connect,
    )


def configured_default_panel_password_hash(default_password: str) -> str:
    return default_panel_password_hash(
        default_password,
        minimum_length=MIN_CLIENT_PANEL_PASSWORD_LENGTH,
        salt_bytes=PANEL_PASSWORD_SALT_BYTES,
        iterations=PANEL_PASSWORD_ITERATIONS,
    )


def configured_panel_password_hash(password: str) -> str:
    return hash_panel_password(
        password,
        salt_bytes=PANEL_PASSWORD_SALT_BYTES,
        iterations=PANEL_PASSWORD_ITERATIONS,
    )


def verify_panel_password(password: str, password_hash: str) -> bool:
    return password_hash_matches(password, password_hash)


def is_panel_password_configured(password_hash: str) -> bool:
    return panel_password_configured(password_hash, disabled_marker=PANEL_PASSWORD_DISABLED)


def configured_panel_password_status(password_hash: str) -> str:
    return panel_password_status(password_hash, disabled_marker=PANEL_PASSWORD_DISABLED)
