"""Client database operations, tenant schema booting, and security config."""

from __future__ import annotations

import logging
from typing import Any

import config
from agent.adapters.adapter_interaction_learning import (
    action_config_from_interaction,
    enrich_interaction_event,
)
from agent.verticals.base import VerticalDefinition
from db.core.database import init_tenant_schema
from db.client_domain.facade import client_facade_workflows
from db.client_domain.lifecycle import client_cleanup, client_lifecycle, client_roster
from db.client_domain.panel import client_panel_password_compat, client_panel_password_workflows
from db.client_domain.reports import client_facade_reports, client_report_persistence
from db.client_domain.facade.client_compat_exports import *  # noqa: F403 - deliberate db.clients compatibility facade.
from db.client_domain.actions.client_action_health import (
    ACTION_HEALTH_EVENT_WINDOW,
    has_crm_action_override as _has_crm_action_override,
    refresh_action_health as _refresh_action_health,
    utc_timestamp as _utc_timestamp,
)
from db.client_domain.reports.client_artifacts import (
    get_latest_crawl_report,
    get_readiness_report,
    get_site_selectors,
    save_crawl_report,
    save_readiness_report,
    save_site_selectors,
)
from db.client_domain.core.client_constants import (
    ACTION_EVENT_TERMINAL_STATUSES,
    CLIENT_STATUS_AVAILABLE,
    CLIENT_STATUS_DELETED,
    CLIENT_STATUS_DISABLED,
    CLIENT_STATUS_LIVE,
    CRAWL_STATUS_ERROR,
    CRAWL_STATUS_NOT_STARTED,
    CRAWL_STATUS_OK,
    CRAWL_STATUS_RUNNING,
    DEFAULT_ADAPTER_NAME,
    DEFAULT_CLIENT_COMPLIANCE_MODE,
    DEFAULT_CLIENT_LOCALE,
    DEFAULT_CLIENT_PANEL_PASSWORD,
    DEFAULT_CLIENT_VERTICAL_KEY,
    DEFAULT_DEPLOY_MODE,
    DEFAULT_PLAN,
    DEFAULT_USAGE_LIMIT,
    SESSION_ID_MAX_LENGTH,
    SETUP_STATUS_CANCELED,
    SETUP_STATUS_RUNNING,
    SETUP_STATUS_TIMED_OUT,
    SITE_ID_MAX_LENGTH,
    SYNTHETIC_DEMO_URL_PATTERN,
    default_client_adapter_name,
    default_client_name,
    default_client_vertical_key,
)
from db.client_domain.events import client_event_persistence
from db.client_domain.lifecycle.client_operations import (
    is_client_widget_enabled,
    record_usage_event,
    update_client_crawl_status,
    update_client_setup_status,
)
from db.client_domain.dashboard import client_overview
from db.client_domain.settings import client_token_limits
from db.client_domain.runtime import client_config_store, client_runtime_workflows
from db.client_domain.lifecycle.client_registration import (
    ACTIVE_CLIENT_UPSERT_SQL,
    AVAILABLE_CLIENT_UPSERT_SQL,
    DEFAULT_CLIENT_UPSERT_SQL,
    available_client_upsert_params as _available_client_upsert_params,
    client_upsert_params as _client_upsert_params,
)
from db.client_domain.verticals import client_vertical_selection, client_vertical_workflows
from db.core.schema import _connect, init_admin_schema
from db.settings.settings_manager import _first_text, _public_hub_origin

logger = logging.getLogger(__name__)

_default_client_vertical_key = default_client_vertical_key
_default_client_adapter_name = default_client_adapter_name
_default_client_name = default_client_name


def ensure_default_client() -> None:
    """Register the configured local client when the CRM starts."""
    client_lifecycle.ensure_default_client(_lifecycle_workflows())


def cleanup_synthetic_demo_clients() -> int:
    """Hide stale example-domain installs that are useful in tests but noisy in local demos."""
    return client_cleanup.cleanup_synthetic_demo_clients(
        init_schema=init_admin_schema,
        connect=_connect,
        deleted_status=CLIENT_STATUS_DELETED,
        available_status=CLIENT_STATUS_AVAILABLE,
        url_pattern=SYNTHETIC_DEMO_URL_PATTERN,
    )


