"""WebSocket transport for the voice sales loop.

The stable HTTP endpoint remains the source of truth. This module wraps the
existing orchestrator stream in a non-blocking WebSocket session so the browser
can keep one connection open across multiple turns.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
import psycopg

from agent import orchestrator
from agent.page_context import sanitize_page_context
from api.action_truth import annotate_ui_actions, new_action_turn_id
from api.turn_logging import print_turn_summary, turn_timer
from db import admin as admin_db
from db.session_memory import get_session_summary, update_session_summary
import config

logger = logging.getLogger(__name__)

DEFAULT_AUDIO_FILENAME = "audio.webm"
MAX_HISTORY_TURNS = 12
WS_TYPE_READY = "ready"
WS_TYPE_CONFIGURED = "configured"
WS_TYPE_CONFIG = "config"
WS_TYPE_AUDIO_CHUNK = "audio_chunk"
WS_TYPE_AUDIO_END = "audio_end"
WS_TYPE_TEXT = "text"
WS_TYPE_ERROR = "error"
WS_TYPE_TRANSCRIPT = "transcript"
WS_TYPE_ACTIONS = "actions"
WS_TYPE_RESPONSE = "response"
WS_TYPE_METRICS = "metrics"
WS_TYPE_DONE = "done"
WS_TYPE_TEXT_CHUNK = "text_chunk"
ORCHESTRATOR_EVENT_AUDIO = "audio"
WS_STATUS_OK = "ok"
WS_STATUS_ERROR = "error"
ERROR_INVALID_JSON_FRAME = "Invalid JSON frame"
ERROR_FRAME_NOT_OBJECT = "Frame must be an object"
ERROR_NO_AUDIO_OR_TEXT = "No audio or text received."
PIPELINE_ERROR_MESSAGE = "Pipeline error"
RECOVERABLE_WS_ERRORS = (RuntimeError, ValueError, TypeError, OSError)


class WebSocketShopSession:
    """One persistent WebSocket conversation for one tenant site."""

    def __init__(self, websocket: WebSocket, site_id: str, session_id: str = ""):
        self.websocket = websocket
        self.site_id = _safe_site_id(site_id)
        self.session_id = _safe_session_id(session_id, self.site_id)
        self.history: list[dict[str, str]] = []
        self.audio_chunks: list[bytes] = []
        self.audio_mime_type = ""
        self.page_context: dict[str, Any] = {}

    async def run(self) -> None:
        await self.websocket.accept()
        await self.send({"type": WS_TYPE_READY, "site_id": self.site_id})

        try:
            while True:
                payload = await self.receive_payload()
                message_type = payload.get("type")

                if message_type == WS_TYPE_ERROR:
                    await self.send({"type": WS_TYPE_ERROR, "message": payload["message"]})
                    continue

                if message_type == WS_TYPE_CONFIG:
                    self.history = _sanitize_history(payload.get("history", []))
                    self.page_context = sanitize_page_context(payload.get("page_context"))
                    if payload.get("session_id"):
                        self.session_id = _safe_session_id(str(payload.get("session_id")), self.site_id)
                    await self.send({"type": WS_TYPE_CONFIGURED, "history_size": len(self.history)})
                    continue

                if message_type == WS_TYPE_AUDIO_CHUNK:
                    self.audio_mime_type = _safe_audio_mime_type(payload.get("mime_type")) or self.audio_mime_type
                    self.audio_chunks.append(_decode_audio_chunk(payload))
                    continue

                if message_type == WS_TYPE_AUDIO_END:
                    self.audio_mime_type = _safe_audio_mime_type(payload.get("mime_type")) or self.audio_mime_type
                    audio = b"".join(self.audio_chunks)
                    audio_filename = _audio_filename_for_mime(self.audio_mime_type)
                    self.audio_chunks = []
                    self.audio_mime_type = ""
                    await self.process_turn(audio_bytes=audio or None, audio_filename=audio_filename)
                    continue

                if message_type == WS_TYPE_TEXT:
                    await self.process_turn(text_input=str(payload.get("text") or ""))
                    continue

                await self.send({"type": WS_TYPE_ERROR, "message": f"Unsupported message type: {message_type}"})
        except WebSocketDisconnect:
            logger.info("WS_SHOP | disconnected site=%s", self.site_id)
        except RECOVERABLE_WS_ERRORS as exc:
            logger.exception("WS_SHOP | fatal error")
            try:
                await self.send({"type": WS_TYPE_ERROR, "message": str(exc)})
                await self.websocket.close()
            except RuntimeError as close_error:
                logger.warning("WS_SHOP | failed to close websocket cleanly: %s", close_error)

    async def receive_payload(self) -> dict[str, Any]:
        raw = await self.websocket.receive_text()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"type": WS_TYPE_ERROR, "message": ERROR_INVALID_JSON_FRAME}
        if not isinstance(payload, dict):
            return {"type": WS_TYPE_ERROR, "message": ERROR_FRAME_NOT_OBJECT}
        return payload

    async def process_turn(
        self,
        *,
        audio_bytes: bytes | None = None,
        text_input: str | None = None,
        audio_filename: str = DEFAULT_AUDIO_FILENAME,
    ) -> None:
        if not audio_bytes and not (text_input or "").strip():
            await self.send({"type": WS_TYPE_ERROR, "message": ERROR_NO_AUDIO_OR_TEXT})
            return
        try:
            admin_db.assert_usage_allowed(self.site_id, self.session_id)
        except admin_db.TokenQuotaExceededError as exc:
            await self.send({"type": WS_TYPE_ERROR, "message": str(exc)})
            return

        started_at = turn_timer()
        action_turn_id = new_action_turn_id()
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def worker() -> None:
            try:
                session_summary = get_session_summary(self.site_id, self.session_id)
                for event in orchestrator.run_stream(
                    site_id=self.site_id,
                    audio_bytes=audio_bytes,
                    text_input=text_input,
                    audio_filename=audio_filename,
                    skip_tts=False,
                    conversation_history=self.history,
                    page_context=self.page_context,
                    session_summary=session_summary,
                ):
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()
            except RECOVERABLE_WS_ERRORS as exc:  # pragma: no cover - defensive bridge
                logger.exception("WS_SHOP | pipeline failed")
                asyncio.run_coroutine_threadsafe(
                    queue.put({"event": WS_TYPE_ERROR, "data": {"error": str(exc)}}), loop
                ).result()
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

        worker_task = loop.run_in_executor(None, worker)
        transcript = ""
        response_text = ""
        ui_actions: list[dict[str, Any]] = []
        latency_ms: dict[str, Any] = {}
        status = WS_STATUS_OK
        error_message = ""
        response_sent = False

        while True:
            event = await queue.get()
            if event is None:
                break

            event_name = event.get("event")
            data = event.get("data") or {}

            if event_name == WS_TYPE_TRANSCRIPT:
                transcript = str(data.get("transcript") or "")
                await self.send({"type": WS_TYPE_TRANSCRIPT, "text": transcript})
                continue

            if event_name == WS_TYPE_ACTIONS:
                ui_actions = annotate_ui_actions(data.get("ui_actions"), turn_id=action_turn_id)
                continue

            if event_name == WS_TYPE_RESPONSE:
                response_text = str(data.get("response_text") or response_text)
                if response_text:
                    response_sent = True
                    await self.send({"type": WS_TYPE_TEXT_CHUNK, "text": response_text})
                continue

            if event_name == ORCHESTRATOR_EVENT_AUDIO:
                response_text = str(data.get("response_text") or response_text)
                latency_ms = data.get("latency_ms") or latency_ms
                if response_text and not response_sent:
                    response_sent = True
                    await self.send({"type": WS_TYPE_TEXT_CHUNK, "text": response_text})
                if data.get("audio_b64"):
                    await self.send({"type": WS_TYPE_AUDIO_CHUNK, "audio_b64": data["audio_b64"]})
                continue

            if event_name == WS_TYPE_METRICS:
                latency_ms = data.get("latency_ms") or latency_ms
                continue

            if event_name == WS_TYPE_ERROR:
                status = WS_STATUS_ERROR
                error_message = str(data.get("error") or PIPELINE_ERROR_MESSAGE)
                await self.send({"type": WS_TYPE_ERROR, "message": error_message})

        await worker_task
        self.update_history(transcript, response_text)
        await self.send(
            {
                "type": WS_TYPE_DONE,
                "response_text": response_text,
                "ui_actions": ui_actions,
                "history": self.history,
                "latency_ms": latency_ms,
            }
        )
        print_turn_summary(
            transport="websocket",
            site_id=self.site_id,
            started_at=started_at,
            transcript=transcript or (text_input or ""),
            response_text=response_text or error_message,
            ui_actions=ui_actions,
            latency_ms=latency_ms,
            status=status,
        )
        self.record_usage(transcript, response_text or error_message, ui_actions, latency_ms, status)
        update_session_summary(
            self.site_id,
            self.session_id,
            history=self.history,
            transcript=transcript or (text_input or ""),
            response_text=response_text or error_message,
        )

    def update_history(self, transcript: str, response_text: str) -> None:
        if transcript:
            self.history.append({"role": "user", "content": transcript[: config.MAX_TRANSCRIPT_CHARS]})
        if response_text:
            self.history.append({"role": "assistant", "content": response_text[: config.MAX_RESPONSE_CHARS]})
        self.history = self.history[-MAX_HISTORY_TURNS:]

    async def send(self, payload: dict[str, Any]) -> None:
        await self.websocket.send_json(payload)

    def record_usage(
        self,
        transcript: str,
        response_text: str,
        ui_actions: list[dict[str, Any]],
        latency_ms: dict[str, Any],
        status: str,
    ) -> None:
        try:
            admin_db.record_usage_event(
                site_id=self.site_id,
                session_id=self.session_id,
                transport="websocket",
                status=status,
                transcript=transcript,
                response_text=response_text,
                intent="",
                action_count=len(ui_actions),
                latency_ms=_total_latency_ms(latency_ms),
            )
        except psycopg.Error as exc:
            logger.warning("CRM usage logging failed: %s", exc)


async def ws_shop_handler(websocket: WebSocket, site_id: str, session_id: str = "") -> None:
    """Handle one hub-spoke voice sales WebSocket session."""

    await WebSocketShopSession(websocket, site_id, session_id).run()


def _decode_audio_chunk(payload: dict[str, Any]) -> bytes:
    data = str(payload.get("data") or payload.get("audio_b64") or "")
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return b""


def _safe_audio_mime_type(value: Any) -> str:
    text = str(value or "").lower().strip()
    if not text.startswith("audio/"):
        return ""
    return text[:80]


def _audio_filename_for_mime(mime_type: str) -> str:
    text = _safe_audio_mime_type(mime_type)
    if "mp4" in text or "mpeg" in text:
        return "audio.mp4"
    if "ogg" in text:
        return "audio.ogg"
    if "wav" in text:
        return "audio.wav"
    return DEFAULT_AUDIO_FILENAME


def _sanitize_history(raw_history: Any) -> list[dict[str, str]]:
    if not isinstance(raw_history, list):
        return []

    history: list[dict[str, str]] = []
    for item in raw_history[-MAX_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if content:
            history.append({"role": role, "content": content[: config.MAX_TRANSCRIPT_CHARS]})
    return history


def _safe_site_id(raw: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in (raw or "").strip().lower())[:80] or config.DEFAULT_SITE_ID


def _safe_session_id(raw: str, site_id: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in (raw or "").strip())
    text = text.strip("_")
    return text[:120] or f"{site_id}_server"


def _total_latency_ms(latency_ms: dict[str, Any]) -> float:
    raw_value = latency_ms.get("total_ms") if isinstance(latency_ms, dict) else 0
    try:
        return float(raw_value or 0)
    except (TypeError, ValueError):
        return 0.0
