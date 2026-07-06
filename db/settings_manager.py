"""Settings management for AI Hub CRM runtime configurations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import set_key

import config
from db.schema import _connect, init_admin_schema

ENV_FILE = Path(config.BASE_DIR) / ".env"

SETTING_KEYS = {
    "ACTION_AUTO_APPROVE_CONFIDENCE",
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
    "OPENAI_ADMIN_KEY",
    "OPENAI_API_KEY",
    "OPENAI_MONTHLY_BUDGET_USD",
    "OPENAI_USAGE_REFRESH_SECONDS",
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
    "TTS_CHUNK_CHARS",
    "TTS_MAX_INPUT_CHARS",
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
    "OPENAI_ADMIN_KEY",
    "OPENAI_API_KEY",
}

FLOAT_SETTING_RANGES = {
    "ACTION_AUTO_APPROVE_CONFIDENCE": (0.0, 1.0),
    "LLM_TEMPERATURE": (0.0, 2.0),
    "OPENAI_MONTHLY_BUDGET_USD": (0.0, 1_000_000_000.0),
}

INTEGER_SETTING_RANGES = {
    "BACKEND_PORT": (1, 65535),
    "CRAWL_MAX_DEPTH": (0, 20),
    "CRAWL_MAX_PAGES": (1, 10000),
    "HTTPS_PORT": (1, 65535),
    "LLM_MAX_TOKENS": (1, 200000),
    "LLM_MAX_TOKENS_HARD_CAP": (1, 500000),
    "OPENAI_USAGE_REFRESH_SECONDS": (60, 86400),
    "PORT": (1, 65535),
    "RAG_TOP_K": (1, 100),
    "RAG_TOP_N": (1, 100),
    "STOREFRONT_PORT": (1, 65535),
    "TTS_CHUNK_CHARS": (300, 4000),
    "TTS_MAX_INPUT_CHARS": (2000, 50000),
}


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


def _first_text(*values: str) -> str:
    for value in values:
        clean_value = str(value or "").strip()
        if clean_value:
            return clean_value
    return ""
