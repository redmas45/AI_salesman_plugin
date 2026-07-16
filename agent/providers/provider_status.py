"""Azure OpenAI health status and local usage monitoring for CRM."""

from __future__ import annotations

import io
import logging
import wave
from collections import deque
from datetime import datetime, timezone
from typing import Any

import config
from agent.providers.azure_openai import (
    AZURE_OPENAI_ERRORS,
    azure_openai_is_configured,
    create_chat_completion,
)
from db.core.schema import _connect, init_admin_schema
from db.runtime.quota import _usage_summary

logger = logging.getLogger(__name__)

RECENT_EVENT_LIMIT = 20
PROVIDER_NAME = "azure_openai"
PROVIDER_VERIFICATION_MAX_AGE_SECONDS = 15 * 60
_RECENT_EVENTS: deque[dict[str, Any]] = deque(maxlen=RECENT_EVENT_LIMIT)


def record_provider_failure(provider: str, exc: BaseException, *, category: str = "error") -> None:
    """Record a provider failure for the CRM health surface."""
    _record_provider_event(provider, category, _safe_error_message(exc))


def record_provider_success(provider: str) -> None:
    """Record provider recovery after a successful chat request."""
    latest = _recent_provider_events(1)
    if latest and latest[0].get("provider") == provider and latest[0].get("category") == "chat_ok":
        return
    _record_provider_event(provider, "chat_ok", "Azure OpenAI chat request completed successfully.")


def provider_usage_status() -> dict[str, Any]:
    """Return Azure deployment health and locally measured usage."""
    local_usage = _usage_summary()
    recent_events = _recent_provider_events()
    return {
        "status": _provider_status(recent_events),
        "provider": PROVIDER_NAME,
        "llm_model": config.AZURE_OPENAI_CHAT_DEPLOYMENT,
        "stt_model": config.AZURE_OPENAI_STT_DEPLOYMENT,
        "tts_model": config.AZURE_OPENAI_TTS_DEPLOYMENT,
        "azure_openai_api_key_configured": bool(config.AZURE_OPENAI_API_KEY),
        "local_tokens": {
            "estimated_total": local_usage["tokens_estimated"],
            "turns_total": local_usage["total_turns"],
            "turns_today": local_usage["turns_today"],
            "avg_latency_ms": local_usage["avg_latency_ms"],
        },
        "billing": {
            "status": "azure_portal",
            "message": "Azure billing is managed through Azure Cost Management.",
        },
        "recent_events": recent_events,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def check_azure_openai_runtime() -> dict[str, Any]:
    """Verify the configured Azure chat, STT, and TTS deployments."""
    if not azure_openai_is_configured():
        _record_provider_event(
            PROVIDER_NAME,
            "not_configured",
            "Azure OpenAI chat configuration is incomplete.",
        )
        return provider_usage_status()

    failures: list[tuple[str, BaseException]] = []
    try:
        create_chat_completion(
            [
                {"role": "system", "content": "Return only JSON."},
                {"role": "user", "content": '{"status":"ok"}'},
            ],
            max_completion_tokens=32,
            json_response=True,
        )
    except AZURE_OPENAI_ERRORS as exc:
        failures.append(("chat", exc))

    failures.extend(_audio_runtime_failures())
    if failures:
        category = _provider_error_category(failures[0][1])
        details = "; ".join(f"{component}: {_safe_error_message(exc)}" for component, exc in failures)
        _record_provider_event(
            PROVIDER_NAME,
            category if category != "error" else "runtime_error",
            f"Azure OpenAI runtime check failed: {details}",
        )
        return provider_usage_status()

    _record_provider_event(PROVIDER_NAME, "runtime_ok", "Azure OpenAI chat, STT, and TTS runtime checks passed.")
    return provider_usage_status()


def _audio_runtime_failures() -> list[tuple[str, BaseException]]:
    from agent.providers import stt, tts

    failures: list[tuple[str, BaseException]] = []
    try:
        stt.verify_runtime(_silent_wav())
    except AZURE_OPENAI_ERRORS as exc:
        failures.append(("stt", exc))
    try:
        tts.verify_runtime()
    except AZURE_OPENAI_ERRORS as exc:
        failures.append(("tts", exc))
    return failures


def _silent_wav() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16_000)
        wav_file.writeframes(b"\x00\x00" * 4_000)
    return output.getvalue()


def _record_provider_event(provider: str, category: str, message: str) -> None:
    event = {
        "provider": provider,
        "category": category,
        "message": message,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    _RECENT_EVENTS.appendleft(event)
    try:
        init_admin_schema()
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO hub_provider_events (provider, category, message)
                VALUES (%s, %s, %s)
                """,
                (provider[:80], category[:80], event["message"]),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("Provider event persistence failed: %s", exc)


def _provider_status(recent_events: list[dict[str, Any]]) -> str:
    if not azure_openai_is_configured():
        return "not_configured"
    runtime_categories = {
        "ok",
        "runtime_ok",
        "runtime_error",
        "quota_exhausted",
        "error",
        "auth_error",
        "invalid_key",
        "not_configured",
    }
    latest = next(
        (
            event
            for event in recent_events
            if event.get("provider") == PROVIDER_NAME
            and str(event.get("category") or "").lower() in runtime_categories
        ),
        None,
    )
    if not latest:
        return "unverified"
    category = str(latest.get("category") or "").lower()
    if category == "quota_exhausted":
        return "quota_exhausted"
    if category in {"error", "runtime_error", "auth_error", "invalid_key"}:
        return "error"
    if category not in {"ok", "runtime_ok"} or not _provider_event_is_fresh(latest):
        return "unverified"
    return "ok"


def _provider_event_is_fresh(event: dict[str, Any]) -> bool:
    raw_timestamp = str(event.get("occurred_at") or "").strip()
    if not raw_timestamp:
        return False
    try:
        occurred_at = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    age_seconds = (
        datetime.now(timezone.utc) - occurred_at.astimezone(timezone.utc)
    ).total_seconds()
    return 0 <= age_seconds <= PROVIDER_VERIFICATION_MAX_AGE_SECONDS


def _recent_provider_events(limit: int = RECENT_EVENT_LIMIT) -> list[dict[str, Any]]:
    try:
        init_admin_schema()
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT provider, category, message, created_at
                FROM hub_provider_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "provider": str(row.get("provider") or ""),
                "category": str(row.get("category") or ""),
                "message": str(row.get("message") or ""),
                "occurred_at": str(row.get("created_at") or ""),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("Provider event lookup failed: %s", exc)
        return list(_RECENT_EVENTS)


def _provider_error_category(exc: BaseException) -> str:
    text = _safe_error_message(exc).lower()
    if "quota" in text or "billing" in text or "insufficient_quota" in text:
        return "quota_exhausted"
    if "401" in text or "403" in text or "api key" in text or "authentication" in text:
        return "auth_error"
    return "error"


def _safe_error_message(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    return text[:500]
