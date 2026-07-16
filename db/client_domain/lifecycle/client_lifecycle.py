"""Client registration and lifecycle creation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


# The facade supplies infrastructure so lifecycle decisions stay testable without global state.
@dataclass(frozen=True)
class ClientLifecycleWorkflows:
    ensure_default_client_on_startup: bool
    current_site_id: str
    default_site_id: str
    current_url: str
    public_api_url: str
    deployment_mode: str
    default_deploy_mode: str
    default_locale: str
    default_compliance_mode: str
    live_status: str
    available_status: str
    deleted_status: str
    safe_site_id: Callable[[str], str]
    first_text: Callable[..., str]
    origin_from_url: Callable[[str], str]
    site_id_from_name: Callable[[str, str], str]
    validated_url: Callable[[str], str]
    required_text: Callable[[Any, str], str]
    validated_vertical: Callable[[str | None], Any]
    plan_for_vertical: Callable[[str, Any], str]
    default_client_vertical_key: Callable[[str], str]
    default_client_adapter_name: Callable[[str], str]
    default_client_name: Callable[[str], str]
    default_panel_password_hash: Callable[[], str]
    client_upsert_params: Callable[..., tuple[Any, ...]]
    available_client_upsert_params: Callable[..., tuple[Any, ...]]
    init_admin_schema: Callable[[], None]
    init_tenant_schema: Callable[[str], None]
    connect: Callable[[], Any]
    get_client_detail: Callable[[str], dict[str, Any]]
    active_client_upsert_sql: str
    available_client_upsert_sql: str
    default_client_upsert_sql: str


def ensure_default_client(deps: ClientLifecycleWorkflows) -> None:
    """Register the configured local client when the CRM starts."""
    deps.init_admin_schema()
    if not deps.ensure_default_client_on_startup:
        return

    site_id = deps.safe_site_id(deps.current_site_id or deps.default_site_id)
    store_url = deps.first_text(deps.current_url, deps.public_api_url, "http://localhost/")
    vertical = deps.validated_vertical(deps.default_client_vertical_key(site_id))
    deps.init_tenant_schema(site_id)
    with deps.connect() as conn:
        conn.execute(
            deps.default_client_upsert_sql,
            deps.client_upsert_params(
                site_id=site_id,
                name=deps.default_client_name(site_id),
                store_url=store_url,
                allowed_origin=deps.origin_from_url(store_url),
                deploy_mode=deps.deployment_mode or deps.default_deploy_mode,
                plan=vertical.default_plan_label,
                adapter_name=deps.default_client_adapter_name(site_id),
                status=deps.live_status,
                password_hash=deps.default_panel_password_hash(),
                vertical=vertical,
                locale=deps.default_locale,
                compliance_mode=deps.default_compliance_mode,
            ),
        )
        conn.commit()


def create_client(
    *,
    name: str,
    store_url: str,
    site_id: str | None,
    deploy_mode: str,
    plan: str,
    adapter_name: str,
    vertical_key: str,
    deps: ClientLifecycleWorkflows,
) -> dict[str, Any]:
    """Create or reactivate a CRM client and its tenant schema."""
    clean_url = deps.validated_url(store_url)
    clean_site_id = deps.safe_site_id(site_id or deps.site_id_from_name(name, clean_url))
    clean_name = deps.required_text(name, "Client name is required.")
    vertical = deps.validated_vertical(vertical_key)
    deps.init_admin_schema()
    deps.init_tenant_schema(clean_site_id)
    params = deps.client_upsert_params(
        site_id=clean_site_id,
        name=clean_name,
        store_url=clean_url,
        allowed_origin=deps.origin_from_url(clean_url),
        deploy_mode=deps.required_text(deploy_mode, "Deploy mode is required."),
        plan=deps.plan_for_vertical(plan, vertical),
        adapter_name=deps.required_text(adapter_name, "Adapter name is required."),
        status=deps.live_status,
        password_hash=deps.default_panel_password_hash(),
        vertical=vertical,
        locale=deps.default_locale,
        compliance_mode=deps.default_compliance_mode,
    )
    with deps.connect() as conn:
        conn.execute(deps.active_client_upsert_sql, params)
        conn.commit()
    return deps.get_client_detail(clean_site_id)


def discover_available_client(
    *,
    name: str,
    store_url: str,
    site_id: str,
    deploy_mode: str,
    plan: str,
    adapter_name: str,
    vertical_key: str,
    deps: ClientLifecycleWorkflows,
) -> dict[str, Any]:
    """Record a script-discovered client without activating Maya for it yet."""
    clean_url = deps.validated_url(store_url)
    clean_site_id = deps.safe_site_id(site_id)
    clean_name = deps.required_text(name, "Client name is required.")
    vertical = deps.validated_vertical(vertical_key)
    deps.init_admin_schema()
    deps.init_tenant_schema(clean_site_id)
    params = deps.client_upsert_params(
        site_id=clean_site_id,
        name=clean_name,
        store_url=clean_url,
        allowed_origin=deps.origin_from_url(clean_url),
        deploy_mode=deps.required_text(deploy_mode, "Deploy mode is required."),
        plan=deps.plan_for_vertical(plan, vertical),
        adapter_name=deps.required_text(adapter_name, "Adapter name is required."),
        status=deps.available_status,
        password_hash=deps.default_panel_password_hash(),
        vertical=vertical,
        locale=deps.default_locale,
        compliance_mode=deps.default_compliance_mode,
    )
    with deps.connect() as conn:
        conn.execute(
            deps.available_client_upsert_sql,
            deps.available_client_upsert_params(
                base_params=params,
                deleted_status=deps.deleted_status,
                available_status=deps.available_status,
            ),
        )
        conn.commit()
    return deps.get_client_detail(clean_site_id)
