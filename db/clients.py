"""Client database operations, tenant schema booting, and security config."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
import psycopg

import config
from agent.actions.registry import is_supported_action, normalize_action_name
from agent.adapter_repair import build_action_repair_proposals, build_flow_repair_proposals
from agent.interaction_learning import (
    action_config_from_interaction,
    candidate_from_interaction,
    enrich_interaction_event,
)
from agent.sales_intake import sanitize_intake_questions
from agent.verticals.registry import (
    DEFAULT_VERTICAL_KEY as DEFAULT_CLIENT_VERTICAL_KEY,
    get_vertical,
    list_verticals as registry_list_verticals,
)
from agent.verticals.base import VerticalDefinition
from db.database import (
    catalog_source_stats,
    catalog_sync_history,
    get_db,
    init_tenant_schema,
    tenant_catalog_preview,
    tenant_catalog_stats,
)
from db.schema import _connect, init_admin_schema
from db.settings_manager import _first_text, _public_hub_origin

logger = logging.getLogger(__name__)

CLIENT_STATUS_LIVE = "live"
CLIENT_STATUS_DISABLED = "disabled"
CLIENT_STATUS_AVAILABLE = "available"
CLIENT_STATUS_DELETED = "deleted"
CRAWL_STATUS_NOT_STARTED = "not_started"
CRAWL_STATUS_RUNNING = "crawling"
CRAWL_STATUS_OK = "ok"
CRAWL_STATUS_ERROR = "error"
SETUP_STATUS_RUNNING = "running"
SETUP_STATUS_CANCELED = "canceled"
SETUP_STATUS_TIMED_OUT = "timed_out"
DEFAULT_PLAN = "Generic AI plan"
DEFAULT_ADAPTER_NAME = "generic_adapter.js"
DEFAULT_DEPLOY_MODE = "public-ip"
DEFAULT_CLIENT_LOCALE = "en-IN"
DEFAULT_CLIENT_COMPLIANCE_MODE = "standard"
DEFAULT_CLIENT_PANEL_PASSWORD = os.getenv("CLIENT_PANEL_DEFAULT_PASSWORD", "")
PANEL_PASSWORD_DISABLED = "disabled"
MIN_CLIENT_PANEL_PASSWORD_LENGTH = 12
GENERATED_PANEL_PASSWORD_BYTES = 24
PANEL_PASSWORD_ITERATIONS = 210_000
PANEL_PASSWORD_SALT_BYTES = 16
SITE_ID_MAX_LENGTH = 80
SESSION_ID_MAX_LENGTH = 120
DEFAULT_USAGE_LIMIT = 200
ADAPTER_ACTION_TYPES = frozenset({"navigate", "click", "form", "sequence", "handoff"})
ADAPTER_FORM_SUBMIT_MODES = frozenset({"submit", "auto_submit", "fill_only", "prepare_only"})
ADAPTER_SEQUENCE_OPERATIONS = frozenset({
    "check",
    "click",
    "fill",
    "focus",
    "navigate",
    "scroll",
    "select",
    "set_value",
    "submit",
    "uncheck",
    "wait",
    "wait_for",
})
MAX_ADAPTER_ACTIONS = 100
MAX_ADAPTER_SEQUENCE_STEPS = 30
MAX_ACTION_FIELD_LENGTH = 500
VALIDATION_REPAIR_THRESHOLD = 0.65
ACTION_HEALTH_FAILURE_THRESHOLD = 3
ACTION_HEALTH_EVENT_WINDOW = 12
ACTION_HEALTH_FAILURE_STATUSES = frozenset({"failed", "error"})
ACTION_EVENT_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "blocked", "skipped", "error"})
MAX_DURABLE_ACTION_EVENT_ROWS = 1000
RUNTIME_STATUS_TIMEOUT_SECONDS = 0.6
RUNTIME_STATUS_CACHE_SECONDS = 8.0
RUNTIME_STATUS_ONLINE = "online"
RUNTIME_STATUS_OFFLINE = "offline"
RUNTIME_STATUS_UNKNOWN = "unknown"
_runtime_status_cache: dict[str, tuple[float, dict[str, Any]]] = {}
DISCOVERY_PRESERVED_KEYS = frozenset({
    "action_health",
    "action_proposals",
    "action_proposal_reviews",
    "action_repairs",
    "action_reviews",
    "flow",
    "flow_repair_proposals",
    "flow_repair_reviews",
    "interaction_events",
    "policy_events",
    "regression",
    "rehearsal",
    "validation",
})
DISCOVERY_DIRECT_KEYS = frozenset({
    "discovery",
    "platform",
    "runtime_capabilities",
})
SYNTHETIC_DEMO_URL_PATTERN = r"^https?://([^/]+\.)?example\.(com|test|org)(/|$)"


def _default_client_vertical_key(site_id: str) -> str:
    return DEFAULT_CLIENT_VERTICAL_KEY


def _default_client_adapter_name(site_id: str) -> str:
    return DEFAULT_ADAPTER_NAME


def _default_client_name(site_id: str) -> str:
    return site_id.replace("_", " ").replace("-", " ").title()


def ensure_default_client() -> None:
    """Register the configured local client when the CRM starts."""
    init_admin_schema()
    if not config.ENSURE_DEFAULT_CLIENT_ON_STARTUP:
        return

    site_id = _safe_site_id(config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID)
    store_url = _first_text(config.CURRENT_URL, config.PUBLIC_API_URL, "http://localhost/")
    name = _default_client_name(site_id)
    vertical = get_vertical(_default_client_vertical_key(site_id))
    adapter_name = _default_client_adapter_name(site_id)
    init_tenant_schema(site_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_clients
                (
                    site_id, name, store_url, allowed_origin, deploy_mode, plan,
                    adapter_name, status, panel_password_hash, vertical_key,
                    vertical_config_json, risk_level, locale, prompt_profile_id,
                    compliance_mode
                )
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
            """,
            (
                site_id,
                name,
                store_url,
                _origin_from_url(store_url),
                os.getenv("DEPLOYMENT_MODE", DEFAULT_DEPLOY_MODE),
                vertical.default_plan_label,
                adapter_name,
                CLIENT_STATUS_LIVE,
                _default_panel_password_hash(),
                vertical.key,
                "{}",
                vertical.risk_level,
                DEFAULT_CLIENT_LOCALE,
                "",
                DEFAULT_CLIENT_COMPLIANCE_MODE,
            ),
        )
        conn.commit()


def cleanup_synthetic_demo_clients() -> int:
    """Hide stale example-domain installs that are useful in tests but noisy in local demos."""
    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET status = %s, updated_at = now()
            WHERE status = %s
              AND (
                COALESCE(store_url, '') ~* %s
                OR COALESCE(allowed_origin, '') ~* %s
              )
            """,
            (
                CLIENT_STATUS_DELETED,
                CLIENT_STATUS_AVAILABLE,
                SYNTHETIC_DEMO_URL_PATTERN,
                SYNTHETIC_DEMO_URL_PATTERN,
            ),
        )
        conn.commit()
        return max(0, int(cursor.rowcount or 0))


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
    clean_url = _validated_url(store_url)
    clean_site_id = _safe_site_id(site_id or _site_id_from_name(name, clean_url))
    clean_name = _required_text(name, "Client name is required.")
    vertical = _validated_vertical(vertical_key)
    clean_plan = _plan_for_vertical(plan, vertical)
    init_admin_schema()
    init_tenant_schema(clean_site_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_clients
                (
                    site_id, name, store_url, allowed_origin, deploy_mode, plan,
                    adapter_name, status, panel_password_hash, vertical_key,
                    vertical_config_json, risk_level, locale, prompt_profile_id,
                    compliance_mode
                )
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
            """,
            (
                clean_site_id,
                clean_name,
                clean_url,
                _origin_from_url(clean_url),
                _required_text(deploy_mode, "Deploy mode is required."),
                clean_plan,
                _required_text(adapter_name, "Adapter name is required."),
                CLIENT_STATUS_LIVE,
                _default_panel_password_hash(),
                vertical.key,
                "{}",
                vertical.risk_level,
                DEFAULT_CLIENT_LOCALE,
                "",
                DEFAULT_CLIENT_COMPLIANCE_MODE,
            ),
        )
        conn.commit()
    return get_client_detail(clean_site_id)


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
    clean_url = _validated_url(store_url)
    clean_site_id = _safe_site_id(site_id)
    clean_name = _required_text(name, "Client name is required.")
    vertical = _validated_vertical(vertical_key)
    clean_plan = _plan_for_vertical(plan, vertical)
    init_admin_schema()
    init_tenant_schema(clean_site_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_clients
                (
                    site_id, name, store_url, allowed_origin, deploy_mode, plan,
                    adapter_name, status, panel_password_hash, vertical_key,
                    vertical_config_json, risk_level, locale, prompt_profile_id,
                    compliance_mode
                )
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
            """,
            (
                clean_site_id,
                clean_name,
                clean_url,
                _origin_from_url(clean_url),
                _required_text(deploy_mode, "Deploy mode is required."),
                clean_plan,
                _required_text(adapter_name, "Adapter name is required."),
                CLIENT_STATUS_AVAILABLE,
                _default_panel_password_hash(),
                vertical.key,
                "{}",
                vertical.risk_level,
                DEFAULT_CLIENT_LOCALE,
                "",
                DEFAULT_CLIENT_COMPLIANCE_MODE,
                CLIENT_STATUS_DELETED,
                CLIENT_STATUS_AVAILABLE,
            ),
        )
        conn.commit()
    return get_client_detail(clean_site_id)


def list_clients() -> list[dict[str, Any]]:
    """Return CRM clients with catalog and usage summaries."""
    ensure_default_client()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM hub_clients
            WHERE status <> %s
            ORDER BY created_at ASC
            """,
            (CLIENT_STATUS_DELETED,),
        ).fetchall()
    return [_client_summary(row) for row in _visible_client_rows(dict(row) for row in rows)]


def _visible_client_rows(rows: Any) -> list[dict[str, Any]]:
    """Collapse duplicate universal auto-clients created from page paths on one origin.

    Explicit site IDs from installer tags are authoritative. If an explicit
    client and an auto-generated client point at the same origin, show only the
    explicit client so the operator does not see duplicate installs for one
    website.
    """
    row_list = list(rows)
    explicit_origins = {
        _client_origin_key(row)
        for row in row_list
        if not str(row.get("site_id") or "").startswith("auto_") and _client_origin_key(row)
    }
    visible: list[dict[str, Any]] = []
    auto_by_origin: dict[str, int] = {}
    for row in row_list:
        origin_key = _auto_client_origin_key(row)
        if not origin_key:
            visible.append(row)
            continue
        if origin_key in explicit_origins:
            continue

        existing_index = auto_by_origin.get(origin_key)
        if existing_index is None:
            auto_by_origin[origin_key] = len(visible)
            visible.append(row)
            continue

        current = visible[existing_index]
        if _auto_client_sort_key(row) < _auto_client_sort_key(current):
            visible[existing_index] = row
    return visible


def _auto_client_origin_key(row: dict[str, Any]) -> str:
    site_id = str(row.get("site_id") or "")
    if not site_id.startswith("auto_"):
        return ""
    return _client_origin_key(row)


def _client_origin_key(row: dict[str, Any]) -> str:
    return _canonical_origin_key(str(row.get("allowed_origin") or row.get("store_url") or ""))


def _canonical_origin_key(raw_url: str) -> str:
    origin = _origin_from_url(raw_url)
    try:
        parsed = urlparse(origin)
    except ValueError:
        return origin.lower()
    if not parsed.scheme or not parsed.netloc:
        return origin.lower()

    hostname = (parsed.hostname or "").lower()
    if hostname in {"127.0.0.1", "localhost", "host.docker.internal"}:
        hostname = "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme.lower()}://{hostname}{port}"


def _auto_client_sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    status_rank = 0 if row.get("status") == CLIENT_STATUS_LIVE else 1
    created_at = str(row.get("created_at") or "")
    return (status_rank, created_at, str(row.get("site_id") or ""))


def get_client_detail(site_id: str) -> dict[str, Any]:
    """Return one client with full CRM-facing details."""
    ensure_default_client()
    client = _client_row(site_id)
    if not client:
        raise LookupError(f"Client {site_id} was not found.")
    detail = _client_summary(client)
    detail["catalog_preview"] = _safe_catalog_preview(client["site_id"])
    detail["sync_runs"] = _safe_sync_history(client["site_id"])
    return detail


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
    return [vertical.to_dict() for vertical in registry_list_verticals()]


