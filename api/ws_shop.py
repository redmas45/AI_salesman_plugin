"""WebSocket transport for the voice shopping loop.

The stable HTTP endpoint remains the source of truth. This module wraps the
existing orchestrator stream in a non-blocking WebSocket session so the browser
can keep one connection open across multiple turns.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from agent import orchestrator
from api.turn_logging import print_turn_summary, turn_timer
import config

logger = logging.getLogger(__name__)


class WebSocketShopSession:
    """One persistent WebSocket conversation for one tenant site."""

    def __init__(self, websocket: WebSocket, site_id: str):
        self.websocket = websocket
        self.site_id = _safe_site_id(site_id)
        self.history: list[dict[str, str]] = []
        self.audio_chunks: list[bytes] = []

    async def run(self) -> None:
        await self.websocket.accept()
        await self.send({"type": "ready", "site_id": self.site_id})

        try:
            while True:
                payload = await self.receive_payload()
                message_type = payload.get("type")

                if message_type == "config":
                    self.history = _sanitize_history(payload.get("history", []))
                    await self.send({"type": "configured", "history_size": len(self.history)})
                    continue

                if message_type == "audio_chunk":
                    self.audio_chunks.append(_decode_audio_chunk(payload))
                    continue

                if message_type == "audio_end":
                    audio = b"".join(self.audio_chunks)
                    self.audio_chunks = []
                    await self.process_turn(audio_bytes=audio or None)
                    continue

                if message_type == "text":
                    await self.process_turn(text_input=str(payload.get("text") or ""))
                    continue

                await self.send({"type": "error", "message": f"Unsupported message type: {message_type}"})
        except WebSocketDisconnect:
            logger.info("WS_SHOP | disconnected site=%s", self.site_id)
        except Exception as exc:
            logger.exception("WS_SHOP | fatal error")
            try:
                await self.send({"type": "error", "message": str(exc)})
                await self.websocket.close()
            except Exception:
                pass

    async def receive_payload(self) -> dict[str, Any]:
        raw = await self.websocket.receive_text()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"type": "error", "message": "Invalid JSON frame"}
        return payload if isinstance(payload, dict) else {"type": "error", "message": "Frame must be an object"}

    async def process_turn(
        self,
        *,
        audio_bytes: bytes | None = None,
        text_input: str | None = None,
    ) -> None:
        if not audio_bytes and not (text_input or "").strip():
            await self.send({"type": "error", "message": "No audio or text received."})
            return

        started_at = turn_timer()
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def worker() -> None:
            try:
                for event in orchestrator.run_stream(
                    site_id=self.site_id,
                    audio_bytes=audio_bytes,
                    text_input=text_input,
                    audio_filename="audio.webm",
                    skip_tts=False,
                    conversation_history=self.history,
                ):
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()
            except Exception as exc:  # pragma: no cover - defensive bridge
                logger.exception("WS_SHOP | pipeline failed")
                asyncio.run_coroutine_threadsafe(
                    queue.put({"event": "error", "data": {"error": str(exc)}}), loop
                ).result()
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

        worker_task = loop.run_in_executor(None, worker)
        transcript = ""
        response_text = ""
        ui_actions: list[dict[str, Any]] = []
        status = "ok"
        error_message = ""

        while True:
            event = await queue.get()
            if event is None:
                break

            event_name = event.get("event")
            data = event.get("data") or {}

            if event_name == "transcript":
                transcript = str(data.get("transcript") or "")
                await self.send({"type": "transcript", "text": transcript})
                continue

            if event_name == "actions":
                ui_actions = data.get("ui_actions") or []
                continue

            if event_name == "audio":
                response_text = str(data.get("response_text") or "")
                if response_text:
                    await self.send({"type": "text_chunk", "text": response_text})
                if data.get("audio_b64"):
                    await self.send({"type": "audio_chunk", "audio_b64": data["audio_b64"]})
                continue

            if event_name == "error":
                status = "error"
                error_message = str(data.get("error") or "Pipeline error")
                await self.send({"type": "error", "message": error_message})

        await worker_task
        self.update_history(transcript, response_text)
        await self.send(
            {
                "type": "done",
                "response_text": response_text,
                "ui_actions": ui_actions,
                "history": self.history,
            }
        )
        print_turn_summary(
            transport="websocket",
            site_id=self.site_id,
            started_at=started_at,
            transcript=transcript or (text_input or ""),
            response_text=response_text or error_message,
            ui_actions=ui_actions,
            status=status,
        )

    def update_history(self, transcript: str, response_text: str) -> None:
        if transcript:
            self.history.append({"role": "user", "content": transcript[: config.MAX_TRANSCRIPT_CHARS]})
        if response_text:
            self.history.append({"role": "assistant", "content": response_text[: config.MAX_RESPONSE_CHARS]})
        self.history = self.history[-12:]

    async def send(self, payload: dict[str, Any]) -> None:
        await self.websocket.send_json(payload)


async def ws_shop_handler(websocket: WebSocket, site_id: str) -> None:
    """Handle one hub-spoke voice shopping WebSocket session."""

    await WebSocketShopSession(websocket, site_id).run()


def _decode_audio_chunk(payload: dict[str, Any]) -> bytes:
    data = str(payload.get("data") or payload.get("audio_b64") or "")
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data)
    except Exception:
        return b""


def _sanitize_history(raw_history: Any) -> list[dict[str, str]]:
    if not isinstance(raw_history, list):
        return []

    history: list[dict[str, str]] = []
    for item in raw_history[-12:]:
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
