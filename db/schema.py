"""Database admin schema and connection management."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

import config

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


def _connect() -> psycopg.Connection:
    """Create a new database connection with dictionary rows."""
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, connect_timeout=3)


def init_admin_schema() -> None:
    """Create CRM-owned public tables if they do not already exist."""
    with _connect() as conn:
        conn.execute(ADMIN_SCHEMA_SQL)
        conn.commit()