def get_vertical_detail(vertical_key: str) -> dict[str, Any]:
    """Return one vertical definition for CRM/API consumers."""
    return _validated_vertical(vertical_key).to_dict()


def get_client_vertical_key(site_id: str) -> str:
    """Return the runtime vertical key for a client, using generic defaults when unregistered."""
    client = _client_row(site_id)
    if not client:
        return _default_client_vertical_key(site_id)
    return _client_vertical(client.get("vertical_key")).key


def update_client_vertical(site_id: str, vertical_key: str) -> dict[str, Any]:
    """Change a client's vertical without touching tenant data."""
    clean_site_id = _safe_site_id(site_id)
    vertical = _validated_vertical(vertical_key)
    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET vertical_key = %s,
                risk_level = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (vertical.key, vertical.risk_level, clean_site_id, CLIENT_STATUS_DELETED),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    _record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="crm_admin",
        event_type="client_vertical_updated",
        event_scope="client_config",
        status="ok",
        message=f"Vertical changed to {vertical.key}.",
        metadata={"vertical_key": vertical.key, "risk_level": vertical.risk_level},
    )
    return get_client_detail(clean_site_id)


def update_client_discovery_config(
    site_id: str,
    *,
    vertical_key: str,
    vertical_config: dict[str, Any],
    adapter_name: str = "generated_adapter.js",
) -> dict[str, Any]:
    """Persist generated runtime config from one-line installer discovery."""
    clean_site_id = _safe_site_id(site_id)
    vertical = _validated_vertical(vertical_key)
    existing_client = _client_row(clean_site_id)
    existing_config = _json_object((existing_client or {}).get("vertical_config_json"))
    existing_vertical = _client_vertical((existing_client or {}).get("vertical_key")).key if existing_client else vertical.key
    merged_config = _merge_discovery_vertical_config(
        existing_config,
        vertical_config,
        vertical_changed=existing_vertical != vertical.key,
    )
    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET vertical_key = %s,
                vertical_config_json = %s,
                adapter_name = %s,
                risk_level = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (
                vertical.key,
                json.dumps(merged_config, ensure_ascii=False, default=str),
                _required_text(adapter_name, "Adapter name is required."),
                vertical.risk_level,
                clean_site_id,
                CLIENT_STATUS_DELETED,
            ),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    _record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="widget",
        event_type="discovery_config_updated",
        event_scope="discovery",
        status="ok",
        message="Widget discovery config updated.",
        metadata={"vertical_key": vertical.key, "adapter_name": adapter_name},
    )
    return get_client_detail(clean_site_id)


def update_client_adapter_actions(site_id: str, actions: dict[str, Any]) -> dict[str, Any]:
    """Replace a client's generated action map with a validated CRM override."""
    clean_site_id = _safe_site_id(site_id)
    vertical_config = _client_vertical_config(clean_site_id)
    vertical_config["actions"] = _validated_action_map(actions)
    vertical_config.setdefault("overrides", {})["actions"] = {
        "source": "crm",
        "updated": True,
    }
    _write_client_vertical_config(clean_site_id, vertical_config)
    _record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="crm_admin",
        event_type="adapter_actions_updated",
        event_scope="adapter",
        status="ok",
        message="Adapter action map updated.",
        metadata={"action_count": len(vertical_config["actions"]), "actions": sorted(vertical_config["actions"])},
    )
    return get_client_detail(clean_site_id)


def review_client_action_candidate(
    site_id: str,
    candidate: dict[str, Any],
    *,
    decision: str,
    action_name: str = "",
    note: str = "",
) -> dict[str, Any]:
    """Approve or reject one discovered adapter action candidate."""
    clean_site_id = _safe_site_id(site_id)
    clean_decision = _safe_action_text(decision).lower()
    if clean_decision not in {"approve", "reject"}:
        raise ValueError("Action candidate decision must be approve or reject.")

    vertical_config = _client_vertical_config(clean_site_id)
    review = _action_candidate_review(candidate, clean_decision, action_name=action_name, note=note)
    if clean_decision == "approve":
        _approve_action_candidate(vertical_config, candidate, review["action"])
    vertical_config["action_reviews"] = _merge_action_reviews(review, vertical_config.get("action_reviews"))
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def refresh_client_action_proposals(site_id: str) -> dict[str, Any]:
    """Rebuild CRM-reviewable adapter action repair proposals from current evidence."""
    clean_site_id = _safe_site_id(site_id)
    vertical_config = _client_vertical_config(clean_site_id)
    vertical_config["action_proposals"] = build_action_repair_proposals(
        vertical_config=vertical_config,
        vertical_key=get_client_vertical_key(clean_site_id),
    )
    _refresh_flow_repair_proposals(clean_site_id, vertical_config)
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def review_client_action_proposal(
    site_id: str,
    proposal: dict[str, Any],
    *,
    decision: str,
    note: str = "",
) -> dict[str, Any]:
    """Approve or reject one generated adapter repair proposal."""
    clean_site_id = _safe_site_id(site_id)
    clean_decision = _safe_action_text(decision).lower()
    if clean_decision not in {"approve", "reject"}:
        raise ValueError("Action proposal decision must be approve or reject.")

    vertical_config = _client_vertical_config(clean_site_id)
    review = _action_proposal_review(proposal, clean_decision, note=note)
    if clean_decision == "approve":
        _approve_action_proposal(vertical_config, proposal, review["action"])
    vertical_config["action_proposal_reviews"] = _merge_action_reviews(
        review,
        vertical_config.get("action_proposal_reviews"),
    )
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def review_client_flow_repair_proposal(
    site_id: str,
    proposal: dict[str, Any],
    *,
    decision: str,
    note: str = "",
) -> dict[str, Any]:
    """Approve or reject one generated flow repair proposal."""
    clean_site_id = _safe_site_id(site_id)
    clean_decision = _safe_action_text(decision).lower()
    if clean_decision not in {"approve", "reject"}:
        raise ValueError("Flow repair proposal decision must be approve or reject.")

    vertical_config = _client_vertical_config(clean_site_id)
    review = _flow_repair_review(proposal, clean_decision, note=note)
    if clean_decision == "approve":
        _approve_flow_repair_proposal(vertical_config, proposal)
    vertical_config["flow_repair_reviews"] = _merge_action_reviews(
        review,
        vertical_config.get("flow_repair_reviews"),
    )
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def _merge_discovery_vertical_config(
    existing_config: dict[str, Any],
    fresh_config: dict[str, Any],
    *,
    vertical_changed: bool,
) -> dict[str, Any]:
    """Merge browser rediscovery without deleting learned/admin runtime state."""
    existing = _dict_config(existing_config)
    fresh = _dict_config(fresh_config)
    merged = dict(existing)

    for key in DISCOVERY_DIRECT_KEYS:
        if key in fresh:
            merged[key] = fresh[key]

    merged["routes"] = {
        **_dict_config(existing.get("routes")),
        **_dict_config(fresh.get("routes")),
    }
    merged["action_candidates"] = _merge_discovery_rows(
        fresh.get("action_candidates"),
        existing.get("action_candidates"),
        ("kind", "action", "selector", "path", "label"),
    )
    merged["actions"] = _merge_discovery_actions(existing, fresh, vertical_changed=vertical_changed)
    # Auto-approve action candidates with confidence >= 0.75
    candidates = merged.get("action_candidates")
    if isinstance(candidates, list):
        actions = merged["actions"].copy()
        action_reviews = list(merged.get("action_reviews") or [])
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            confidence = 0.0
            try:
                confidence = float(candidate.get("confidence") or 0.0)
            except (ValueError, TypeError):
                pass

            review_status = str(candidate.get("review") or "").lower()
            action_name = str(candidate.get("action") or "")
            if confidence >= 0.75 and review_status != "reject" and action_name:
                candidate["review"] = "approve"
                try:
                    action_config = _action_config_from_candidate(candidate, actions.get(action_name))
                    actions[action_name] = action_config

                    review = _action_candidate_review(candidate, "approve", action_name=action_name)
                    action_reviews = _merge_action_reviews(review, action_reviews)
                except Exception:
                    pass
        merged["actions"] = actions
        merged["action_reviews"] = action_reviews

    merged["prompt_suggestions"] = _merge_discovery_texts(
        fresh.get("prompt_suggestions"),
        existing.get("prompt_suggestions"),
    )
    merged["intake_questions"] = _merge_intake_questions(
        fresh.get("intake_questions"),
        existing.get("intake_questions"),
        vertical_changed=vertical_changed,
    )
    merged["barriers"] = _merge_discovery_barriers(existing.get("barriers"), fresh.get("barriers"))

    for key, value in fresh.items():
        if key in merged or key in DISCOVERY_PRESERVED_KEYS:
            continue
        merged[key] = value
    return merged


def _merge_discovery_actions(existing: dict[str, Any], fresh: dict[str, Any], *, vertical_changed: bool) -> dict[str, Any]:
    existing_actions = _dict_config(existing.get("actions"))
    fresh_actions = _dict_config(fresh.get("actions"))
    if _has_crm_action_override(existing):
        return existing_actions
    if vertical_changed:
        return fresh_actions
    return {**existing_actions, **fresh_actions}


def _merge_intake_questions(fresh_value: Any, existing_value: Any, *, vertical_changed: bool) -> list[dict[str, Any]]:
    fresh = sanitize_intake_questions(fresh_value)
    existing = sanitize_intake_questions(existing_value)
    if vertical_changed:
        return fresh
    return fresh or existing


def _has_crm_action_override(vertical_config: dict[str, Any]) -> bool:
    overrides = _dict_config(vertical_config.get("overrides"))
    action_override = _dict_config(overrides.get("actions"))
    return _safe_action_text(action_override.get("source")).lower() == "crm"


def _action_candidate_review(
    candidate: dict[str, Any],
    decision: str,
    *,
    action_name: str = "",
    note: str = "",
) -> dict[str, Any]:
    row = _dict_config(candidate)
    action = normalize_action_name(action_name or _safe_action_text(row.get("action")))
    if not is_supported_action(action):
        raise ValueError("Action candidate does not map to a supported action.")
    return {
        "key": _action_candidate_key(row, action),
        "action": action,
        "decision": decision,
        "kind": _safe_action_text(row.get("kind")),
        "type": _safe_action_text(row.get("type")),
        "label": _safe_action_text(row.get("label")),
        "selector": _safe_action_text(row.get("selector")),
        "path": _safe_action_text(row.get("path")),
        "confidence": _safe_confidence(row.get("confidence"), 0.0),
        "note": _safe_action_text(note),
        "reviewed_at": _utc_timestamp(),
    }


def _approve_action_candidate(vertical_config: dict[str, Any], candidate: dict[str, Any], action_name: str) -> None:
    actions = _dict_config(vertical_config.get("actions")).copy()
    action_config = _action_config_from_candidate(candidate, actions.get(action_name))
    actions[action_name] = action_config
    vertical_config["actions"] = actions
    vertical_config.setdefault("overrides", {})["actions"] = {
        "source": "crm",
        "updated": True,
        "approved_action": action_name,
    }


def _action_config_from_candidate(candidate: dict[str, Any], existing_config: Any) -> dict[str, Any]:
    row = _dict_config(candidate)
    action_type = _safe_action_text(row.get("type")).lower()
    selector = _safe_action_text(row.get("selector"))
    path = _safe_candidate_path(row.get("path"))
    base = {
        "label": _safe_action_text(row.get("label")),
        "source": "crm_approved_candidate",
        "confidence": max(_safe_confidence(row.get("confidence"), 0.7), 0.7),
    }
    if action_type == "click" and selector:
        return _validated_action_config({**base, "type": "click", "selector": selector})
    if action_type in {"navigate", "click"} and path:
        return _validated_action_config({**base, "type": "navigate", "path": path})
    if action_type in {"form", "sequence"}:
        return _existing_candidate_config(existing_config, base)
    raise ValueError("Approved action candidate has no safe executable target.")


def _existing_candidate_config(existing_config: Any, base: dict[str, Any]) -> dict[str, Any]:
    existing = _dict_config(existing_config)
    if not existing:
        raise ValueError("Form and sequence candidates require an existing generated action config.")
    return _validated_action_config({**existing, **base})


def _safe_candidate_path(value: Any) -> str:
    path = _safe_action_text(value)
    if not path or path.lower().startswith(("http://", "https://", "javascript:", "data:")):
        return ""
    return path if path.startswith("/") else ""


def _merge_action_reviews(review: dict[str, Any], existing_reviews: Any) -> list[dict[str, Any]]:
    rows = [review, *_safe_flow_list(existing_reviews, MAX_ADAPTER_ACTIONS - 1)]
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = _safe_action_text(row.get("key"))
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged[:MAX_ADAPTER_ACTIONS]