def create_client(
    *,
    name: str,
    store_url: str,
    site_id: str | None = None,
    deploy_mode: str = DEFAULT_DEPLOY_MODE,
    plan: str = DEFAULT_PLAN,
    adapter_name: str = DEFAULT_ADAPTER_NAME,
    vertical_key: str = DEFAULT_CLIENT_VERTICAL_KEY,
) -> dict[str, Any]:
    """Create or reactivate a CRM client and its tenant schema."""
    return client_lifecycle.create_client(
        name=name,
        store_url=store_url,
        site_id=site_id,
        deploy_mode=deploy_mode,
        plan=plan,
        adapter_name=adapter_name,
        vertical_key=vertical_key,
        deps=_lifecycle_workflows(),
    )


def discover_available_client(
    *,
    name: str,
    store_url: str,
    site_id: str,
    deploy_mode: str = DEFAULT_DEPLOY_MODE,
    plan: str = DEFAULT_PLAN,
    adapter_name: str = DEFAULT_ADAPTER_NAME,
    vertical_key: str = DEFAULT_CLIENT_VERTICAL_KEY,
) -> dict[str, Any]:
    """Record a script-discovered client without activating Maya for it yet."""
    return client_lifecycle.discover_available_client(
        name=name,
        store_url=store_url,
        site_id=site_id,
        deploy_mode=deploy_mode,
        plan=plan,
        adapter_name=adapter_name,
        vertical_key=vertical_key,
        deps=_lifecycle_workflows(),
    )


def list_clients() -> list[dict[str, Any]]:
    """Return CRM clients with catalog and usage summaries."""
    return client_roster.list_clients(_roster_workflows())


def get_client_detail(site_id: str) -> dict[str, Any]:
    """Return one client with full CRM-facing details."""
    return client_roster.get_client_detail(site_id, _roster_workflows())


def remove_client(site_id: str) -> None:
    """Hide a client from CRM lists while keeping tenant data for traceability."""
    _update_client_status(site_id, CLIENT_STATUS_DELETED)


def move_client_to_available(site_id: str) -> dict[str, Any]:
    """Move a current/disabled client back to the Available board."""
    _update_client_status(site_id, CLIENT_STATUS_AVAILABLE)
    return get_client_detail(site_id)


def activate_client(site_id: str) -> dict[str, Any]:
    """Promote an available/discovered client into the current live roster."""
    _update_client_status(site_id, CLIENT_STATUS_LIVE)
    return get_client_detail(site_id)


def set_client_enabled(site_id: str, enabled: bool) -> dict[str, Any]:
    """Enable or disable a client widget from the CRM."""
    status = CLIENT_STATUS_LIVE if enabled else CLIENT_STATUS_DISABLED
    _update_client_status(site_id, status)
    return get_client_detail(site_id)


def list_verticals() -> list[dict[str, Any]]:
    """Return built-in verticals for CRM selection."""
    return client_vertical_selection.list_verticals()


def get_vertical_detail(vertical_key: str) -> dict[str, Any]:
    """Return one vertical definition for CRM/API consumers."""
    return client_vertical_selection.get_vertical_detail(vertical_key, DEFAULT_CLIENT_VERTICAL_KEY)


def get_client_vertical_key(site_id: str) -> str:
    """Return the runtime vertical key for a client, using generic defaults when unregistered."""
    return client_vertical_selection.get_client_vertical_key(
        site_id,
        client_row=_client_row,
        default_key=_default_client_vertical_key(site_id),
    )


def update_client_vertical(site_id: str, vertical_key: str) -> dict[str, Any]:
    """Change a client's vertical without touching tenant data."""
    return client_vertical_workflows.update_client_vertical(site_id, vertical_key, _vertical_update_workflows())


def update_client_discovery_config(
    site_id: str,
    *,
    vertical_key: str,
    vertical_config: dict[str, Any],
    adapter_name: str = "generated_adapter.js",
) -> dict[str, Any]:
    """Persist generated runtime config from one-line installer discovery."""
    return client_runtime_workflows.update_client_discovery_config(
        site_id,
        vertical_key=vertical_key,
        vertical_config=vertical_config,
        adapter_name=adapter_name,
        deps=_runtime_workflows(),
    )


