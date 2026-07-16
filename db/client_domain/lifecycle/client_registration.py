"""SQL builders for client registration rows."""

from __future__ import annotations

from agent.verticals.base import VerticalDefinition

CLIENT_UPSERT_COLUMNS: str = """
    (
        site_id, name, store_url, allowed_origin, deploy_mode, plan,
        adapter_name, status, panel_password_hash, vertical_key,
        vertical_config_json, risk_level, locale, prompt_profile_id,
        compliance_mode
    )
"""

DEFAULT_CLIENT_UPSERT_SQL = f"""
    INSERT INTO hub_clients
        {CLIENT_UPSERT_COLUMNS}
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (site_id) DO UPDATE SET
        store_url = EXCLUDED.store_url,
        allowed_origin = EXCLUDED.allowed_origin,
        deploy_mode = EXCLUDED.deploy_mode,
        panel_password_hash = COALESCE(NULLIF(hub_clients.panel_password_hash, ''), EXCLUDED.panel_password_hash),
        vertical_key = COALESCE(NULLIF(hub_clients.vertical_key, ''), EXCLUDED.vertical_key),
        vertical_config_json = COALESCE(NULLIF(hub_clients.vertical_config_json, ''), EXCLUDED.vertical_config_json),
        risk_level = COALESCE(NULLIF(hub_clients.risk_level, ''), EXCLUDED.risk_level),
        locale = COALESCE(NULLIF(hub_clients.locale, ''), EXCLUDED.locale),
        compliance_mode = COALESCE(NULLIF(hub_clients.compliance_mode, ''), EXCLUDED.compliance_mode),
        updated_at = now()
"""

ACTIVE_CLIENT_UPSERT_SQL = f"""
    INSERT INTO hub_clients
        {CLIENT_UPSERT_COLUMNS}
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (site_id) DO UPDATE SET
        name = EXCLUDED.name,
        store_url = EXCLUDED.store_url,
        allowed_origin = EXCLUDED.allowed_origin,
        deploy_mode = EXCLUDED.deploy_mode,
        plan = EXCLUDED.plan,
        adapter_name = EXCLUDED.adapter_name,
        vertical_key = EXCLUDED.vertical_key,
        risk_level = EXCLUDED.risk_level,
        locale = COALESCE(NULLIF(hub_clients.locale, ''), EXCLUDED.locale),
        compliance_mode = COALESCE(NULLIF(hub_clients.compliance_mode, ''), EXCLUDED.compliance_mode),
        status = EXCLUDED.status,
        panel_password_hash = COALESCE(NULLIF(hub_clients.panel_password_hash, ''), EXCLUDED.panel_password_hash),
        updated_at = now()
"""

AVAILABLE_CLIENT_UPSERT_SQL = f"""
    INSERT INTO hub_clients
        {CLIENT_UPSERT_COLUMNS}
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (site_id) DO UPDATE SET
        name = EXCLUDED.name,
        store_url = EXCLUDED.store_url,
        allowed_origin = EXCLUDED.allowed_origin,
        deploy_mode = EXCLUDED.deploy_mode,
        plan = EXCLUDED.plan,
        adapter_name = EXCLUDED.adapter_name,
        vertical_key = EXCLUDED.vertical_key,
        risk_level = EXCLUDED.risk_level,
        locale = COALESCE(NULLIF(hub_clients.locale, ''), EXCLUDED.locale),
        compliance_mode = COALESCE(NULLIF(hub_clients.compliance_mode, ''), EXCLUDED.compliance_mode),
        status = CASE
            WHEN hub_clients.status = %s THEN EXCLUDED.status
            WHEN hub_clients.status = %s THEN EXCLUDED.status
            ELSE hub_clients.status
        END,
        panel_password_hash = COALESCE(NULLIF(hub_clients.panel_password_hash, ''), EXCLUDED.panel_password_hash),
        updated_at = now()
"""


def client_upsert_params(
    *,
    site_id: str,
    name: str,
    store_url: str,
    allowed_origin: str,
    deploy_mode: str,
    plan: str,
    adapter_name: str,
    status: str,
    password_hash: str,
    vertical: VerticalDefinition,
    locale: str,
    compliance_mode: str,
) -> tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, str, str]:
    return (
        site_id,
        name,
        store_url,
        allowed_origin,
        deploy_mode,
        plan,
        adapter_name,
        status,
        password_hash,
        vertical.key,
        "{}",
        vertical.risk_level,
        locale,
        "",
        compliance_mode,
    )


def available_client_upsert_params(
    *,
    base_params: tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, str, str],
    deleted_status: str,
    available_status: str,
) -> tuple[str, ...]:
    return (*base_params, deleted_status, available_status)