def _action_proposal_review(proposal: dict[str, Any], decision: str, *, note: str = "") -> dict[str, Any]:
    row = _dict_config(proposal)
    action = normalize_action_name(_safe_action_text(row.get("action")))
    if not is_supported_action(action):
        raise ValueError("Action proposal does not map to a supported action.")
    config = _validated_action_config(row.get("config"))
    return {
        "key": _action_proposal_key(row, action, config),
        "action": action,
        "decision": decision,
        "kind": _safe_action_text(row.get("kind")),
        "source": _safe_action_text(row.get("source")),
        "type": _safe_action_text(config.get("type")),
        "selector": _safe_action_text(config.get("selector") or config.get("input")),
        "path": _safe_action_text(config.get("path")),
        "confidence": _safe_confidence(row.get("confidence"), 0.0),
        "note": _safe_action_text(note),
        "reviewed_at": _utc_timestamp(),
    }


def _approve_action_proposal(vertical_config: dict[str, Any], proposal: dict[str, Any], action_name: str) -> None:
    actions = _dict_config(vertical_config.get("actions")).copy()
    current = _dict_config(actions.get(action_name))
    proposed = _validated_action_config(_dict_config(proposal).get("config"))
    actions[action_name] = _validated_action_config(
        {
            **current,
            **proposed,
            "source": "crm_approved_proposal",
            "confidence": max(
                _safe_confidence(current.get("confidence"), 0.0),
                _safe_confidence(proposed.get("confidence"), 0.0),
            ),
        }
    )
    vertical_config["actions"] = actions
    vertical_config.setdefault("overrides", {})["actions"] = {
        "source": "crm",
        "updated": True,
        "approved_action": action_name,
    }


def _flow_repair_review(proposal: dict[str, Any], decision: str, *, note: str = "") -> dict[str, Any]:
    row = _dict_config(proposal)
    patch = _validated_flow_repair_patch(row.get("patch"), require_patch=decision == "approve")
    return {
        "key": _flow_repair_proposal_key(row, patch),
        "proposal_key": _safe_action_text(row.get("key")),
        "decision": decision,
        "kind": _safe_action_text(row.get("kind")),
        "scope": _safe_action_text(row.get("scope")),
        "item": _safe_action_text(row.get("item")),
        "confidence": _safe_confidence(row.get("confidence"), 0.0),
        "note": _safe_action_text(note),
        "patch": _safe_json_value(patch),
        "reviewed_at": _utc_timestamp(),
    }


def _approve_flow_repair_proposal(vertical_config: dict[str, Any], proposal: dict[str, Any]) -> None:
    patch = _validated_flow_repair_patch(_dict_config(proposal).get("patch"), require_patch=True)
    route_patch = _safe_route_map(patch.get("routes"))
    action_patch = _validated_action_map(_dict_config(patch.get("actions")))
    if route_patch:
        vertical_config["routes"] = {**_dict_config(vertical_config.get("routes")), **route_patch}
    if action_patch:
        vertical_config["actions"] = {**_dict_config(vertical_config.get("actions")), **action_patch}
    vertical_config.setdefault("overrides", {})["flow_repairs"] = {
        "source": "crm",
        "updated": True,
        "approved_item": _safe_action_text(_dict_config(proposal).get("item")),
    }


def _validated_flow_repair_patch(raw_patch: Any, *, require_patch: bool) -> dict[str, Any]:
    patch = _dict_config(raw_patch)
    route_patch = _safe_route_map(patch.get("routes"))
    action_patch = _validated_action_map(_dict_config(patch.get("actions")))
    if require_patch and not route_patch and not action_patch:
        raise ValueError("Flow repair proposal has no safe route or action patch.")
    return {"routes": route_patch, "actions": action_patch}