def update_client_adapter_actions(site_id: str, actions: dict[str, Any]) -> dict[str, Any]:
    """Replace a client's generated action map with a validated CRM override."""
    return client_runtime_workflows.update_client_adapter_actions(site_id, actions, _runtime_workflows())


def review_client_action_candidate(
    site_id: str,
    candidate: dict[str, Any],
    *,
    decision: str,
    action_name: str = "",
    note: str = "",
) -> dict[str, Any]:
    """Approve or reject one discovered adapter action candidate."""
    return client_runtime_workflows.review_client_action_candidate(
        site_id,
        candidate,
        decision=decision,
        action_name=action_name,
        note=note,
        deps=_runtime_workflows(),
    )


def refresh_client_action_proposals(site_id: str) -> dict[str, Any]:
    """Rebuild CRM-reviewable adapter action repair proposals from current evidence."""
    return client_runtime_workflows.refresh_client_action_proposals(site_id, _runtime_workflows())


def review_client_action_proposal(
    site_id: str,
    proposal: dict[str, Any],
    *,
    decision: str,
    note: str = "",
) -> dict[str, Any]:
    """Approve or reject one generated adapter repair proposal."""
    return client_runtime_workflows.review_client_action_proposal(
        site_id,
        proposal,
        decision=decision,
        note=note,
        deps=_runtime_workflows(),
    )


def review_client_flow_repair_proposal(
    site_id: str,
    proposal: dict[str, Any],
    *,
    decision: str,
    note: str = "",
) -> dict[str, Any]:
    """Approve or reject one generated flow repair proposal."""
    return client_runtime_workflows.review_client_flow_repair_proposal(
        site_id,
        proposal,
        decision=decision,
        note=note,
        deps=_runtime_workflows(),
    )


