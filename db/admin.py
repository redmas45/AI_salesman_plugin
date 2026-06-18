"""Admin CRM persistence helpers for AI Hub clients and usage."""

from __future__ import annotations

import os
import re
import json
import base64
import hashlib
import hmac
import logging
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg
from dotenv import set_key
from psycopg.rows import dict_row

import config
from db.database import (
    catalog_source_stats,
    catalog_sync_history,
    get_all_products,
    get_db,
    init_tenant_schema,
    tenant_catalog_preview,
    tenant_catalog_stats,
)

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
DEFAULT_USAGE_LIMIT = 200
DEFAULT_CLIENT_TOKEN_LIMIT = 5000
DEFAULT_SESSION_TOKEN_LIMIT = 1000
DEFAULT_CLIENT_PANEL_PASSWORD = os.getenv("CLIENT_PANEL_DEFAULT_PASSWORD", "client123")
PANEL_PASSWORD_ITERATIONS = 210_000
PANEL_PASSWORD_SALT_BYTES = 16
TOKEN_CHAR_RATIO = 4
SITE_ID_MAX_LENGTH = 80
SESSION_ID_MAX_LENGTH = 120
PERCENT_SCALE = 100
LATENCY_FAST_MS = 1000
LATENCY_ACCEPTABLE_MS = 3000
ENV_FILE = Path(config.BASE_DIR) / ".env"
ANALYTICS_DEFAULT_RANGE = "7d"
ANALYTICS_CATALOG_PRODUCT_LIMIT = 1000
PRODUCT_FULL_MATCH_WEIGHT = 3
PRODUCT_TOKEN_MATCH_WEIGHT = 1
PRODUCT_COMMON_TOKEN_RATIO = 0.6
PRODUCT_COMMON_TOKEN_MIN_COUNT = 3
SUMMARY_MAX_BULLETS = 6

RANGE_DAYS = {
    "1d": 1,
    "3d": 3,
    "7d": 7,
    "15d": 15,
    "30d": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
}

ANALYTICS_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "can",
    "could",
    "for",
    "from",
    "have",
    "how",
    "into",
    "like",
    "me",
    "more",
    "need",
    "please",
    "show",
    "that",
    "the",
    "this",
    "what",
    "with",
    "you",
    "your",
}

PRODUCT_TOKEN_STOPWORDS = ANALYTICS_STOPWORDS | {
    "any",
    "best",
    "buy",
    "choice",
    "get",
    "good",
    "great",
    "help",
    "hello",
    "here",
    "interested",
    "looking",
    "might",
    "one",
    "ready",
    "see",
    "some",
    "want",
    "yaar",
}
PRODUCT_TYPE_TOKENS = {
    "bag",
    "bottom",
    "cap",
    "cup",
    "hoodie",
    "jacket",
    "mug",
    "onesie",
    "pant",
    "shirt",
    "shoe",
    "sticker",
    "top",
}

SETTING_KEYS = {
    "AI_DEFAULT_SITE_ID",
    "BACKEND_PORT",
    "CLIENT_PANEL_DEFAULT_PASSWORD",
    "CLIENT_PANEL_TOKEN_SECRET",
    "CLIENT_STORE_URL",
    "CORS_ORIGINS",
    "CRM_ADMIN_TOKEN",
    "CRAWL_MAX_DEPTH",
    "CRAWL_MAX_PAGES",
    "CRAWL_ON_STARTUP",
    "CRAWL_PERIODIC_ENABLED",
    "CURRENT_SITE_ID",
    "CURRENT_URL",
    "DATABASE_URL",
    "DEFAULT_SITE_ID",
    "DEPLOYMENT_MODE",
    "EMBEDDING_MODEL",
    "FAST_TTS_MODEL",
    "FAST_VOICE_MODE",
    "GROQ_API_KEY",
    "GROQ_FALLBACK_TO_OPENAI",
    "GROQ_STT_MODEL",
    "GROQ_TTS_MODEL",
    "GROQ_TTS_RESPONSE_FORMAT",
    "GROQ_TTS_VOICE",
    "HOST",
    "HTTPS_PORT",
    "HUB_PUBLIC_URL",
    "HUB_TLS_CERT_FILE",
    "HUB_TLS_KEY_FILE",
    "LLM_MAX_TOKENS",
    "LLM_MAX_TOKENS_HARD_CAP",
    "LLM_MODEL",
    "LLM_TEMPERATURE",
    "MANUAL_WIDGET_SCRIPT",
    "OPENAI_API_KEY",
    "PORT",
    "PUBLIC_API_URL",
    "PUBLIC_HTTPS_ORIGIN",
    "PUBLIC_STOREFRONT_ORIGIN",
    "PUBLIC_WIDGET_SCRIPT_URL",
    "RAG_TOP_K",
    "RAG_TOP_N",
    "STOREFRONT_PORT",
    "STT_LANGUAGE",
    "STT_MODEL",
    "STT_PROVIDER",
    "TTS_MODEL",
    "TTS_PROVIDER",
    "TTS_VOICE",
    "VOICE_ORB_API_URL",
}
SECRET_SETTING_KEYS = {
    "CLIENT_PANEL_DEFAULT_PASSWORD",
    "CLIENT_PANEL_TOKEN_SECRET",
    "CRM_ADMIN_TOKEN",
    "DATABASE_URL",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
}
FLOAT_SETTING_RANGES = {
    "LLM_TEMPERATURE": (0.0, 2.0),
}
INTEGER_SETTING_RANGES = {
    "BACKEND_PORT": (1, 65535),
    "CRAWL_MAX_DEPTH": (0, 20),
    "CRAWL_MAX_PAGES": (1, 10000),
    "HTTPS_PORT": (1, 65535),
    "LLM_MAX_TOKENS": (1, 200000),
    "LLM_MAX_TOKENS_HARD_CAP": (1, 500000),
    "PORT": (1, 65535),
    "RAG_TOP_K": (1, 100),
    "RAG_TOP_N": (1, 100),
    "STOREFRONT_PORT": (1, 65535),
}