def _action_proposal_key(proposal: dict[str, Any], action_name: str, config: dict[str, Any]) -> str:
    parts = [
        action_name,
        _safe_action_text(proposal.get("kind")),
        _safe_action_text(proposal.get("source")),
        _safe_action_text(config.get("type")),
        _safe_action_text(config.get("selector") or config.get("input")),
        _safe_action_text(config.get("path")),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _flow_repair_proposal_key(proposal: dict[str, Any], patch: dict[str, Any]) -> str:
    parts = [
        _safe_action_text(proposal.get("key")),
        _safe_action_text(proposal.get("kind")),
        _safe_action_text(proposal.get("scope")),
        _safe_action_text(proposal.get("item")),
        json.dumps(_safe_json_value(patch), sort_keys=True),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _action_candidate_key(candidate: dict[str, Any], action_name: str) -> str:
    parts = [
        action_name,
        _safe_action_text(candidate.get("kind")),
        _safe_action_text(candidate.get("type")),
        _safe_action_text(candidate.get("selector")),
        _safe_action_text(candidate.get("path")),
        _safe_action_text(candidate.get("label")),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _merge_discovery_rows(new_rows: Any, old_rows: Any, key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    rows = [*_safe_flow_list(new_rows, MAX_ADAPTER_ACTIONS), *_safe_flow_list(old_rows, MAX_ADAPTER_ACTIONS)]
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(_safe_action_text(row.get(field)) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged[:MAX_ADAPTER_ACTIONS]


def _merge_discovery_texts(new_values: Any, old_values: Any) -> list[str]:
    values = [*_safe_text_list(new_values, 20), *_safe_text_list(old_values, 20)]
    return list(dict.fromkeys(values))[:20]


def _merge_discovery_barriers(existing_barriers: Any, fresh_barriers: Any) -> dict[str, Any]:
    existing = _validated_barrier_report(existing_barriers)
    fresh = _validated_barrier_report(fresh_barriers)
    findings = _merge_discovery_rows(fresh.get("findings"), existing.get("findings"), ("key", "page_url", "evidence"))
    return {
        "site_id": _safe_action_text(fresh.get("site_id") or existing.get("site_id")),
        "site_url": _safe_action_text(fresh.get("site_url") or existing.get("site_url")),
        "summary": _barrier_summary(findings),
        "findings": findings,
        "detected_at": _safe_action_text(fresh.get("detected_at") or existing.get("detected_at")),
    }


def _barrier_summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(findings),
        "high": _barrier_severity_count(findings, "high"),
        "medium": _barrier_severity_count(findings, "medium"),
        "low": _barrier_severity_count(findings, "low"),
        "keys": sorted({_safe_action_text(finding.get("key")) for finding in findings if _safe_action_text(finding.get("key"))}),
    }


def _barrier_severity_count(findings: list[dict[str, Any]], severity: str) -> int:
    return sum(1 for finding in findings if _safe_action_text(finding.get("severity")).lower() == severity)


def save_adapter_validation_report(site_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Persist browser runtime validation and apply high-confidence repairs."""
    clean_site_id = _safe_site_id(site_id)
    vertical_config = _client_vertical_config(clean_site_id)
    validation = _validated_adapter_validation(report)
    vertical_config["validation"] = validation
    _apply_validation_repairs(vertical_config, validation)
    _refresh_action_health(
        vertical_config,
        events=list_client_action_events({clean_site_id}, limit=ACTION_HEALTH_EVENT_WINDOW).get(clean_site_id, []),
    )
    _refresh_flow_repair_proposals(clean_site_id, vertical_config)
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def save_client_flow_report(site_id: str, flow_report: dict[str, Any]) -> dict[str, Any]:
    """Persist server-side flow discovery and merge runtime-safe actions."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(flow_report, dict):
        raise ValueError("Flow report must be a JSON object.")
    vertical_config = _client_vertical_config(clean_site_id)
    vertical_config["flow"] = _validated_flow_report(flow_report)
    vertical_config["barriers"] = _validated_barrier_report(flow_report.get("barriers"))
    vertical_config["routes"] = {
        **_dict_config(vertical_config.get("routes")),
        **_safe_route_map(flow_report.get("routes")),
    }
    vertical_config["actions"] = {
        **_dict_config(vertical_config.get("actions")),
        **_validated_action_map(_dict_config(flow_report.get("adapter_actions"))),
    }
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def save_client_rehearsal_report(site_id: str, rehearsal_report: dict[str, Any]) -> dict[str, Any]:
    """Persist safe server-side flow rehearsal evidence for one client."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(rehearsal_report, dict):
        raise ValueError("Flow rehearsal report must be a JSON object.")
    vertical_config = _client_vertical_config(clean_site_id)
    vertical_config["rehearsal"] = _validated_rehearsal_report(rehearsal_report)
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def save_client_regression_report(site_id: str, regression_report: dict[str, Any]) -> dict[str, Any]:
    """Persist flow regression evidence for one client."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(regression_report, dict):
        raise ValueError("Flow regression report must be a JSON object.")
    vertical_config = _client_vertical_config(clean_site_id)
    vertical_config["regression"] = _validated_regression_report(regression_report)
    _refresh_flow_repair_proposals(clean_site_id, vertical_config)
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def save_client_initialization_report(site_id: str, initialization_report: dict[str, Any]) -> dict[str, Any]:
    """Persist automatic one-script onboarding stage evidence."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(initialization_report, dict):
        raise ValueError("Initialization report must be a JSON object.")
    vertical_config = _client_vertical_config(clean_site_id)
    existing_initialization = _dict_config(vertical_config.get("initialization"))
    next_initialization = _validated_initialization_report(initialization_report)
    if (
        str(existing_initialization.get("status") or "").lower() in {SETUP_STATUS_CANCELED, SETUP_STATUS_TIMED_OUT}
        and _same_setup_run(existing_initialization, next_initialization)
    ):
        return get_client_detail(clean_site_id)
    if (
        next_initialization.get("status") == SETUP_STATUS_RUNNING
        and existing_initialization.get("cancel_requested")
        and _same_setup_run(existing_initialization, next_initialization)
    ):
        next_initialization["cancel_requested"] = True
        next_initialization["cancel_requested_at"] = _safe_action_text(existing_initialization.get("cancel_requested_at"))
    vertical_config["initialization"] = next_initialization
    _write_client_vertical_config(clean_site_id, vertical_config)
    _record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="setup_runner",
        event_type="setup_run_status",
        event_scope="setup",
        status=next_initialization["status"],
        request_id=next_initialization["run_id"],
        message=next_initialization["error"] or next_initialization["status"],
        metadata={
            "stage_count": len(next_initialization["stages"]),
            "duration_ms": next_initialization["duration_ms"],
            "cancel_requested": next_initialization["cancel_requested"],
        },
    )
    return get_client_detail(clean_site_id)


def setup_cancel_requested(site_id: str, run_id: str = "") -> bool:
    """Return whether the current setup run has a persisted stop request."""
    initialization = _dict_config(_client_vertical_config(_safe_site_id(site_id)).get("initialization"))
    if not initialization.get("cancel_requested"):
        return False
    return not run_id or _same_setup_run(initialization, {"run_id": run_id})


def request_client_setup_cancel(site_id: str) -> dict[str, Any]:
    """Persist a cooperative stop request for the active setup run."""
    clean_site_id = _safe_site_id(site_id)
    vertical_config = _client_vertical_config(clean_site_id)
    initialization = _dict_config(vertical_config.get("initialization")).copy()
    if str(initialization.get("status") or "").lower() != SETUP_STATUS_RUNNING:
        raise ValueError("No setup run is running for this client.")
    if not initialization.get("cancel_requested"):
        initialization["cancel_requested"] = True
        initialization["cancel_requested_at"] = _utc_timestamp()
        vertical_config["initialization"] = _validated_initialization_report(initialization)
        _write_client_vertical_config(clean_site_id, vertical_config)
        _record_audit_event_safely(
            site_id=clean_site_id,
            actor_type="crm_admin",
            event_type="setup_cancel_requested",
            event_scope="setup",
            status="requested",
            request_id=_safe_action_text(initialization.get("run_id")),
            message="Setup stop requested from CRM.",
        )
    return get_client_detail(clean_site_id)


def expire_stale_client_initialization_runs(max_age_seconds: int) -> int:
    """Mark stored setup runs as timed out when no background task can still own them."""
    max_age = max(60, int(max_age_seconds or config.SETUP_RUN_TIMEOUT_SECONDS or 7200))
    now_epoch = time.time()
    now_text = _utc_timestamp()
    expired = 0
    init_admin_schema()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT site_id, vertical_config_json
            FROM hub_clients
            WHERE status <> %s
            """,
            (CLIENT_STATUS_DELETED,),
        ).fetchall()
        for row in rows:
            site_id = _safe_site_id(row.get("site_id"))
            vertical_config = _json_object(row.get("vertical_config_json"))
            initialization = _dict_config(vertical_config.get("initialization")).copy()
            if str(initialization.get("status") or "").lower() != SETUP_STATUS_RUNNING:
                continue
            started_epoch = _timestamp_value(initialization.get("started_at"))
            try:
                saved_duration_ms = max(0.0, float(initialization.get("duration_ms") or 0.0))
            except (TypeError, ValueError):
                saved_duration_ms = 0.0
            age_seconds = (now_epoch - started_epoch) if started_epoch > 0 else (saved_duration_ms / 1000 if saved_duration_ms > 0 else max_age + 1)
            if age_seconds < max_age:
                continue
            message = f"Setup run timed out after {max_age} seconds."
            initialization["status"] = SETUP_STATUS_TIMED_OUT
            initialization["completed_at"] = now_text
            initialization["duration_ms"] = max(saved_duration_ms, age_seconds * 1000)
            initialization["error"] = message
            initialization["stages"] = _setup_stages_with_stop_status(
                initialization.get("stages"),
                SETUP_STATUS_TIMED_OUT,
                message,
                now_text,
            )
            vertical_config["initialization"] = _validated_initialization_report(initialization)
            conn.execute(
                """
                UPDATE hub_clients
                SET vertical_config_json = %s,
                    last_crawl_status = %s,
                    last_crawl_message = %s,
                    updated_at = now()
                WHERE site_id = %s AND status <> %s
                """,
                (
                    json.dumps(vertical_config, ensure_ascii=False, default=str),
                    CRAWL_STATUS_ERROR,
                    message[:500],
                    site_id,
                    CLIENT_STATUS_DELETED,
                ),
            )
            expired += 1
        conn.commit()
    return expired


def save_client_assistant_smoke_report(site_id: str, smoke_report: dict[str, Any]) -> dict[str, Any]:
    """Persist standalone assistant prompt smoke-test evidence for one client."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(smoke_report, dict):
        raise ValueError("Assistant smoke report must be a JSON object.")
    vertical_config = _client_vertical_config(clean_site_id)
    vertical_config["assistant_smoke_tests"] = _validated_assistant_smoke_report(smoke_report)
    _write_client_vertical_config(clean_site_id, vertical_config)
    report = vertical_config["assistant_smoke_tests"]
    _record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="setup_runner",
        event_type="assistant_smoke_report",
        event_scope="prompt_checks",
        status=report["status"],
        message=report["message"],
        metadata={"total": report["total"], "passed": report["passed"], "failed": report["failed"]},
    )
    return get_client_detail(clean_site_id)


def save_client_policy_event(site_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Persist a runtime action-policy event without altering selector validation."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(event, dict):
        raise ValueError("Policy event must be a JSON object.")
    clean_event = _validated_policy_event(event)
    record_audit_event(
        site_id=clean_site_id,
        actor_type="browser_runtime",
        event_type="policy_event",
        event_scope="runtime",
        status=clean_event["status"],
        action=clean_event["action"],
        message=clean_event["reason"],
        metadata={"url": clean_event["url"], "policy": clean_event["policy"]},
    )
    vertical_config = _client_vertical_config(clean_site_id)
    existing = vertical_config.get("policy_events")
    events = existing if isinstance(existing, list) else []
    vertical_config["policy_events"] = [clean_event, *_safe_flow_list(events, 29)]
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def save_client_action_event(site_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Persist browser runtime action execution evidence for adapter repair."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(event, dict):
        raise ValueError("Action execution event must be a JSON object.")
    clean_event = _validated_action_event(event)
    _insert_client_action_event(clean_site_id, clean_event)
    if clean_event["status"] in ACTION_EVENT_TERMINAL_STATUSES:
        record_audit_event(
            site_id=clean_site_id,
            actor_type="browser_runtime",
            event_type="action_terminal",
            event_scope="runtime_action",
            status=clean_event["status"],
            request_id=clean_event["request_id"],
            action=clean_event["action"],
            message=clean_event["reason"],
            metadata={
                "turn_id": clean_event["turn_id"],
                "sequence": clean_event["sequence"],
                "stage": clean_event["stage"],
                "requested_url": clean_event["requested_url"],
                "final_url": clean_event["final_url"],
            },
        )
    vertical_config = _client_vertical_config(clean_site_id)
    recent_events = list_client_action_events({clean_site_id}, limit=ACTION_HEALTH_EVENT_WINDOW).get(clean_site_id, [])
    if not recent_events:
        recent_events = [clean_event]
    _refresh_action_health(vertical_config, events=recent_events)
    vertical_config.pop("action_events", None)
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def save_client_interaction_event(site_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Persist privacy-safe browser interaction metadata for adapter learning."""
    clean_site_id = _safe_site_id(site_id)
    if not isinstance(event, dict):
        raise ValueError("Interaction event must be a JSON object.")
    vertical_config = _client_vertical_config(clean_site_id)
    existing = vertical_config.get("interaction_events")
    events = existing if isinstance(existing, list) else []
    clean_event = enrich_interaction_event(_validated_interaction_event(event), get_client_vertical_key(clean_site_id))
    vertical_config["interaction_events"] = [clean_event, *_safe_flow_list(events, 49)]
    vertical_config["action_candidates"] = _merge_interaction_candidate(
        vertical_config.get("action_candidates"),
        clean_event,
    )
    action_name, action_config = action_config_from_interaction(clean_event)
    if action_name and action_config:
        vertical_config["actions"] = _merge_learned_action(
            vertical_config.get("actions"),
            action_name,
            action_config,
        )
    _write_client_vertical_config(clean_site_id, vertical_config)
    return get_client_detail(clean_site_id)


def record_audit_event(
    *,
    site_id: str = "",
    actor_type: str = "system",
    event_type: str,
    event_scope: str = "",
    status: str = "ok",
    request_id: str = "",
    action: str = "",
    message: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append one durable server-owned audit event."""
    clean_site_id = _safe_site_id(site_id) if site_id else ""
    clean_metadata = _safe_json_value(metadata or {})
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_audit_events
                (
                    site_id, actor_type, event_type, event_scope, status,
                    request_id, action, message, metadata_json
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                clean_site_id,
                _safe_action_text(actor_type) or "system",
                _safe_action_text(event_type) or "event",
                _safe_action_text(event_scope),
                _safe_audit_status(status),
                _safe_action_text(request_id),
                normalize_action_name(_safe_action_text(action)),
                _safe_action_text(message),
                json.dumps(clean_metadata, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()


def _record_audit_event_safely(**kwargs: Any) -> None:
    try:
        record_audit_event(**kwargs)
    except Exception as exc:
        logger.warning("Audit event write skipped: %s", exc)


def list_client_action_events(site_ids: list[str] | set[str], *, limit: int = 500) -> dict[str, list[dict[str, Any]]]:
    """Return durable browser action events grouped by site ID."""
    clean_site_ids = sorted({_safe_site_id(site_id) for site_id in site_ids if str(site_id or "").strip()})
    if not clean_site_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(clean_site_ids))
    row_limit = max(1, min(int(limit or 500), MAX_DURABLE_ACTION_EVENT_ROWS))
    init_admin_schema()
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                site_id,
                request_id,
                turn_id,
                sequence,
                action,
                status,
                stage,
                reason,
                origin,
                url,
                requested_url,
                final_url,
                duration_ms,
                param_keys_json,
                evidence_json,
                occurred_at::TEXT AS occurred_at
            FROM hub_action_events
            WHERE site_id IN ({placeholders})
            ORDER BY occurred_at DESC, id DESC
            LIMIT %s
            """,
            (*clean_site_ids, row_limit),
        ).fetchall()
    events_by_site: dict[str, list[dict[str, Any]]] = {site_id: [] for site_id in clean_site_ids}
    for row in rows:
        event = _action_event_row_to_dict(dict(row))
        events_by_site.setdefault(event["site_id"], []).append(event)
    return events_by_site


def _insert_client_action_event(site_id: str, event: dict[str, Any]) -> None:
    """Store one normalized browser action event in durable Postgres rows."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_action_events
                (
                    site_id, request_id, turn_id, sequence, action, status, stage,
                    reason, origin, url, requested_url, final_url, duration_ms,
                    param_keys_json, evidence_json, occurred_at
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
            """,
            (
                site_id,
                event["request_id"],
                event["turn_id"],
                event["sequence"],
                event["action"],
                event["status"],
                event["stage"],
                event["reason"],
                event["origin"],
                event["url"],
                event["requested_url"],
                event["final_url"],
                event["duration_ms"],
                json.dumps(event["param_keys"], ensure_ascii=False, default=str),
                json.dumps(event["evidence"], ensure_ascii=False, default=str),
                _event_datetime(event.get("occurred_at")),
            ),
        )
        conn.commit()


def _action_event_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "site_id": _safe_site_id(row.get("site_id")),
        "source": "server_durable",
        "origin": _safe_action_text(row.get("origin")),
        "url": _safe_action_text(row.get("url")),
        "occurred_at": _safe_action_text(row.get("occurred_at")),
        "request_id": _safe_action_text(row.get("request_id")),
        "turn_id": _safe_action_text(row.get("turn_id")),
        "sequence": _safe_int(row.get("sequence")),
        "action": normalize_action_name(_safe_action_text(row.get("action"))),
        "status": _safe_action_status(row.get("status")),
        "stage": _safe_action_stage(row.get("stage")),
        "reason": _safe_action_text(row.get("reason")),
        "duration_ms": _safe_duration_ms(row.get("duration_ms")),
        "param_keys": _safe_text_list(_json_list(row.get("param_keys_json")), 20),
        "requested_url": _safe_action_text(row.get("requested_url")),
        "final_url": _safe_action_text(row.get("final_url")),
        "evidence": _safe_json_value(_json_object(row.get("evidence_json"))),
    }


def _event_datetime(value: Any) -> datetime | None:
    text = _safe_action_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _json_list(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        data = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def verify_client_panel_password(site_id: str, password: str) -> dict[str, Any]:
    """Return client detail when the client-panel password is valid."""
    clean_site_id = _safe_site_id(site_id)
    client = _client_row(clean_site_id)
    if not client:
        raise LookupError(f"Client {clean_site_id} was not found.")
    password_hash = client.get("panel_password_hash") or ""
    if password_hash == PANEL_PASSWORD_DISABLED:
        raise PermissionError("Client panel password is disabled.")
    if not password_hash:
        password_hash = _set_default_panel_password(clean_site_id)
    if not _verify_panel_password(password, password_hash):
        raise PermissionError("Invalid client panel credentials.")
    return get_client_detail(clean_site_id)


def generate_client_panel_password() -> str:
    """Generate a strong one-time client-panel password for CRM operators."""
    return secrets.token_urlsafe(GENERATED_PANEL_PASSWORD_BYTES)


def update_client_panel_password(site_id: str, password: str) -> dict[str, Any]:
    """Set a new client-panel password using salted PBKDF2-SHA256 storage."""
    clean_site_id = _safe_site_id(site_id)
    clean_password = str(password or "")
    if len(clean_password) < MIN_CLIENT_PANEL_PASSWORD_LENGTH:
        raise ValueError(f"Client panel password must be at least {MIN_CLIENT_PANEL_PASSWORD_LENGTH} characters.")
    password_hash = _hash_panel_password(clean_password)
    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET panel_password_hash = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (password_hash, clean_site_id, CLIENT_STATUS_DELETED),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    _record_audit_event_safely(
        site_id=clean_site_id,
        actor_type="crm_admin",
        event_type="client_panel_password_updated",
        event_scope="security",
        status="ok",
        message="Client panel password updated.",
        metadata={"password_configured": True},
    )
    return get_client_detail(clean_site_id)


def revoke_client_panel_password(site_id: str) -> dict[str, Any]:
    """Disable client-panel password login until a new password is set."""
    clean_site_id = _safe_site_id(site_id)
    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET panel_password_hash = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (PANEL_PASSWORD_DISABLED, clean_site_id, CLIENT_STATUS_DELETED),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    return get_client_detail(clean_site_id)


def update_client_session_token_limit(site_id: str, limit: int) -> dict[str, Any]:
    """Allow a client panel to change the per-shopper/session token limit."""
    clean_site_id = _safe_site_id(site_id)
    from db.quota import MAX_SESSION_TOKEN_LIMIT
    clean_limit = max(1, min(int(limit), MAX_SESSION_TOKEN_LIMIT))
    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET session_token_limit = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (clean_limit, clean_site_id, CLIENT_STATUS_DELETED),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    return get_client_detail(clean_site_id)


def update_client_token_limits(site_id: str, token_limit: int, session_token_limit: int) -> dict[str, Any]:
    """Allow CRM admins to change the client and per-session token limits."""
    clean_site_id = _safe_site_id(site_id)
    from db.quota import MAX_CLIENT_TOKEN_LIMIT, MAX_SESSION_TOKEN_LIMIT
    clean_token_limit = max(1, min(int(token_limit), MAX_CLIENT_TOKEN_LIMIT))
    clean_session_limit = max(1, min(int(session_token_limit), MAX_SESSION_TOKEN_LIMIT))
    if clean_session_limit > clean_token_limit:
        raise ValueError("Session token limit cannot be greater than the client token limit.")

    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET token_limit = %s,
                session_token_limit = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (clean_token_limit, clean_session_limit, clean_site_id, CLIENT_STATUS_DELETED),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    return get_client_detail(clean_site_id)


def is_client_widget_enabled(site_id: str) -> bool:
    """Return whether the public widget should boot for this client."""
    client = _client_row(site_id)
    if client is None:
        return True
    return client["status"] == CLIENT_STATUS_LIVE


def update_client_crawl_status(site_id: str, status: str, message: str = "") -> None:
    """Persist crawler state for a client row."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE hub_clients
            SET last_crawl_status = %s,
                last_crawl_message = %s,
                last_crawl_at = now(),
                updated_at = now()
            WHERE site_id = %s
            """,
            (status, message[:500], _safe_site_id(site_id)),
        )
        conn.commit()


def update_client_setup_status(site_id: str, needs_setup: bool, last_setup_at: str | None = None) -> None:
    """Persist setup state and drift flagging for a client row."""
    init_admin_schema()
    with _connect() as conn:
        if last_setup_at:
            conn.execute(
                """
                UPDATE hub_clients
                SET needs_setup = %s,
                    last_setup_at = %s,
                    updated_at = now()
                WHERE site_id = %s
                """,
                (needs_setup, last_setup_at, _safe_site_id(site_id)),
            )
        else:
            conn.execute(
                """
                UPDATE hub_clients
                SET needs_setup = %s,
                    updated_at = now()
                WHERE site_id = %s
                """,
                (needs_setup, _safe_site_id(site_id)),
            )
        conn.commit()


def script_tag_for_site(site_id: str) -> str:
    """Build the one-line script tag for a client site."""
    clean_site_id = _safe_site_id(site_id)
    origin = _public_hub_origin()
    return (
        f'<script defer src="{origin}/install.js?site={clean_site_id}" '
        f'data-site-id="{clean_site_id}"></script>'
    )


def record_usage_event(
    *,
    site_id: str,
    session_id: str = "",
    transport: str,
    status: str,
    transcript: str,
    response_text: str,
    intent: str,
    action_count: int,
    latency_ms: float,
) -> None:
    """Store one customer turn for CRM usage reporting."""
    init_admin_schema()
    clean_site_id = _safe_site_id(site_id)
    clean_session_id = _safe_session_id(session_id, clean_site_id)

    from db.quota import estimate_tokens, _ensure_conversation_session
    input_tokens = estimate_tokens(transcript)
    output_tokens = estimate_tokens(response_text)
    total_tokens = input_tokens + output_tokens
    _ensure_conversation_session(clean_site_id, clean_session_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_usage_events
                (
                    site_id, session_id, transport, status, input_tokens, output_tokens,
                    latency_ms, intent, action_count, transcript, response_text
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                clean_site_id,
                clean_session_id,
                transport,
                status,
                input_tokens,
                output_tokens,
                max(float(latency_ms or 0), 0.0),
                intent[:100],
                max(int(action_count), 0),
                str(transcript or "")[: config.MAX_TRANSCRIPT_CHARS],
                str(response_text or "")[: config.MAX_RESPONSE_CHARS],
            ),
        )
        conn.execute(
            """
            UPDATE hub_conversation_sessions
            SET token_used = token_used + %s,
                turn_count = turn_count + 1,
                last_seen_at = now()
            WHERE site_id = %s AND session_id = %s
            """,
            (total_tokens, clean_site_id, clean_session_id),
        )
        conn.commit()


def overview() -> dict[str, Any]:
    """Return the dashboard summary payload."""
    clients = list_clients()
    current_clients = [client for client in clients if client["status"] != CLIENT_STATUS_AVAILABLE]
    from db.quota import _usage_summary
    from agent.provider_status import provider_usage_status
    usage = _usage_summary()
    products_indexed = sum(int(client["catalog"]["active_products"]) for client in current_clients)
    cache_hits = sum(int((client.get("answer_cache") or {}).get("hits") or 0) for client in current_clients)
    cache_fresh = sum(int((client.get("answer_cache") or {}).get("fresh") or 0) for client in current_clients)
    tokens_saved = sum(int((client.get("answer_cache") or {}).get("estimated_tokens_saved") or 0) for client in current_clients)
    return {
        "health": _health_snapshot(),
        "provider_usage": provider_usage_status(),
        "metrics": {
            "active_clients": len([item for item in clients if item["status"] == CLIENT_STATUS_LIVE]),
            "voice_turns_today": usage["turns_today"],
            "total_voice_turns": usage["total_turns"],
            "products_indexed": products_indexed,
            "avg_latency_ms": usage["avg_latency_ms"],
            "tokens_estimated": usage["tokens_estimated"],
            "answer_cache_hits": cache_hits,
            "answer_cache_fresh": cache_fresh,
            "answer_cache_tokens_saved": tokens_saved,
        },
        "clients": clients,
        "recent_activity": _recent_usage_events(),
    }


def save_readiness_report(site_id: str, report: dict[str, Any]) -> None:
    """Persist a readiness scan result for a client."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE hub_clients
            SET readiness_report = %s,
                updated_at = now()
            WHERE site_id = %s
            """,
            (json.dumps(report, ensure_ascii=False), _safe_site_id(site_id)),
        )
        conn.commit()


def get_readiness_report(site_id: str) -> dict[str, Any] | None:
    """Return the saved readiness report for a client, or None."""
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT readiness_report FROM hub_clients WHERE site_id = %s",
            (_safe_site_id(site_id),),
        ).fetchone()
    if not row:
        return None
    raw = row.get("readiness_report") or ""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def save_crawl_report(site_id: str, report: dict[str, Any]) -> None:
    """Persist a crawl coverage report for a client."""
    init_admin_schema()
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        conn.execute(
            """
            UPDATE catalog_sync_runs
            SET report_json = %s
            WHERE id = (
                SELECT id FROM catalog_sync_runs
                ORDER BY created_at DESC
                LIMIT 1
            )
            """,
            (json.dumps(report, ensure_ascii=False),),
        )
        conn.commit()


