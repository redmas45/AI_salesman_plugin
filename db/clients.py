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
from typing import Any
from urllib.parse import urlparse

import psycopg

import config
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
CLIENT_STATUS_DELETED = "deleted"
CRAWL_STATUS_NOT_STARTED = "not_started"
CRAWL_STATUS_RUNNING = "crawling"
CRAWL_STATUS_OK = "ok"
CRAWL_STATUS_ERROR = "error"
DEFAULT_PLAN = "Commerce plan"
DEFAULT_ADAPTER_NAME = "generic_adapter.js"
DEFAULT_DEPLOY_MODE = "public-ip"
DEFAULT_CLIENT_NAME = "AI-KART"
DEFAULT_CLIENT_LOCALE = "en-IN"
DEFAULT_CLIENT_COMPLIANCE_MODE = "standard"
DEFAULT_CLIENT_PANEL_PASSWORD = os.getenv("CLIENT_PANEL_DEFAULT_PASSWORD", "client123")
PANEL_PASSWORD_DISABLED = "disabled"
MIN_CLIENT_PANEL_PASSWORD_LENGTH = 12
GENERATED_PANEL_PASSWORD_BYTES = 24
PANEL_PASSWORD_ITERATIONS = 210_000
PANEL_PASSWORD_SALT_BYTES = 16
SITE_ID_MAX_LENGTH = 80
SESSION_ID_MAX_LENGTH = 120
DEFAULT_USAGE_LIMIT = 200


def ensure_default_client() -> None:
    """Register the current AI-KART local client when the CRM starts."""
    init_admin_schema()
    site_id = _safe_site_id(config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID)
    store_url = _first_text(config.CURRENT_URL, config.PUBLIC_API_URL, "http://143.198.5.97/")
    name = DEFAULT_CLIENT_NAME if site_id == "ai_kart" else site_id.replace("_", " ").title()
    vertical = get_vertical(DEFAULT_CLIENT_VERTICAL_KEY)
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
                DEFAULT_PLAN,
                "ai_kart_adapter.js",
                CLIENT_STATUS_LIVE,
                _hash_panel_password(DEFAULT_CLIENT_PANEL_PASSWORD),
                vertical.key,
                "{}",
                vertical.risk_level,
                DEFAULT_CLIENT_LOCALE,
                "",
                DEFAULT_CLIENT_COMPLIANCE_MODE,
            ),
        )
        conn.commit()


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
                _hash_panel_password(DEFAULT_CLIENT_PANEL_PASSWORD),
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
    return [_client_summary(dict(row)) for row in rows]


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
    """Soft-delete a client without dropping tenant inventory data."""
    _update_client_status(site_id, CLIENT_STATUS_DELETED)


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
    """Return the runtime vertical key for a client, defaulting to ecommerce."""
    client = _client_row(site_id)
    if not client:
        return DEFAULT_CLIENT_VERTICAL_KEY
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
                json.dumps(vertical_config, ensure_ascii=False, default=str),
                _required_text(adapter_name, "Adapter name is required."),
                vertical.risk_level,
                clean_site_id,
                CLIENT_STATUS_DELETED,
            ),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {clean_site_id} was not found.")
    return get_client_detail(clean_site_id)


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
    from db.quota import _usage_summary
    usage = _usage_summary()
    products_indexed = sum(int(client["catalog"]["active_products"]) for client in clients)
    return {
        "health": _health_snapshot(),
        "metrics": {
            "active_clients": len([item for item in clients if item["status"] == CLIENT_STATUS_LIVE]),
            "voice_turns_today": usage["turns_today"],
            "total_voice_turns": usage["total_turns"],
            "products_indexed": products_indexed,
            "avg_latency_ms": usage["avg_latency_ms"],
            "tokens_estimated": usage["tokens_estimated"],
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
        "catalog": _safe_catalog_summary(site_id),
        "usage": _usage_summary(site_id),
        "quota": quota_status(site_id),
        "panel_password_configured": _panel_password_configured(panel_password_hash),
        "panel_password_status": _panel_password_status(panel_password_hash),
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
    password_hash = _hash_panel_password(DEFAULT_CLIENT_PANEL_PASSWORD)
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