class TokenQuotaExceededError(RuntimeError):
    """Raised when a client or session has exhausted its token budget."""

ADMIN_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS hub_clients (
    site_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    store_url TEXT NOT NULL,
    allowed_origin TEXT NOT NULL,
    deploy_mode TEXT NOT NULL DEFAULT 'public-ip',
    plan TEXT NOT NULL DEFAULT 'Commerce plan',
    adapter_name TEXT NOT NULL DEFAULT 'generic_adapter.js',
    status TEXT NOT NULL DEFAULT 'live',
    token_limit INTEGER NOT NULL DEFAULT 5000,
    session_token_limit INTEGER NOT NULL DEFAULT 1000,
    panel_password_hash TEXT NOT NULL DEFAULT '',
    last_crawl_status TEXT NOT NULL DEFAULT 'not_started',
    last_crawl_message TEXT NOT NULL DEFAULT '',
    last_crawl_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hub_usage_events (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT NOT NULL,
    transport TEXT NOT NULL,
    request_type TEXT NOT NULL DEFAULT 'shop_turn',
    session_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms REAL NOT NULL DEFAULT 0,
    intent TEXT NOT NULL DEFAULT '',
    action_count INTEGER NOT NULL DEFAULT 0,
    transcript TEXT NOT NULL DEFAULT '',
    response_text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hub_usage_events_site_created
    ON hub_usage_events(site_id, created_at DESC);

CREATE TABLE IF NOT EXISTS hub_conversation_sessions (
    session_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    token_limit INTEGER NOT NULL DEFAULT 1000,
    token_used INTEGER NOT NULL DEFAULT 0,
    turn_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (site_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_hub_conversation_sessions_last_seen
    ON hub_conversation_sessions(site_id, last_seen_at DESC);

CREATE TABLE IF NOT EXISTS hub_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    is_secret BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS token_limit INTEGER NOT NULL DEFAULT 5000;
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS session_token_limit INTEGER NOT NULL DEFAULT 1000;
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS panel_password_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_usage_events
    ADD COLUMN IF NOT EXISTS session_id TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_usage_events
    ADD COLUMN IF NOT EXISTS transcript TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_usage_events
    ADD COLUMN IF NOT EXISTS response_text TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_hub_usage_events_session_created
    ON hub_usage_events(site_id, session_id, created_at DESC);

ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS readiness_report TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS site_selectors (
    site_id TEXT PRIMARY KEY,
    selectors_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 0.0,
    validated BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_admin_schema() -> None:
    """Create CRM-owned public tables if they do not already exist."""
    with _connect() as conn:
        conn.execute(ADMIN_SCHEMA_SQL)
        conn.commit()


def ensure_default_client() -> None:
    """Register the current AI-KART local client when the CRM starts."""
    init_admin_schema()
    site_id = _safe_site_id(config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID)
    store_url = _first_text(config.CURRENT_URL, config.PUBLIC_API_URL, "http://143.198.5.97/")
    name = DEFAULT_CLIENT_NAME if site_id == "ai_kart" else site_id.replace("_", " ").title()
    init_tenant_schema(site_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_clients
                (site_id, name, store_url, allowed_origin, deploy_mode, plan, adapter_name, status, panel_password_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (site_id) DO UPDATE SET
                store_url = EXCLUDED.store_url,
                allowed_origin = EXCLUDED.allowed_origin,
                deploy_mode = EXCLUDED.deploy_mode,
                panel_password_hash = COALESCE(NULLIF(hub_clients.panel_password_hash, ''), EXCLUDED.panel_password_hash),
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
) -> dict[str, Any]:
    """Create or reactivate a CRM client and its tenant schema."""
    clean_url = _validated_url(store_url)
    clean_site_id = _safe_site_id(site_id or _site_id_from_name(name, clean_url))
    clean_name = _required_text(name, "Client name is required.")
    init_admin_schema()
    init_tenant_schema(clean_site_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_clients
                (site_id, name, store_url, allowed_origin, deploy_mode, plan, adapter_name, status, panel_password_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (site_id) DO UPDATE SET
                name = EXCLUDED.name,
                store_url = EXCLUDED.store_url,
                allowed_origin = EXCLUDED.allowed_origin,
                deploy_mode = EXCLUDED.deploy_mode,
                plan = EXCLUDED.plan,
                adapter_name = EXCLUDED.adapter_name,
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
                _required_text(plan, "Plan is required."),
                _required_text(adapter_name, "Adapter name is required."),
                CLIENT_STATUS_LIVE,
                _hash_panel_password(DEFAULT_CLIENT_PANEL_PASSWORD),
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


def verify_client_panel_password(site_id: str, password: str) -> dict[str, Any]:
    """Return client detail when the client-panel password is valid."""
    clean_site_id = _safe_site_id(site_id)
    client = _client_row(clean_site_id)
    if not client:
        raise LookupError(f"Client {clean_site_id} was not found.")
    password_hash = client.get("panel_password_hash") or ""
    if not password_hash:
        password_hash = _set_default_panel_password(clean_site_id)
    if not _verify_panel_password(password, password_hash):
        raise PermissionError("Invalid client panel credentials.")
    return get_client_detail(clean_site_id)


def update_client_session_token_limit(site_id: str, limit: int) -> dict[str, Any]:
    """Allow a client panel to change the per-shopper/session token limit."""
    clean_site_id = _safe_site_id(site_id)
    clean_limit = max(1, min(int(limit), 1_000_000))
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


def assert_usage_allowed(site_id: str, session_id: str = "") -> None:
    """Raise when the client or current session has no token budget left."""
    quota = quota_status(site_id, session_id)
    if quota["client"]["remaining"] <= 0:
        raise TokenQuotaExceededError("Client token quota is exhausted.")
    if quota["session"]["remaining"] <= 0:
        raise TokenQuotaExceededError("Session token quota is exhausted.")


def quota_status(site_id: str, session_id: str = "") -> dict[str, Any]:
    """Return client and session token quota state."""
    clean_site_id = _safe_site_id(site_id)
    client = _client_row(clean_site_id)
    client_limit = int(client.get("token_limit") or DEFAULT_CLIENT_TOKEN_LIMIT) if client else DEFAULT_CLIENT_TOKEN_LIMIT
    session_limit = (
        int(client.get("session_token_limit") or DEFAULT_SESSION_TOKEN_LIMIT)
        if client
        else DEFAULT_SESSION_TOKEN_LIMIT
    )
    clean_session_id = _safe_session_id(session_id, clean_site_id) if session_id else ""
    if clean_session_id:
        _ensure_conversation_session(clean_site_id, clean_session_id, token_limit=session_limit)
    client_used = _usage_summary(clean_site_id)["tokens_estimated"]
    session_used = _session_token_total(clean_site_id, clean_session_id) if clean_session_id else 0
    return {
        "site_id": clean_site_id,
        "session_id": clean_session_id,
        "client": _quota_part(client_used, client_limit),
        "session": _quota_part(session_used, session_limit),
    }


def estimate_tokens(text: str) -> int:
    """Return a rough token estimate for providers that do not expose usage."""
    clean_text = str(text or "").strip()
    if not clean_text:
        return 0
    return max(1, len(clean_text) // TOKEN_CHAR_RATIO)


def overview() -> dict[str, Any]:
    """Return the dashboard summary payload."""
    clients = list_clients()
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


def conversation_log(range_key: str = ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Return date-grouped conversation sessions and turns for CRM review."""
    rows = _usage_rows(range_key, site_id, limit=500)
    sessions: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        session_key = (row["site_id"], row["session_id"])
        session = sessions.setdefault(
            session_key,
            {
                "site_id": row["site_id"],
                "session_id": row["session_id"],
                "started_at": row["created_at"],
                "last_seen_at": row["created_at"],
                "turn_count": 0,
                "tokens_used": 0,
                "turns": [],
            },
        )
        session["turn_count"] += 1
        session["tokens_used"] += _row_tokens(row)
        session["last_seen_at"] = row["created_at"]
        session["turns"].append(_conversation_turn(row))

    date_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions.values():
        group_date = str(session["last_seen_at"])[:10]
        session["turns"].sort(key=lambda item: item["created_at"], reverse=True)
        date_groups[group_date].append(session)

    groups = [
        {
            "date": date,
            "sessions": sorted(items, key=lambda item: item["last_seen_at"], reverse=True),
        }
        for date, items in sorted(date_groups.items(), reverse=True)
    ]
    return {"range": _clean_range_key(range_key), "site_id": site_id or "all", "groups": groups}


def analytics_snapshot(range_key: str = ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Return CRM analytics computed from stored conversation turns."""
    rows = _usage_rows(range_key, site_id, limit=2000)
    tokens = sum(_row_tokens(row) for row in rows)
    sessions = {(row["site_id"], row["session_id"]) for row in rows}
    intents = Counter(row["intent"] or "unknown" for row in rows)
    products = _top_product_mentions(rows)
    statuses = Counter(row["status"] or "unknown" for row in rows)
    transports = Counter(row["transport"] or "unknown" for row in rows)
    sites = Counter(row["site_id"] or "unknown" for row in rows)
    action_count = sum(int(row.get("action_count") or 0) for row in rows)
    action_turn_count = sum(1 for row in rows if int(row.get("action_count") or 0) > 0)
    error_count = sum(1 for row in rows if str(row.get("status") or "").lower() not in {"ok", "success"})
    series = _daily_series(rows)
    peak_day = _peak_series_day(series)
    return {
        "range": _clean_range_key(range_key),
        "site_id": site_id or "all",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "turns": len(rows),
            "tokens": tokens,
            "sessions": len(sessions),
            "avg_latency_ms": _average_latency(rows),
            "actions": action_count,
            "action_rate": _percent(action_turn_count, len(rows)),
            "error_rate": _percent(error_count, len(rows)),
            "tokens_per_turn": round(tokens / len(rows), 1) if rows else 0,
        },
        "top_intents": _counter_rows(intents, limit=8),
        "top_products": _counter_rows(products, limit=12),
        "top_terms": _counter_rows(products, limit=12),
        "status_mix": _counter_rows(statuses, limit=8),
        "transport_mix": _counter_rows(transports, limit=8),
        "site_mix": _counter_rows(sites, limit=8),
        "latency_buckets": _latency_bucket_rows(rows),
        "peak_day": peak_day,
        "recent_events": rows[:8],
        "series": series,
        "summary": _heuristic_summary(rows, intents, products),
    }


def generate_analytics_summary(range_key: str = ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Generate an AI analytics summary when OpenAI is configured."""
    snapshot = analytics_snapshot(range_key, site_id)
    if not config.OPENAI_API_KEY:
        return {**snapshot, "summary_source": "heuristic"}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize ecommerce voice-assistant analytics for a store manager. "
                        "Return 4 to 6 plain bullet points only. Start each line with '- '. "
                        "Focus on what customers are looking for, what to stock, and what operational "
                        "action to take. Mention demand terms only when they are product names from "
                        "top_products. Do not use markdown headings."
                    ),
                },
                {
                    "role": "user",
                    "content": json_ready_analytics(snapshot),
                },
            ],
            temperature=0.2,
            max_tokens=280,
        )
        summary = completion.choices[0].message.content or snapshot["summary"]
        return {**snapshot, "summary": _clean_summary_bullets(summary), "summary_source": "openai"}
    except Exception as exc:
        logger.warning("OpenAI analytics summary failed; using heuristic summary: %s", exc)
        return {**snapshot, "summary_source": "heuristic"}


def settings_snapshot() -> dict[str, Any]:
    """Return whitelisted runtime settings for the CRM settings screen."""
    init_admin_schema()
    settings: list[dict[str, Any]] = []
    for key in sorted(SETTING_KEYS):
        value, source = _setting_value(key)
        is_secret = key in SECRET_SETTING_KEYS
        settings.append(
            {
                "key": key,
                "value": _masked_value(value) if is_secret else value,
                "is_secret": is_secret,
                "configured": _setting_is_configured(key),
                "source": source,
            }
        )
    return {"restart_required": True, "settings": settings}


def update_settings(values: dict[str, str]) -> dict[str, Any]:
    """Write whitelisted settings to .env and the CRM settings table."""
    init_admin_schema()
    clean_values = _validated_settings(values)
    with _connect() as conn:
        for key, value in clean_values.items():
            conn.execute(
                """
                INSERT INTO hub_settings (key, value, is_secret, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    is_secret = EXCLUDED.is_secret,
                    updated_at = now()
                """,
                (key, value, key in SECRET_SETTING_KEYS),
            )
        conn.commit()
    for key, value in clean_values.items():
        os.environ[key] = value
        set_key(str(ENV_FILE), key, value)
    return settings_snapshot()


def script_tag_for_site(site_id: str) -> str:
    """Build the one-line script tag for a client site."""
    clean_site_id = _safe_site_id(site_id)
    origin = _public_hub_origin()
    return (
        f'<script defer src="{origin}/shopbot.js?site={clean_site_id}" '
        f'data-site-id="{clean_site_id}"></script>'
    )


def _client_summary(client: dict[str, Any]) -> dict[str, Any]:
    site_id = client["site_id"]
    public_client = {key: value for key, value in client.items() if key != "panel_password_hash"}
    return {
        **public_client,
        "script_tag": script_tag_for_site(site_id),
        "catalog": _safe_catalog_summary(site_id),
        "usage": _usage_summary(site_id),
        "quota": quota_status(site_id),
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


def _usage_summary(site_id: str | None = None) -> dict[str, Any]:
    init_admin_schema()
    where_clause = "WHERE site_id = %s" if site_id else ""
    params = (_safe_site_id(site_id),) if site_id else ()
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_turns,
                COUNT(*) FILTER (WHERE created_at >= date_trunc('day', now())) AS turns_today,
                COALESCE(SUM(input_tokens + output_tokens), 0) AS tokens_estimated,
                COALESCE(ROUND(AVG(NULLIF(latency_ms, 0))::numeric, 0), 0) AS avg_latency_ms
            FROM hub_usage_events
            {where_clause}
            """,
            params,
        ).fetchone()
    return {
        "total_turns": int(row["total_turns"] if row else 0),
        "turns_today": int(row["turns_today"] if row else 0),
        "tokens_estimated": int(row["tokens_estimated"] if row else 0),
        "avg_latency_ms": int(row["avg_latency_ms"] if row else 0),
    }


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


def _usage_rows(range_key: str, site_id: str = "", limit: int = DEFAULT_USAGE_LIMIT) -> list[dict[str, Any]]:
    init_admin_schema()
    clean_site_id = _safe_site_id(site_id) if site_id else ""
    start_at = _range_start(_clean_range_key(range_key))
    clauses: list[str] = []
    params: list[Any] = []
    if clean_site_id:
        clauses.append("site_id = %s")
        params.append(clean_site_id)
    if start_at:
        clauses.append("created_at >= %s")
        params.append(start_at)
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, int(limit)))
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                site_id, session_id, transport, status, intent, action_count,
                input_tokens, output_tokens, latency_ms, transcript, response_text,
                created_at::TEXT AS created_at
            FROM hub_usage_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def _ensure_conversation_session(site_id: str, session_id: str, token_limit: int | None = None) -> None:
    clean_site_id = _safe_site_id(site_id)
    clean_session_id = _safe_session_id(session_id, clean_site_id)
    limit = int(token_limit or _client_session_limit(clean_site_id))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_conversation_sessions (site_id, session_id, token_limit)
            VALUES (%s, %s, %s)
            ON CONFLICT (site_id, session_id) DO UPDATE SET
                token_limit = EXCLUDED.token_limit,
                last_seen_at = hub_conversation_sessions.last_seen_at
            """,
            (clean_site_id, clean_session_id, limit),
        )
        conn.commit()


def _session_token_total(site_id: str, session_id: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(input_tokens + output_tokens), 0) AS total
            FROM hub_usage_events
            WHERE site_id = %s AND session_id = %s
            """,
            (_safe_site_id(site_id), _safe_session_id(session_id, _safe_site_id(site_id))),
        ).fetchone()
    return int(row["total"] if row else 0)


def _client_session_limit(site_id: str) -> int:
    client = _client_row(site_id)
    if not client:
        return DEFAULT_SESSION_TOKEN_LIMIT
    return int(client.get("session_token_limit") or DEFAULT_SESSION_TOKEN_LIMIT)


def _quota_part(used: int, limit: int) -> dict[str, int]:
    clean_limit = max(int(limit or 0), 0)
    clean_used = max(int(used or 0), 0)
    return {
        "used": clean_used,
        "limit": clean_limit,
        "remaining": max(clean_limit - clean_used, 0),
    }


def _conversation_turn(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": row["created_at"],
        "transport": row["transport"],
        "status": row["status"],
        "intent": row["intent"] or "unknown",
        "tokens": _row_tokens(row),
        "latency_ms": int(float(row["latency_ms"] or 0)),
        "transcript": row["transcript"],
        "response_text": row["response_text"],
        "action_count": int(row["action_count"] or 0),
    }


def _row_tokens(row: dict[str, Any]) -> int:
    return int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0)


def _clean_range_key(range_key: str) -> str:
    text = str(range_key or ANALYTICS_DEFAULT_RANGE).strip().lower()
    if text == "all":
        return "all"
    return text if text in RANGE_DAYS else ANALYTICS_DEFAULT_RANGE


def _range_start(range_key: str) -> datetime | None:
    if range_key == "all":
        return None
    return datetime.now(timezone.utc) - timedelta(days=RANGE_DAYS[range_key])


def _top_product_mentions(rows: list[dict[str, Any]]) -> Counter[str]:
    products: Counter[str] = Counter()
    matchers_by_site = _product_matchers_by_site({row["site_id"] for row in rows})
    for row in rows:
        matchers = matchers_by_site.get(row["site_id"], [])
        exact_matches = _exact_product_matches(row, matchers)
        if exact_matches:
            products.update(exact_matches)
            continue
        products.update(_fallback_product_matches(row, matchers))
    return products


def _exact_product_matches(row: dict[str, Any], matchers: list[dict[str, Any]]) -> Counter[str]:
    matches: Counter[str] = Counter()
    normalized_text = _normalized_product_text(_conversation_product_text(row))
    for matcher in matchers:
        if matcher["full_text"] and matcher["full_text"] in normalized_text:
            matches[matcher["name"]] += PRODUCT_FULL_MATCH_WEIGHT
    return matches


def _fallback_product_matches(row: dict[str, Any], matchers: list[dict[str, Any]]) -> Counter[str]:
    matches: Counter[str] = Counter()
    text_tokens = set(_normalized_product_tokens(_customer_demand_text(row)))
    for matcher in matchers:
        if matcher["tokens"] & text_tokens:
            matches[matcher["name"]] += PRODUCT_TOKEN_MATCH_WEIGHT
    return matches


def _product_matchers_by_site(site_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    products_by_site = _catalog_product_names(site_ids)
    return {
        site_id: _product_matchers(product_names)
        for site_id, product_names in products_by_site.items()
    }


def _catalog_product_names(site_ids: set[str]) -> dict[str, list[str]]:
    product_names: dict[str, list[str]] = {}
    for site_id in site_ids:
        try:
            products = get_all_products(site_id, limit=ANALYTICS_CATALOG_PRODUCT_LIMIT)
        except psycopg.Error:
            product_names[site_id] = []
            continue
        product_names[site_id] = _unique_product_names(products)
    return product_names


def _unique_product_names(products: list[dict[str, Any]]) -> list[str]:
    names = {
        str(product.get("name") or "").strip()
        for product in products
        if str(product.get("name") or "").strip()
    }
    return sorted(names)


def _product_matchers(product_names: list[str]) -> list[dict[str, Any]]:
    common_tokens = _common_product_tokens(product_names)
    return [
        {
            "name": product_name,
            "full_text": _normalized_product_text(product_name),
            "tokens": _significant_product_tokens(product_name, common_tokens),
        }
        for product_name in product_names
    ]


def _common_product_tokens(product_names: list[str]) -> set[str]:
    token_counts: Counter[str] = Counter()
    for product_name in product_names:
        token_counts.update(set(_normalized_product_tokens(product_name)))
    threshold = max(PRODUCT_COMMON_TOKEN_MIN_COUNT, int(len(product_names) * PRODUCT_COMMON_TOKEN_RATIO))
    return {
        token
        for token, count in token_counts.items()
        if count >= threshold and token not in PRODUCT_TYPE_TOKENS
    }


def _significant_product_tokens(product_name: str, common_tokens: set[str]) -> set[str]:
    tokens = {
        token
        for token in _normalized_product_tokens(product_name)
        if _is_product_signal_token(token, common_tokens)
    }
    if tokens:
        return tokens
    return set(_normalized_product_tokens(product_name)) - common_tokens


def _is_product_signal_token(token: str, common_tokens: set[str]) -> bool:
    if len(token) < 3:
        return False
    if token in PRODUCT_TOKEN_STOPWORDS or token in common_tokens:
        return False
    return True


def _customer_demand_text(row: dict[str, Any]) -> str:
    return str(row.get("transcript") or "")


def _conversation_product_text(row: dict[str, Any]) -> str:
    return f"{row.get('transcript', '')} {row.get('response_text', '')}"


def _normalized_product_text(value: str) -> str:
    return " ".join(_normalized_product_tokens(value))


def _normalized_product_tokens(value: str) -> list[str]:
    text = str(value or "").lower()
    text = re.sub(r"\bt[\s-]?shirts?\b", " t shirt ", text)
    text = re.sub(r"\btees?\b", " t shirt ", text)
    return [_singular_token(token) for token in re.findall(r"[a-z0-9]+", text)]


def _singular_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _daily_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"turns": 0, "tokens": 0})
    for row in rows:
        day = str(row["created_at"])[:10]
        daily[day]["turns"] += 1
        daily[day]["tokens"] += _row_tokens(row)
    return [
        {"date": day, "turns": values["turns"], "tokens": values["tokens"]}
        for day, values in sorted(daily.items())
    ]


def _average_latency(rows: list[dict[str, Any]]) -> int:
    values = [float(row["latency_ms"] or 0) for row in rows if float(row["latency_ms"] or 0) > 0]
    if not values:
        return 0
    return int(round(sum(values) / len(values)))


def _counter_rows(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"label": label, "count": count} for label, count in counter.most_common(limit)]


def _latency_bucket_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: Counter[str] = Counter()
    for row in rows:
        latency_ms = float(row.get("latency_ms") or 0)
        if latency_ms <= 0:
            buckets["No timing"] += 1
        elif latency_ms < LATENCY_FAST_MS:
            buckets["Under 1s"] += 1
        elif latency_ms <= LATENCY_ACCEPTABLE_MS:
            buckets["1s to 3s"] += 1
        else:
            buckets["Over 3s"] += 1
    ordered_labels = ["Under 1s", "1s to 3s", "Over 3s", "No timing"]
    return [{"label": label, "count": buckets[label]} for label in ordered_labels if buckets[label]]


def _peak_series_day(series: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not series:
        return None
    return max(series, key=lambda row: int(row.get("turns") or 0))


def _percent(value: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(round((value / total) * PERCENT_SCALE))


def _heuristic_summary(
    rows: list[dict[str, Any]],
    intents: Counter[str],
    products: Counter[str],
) -> str:
    if not rows:
        return "\n".join(
            [
                "- No customer conversations are logged for this range yet.",
                "- Keep collecting voice turns before making stock or merchandising decisions.",
            ]
        )
    top_intent = intents.most_common(1)[0][0] if intents else "unknown"
    top_products = [label for label, _count in products.most_common(5)]
    bullets = [
        f"- Customers completed {len(rows)} voice turns in this range; the main intent is {top_intent}.",
        _demand_summary_bullet(top_products),
        _stock_summary_bullet(intents, top_products),
        _latency_summary_bullet(rows),
    ]
    return "\n".join(bullets)


def _demand_summary_bullet(top_products: list[str]) -> str:
    if not top_products:
        return "- No clear product demand signal is visible yet; collect more conversations before changing stock."
    return f"- Customers are showing interest in {', '.join(top_products[:3])}."


def _stock_summary_bullet(intents: Counter[str], top_products: list[str]) -> str:
    out_of_stock_count = intents.get("out_of_stock", 0)
    if out_of_stock_count and top_products:
        return f"- Stock check: review availability for {', '.join(top_products[:3])}; out-of-stock came up {out_of_stock_count} time(s)."
    if top_products:
        return f"- Merchandising action: keep {top_products[0]} visible in search, recommendations, and featured sections."
    return "- Stock action: wait for stronger product-level demand before increasing inventory."


def _latency_summary_bullet(rows: list[dict[str, Any]]) -> str:
    latency_ms = _average_latency(rows)
    if latency_ms <= 0:
        return "- Operations action: no latency trend is available yet."
    if latency_ms > 3000:
        return f"- Operations action: average latency is {latency_ms} ms, so response speed should be improved."
    return f"- Operations action: average latency is {latency_ms} ms, which is acceptable for this range."


def json_ready_analytics(snapshot: dict[str, Any]) -> str:
    payload = {
        "range": snapshot["range"],
        "metrics": snapshot["metrics"],
        "top_intents": snapshot["top_intents"],
        "top_products": snapshot["top_products"],
        "series": snapshot["series"][-14:],
    }
    return json.dumps(payload, ensure_ascii=True)


def _clean_summary_bullets(summary: str) -> str:
    lines = [_clean_summary_line(line) for line in str(summary or "").splitlines()]
    bullets = [line for line in lines if line]
    if not bullets:
        return "- No actionable analytics summary was generated."
    return "\n".join(f"- {line}" for line in bullets[:SUMMARY_MAX_BULLETS])


def _clean_summary_line(line: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", str(line or "").strip())
    text = text.replace("**", "").strip()
    text = re.sub(r"^[-*]\s+", "", text)
    text = re.sub(r"^\d+[\.)]\s+", "", text)
    if not text or text.lower().startswith("key metrics"):
        return ""
    return text


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


def _setting_value(key: str) -> tuple[str, str]:
    env_value = os.getenv(key)
    if env_value is not None and str(env_value).strip():
        return str(env_value), "env"
    fallback = _setting_runtime_default(key)
    if fallback:
        return fallback, "runtime default"
    return "", "empty"


def _setting_runtime_default(key: str) -> str:
    direct_value = getattr(config, key, None)
    if direct_value is not None:
        return _setting_text(direct_value)
    aliases = {
        "AI_DEFAULT_SITE_ID": config.DEFAULT_SITE_ID,
        "CLIENT_STORE_URL": config.CURRENT_URL,
        "FAST_TTS_MODEL": config.TTS_MODEL,
        "HUB_PUBLIC_URL": _public_hub_origin(),
    }
    if key in aliases:
        return _setting_text(aliases[key])
    return ""


def _setting_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value or "").strip()


def _setting_is_configured(key: str) -> bool:
    return bool(str(os.getenv(key, "")).strip())


def _validated_settings(values: dict[str, str]) -> dict[str, str]:
    clean_values: dict[str, str] = {}
    for key, value in values.items():
        if key not in SETTING_KEYS:
            raise ValueError(f"Setting {key} is not editable from CRM.")
        text_value = str(value or "").strip()
        if key in SECRET_SETTING_KEYS and not text_value:
            continue
        if text_value:
            _validate_numeric_setting(key, text_value)
        clean_values[key] = text_value
    return clean_values


def _validate_numeric_setting(key: str, value: str) -> None:
    if key in FLOAT_SETTING_RANGES:
        _validate_float_range(key, value, FLOAT_SETTING_RANGES[key])
    if key in INTEGER_SETTING_RANGES:
        _validate_integer_range(key, value, INTEGER_SETTING_RANGES[key])


def _validate_float_range(key: str, value: str, valid_range: tuple[float, float]) -> None:
    try:
        numeric_value = float(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be numeric.") from exc
    low, high = valid_range
    if numeric_value < low or numeric_value > high:
        raise ValueError(f"{key} must be between {low:g} and {high:g}.")


def _validate_integer_range(key: str, value: str, valid_range: tuple[int, int]) -> None:
    try:
        numeric_value = int(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be a whole number.") from exc
    low, high = valid_range
    if numeric_value < low or numeric_value > high:
        raise ValueError(f"{key} must be between {low} and {high}.")


def _masked_value(value: str) -> str:
    clean_value = str(value or "")
    if not clean_value:
        return ""
    if len(clean_value) <= 8:
        return "********"
    return f"{clean_value[:4]}...{clean_value[-4:]}"


def _public_hub_origin() -> str:
    origin = _first_text(
        os.getenv("PUBLIC_API_URL", ""),
        os.getenv("PUBLIC_STOREFRONT_ORIGIN", ""),
        os.getenv("VOICE_ORB_API_URL", ""),
        config.PUBLIC_API_URL,
        f"http://127.0.0.1:{config.PORT}",
    )
    return origin.rstrip("/")


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


def _first_text(*values: str) -> str:
    for value in values:
        clean_value = str(value or "").strip()
        if clean_value:
            return clean_value
    return ""


def _set_default_panel_password(site_id: str) -> str:
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


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _connect() -> psycopg.Connection:
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, connect_timeout=3)


# ── Readiness Scanner Persistence ───────────────────────────────────────────


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


# ── Crawl Report Persistence ────────────────────────────────────────────────


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


# ── Site Selectors Persistence (LLM Extractor) ──────────────────────────────


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