def get_latest_crawl_report(site_id: str) -> dict[str, Any] | None:
    """Return the latest crawl report for a client."""
    init_admin_schema()
    try:
        with get_db(site_id) as conn:
            row = conn.execute(
                """
                SELECT report_json
                FROM catalog_sync_runs
                WHERE report_json IS NOT NULL AND report_json <> ''
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    raw = row.get("report_json") or ""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def save_site_selectors(
    site_id: str,
    selectors: dict[str, Any],
    confidence: float,
    validated: bool,
) -> None:
    """Persist LLM-extracted CSS selectors for a client site."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO site_selectors
                (site_id, selectors_json, confidence, validated, updated_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (site_id) DO UPDATE SET
                selectors_json = EXCLUDED.selectors_json,
                confidence = EXCLUDED.confidence,
                validated = EXCLUDED.validated,
                updated_at = now()
            """,
            (
                _safe_site_id(site_id),
                json.dumps(selectors, ensure_ascii=False),
                max(0.0, min(float(confidence), 1.0)),
                bool(validated),
            ),
        )
        conn.commit()


def get_site_selectors(site_id: str) -> dict[str, Any] | None:
    """Return saved LLM-extracted selectors for a client site."""
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM site_selectors WHERE site_id = %s",
            (_safe_site_id(site_id),),
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    try:
        result["selectors"] = json.loads(result.pop("selectors_json", "{}"))
    except json.JSONDecodeError:
        result["selectors"] = {}
    return result


def _client_vertical_config(site_id: str) -> dict[str, Any]:
    client = _client_row(site_id)
    if not client:
        raise LookupError(f"Client {site_id} was not found.")
    return _json_object(client.get("vertical_config_json"))


def _write_client_vertical_config(site_id: str, vertical_config: dict[str, Any]) -> None:
    init_admin_schema()
    clean_vertical_config = dict(vertical_config)
    clean_vertical_config.pop("action_events", None)
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET vertical_config_json = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (
                json.dumps(clean_vertical_config, ensure_ascii=False, default=str),
                _safe_site_id(site_id),
                CLIENT_STATUS_DELETED,
            ),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {site_id} was not found.")
    try:
        from db.answer_cache import bump_data_version

        bump_data_version(site_id, reason="client_runtime_config_changed")
    except Exception as exc:
        logger.warning("Answer cache invalidation skipped for %s: %s", site_id, exc)


def _validated_action_map(raw_actions: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_actions, dict):
        raise ValueError("Adapter actions must be a JSON object.")
    clean_actions: dict[str, Any] = {}
    for raw_name, raw_config in list(raw_actions.items())[:MAX_ADAPTER_ACTIONS]:
        action_name = normalize_action_name(str(raw_name))
        if not is_supported_action(action_name):
            raise ValueError(f"Unsupported adapter action: {raw_name}.")
        clean_actions[action_name] = _validated_action_config(raw_config)
    return clean_actions


def _validated_flow_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": _safe_action_text(report.get("site_id")),
        "site_url": _safe_action_text(report.get("site_url")),
        "vertical_key": _safe_action_text(report.get("vertical_key")),
        "detected_vertical_key": _safe_action_text(report.get("detected_vertical_key")),
        "confidence": _safe_confidence(report.get("confidence"), 0.0),
        "engine": _safe_action_text(report.get("engine")),
        "summary": _dict_config(report.get("summary")),
        "routes": _safe_route_map(report.get("routes")),
        "actions": _safe_flow_list(report.get("actions"), MAX_ADAPTER_ACTIONS),
        "pages": _safe_flow_list(report.get("pages"), MAX_ADAPTER_ACTIONS),
        "prompt_suggestions": _safe_text_list(report.get("prompt_suggestions"), 20),
        "barriers": _validated_barrier_report(report.get("barriers")),
        "discovered_at": _safe_action_text(report.get("discovered_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
    }


def _validated_barrier_report(raw_report: Any) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": _safe_action_text(report.get("site_id")),
        "site_url": _safe_action_text(report.get("site_url")),
        "summary": _dict_config(report.get("summary")),
        "findings": _safe_flow_list(report.get("findings"), MAX_ADAPTER_ACTIONS),
        "detected_at": _safe_action_text(report.get("detected_at")),
    }


def _validated_rehearsal_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": _safe_action_text(report.get("site_id")),
        "site_url": _safe_action_text(report.get("site_url")),
        "engine": _safe_action_text(report.get("engine")),
        "summary": _dict_config(report.get("summary")),
        "steps": _safe_flow_list(report.get("steps"), MAX_ADAPTER_ACTIONS),
        "rehearsed_at": _safe_action_text(report.get("rehearsed_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
    }


def _validated_regression_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "site_id": _safe_action_text(report.get("site_id")),
        "site_url": _safe_action_text(report.get("site_url")),
        "status": _safe_action_text(report.get("status")) or "unknown",
        "summary": _dict_config(report.get("summary")),
        "changes": _safe_flow_list(report.get("changes"), MAX_ADAPTER_ACTIONS),
        "compared_at": _safe_action_text(report.get("compared_at")),
    }


def _validated_initialization_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "source": _safe_action_text(report.get("source")) or "widget_registration",
        "status": _safe_action_text(report.get("status")) or "unknown",
        "run_id": _safe_action_text(report.get("run_id")),
        "site_id": _safe_action_text(report.get("site_id")),
        "site_url": _safe_action_text(report.get("site_url")),
        "vertical_key": _safe_action_text(report.get("vertical_key")),
        "started_at": _safe_action_text(report.get("started_at")),
        "completed_at": _safe_action_text(report.get("completed_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
        "timeout_seconds": max(0, int(report.get("timeout_seconds") or 0)),
        "cancel_requested": bool(report.get("cancel_requested")),
        "cancel_requested_at": _safe_action_text(report.get("cancel_requested_at")),
        "stages": _safe_flow_list(report.get("stages"), MAX_ADAPTER_ACTIONS),
        "error": _safe_action_text(report.get("error")),
    }


def _same_setup_run(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_run_id = _safe_action_text(left.get("run_id"))
    right_run_id = _safe_action_text(right.get("run_id"))
    return bool(left_run_id and right_run_id and left_run_id == right_run_id)


def _setup_stages_with_stop_status(raw_stages: Any, status: str, message: str, completed_at: str) -> list[dict[str, Any]]:
    stages = _safe_flow_list(raw_stages, MAX_ADAPTER_ACTIONS)
    if stages:
        updated = [dict(stage) for stage in stages]
        if str(updated[-1].get("status") or "").lower() == SETUP_STATUS_RUNNING:
            updated[-1] = {
                **updated[-1],
                "status": status,
                "message": message,
                "completed_at": completed_at,
            }
        elif not any(str(stage.get("status") or "").lower() in {status, "failed"} for stage in updated):
            updated.append({
                "name": "setup_stopped",
                "status": status,
                "message": message,
                "started_at": completed_at,
                "completed_at": completed_at,
            })
        return updated[:MAX_ADAPTER_ACTIONS]
    return [{
        "name": "setup_stopped",
        "status": status,
        "message": message,
        "started_at": completed_at,
        "completed_at": completed_at,
    }]


def _validated_assistant_smoke_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    report = raw_report if isinstance(raw_report, dict) else {}
    return {
        "source": _safe_action_text(report.get("source")) or "crm_assistant_smoke_tests",
        "status": _safe_action_text(report.get("status")) or "unknown",
        "site_id": _safe_action_text(report.get("site_id")),
        "vertical_key": _safe_action_text(report.get("vertical_key")),
        "started_at": _safe_action_text(report.get("started_at")),
        "completed_at": _safe_action_text(report.get("completed_at")),
        "duration_ms": max(0.0, float(report.get("duration_ms") or 0.0)),
        "message": _safe_action_text(report.get("message")),
        "total": max(0, int(report.get("total") or 0)),
        "passed": max(0, int(report.get("passed") or 0)),
        "failed": max(0, int(report.get("failed") or 0)),
        "tests": _safe_flow_list(report.get("tests"), 20),
    }


def _validated_policy_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    event = raw_event if isinstance(raw_event, dict) else {}
    return {
        "source": _safe_action_text(event.get("source")) or "browser_runtime",
        "origin": _safe_action_text(event.get("origin")),
        "url": _safe_action_text(event.get("url")),
        "occurred_at": _safe_action_text(event.get("occurred_at")),
        "action": normalize_action_name(_safe_action_text(event.get("action"))),
        "status": _safe_action_text(event.get("status")) or "unknown",
        "reason": _safe_action_text(event.get("reason")),
        "policy": _safe_json_value(event.get("policy")),
    }


def _validated_action_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    event = raw_event if isinstance(raw_event, dict) else {}
    return {
        "source": _safe_action_text(event.get("source")) or "browser_runtime",
        "origin": _safe_action_text(event.get("origin")),
        "url": _safe_action_text(event.get("url")),
        "occurred_at": _safe_action_text(event.get("occurred_at")),
        "request_id": _safe_action_text(event.get("request_id")),
        "turn_id": _safe_action_text(event.get("turn_id")),
        "sequence": _safe_int(event.get("sequence")),
        "action": normalize_action_name(_safe_action_text(event.get("action"))),
        "status": _safe_action_status(event.get("status")),
        "stage": _safe_action_stage(event.get("stage")),
        "reason": _safe_action_text(event.get("reason")),
        "duration_ms": _safe_duration_ms(event.get("duration_ms")),
        "param_keys": _safe_text_list(event.get("param_keys"), 20),
        "requested_url": _safe_action_text(event.get("requested_url")),
        "final_url": _safe_action_text(event.get("final_url")),
        "evidence": _safe_json_value(event.get("evidence")),
    }


def _refresh_action_health(vertical_config: dict[str, Any], *, events: list[dict[str, Any]] | None = None) -> None:
    action_events = _safe_flow_list(events, 50)
    validation = _dict_config(vertical_config.get("validation"))
    repair_candidates = _runtime_repair_candidates(vertical_config)
    health = _action_health_from_events(action_events, validation, repair_candidates)
    applied_repairs = _apply_action_health_repairs(vertical_config, health)
    if applied_repairs:
        health = _mark_action_health_repairs_applied(health, applied_repairs)
        vertical_config["action_repairs"] = _merge_action_repairs(
            applied_repairs,
            vertical_config.get("action_repairs"),
        )
    vertical_config["action_health"] = health


def _refresh_flow_repair_proposals(site_id: str, vertical_config: dict[str, Any]) -> None:
    vertical_config["flow_repair_proposals"] = build_flow_repair_proposals(
        vertical_config=vertical_config,
        vertical_key=get_client_vertical_key(site_id),
    )


def _action_health_from_events(
    events: list[dict[str, Any]],
    validation: dict[str, Any],
    repair_candidates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw_event in events[:ACTION_HEALTH_EVENT_WINDOW]:
        event = _validated_action_event(raw_event)
        action_name = event["action"]
        if not action_name or not is_supported_action(action_name):
            continue
        grouped.setdefault(action_name, []).append(event)

    action_rows = {
        action_name: _action_health_row(
            action_name,
            action_events,
            validation,
            repair_candidates.get(action_name),
        )
        for action_name, action_events in grouped.items()
    }
    needs_repair = [row for row in action_rows.values() if row["status"] in {"needs_repair", "blocked"}]
    blocked_actions = sorted(row["action"] for row in needs_repair if row["status"] == "blocked")
    return {
        "summary": {
            "tracked": len(action_rows),
            "needs_repair": len(needs_repair),
            "blocked": len(blocked_actions),
        },
        "actions": action_rows,
        "needs_repair": sorted(needs_repair, key=lambda row: (-int(row["failure_count"]), row["action"]))[:20],
        "blocked_actions": blocked_actions,
    }


def _action_health_row(
    action_name: str,
    events: list[dict[str, Any]],
    validation: dict[str, Any],
    repair_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    latest = events[0]
    validation_state = _validation_health_state(action_name, latest, validation, repair_candidate)
    if validation_state:
        return validation_state

    failure_count = _consecutive_failure_count(events)
    status = _action_health_status(latest["status"], failure_count)
    return _action_health_payload(action_name, latest, status, failure_count, repair_candidate)


def _validation_health_state(
    action_name: str,
    latest_event: dict[str, Any],
    validation: dict[str, Any],
    repair_candidate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not _validation_is_newer(latest_event, validation):
        return None
    evidence = _dict_config(_dict_config(validation.get("actions")).get(action_name))
    if bool(evidence.get("supported")):
        return _action_health_payload(action_name, latest_event, "validated", 0, repair_candidate)
    repair = _dict_config(evidence.get("repair"))
    if _safe_confidence(repair.get("confidence"), 0.0) >= VALIDATION_REPAIR_THRESHOLD:
        return _action_health_payload(action_name, latest_event, "repair_applied", 0, repair_candidate)
    return None


def _validation_is_newer(latest_event: dict[str, Any], validation: dict[str, Any]) -> bool:
    validated_at = _timestamp_value(validation.get("validated_at"))
    event_at = _timestamp_value(latest_event.get("occurred_at"))
    return validated_at > 0 and validated_at >= event_at


def _consecutive_failure_count(events: list[dict[str, Any]]) -> int:
    failures = 0
    for event in events:
        status = _safe_action_status(event.get("status"))
        if status in ACTION_HEALTH_FAILURE_STATUSES:
            failures += 1
            continue
        if status == "blocked":
            continue
        break
    return failures


def _action_health_status(latest_status: str, failure_count: int) -> str:
    if latest_status in {"ok", "succeeded"}:
        return "healthy"
    if latest_status == "blocked":
        return "policy_blocked"
    if latest_status == "needs_handoff":
        return "handoff_required"
    if failure_count >= ACTION_HEALTH_FAILURE_THRESHOLD:
        return "blocked"
    if failure_count > 0:
        return "needs_repair"
    return "unknown"


def _action_health_payload(
    action_name: str,
    latest_event: dict[str, Any],
    status: str,
    failure_count: int,
    repair_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "action": action_name,
        "status": status,
        "failure_count": failure_count,
        "last_status": _safe_action_status(latest_event.get("status")),
        "last_stage": _safe_action_stage(latest_event.get("stage")),
        "last_reason": _safe_action_text(latest_event.get("reason")),
        "last_url": _safe_action_text(latest_event.get("final_url")) or _safe_action_text(latest_event.get("url")),
        "last_request_id": _safe_action_text(latest_event.get("request_id")),
        "last_seen_at": _safe_action_text(latest_event.get("occurred_at")),
    }
    if status in {"needs_repair", "blocked"}:
        clean_candidate = _validated_repair_candidate(repair_candidate)
        if clean_candidate:
            payload["repair_candidate"] = clean_candidate
    return payload


def _runtime_repair_candidates(vertical_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for event in _safe_flow_list(vertical_config.get("interaction_events"), 50):
        action_name, action_config = action_config_from_interaction(event)
        if not action_name or not action_config:
            continue
        repair_candidate = _validated_repair_candidate(
            {
                **action_config,
                "source": "runtime_interaction_repair",
                "reason": "matched_recent_browser_interaction",
            }
        )
        if not repair_candidate:
            continue
        existing = candidates.get(action_name)
        if _safe_confidence(repair_candidate.get("confidence"), 0.0) <= _safe_confidence(
            _dict_config(existing).get("confidence"),
            0.0,
        ):
            continue
        candidates[action_name] = repair_candidate
    return candidates


def _validated_repair_candidate(raw_candidate: Any) -> dict[str, Any]:
    candidate = raw_candidate if isinstance(raw_candidate, dict) else {}
    try:
        clean_config = _validated_action_config(candidate)
    except ValueError:
        return {}
    if _safe_confidence(clean_config.get("confidence"), 0.0) < VALIDATION_REPAIR_THRESHOLD:
        return {}
    clean_config["source"] = _safe_action_text(candidate.get("source")) or "runtime_repair_candidate"
    reason = _safe_action_text(candidate.get("reason"))
    if reason:
        clean_config["reason"] = reason
    return clean_config


def _apply_action_health_repairs(vertical_config: dict[str, Any], health: dict[str, Any]) -> list[dict[str, Any]]:
    if _has_crm_action_override(vertical_config):
        return []
    actions = _dict_config(vertical_config.get("actions")).copy()
    applied: list[dict[str, Any]] = []
    for row in _safe_flow_list(health.get("needs_repair"), 20):
        action_name = normalize_action_name(_safe_action_text(row.get("action")))
        repair_candidate = _validated_repair_candidate(row.get("repair_candidate"))
        if not action_name or not repair_candidate:
            continue
        current = _dict_config(actions.get(action_name))
        if _safe_action_text(current.get("source")).lower() == "crm":
            continue
        repaired_config = _validated_action_config(
            {
                **current,
                **repair_candidate,
                "source": "runtime_repair",
                "confidence": max(
                    _safe_confidence(current.get("confidence"), 0.0),
                    _safe_confidence(repair_candidate.get("confidence"), 0.0),
                ),
            }
        )
        if _same_action_target(current, repaired_config):
            continue
        actions[action_name] = repaired_config
        applied.append(
            {
                "action": action_name,
                "status": "applied",
                "source": "runtime_repair",
                "reason": _safe_action_text(repair_candidate.get("reason")) or "matched_recent_browser_interaction",
                "repair": repaired_config,
                "failure_count": _safe_int(row.get("failure_count")),
                "last_url": _safe_action_text(row.get("last_url")),
                "applied_at": _utc_timestamp(),
            }
        )
    if applied:
        vertical_config["actions"] = actions
    return applied


def _same_action_target(current: dict[str, Any], repaired: dict[str, Any]) -> bool:
    if _safe_action_text(current.get("type")) != _safe_action_text(repaired.get("type")):
        return False
    target_keys = ("path", "selector", "form", "input", "submit")
    return all(_safe_action_text(current.get(key)) == _safe_action_text(repaired.get(key)) for key in target_keys)


def _mark_action_health_repairs_applied(health: dict[str, Any], repairs: list[dict[str, Any]]) -> dict[str, Any]:
    repaired_actions = {normalize_action_name(repair.get("action")) for repair in repairs}
    actions = _dict_config(health.get("actions")).copy()
    for action_name in repaired_actions:
        row = _dict_config(actions.get(action_name))
        if not row:
            continue
        row["status"] = "repair_applied"
        row["runtime_repair_applied"] = True
        row["failure_count"] = 0
        actions[action_name] = row
    needs_repair = [
        row
        for row in _safe_flow_list(health.get("needs_repair"), 20)
        if normalize_action_name(row.get("action")) not in repaired_actions
    ]
    blocked_actions = [
        action
        for action in _safe_text_list(health.get("blocked_actions"), 20)
        if normalize_action_name(action) not in repaired_actions
    ]
    summary = _dict_config(health.get("summary")).copy()
    summary["needs_repair"] = len(needs_repair)
    summary["blocked"] = len(blocked_actions)
    return {
        **health,
        "summary": summary,
        "actions": actions,
        "needs_repair": needs_repair,
        "blocked_actions": blocked_actions,
        "repairs_applied": _safe_flow_list(repairs, 20),
    }


def _merge_action_repairs(new_repairs: list[dict[str, Any]], old_repairs: Any) -> list[dict[str, Any]]:
    rows = [*_safe_flow_list(new_repairs, 20), *_safe_flow_list(old_repairs, 30)]
    return rows[:30]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_value(value: Any) -> float:
    text = _safe_action_text(value)
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _safe_action_status(value: Any) -> str:
    status = _safe_action_text(value).lower()
    allowed = {
        "ok",
        "requested",
        "executing",
        "succeeded",
        "failed",
        "blocked",
        "needs_handoff",
        "error",
        "unknown",
    }
    return status if status in allowed else "unknown"


def _safe_audit_status(value: Any) -> str:
    status = re.sub(r"[^a-z0-9_]+", "_", _safe_action_text(value).lower()).strip("_")
    if not status:
        return "unknown"
    return status[:80]


def _safe_action_stage(value: Any) -> str:
    stage = re.sub(r"[^a-z0-9_]+", "_", _safe_action_text(value).lower()).strip("_")
    return stage[:80]


def _safe_duration_ms(value: Any) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, number), 2)


def _validated_interaction_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    event = raw_event if isinstance(raw_event, dict) else {}
    event_type = _safe_action_text(event.get("event_type")).lower()
    if event_type not in {"click", "submit"}:
        event_type = "unknown"
    return {
        "source": _safe_action_text(event.get("source")) or "browser_runtime",
        "origin": _safe_action_text(event.get("origin")),
        "url": _safe_action_text(event.get("url")),
        "occurred_at": _safe_action_text(event.get("occurred_at")),
        "event_type": event_type,
        "label": _safe_action_text(event.get("label")),
        "selector": _safe_action_text(event.get("selector")),
        "tag": _safe_action_text(event.get("tag")),
        "href": _safe_action_text(event.get("href")),
        "form": _validated_interaction_form(event.get("form")),
    }


def _validated_interaction_form(raw_form: Any) -> dict[str, Any]:
    form = raw_form if isinstance(raw_form, dict) else {}
    return {
        "selector": _safe_action_text(form.get("selector")),
        "submit_selector": _safe_action_text(form.get("submit_selector")),
        "fields": _validated_interaction_fields(form.get("fields")),
    }


def _validated_interaction_fields(raw_fields: Any) -> list[dict[str, str]]:
    if not isinstance(raw_fields, list):
        return []
    fields: list[dict[str, str]] = []
    for raw_field in raw_fields[:12]:
        field = raw_field if isinstance(raw_field, dict) else {}
        selector = _safe_action_text(field.get("selector"))
        if not selector:
            continue
        fields.append(
            {
                "selector": selector,
                "name": _safe_action_text(field.get("name")),
                "type": _safe_action_text(field.get("type")),
                "placeholder": _safe_action_text(field.get("placeholder")),
            }
        )
    return fields


def _merge_interaction_candidate(raw_candidates: Any, event: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = raw_candidates if isinstance(raw_candidates, list) else []
    candidate = candidate_from_interaction(event)
    if not candidate:
        return _safe_flow_list(candidates, MAX_ADAPTER_ACTIONS)

    rows = [candidate, *_safe_flow_list(candidates, MAX_ADAPTER_ACTIONS - 1)]
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            _safe_action_text(row.get("kind")),
            _safe_action_text(row.get("selector")),
            _safe_action_text(row.get("path")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:MAX_ADAPTER_ACTIONS]


def _merge_learned_action(raw_actions: Any, action_name: str, raw_config: dict[str, Any]) -> dict[str, Any]:
    actions = _dict_config(raw_actions).copy()
    normalized = normalize_action_name(action_name)
    if not is_supported_action(normalized):
        return actions
    try:
        clean_config = _validated_action_config(raw_config)
    except ValueError as exc:
        logger.info("Ignoring learned adapter action %s: %s", normalized, exc)
        return actions

    existing = _dict_config(actions.get(normalized))
    if not existing:
        actions[normalized] = clean_config
        return actions
    if _safe_action_text(existing.get("source")) != "browser_interaction":
        return actions
    if _safe_confidence(existing.get("confidence"), 0.0) >= _safe_confidence(clean_config.get("confidence"), 0.0):
        return actions
    actions[normalized] = clean_config
    return actions


def _safe_flow_list(value: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        rows.append({str(key)[:80]: _safe_json_value(raw_value) for key, raw_value in item.items()})
    return rows


def _safe_text_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_action_text(item) for item in value[:limit] if _safe_action_text(item)]


def _safe_route_map(value: Any) -> dict[str, str]:
    routes = _dict_config(value)
    safe_routes: dict[str, str] = {}
    for raw_key, raw_value in routes.items():
        key = re.sub(r"[^a-z0-9_]+", "_", str(raw_key or "").strip().lower()).strip("_")[:80]
        path = _safe_action_text(raw_value)
        if key and path.startswith("/"):
            safe_routes[key] = path
    return safe_routes


def _dict_config(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_json_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        return [_safe_json_value(item) for item in value[:20]]
    if isinstance(value, dict):
        return {str(key)[:80]: _safe_json_value(item) for key, item in list(value.items())[:40]}
    return _safe_action_text(value)


def _validated_action_config(raw_config: Any) -> dict[str, Any]:
    if not isinstance(raw_config, dict):
        raise ValueError("Adapter action config must be a JSON object.")
    action_type = str(raw_config.get("type") or "").strip().lower()
    if action_type not in ADAPTER_ACTION_TYPES:
        raise ValueError("Adapter action type must be navigate, click, form, sequence, or handoff.")
    clean_config = {"type": action_type}
    for key in ("path", "selector", "form", "input", "submit", "submit_mode", "label", "source", "note", "message", "reason"):
        value = _safe_action_text(raw_config.get(key))
        if key == "submit_mode" and value not in ADAPTER_FORM_SUBMIT_MODES:
            continue
        if value:
            clean_config[key] = value
    for raw_key, clean_key in (
        ("page_path", "page_path"),
        ("pagePath", "page_path"),
        ("source_path", "source_path"),
        ("sourcePath", "source_path"),
    ):
        if clean_key in clean_config:
            continue
        value = _safe_action_page_path(raw_config.get(raw_key))
        if value:
            clean_config[clean_key] = value
    fields = _safe_text_list(raw_config.get("fields"), 20)
    if fields and action_type in {"form", "sequence"}:
        clean_config["fields"] = fields
    required_fields = _safe_text_list(raw_config.get("required_fields"), 20)
    if action_type in {"form", "sequence"} and ("required_fields" in raw_config or raw_config.get("required_fields_known") is True):
        clean_config["required_fields"] = required_fields
        clean_config["required_fields_known"] = True
    field_schema = _validated_field_schema(raw_config.get("field_schema"))
    if field_schema and action_type in {"form", "sequence"}:
        clean_config["field_schema"] = field_schema
    if action_type == "sequence":
        clean_config["steps"] = _validated_adapter_sequence(raw_config.get("steps"))
    clean_config["confidence"] = _safe_confidence(raw_config.get("confidence"), 0.7)
    return clean_config


def _validated_field_schema(raw_schema: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_schema, list):
        return []
    rows = [_validated_field_schema_item(item) for item in raw_schema[:20]]
    return [row for row in rows if row]


def _validated_field_schema_item(raw_item: Any) -> dict[str, Any]:
    if not isinstance(raw_item, dict):
        return {}
    param = _safe_action_text(raw_item.get("param"))[:80]
    if not param:
        return {}
    row: dict[str, Any] = {"param": param, "required": bool(raw_item.get("required") is True)}
    for key in ("label", "type", "autocomplete"):
        value = _safe_action_text(raw_item.get(key))[:120]
        if value:
            row[key] = value
    options = _validated_field_options(raw_item.get("options"))
    if options:
        row["options"] = options
    return row


def _validated_field_options(raw_options: Any) -> list[dict[str, str]]:
    if not isinstance(raw_options, list):
        return []
    rows = [_validated_field_option(option) for option in raw_options[:20]]
    return [row for row in rows if row]


def _validated_field_option(raw_option: Any) -> dict[str, str]:
    if isinstance(raw_option, dict):
        label = _safe_action_text(raw_option.get("label"))[:120]
        value = _safe_action_text(raw_option.get("value"))[:120]
    else:
        label = _safe_action_text(raw_option)[:120]
        value = label
    if not label and not value:
        return {}
    return {"label": label or value, "value": value or label}


def _validated_adapter_sequence(raw_steps: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_steps, list):
        raise ValueError("Sequence adapter actions require steps.")
    steps = [_validated_adapter_sequence_step(step) for step in raw_steps[:MAX_ADAPTER_SEQUENCE_STEPS]]
    clean_steps = [step for step in steps if step]
    if not clean_steps:
        raise ValueError("Sequence adapter actions require at least one valid step.")
    return clean_steps


def _validated_adapter_sequence_step(raw_step: Any) -> dict[str, Any]:
    if not isinstance(raw_step, dict):
        return {}
    operation = _safe_action_text(raw_step.get("op") or raw_step.get("type") or raw_step.get("action")).lower()
    if operation not in ADAPTER_SEQUENCE_OPERATIONS:
        return {}
    step: dict[str, Any] = {"op": operation}
    for key in ("selector", "label", "text", "name", "param", "parameter", "value", "path", "to"):
        value = _safe_action_text(raw_step.get(key))
        if value:
            step[key] = value
    if raw_step.get("optional") is True:
        step["optional"] = True
    if raw_step.get("ms") is not None:
        step["ms"] = _safe_wait_ms(raw_step.get("ms"))
    for key in ("x", "y"):
        if raw_step.get(key) is not None:
            step[key] = _safe_int(raw_step.get(key))
    return step


def _safe_wait_ms(value: Any) -> int:
    return max(0, min(_safe_int(value), 5000))


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _validated_adapter_validation(raw_report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_report, dict):
        raise ValueError("Adapter validation report must be a JSON object.")
    actions = raw_report.get("actions")
    if not isinstance(actions, dict):
        actions = {}
    clean_actions = {
        normalize_action_name(name): _validated_action_evidence(evidence)
        for name, evidence in list(actions.items())[:MAX_ADAPTER_ACTIONS]
        if is_supported_action(normalize_action_name(name))
    }
    return {
        "source": _safe_action_text(raw_report.get("source")) or "browser_runtime",
        "origin": _safe_action_text(raw_report.get("origin")),
        "url": _safe_action_text(raw_report.get("url")),
        "validated_at": _safe_action_text(raw_report.get("validated_at")),
        "summary": _validation_summary(clean_actions),
        "actions": clean_actions,
    }


def _validated_action_evidence(raw_evidence: Any) -> dict[str, Any]:
    evidence = raw_evidence if isinstance(raw_evidence, dict) else {}
    clean_evidence = {
        "type": _safe_action_text(evidence.get("type")),
        "status": _safe_action_text(evidence.get("status")) or "unknown",
        "target": _safe_action_text(evidence.get("target")),
        "evidence": _safe_action_text(evidence.get("evidence")),
        "supported": bool(evidence.get("supported")),
        "confidence": _safe_confidence(evidence.get("confidence"), 0.0),
    }
    repair = _repair_config(evidence.get("repair"))
    if repair:
        clean_evidence["repair"] = repair
    return clean_evidence


def _repair_config(raw_repair: Any) -> dict[str, Any]:
    if not isinstance(raw_repair, dict):
        return {}
    clean_repair: dict[str, Any] = {}
    for key in ("selector", "form", "input", "submit", "path", "label"):
        value = _safe_action_text(raw_repair.get(key))
        if value:
            clean_repair[key] = value
    repair_type = _safe_action_text(raw_repair.get("type"))
    if repair_type in ADAPTER_ACTION_TYPES:
        clean_repair["type"] = repair_type
    clean_repair["confidence"] = _safe_confidence(raw_repair.get("confidence"), 0.0)
    return clean_repair


def _apply_validation_repairs(vertical_config: dict[str, Any], validation: dict[str, Any]) -> None:
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict):
        return
    for action_name, evidence in validation.get("actions", {}).items():
        repair = evidence.get("repair")
        if not _should_apply_repair(evidence, repair) or action_name not in actions:
            continue
        actions[action_name] = _validated_action_config({
            **actions[action_name],
            **repair,
            "source": "browser_repair",
            "confidence": max(
                _safe_confidence(actions[action_name].get("confidence"), 0.0),
                _safe_confidence(repair.get("confidence"), 0.0),
            ),
        })


def _should_apply_repair(evidence: dict[str, Any], repair: Any) -> bool:
    if bool(evidence.get("supported")):
        return False
    if not isinstance(repair, dict):
        return False
    return _safe_confidence(repair.get("confidence"), 0.0) >= VALIDATION_REPAIR_THRESHOLD


def _validation_summary(actions: dict[str, dict[str, Any]]) -> dict[str, int]:
    supported = sum(1 for action in actions.values() if action.get("supported"))
    repaired = sum(1 for action in actions.values() if action.get("repair"))
    return {
        "total": len(actions),
        "supported": supported,
        "needs_repair": max(0, len(actions) - supported),
        "repair_suggestions": repaired,
    }


def _safe_action_text(value: Any) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if text.lower().startswith(("javascript:", "data:")):
        return ""
    return text[:MAX_ACTION_FIELD_LENGTH]


def _safe_action_page_path(value: Any) -> str:
    path = _safe_action_text(value)
    if not path or not path.startswith("/") or path.startswith("//"):
        return ""
    if path.lower().startswith(("/javascript:", "/data:")):
        return ""
    return path


def _safe_confidence(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return round(max(0.0, min(number, 1.0)), 2)


def _client_summary(client: dict[str, Any]) -> dict[str, Any]:
    site_id = client["site_id"]
    panel_password_hash = client.get("panel_password_hash") or ""
    public_client = {key: value for key, value in client.items() if key != "panel_password_hash"}
    vertical = _client_vertical(public_client.get("vertical_key"))
    public_client["vertical_key"] = vertical.key
    public_client["vertical_label"] = vertical.label
    public_client["risk_level"] = _risk_level_text(public_client.get("risk_level"), vertical.risk_level)
    public_client["vertical_config"] = _json_object(public_client.pop("vertical_config_json", "{}"))

    from db.quota import quota_status, _usage_summary
    return {
        **public_client,
        "script_tag": script_tag_for_site(site_id),
        "runtime_status": _runtime_status(_runtime_status_source_urls(public_client)),
        "catalog": _safe_catalog_summary(site_id),
        "answer_cache": _safe_answer_cache_summary(site_id),
        "usage": _usage_summary(site_id),
        "quota": quota_status(site_id),
        "panel_password_configured": _panel_password_configured(panel_password_hash),
        "panel_password_status": _panel_password_status(panel_password_hash),
    }


def _runtime_status(raw_url: Any) -> dict[str, Any]:
    """Return a short-lived read-only website reachability snapshot for CRM display."""
    target_urls = _runtime_status_urls(raw_url)
    if not target_urls:
        return {
            "status": RUNTIME_STATUS_UNKNOWN,
            "label": "No URL",
            "checked_url": "",
            "message": "Client URL is not configured.",
        }

    candidates = []
    for target_url in target_urls:
        candidates.extend(_runtime_status_candidates(target_url))
    candidates = list(dict.fromkeys(candidates))
    cache_key = "|".join(candidates)
    cached = _runtime_status_cache.get(cache_key)
    now = time.monotonic()
    if cached and now - cached[0] < RUNTIME_STATUS_CACHE_SECONDS:
        return dict(cached[1])

    status = _probe_runtime_status(candidates)
    _runtime_status_cache[cache_key] = (now, status)
    return dict(status)


def _runtime_status_source_urls(client: dict[str, Any]) -> list[str]:
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    runtime = vertical_config.get("runtime_capabilities") if isinstance(vertical_config.get("runtime_capabilities"), dict) else {}
    discovery = vertical_config.get("discovery") if isinstance(vertical_config.get("discovery"), dict) else {}
    return [
        runtime.get("url"),
        runtime.get("origin"),
        discovery.get("url"),
        client.get("store_url"),
        client.get("allowed_origin"),
    ]


def _runtime_status_urls(raw_url: Any) -> list[str]:
    if isinstance(raw_url, (list, tuple)):
        values = raw_url
    else:
        values = [raw_url]
    urls = [_runtime_status_url(value) for value in values]
    return list(dict.fromkeys(url for url in urls if url))


def _runtime_status_url(raw_url: Any) -> str:
    text = str(raw_url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return text
    return ""


def _runtime_status_candidates(target_url: str) -> list[str]:
    parsed = urlparse(target_url)
    candidates = [target_url]
    if parsed.hostname in {"127.0.0.1", "localhost"}:
        port = f":{parsed.port}" if parsed.port else ""
        candidates.append(parsed._replace(netloc=f"host.docker.internal{port}").geturl())
    return list(dict.fromkeys(candidates))


def _probe_runtime_status(target_urls: list[str]) -> dict[str, Any]:
    last_error = ""
    for target_url in target_urls:
        try:
            with httpx.Client(follow_redirects=True, timeout=RUNTIME_STATUS_TIMEOUT_SECONDS, verify=False) as client:
                response = client.head(target_url)
                if response.status_code in {405, 501}:
                    response = client.get(target_url)
        except (httpx.HTTPError, OSError, ValueError) as exc:
            last_error = str(exc)
            continue

        online = response.status_code < 500
        return {
            "status": RUNTIME_STATUS_ONLINE if online else RUNTIME_STATUS_OFFLINE,
            "label": "Online" if online else "Offline",
            "checked_url": target_url,
            "status_code": response.status_code,
            "message": f"HTTP {response.status_code}",
        }

    return {
        "status": RUNTIME_STATUS_OFFLINE,
        "label": "Offline",
        "checked_url": target_urls[0] if target_urls else "",
        "message": last_error or "Website did not respond.",
    }


def _client_row(site_id: str) -> dict[str, Any] | None:
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM hub_clients WHERE site_id = %s AND status <> %s",
            (_safe_site_id(site_id), CLIENT_STATUS_DELETED),
        ).fetchone()
    return dict(row) if row else None


def _update_client_status(site_id: str, status: str) -> None:
    init_admin_schema()
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE hub_clients SET status = %s, updated_at = now() WHERE site_id = %s",
            (status, _safe_site_id(site_id)),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {site_id} was not found.")


def _safe_catalog_summary(site_id: str) -> dict[str, Any]:
    try:
        stats = tenant_catalog_stats(site_id)
        stats["categories"] = _category_count(site_id)
        stats["sources"] = catalog_source_stats(site_id)
        stats["last_sync"] = _latest_sync(site_id)
        return stats
    except psycopg.Error as exc:
        return _empty_catalog_summary(str(exc))


def _safe_answer_cache_summary(site_id: str) -> dict[str, Any]:
    try:
        from db.answer_cache import answer_cache_summary

        return answer_cache_summary(site_id, limit=5)
    except Exception as exc:
        return {
            "site_id": site_id,
            "data_version": 0,
            "total": 0,
            "fresh": 0,
            "stale": 0,
            "hits": 0,
            "estimated_tokens_saved": 0,
            "items": [],
            "error": str(exc),
        }


def _empty_catalog_summary(message: str = "") -> dict[str, Any]:
    return {
        "total_products": 0,
        "active_products": 0,
        "missing_embeddings": 0,
        "categories": 0,
        "sources": [],
        "last_sync": None,
        "error": message,
    }


def _safe_catalog_preview(site_id: str) -> list[dict[str, Any]]:
    try:
        return tenant_catalog_preview(site_id, limit=12)
    except psycopg.Error:
        return []


def _safe_sync_history(site_id: str) -> list[dict[str, Any]]:
    try:
        return catalog_sync_history(site_id, limit=8)
    except psycopg.Error:
        return []


def _latest_sync(site_id: str) -> dict[str, Any] | None:
    runs = _safe_sync_history(site_id)
    return runs[0] if runs else None


def _category_count(site_id: str) -> int:
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM categories").fetchone()
    return int(row["total"] if row else 0)


def _recent_usage_events(limit: int = DEFAULT_USAGE_LIMIT) -> list[dict[str, Any]]:
    init_admin_schema()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                site_id, session_id, transport, status, intent, action_count,
                latency_ms, input_tokens, output_tokens, transcript, response_text,
                created_at::TEXT AS created_at
            FROM hub_usage_events
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def _health_snapshot() -> dict[str, str]:
    return {
        "fastapi": "up",
        "postgres": _postgres_health(),
        "pgvector": "up",
        "crawler": "ready",
    }


def _postgres_health() -> str:
    try:
        with _connect() as conn:
            conn.execute("SELECT 1")
        return "up"
    except psycopg.Error:
        return "down"


def _site_id_from_name(name: str, store_url: str) -> str:
    candidate = name or urlparse(store_url).hostname or "client"
    return _safe_site_id(candidate)


def _safe_site_id(raw: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(raw or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        return "client"
    if text[0].isdigit():
        text = f"site_{text}"
    return text[:SITE_ID_MAX_LENGTH]


def _safe_session_id(raw: str, site_id: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(raw or "").strip())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = f"{_safe_site_id(site_id)}_server"
    return text[:SESSION_ID_MAX_LENGTH]


def _validated_url(raw_url: str) -> str:
    value = _required_text(raw_url, "Client URL is required.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Client URL must start with http:// or https://.")
    return value.rstrip("/")


def _origin_from_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return raw_url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"


def _required_text(value: str, message: str) -> str:
    clean_value = str(value or "").strip()
    if not clean_value:
        raise ValueError(message)
    return clean_value


def _validated_vertical(vertical_key: str | None) -> VerticalDefinition:
    try:
        return get_vertical(vertical_key or DEFAULT_CLIENT_VERTICAL_KEY)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _client_vertical(vertical_key: str | None) -> VerticalDefinition:
    try:
        return get_vertical(vertical_key or DEFAULT_CLIENT_VERTICAL_KEY)
    except ValueError:
        return get_vertical(DEFAULT_CLIENT_VERTICAL_KEY)


def _plan_for_vertical(plan: str, vertical: VerticalDefinition) -> str:
    clean_plan = _required_text(plan, "Plan is required.")
    if clean_plan == DEFAULT_PLAN and vertical.default_plan_label != DEFAULT_PLAN:
        return vertical.default_plan_label
    return clean_plan


def _risk_level_text(value: str | None, fallback: str) -> str:
    clean_value = str(value or "").strip().lower()
    return clean_value if clean_value in {"low", "medium", "high"} else fallback


def _json_object(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _set_default_panel_password(site_id: str) -> str:
    if len(DEFAULT_CLIENT_PANEL_PASSWORD) < MIN_CLIENT_PANEL_PASSWORD_LENGTH:
        raise PermissionError("Client panel default password is not configured securely.")
    password_hash = _default_panel_password_hash()
    if not password_hash:
        raise PermissionError("Client panel default password is not configured securely.")
    with _connect() as conn:
        conn.execute(
            """
            UPDATE hub_clients
            SET panel_password_hash = %s,
                updated_at = now()
            WHERE site_id = %s
            """,
            (password_hash, _safe_site_id(site_id)),
        )
        conn.commit()
    return password_hash


def _default_panel_password_hash() -> str:
    """Return a default panel-password hash only when the configured default is strong enough."""
    if len(str(DEFAULT_CLIENT_PANEL_PASSWORD or "")) < MIN_CLIENT_PANEL_PASSWORD_LENGTH:
        return ""
    return _hash_panel_password(DEFAULT_CLIENT_PANEL_PASSWORD)


def _hash_panel_password(password: str) -> str:
    clean_password = str(password or "")
    if len(clean_password) < 6:
        raise ValueError("Client panel password must be at least 6 characters.")
    salt = secrets.token_bytes(PANEL_PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        clean_password.encode("utf-8"),
        salt,
        PANEL_PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PANEL_PASSWORD_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def _verify_panel_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = str(password_hash or "").split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = _unb64(salt_text)
    expected = _unb64(digest_text)
    actual = hashlib.pbkdf2_hmac("sha256", str(password or "").encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def _panel_password_configured(password_hash: str) -> bool:
    return bool(password_hash and password_hash != PANEL_PASSWORD_DISABLED)


def _panel_password_status(password_hash: str) -> str:
    if password_hash == PANEL_PASSWORD_DISABLED:
        return "revoked"
    if password_hash:
        return "configured"
    return "not_configured"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
