"""Runtime payload parsing, turn state, and usage logging helpers."""

from __future__ import annotations

import base64
import binascii
import json
import logging
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Optional, Protocol

import psycopg
from fastapi import HTTPException, UploadFile, status

import config
from agent.prompts.page_context import parse_page_context

DEFAULT_AUDIO_FILENAME = "audio.wav"
MAX_CONVERSATION_HISTORY_TURNS = 12
HTTP_UNPROCESSABLE_INPUT = status.HTTP_422_UNPROCESSABLE_CONTENT


class UsageRecorder(Protocol):
    TokenQuotaExceededError: type[Exception]

    def record_usage_event(self, **kwargs: Any) -> Any: ...

    def is_client_widget_enabled(self, site_id: str) -> bool: ...

    def assert_usage_allowed(self, site_id: str, session_id: str) -> Any: ...

    def _safe_site_id(self, site_id: str) -> str: ...


SessionSummaryUpdater = Callable[[str, str], Any]


@dataclass(frozen=True)
class ShoppingTurnPayload:
    audio_bytes: bytes | None
    audio_filename: str
    conversation_history: list[dict[str, str]]
    page_context: dict[str, Any]


@dataclass(frozen=True)
class TurnLogState:
    transcript: str = ""
    response_text: str = ""
    ui_actions: list[Any] = field(default_factory=list)
    latency_ms: dict[str, float] = field(default_factory=dict)
    status: str = "ok"


async def build_runtime_turn_payload(
    *,
    audio: UploadFile | None,
    text: str | None,
    conversation_history: str | None,
    page_context: str | None = None,
) -> ShoppingTurnPayload:
    if audio is None and not (text and text.strip()):
        raise HTTPException(
            status_code=HTTP_UNPROCESSABLE_INPUT,
            detail="Provide either an audio file or text input.",
        )

    if audio is None:
        return ShoppingTurnPayload(
            audio_bytes=None,
            audio_filename=DEFAULT_AUDIO_FILENAME,
            conversation_history=parse_conversation_history(conversation_history),
            page_context=parse_page_context(page_context),
        )

    audio_bytes = await audio.read(config.MAX_AUDIO_UPLOAD_BYTES + 1)
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )
    if len(audio_bytes) > config.MAX_AUDIO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Uploaded audio file is too large.",
        )

    return ShoppingTurnPayload(
        audio_bytes=audio_bytes,
        audio_filename=audio.filename or DEFAULT_AUDIO_FILENAME,
        conversation_history=parse_conversation_history(conversation_history),
        page_context=parse_page_context(page_context),
    )


def update_turn_log_state(state: TurnLogState, event: dict[str, Any]) -> TurnLogState:
    event_name = event.get("event")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}

    if event_name == "transcript":
        return replace(state, transcript=data.get("transcript") or state.transcript)
    if event_name == "response":
        return replace(state, response_text=data.get("response_text") or state.response_text)
    if event_name == "actions":
        return replace(state, ui_actions=data.get("ui_actions") or [])
    if event_name == "audio":
        return replace(
            state,
            response_text=data.get("response_text") or state.response_text,
            latency_ms=data.get("latency_ms") or state.latency_ms,
        )
    if event_name == "metrics":
        return replace(state, latency_ms=data.get("latency_ms") or state.latency_ms)
    if event_name == "error":
        return replace(
            state,
            response_text=data.get("error") or state.response_text,
            status="error",
        )
    return state


def record_usage_state(
    *,
    site_id: str,
    session_id: str,
    transport: str,
    state: TurnLogState,
    usage_recorder: UsageRecorder,
    logger: logging.Logger,
) -> None:
    record_usage_safely(
        site_id=site_id,
        session_id=session_id,
        transport=transport,
        status=state.status,
        transcript=state.transcript,
        response_text=state.response_text,
        intent="",
        action_count=len(state.ui_actions),
        latency_ms=total_latency_ms(state.latency_ms),
        usage_recorder=usage_recorder,
        logger=logger,
    )