def save_adapter_validation_report(site_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Persist browser runtime validation and apply high-confidence repairs."""
    return client_runtime_workflows.save_adapter_validation_report(site_id, report, _runtime_workflows())


def verify_client_panel_password(site_id: str, password: str) -> dict[str, Any]:
    """Return client detail when the client-panel password is valid."""
    return client_panel_password_workflows.verify_client_panel_password(site_id, password, _panel_password_workflows())


def generate_client_panel_password() -> str:
    """Generate a strong one-time client-panel password for CRM operators."""
    return client_panel_password_workflows.generate_client_panel_password()


def update_client_panel_password(site_id: str, password: str) -> dict[str, Any]:
    """Set a new client-panel password using salted PBKDF2-SHA256 storage."""
    return client_panel_password_workflows.update_client_panel_password(site_id, password, _panel_password_workflows())


def revoke_client_panel_password(site_id: str) -> dict[str, Any]:
    """Disable client-panel password login until a new password is set."""
    return client_panel_password_workflows.revoke_client_panel_password(site_id, _panel_password_workflows())


def update_client_session_token_limit(site_id: str, limit: int) -> dict[str, Any]:
    """Allow a client panel to change the per-shopper/session token limit."""
    return client_token_limits.update_client_session_token_limit(
        site_id,
        limit,
        safe_site_id=_safe_site_id,
        init_schema=init_admin_schema,
        connect=_connect,
        deleted_status=CLIENT_STATUS_DELETED,
        get_client_detail=get_client_detail,
    )


def update_client_token_limits(site_id: str, token_limit: int, session_token_limit: int) -> dict[str, Any]:
    """Allow CRM admins to change the client and per-session token limits."""
    return client_token_limits.update_client_token_limits(
        site_id,
        token_limit,
        session_token_limit,
        safe_site_id=_safe_site_id,
        init_schema=init_admin_schema,
        connect=_connect,
        deleted_status=CLIENT_STATUS_DELETED,
        get_client_detail=get_client_detail,
    )


def overview() -> dict[str, Any]:
    """Return the dashboard summary payload."""
    return client_overview.overview(
        list_clients=list_clients,
        live_status=CLIENT_STATUS_LIVE,
        available_status=CLIENT_STATUS_AVAILABLE,
        health_snapshot=_health_snapshot,
        recent_usage_events=_recent_usage_events,
    )


def script_tag_for_site(site_id: str) -> str:
    """Build the one-line script tag for a client site."""
    return client_overview.script_tag_for_site(
        site_id,
        safe_site_id=_safe_site_id,
        public_hub_origin=_public_hub_origin,
    )


def _facade_runtime() -> Any:
    import sys

    return sys.modules[__name__]


def _lifecycle_workflows() -> client_lifecycle.ClientLifecycleWorkflows:
    return client_facade_workflows.lifecycle_workflows(_facade_runtime())


def _roster_workflows() -> client_roster.ClientRosterWorkflows:
    return client_facade_workflows.roster_workflows(_facade_runtime())


def _config_store() -> client_config_store.ClientConfigStore:
    return client_facade_workflows.config_store(_facade_runtime())


def _vertical_update_workflows() -> client_vertical_workflows.ClientVerticalUpdateWorkflows:
    return client_facade_workflows.vertical_update_workflows(_facade_runtime())


def _runtime_workflows() -> client_runtime_workflows.ClientRuntimeWorkflows:
    return client_facade_workflows.runtime_workflows(_facade_runtime())


def _report_persistence() -> client_report_persistence.ClientReportPersistence:
    return client_facade_workflows.report_persistence(_facade_runtime())


def _event_persistence() -> client_event_persistence.ClientEventPersistence:
    return client_facade_workflows.event_persistence(_facade_runtime())


def _panel_password_workflows() -> client_panel_password_workflows.ClientPanelPasswordWorkflows:
    return client_facade_workflows.panel_password_workflows(_facade_runtime())


def _client_vertical_config(site_id: str) -> dict[str, Any]:
    return client_config_store.client_vertical_config(site_id, _config_store())


def _write_client_vertical_config(site_id: str, vertical_config: dict[str, Any]) -> None:
    client_config_store.write_client_vertical_config(site_id, vertical_config, _config_store())


def _refresh_flow_repair_proposals(site_id: str, vertical_config: dict[str, Any]) -> None:
    _refresh_flow_repair_proposals_impl(
        site_id,
        vertical_config,
        vertical_key_for_site=_client_vertical_key_from_detail,
    )


def _client_vertical_key_from_detail(site_id: str) -> str:
    try:
        client = get_client_detail(site_id)
    except LookupError:
        return DEFAULT_CLIENT_VERTICAL_KEY
    return str(client.get("vertical_key") or DEFAULT_CLIENT_VERTICAL_KEY)


def _apply_validation_repairs(vertical_config: dict[str, Any], validation: dict[str, Any]) -> None:
    _apply_validation_repairs_impl(vertical_config, validation)


def _client_summary(client: dict[str, Any]) -> dict[str, Any]:
    return client_roster.client_summary(client, _roster_workflows())


def _client_row(site_id: str) -> dict[str, Any] | None:
    return client_roster.client_row(site_id, _roster_workflows())


def _update_client_status(site_id: str, status: str) -> None:
    client_roster.update_client_status(site_id, status, _roster_workflows())


def _validated_vertical(vertical_key: str | None) -> VerticalDefinition:
    return client_vertical_selection.validated_vertical(vertical_key, DEFAULT_CLIENT_VERTICAL_KEY)


def _client_vertical(vertical_key: str | None) -> VerticalDefinition:
    return client_vertical_selection.client_vertical(vertical_key, DEFAULT_CLIENT_VERTICAL_KEY)


def _plan_for_vertical(plan: str, vertical: VerticalDefinition) -> str:
    return client_vertical_selection.plan_for_vertical(plan, vertical, default_plan=DEFAULT_PLAN)


def _risk_level_text(value: str | None, fallback: str) -> str:
    return client_vertical_selection.risk_level_text(value, fallback)


globals().update(client_panel_password_compat.exports(_facade_runtime()))
globals().update(client_facade_reports.exports(_facade_runtime()))
