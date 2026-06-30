"""Database admin schema and connection management."""

from __future__ import annotations

import threading

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
    plan TEXT NOT NULL DEFAULT 'Generic AI plan',
    vertical_key TEXT NOT NULL DEFAULT 'generic',
    vertical_config_json TEXT NOT NULL DEFAULT '{}',
    risk_level TEXT NOT NULL DEFAULT 'low',
    locale TEXT NOT NULL DEFAULT 'en-IN',
    prompt_profile_id TEXT NOT NULL DEFAULT '',
    compliance_mode TEXT NOT NULL DEFAULT 'standard',
    adapter_name TEXT NOT NULL DEFAULT 'generic_adapter.js',
    status TEXT NOT NULL DEFAULT 'live',
    token_limit INTEGER NOT NULL DEFAULT 5000,
    session_token_limit INTEGER NOT NULL DEFAULT 1000,
    panel_password_hash TEXT NOT NULL DEFAULT '',
    last_crawl_status TEXT NOT NULL DEFAULT 'not_started',
    last_crawl_message TEXT NOT NULL DEFAULT '',
    last_crawl_at TIMESTAMPTZ,
    last_setup_at TIMESTAMPTZ,
    needs_setup BOOLEAN NOT NULL DEFAULT true,
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

CREATE TABLE IF NOT EXISTS hub_provider_events (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hub_provider_events_created
    ON hub_provider_events(created_at DESC);

CREATE TABLE IF NOT EXISTS hub_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    is_secret BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hub_prompt_profiles (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    vertical_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_by TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hub_prompt_versions (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    system_prompt TEXT NOT NULL,
    developer_rules TEXT NOT NULL DEFAULT '',
    response_schema_json TEXT NOT NULL DEFAULT '{}',
    variables_json TEXT NOT NULL DEFAULT '{}',
    allowed_actions_json TEXT NOT NULL DEFAULT '[]',
    changelog TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    UNIQUE (profile_id, version)
);

CREATE TABLE IF NOT EXISTS hub_prompt_test_cases (
    id TEXT PRIMARY KEY,
    vertical_key TEXT NOT NULL,
    name TEXT NOT NULL,
    user_message TEXT NOT NULL,
    expected_intent TEXT NOT NULL DEFAULT '',
    expected_actions_json TEXT NOT NULL DEFAULT '[]',
    forbidden_terms_json TEXT NOT NULL DEFAULT '[]',
    required_terms_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hub_prompt_eval_runs (
    id TEXT PRIMARY KEY,
    prompt_version_id TEXT NOT NULL,
    status TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS token_limit INTEGER NOT NULL DEFAULT 5000;
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS session_token_limit INTEGER NOT NULL DEFAULT 1000;
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS panel_password_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS vertical_key TEXT NOT NULL DEFAULT 'generic';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS vertical_config_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS risk_level TEXT NOT NULL DEFAULT 'low';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS locale TEXT NOT NULL DEFAULT 'en-IN';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS prompt_profile_id TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS compliance_mode TEXT NOT NULL DEFAULT 'standard';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS last_crawl_status TEXT NOT NULL DEFAULT 'not_started';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS last_crawl_message TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS last_crawl_at TIMESTAMPTZ;
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS last_setup_at TIMESTAMPTZ;
ALTER TABLE hub_clients
    ADD COLUMN IF NOT EXISTS needs_setup BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE hub_usage_events
    ADD COLUMN IF NOT EXISTS session_id TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_usage_events
    ADD COLUMN IF NOT EXISTS transcript TEXT NOT NULL DEFAULT '';
ALTER TABLE hub_usage_events
    ADD COLUMN IF NOT EXISTS response_text TEXT NOT NULL DEFAULT '';

ALTER TABLE hub_prompt_profiles
    ADD COLUMN IF NOT EXISTS site_id TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_hub_prompt_profiles_site
    ON hub_prompt_profiles(site_id, vertical_key);
CREATE INDEX IF NOT EXISTS idx_hub_prompt_versions_profile
    ON hub_prompt_versions(profile_id, created_at DESC);

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

_admin_schema_lock = threading.Lock()
_admin_schema_initialized = False


def _connect() -> psycopg.Connection:
    """Create a new database connection with dictionary rows."""
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, connect_timeout=3)


def init_admin_schema() -> None:
    """Create CRM-owned public tables if they do not already exist."""
    global _admin_schema_initialized
    if _admin_schema_initialized:
        return

    with _admin_schema_lock:
        if _admin_schema_initialized:
            return
        with _connect() as conn:
            conn.execute(ADMIN_SCHEMA_SQL)
            conn.commit()
        _admin_schema_initialized = True