def record_usage_result(
    *,
    site_id: str,
    session_id: str,
    transport: str,
    result: dict[str, Any],
    history: list[dict[str, str]] | None,
    usage_recorder: UsageRecorder,
    update_session_summary: Callable[..., Any],
    logger: logging.Logger,
) -> None:
    status_text = "error" if result.get("intent") == "error" else "ok"
    record_usage_safely(
        site_id=site_id,
        session_id=session_id,
        transport=transport,
        status=status_text,
        transcript=str(result.get("transcript") or ""),
        response_text=str(result.get("response_text") or ""),
        intent=str(result.get("intent") or ""),
        action_count=len(result.get("ui_actions") or []),
        latency_ms=total_latency_ms(result.get("latency_ms") or {}),
        usage_recorder=usage_recorder,
        logger=logger,
    )
    update_session_summary(
        site_id,
        session_id,
        history=history or [],
        transcript=str(result.get("transcript") or ""),
        response_text=str(result.get("response_text") or ""),
    )


def record_usage_safely(
    *,
    site_id: str,
    session_id: str,
    transport: str,
    status: str,
    transcript: str,
    response_text: str,
    intent: str,
    action_count: int,
    latency_ms: float,
    usage_recorder: UsageRecorder,
    logger: logging.Logger,
) -> None:
    try:
        usage_recorder.record_usage_event(
            site_id=site_id,
            session_id=session_id,
            transport=transport,
            status=status,
            transcript=transcript,
            response_text=response_text,
            intent=intent,
            action_count=action_count,
            latency_ms=latency_ms,
        )
    except psycopg.Error as exc:
        logger.warning("CRM usage logging failed: %s", exc)


def total_latency_ms(latency_ms: dict[str, Any]) -> float:
    raw_value = latency_ms.get("total_ms") if isinstance(latency_ms, dict) else 0
    try:
        return float(raw_value or 0)
    except (TypeError, ValueError):
        return 0.0


def decode_audio_b64(audio_b64: Any) -> bytes | None:
    if audio_b64 in (None, ""):
        return None
    if not isinstance(audio_b64, str):
        raise ValueError("audio_b64 must be a base64 string.")
    decoded = base64.b64decode(audio_b64, validate=True)
    if len(decoded) > config.MAX_AUDIO_UPLOAD_BYTES:
        raise ValueError("Decoded audio payload is too large.")
    return decoded


def coerce_websocket_payload(raw_data: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ValueError("WebSocket payload must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("WebSocket payload must be a JSON object.")
    return payload


def parse_conversation_history(raw_history: Optional[str]) -> list[dict[str, str]]:
    if not raw_history:
        return []

    try:
        decoded = json.loads(raw_history)
    except (json.JSONDecodeError, ValueError, TypeError):
        return []

    if not isinstance(decoded, list):
        return []

    clean_history: list[dict[str, str]] = []
    for item in decoded[-MAX_CONVERSATION_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue

        content = content.strip()
        if not content:
            continue

        clean_history.append(
            {
                "role": role,
                "content": content[: config.MAX_TRANSCRIPT_CHARS],
            }
        )

    return clean_history


def raise_if_client_disabled(site_id: str, usage_recorder: UsageRecorder, disabled_message: str) -> None:
    if usage_recorder.is_client_widget_enabled(site_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=disabled_message)


def runtime_site_id(site_id: str, usage_recorder: UsageRecorder) -> str:
    return usage_recorder._safe_site_id(site_id)


def raise_if_quota_exceeded(
    site_id: str,
    session_id: str,
    usage_recorder: UsageRecorder,
    quota_message: str,
) -> None:
    try:
        usage_recorder.assert_usage_allowed(site_id, session_id)
    except usage_recorder.TokenQuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc) or quota_message,
        ) from exc
