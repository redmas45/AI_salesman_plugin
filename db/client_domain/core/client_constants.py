"""Shared client facade constants and default helpers."""

from __future__ import annotations

import os

from agent.verticals.registry import DEFAULT_VERTICAL_KEY as DEFAULT_CLIENT_VERTICAL_KEY

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
SITE_ID_MAX_LENGTH = 80
SESSION_ID_MAX_LENGTH = 120
DEFAULT_USAGE_LIMIT = 200
ACTION_EVENT_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "blocked", "skipped", "error"})
SYNTHETIC_DEMO_URL_PATTERN = r"^https?://([^/]+\.)?example\.(com|test|org)(/|$)"


def default_client_vertical_key(site_id: str) -> str:
    return DEFAULT_CLIENT_VERTICAL_KEY


def default_client_adapter_name(site_id: str) -> str:
    return DEFAULT_ADAPTER_NAME


def default_client_name(site_id: str) -> str:
    return site_id.replace("_", " ").replace("-", " ").title()
