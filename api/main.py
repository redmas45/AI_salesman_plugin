"""FastAPI application for the AI Hub runtime API."""

import asyncio
import base64
import binascii
import concurrent.futures
import functools
import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import psycopg
from starlette.exceptions import HTTPException as StarletteHTTPException

import config
from agent import orchestrator
from agent.page_context import parse_page_context
from api import client_panel as client_panel_api
from api import crm as crm_api
from api.middleware import RateLimitMiddleware, RequestTracingMiddleware, SecurityHeadersMiddleware
from api.routes import clients as clients_router
from api.routes import analytics as analytics_router
from api.routes import ecommerce as ecommerce_router
from api.routes import settings as settings_router
from api.turn_logging import print_turn_summary, turn_timer
from api.ws_shop import ws_shop_handler
from db import admin as admin_db

from api.models import (
    KnowledgeItemResponse,
    ShopResponse,
)

# Module-level logger — file handler is added inside lifespan() AFTER
# uvicorn has called its own logging.config.dictConfig(), so we don't
# conflict with its formatter configuration.
logger = logging.getLogger(__name__)
CLIENT_DISABLED_MESSAGE = "AI assistant is disabled for this client."
TOKEN_QUOTA_EXCEEDED_MESSAGE = "AI assistant token quota is exhausted for this client or session."

DEFAULT_AUDIO_FILENAME = "audio.wav"
CRAWLER_SOURCE_NAME = "custom_url_crawler"
CRAWLER_POLL_INTERVAL_SECONDS = 120
MAX_CONVERSATION_HISTORY_TURNS = 12
MAX_PUBLIC_KNOWLEDGE_IDS = 30
MAX_PUBLIC_KNOWLEDGE_ID_LENGTH = 180
MAX_PUBLIC_KNOWLEDGE_TEXT_CHARS = 1200
HTTP_UNPROCESSABLE_INPUT = status.HTTP_422_UNPROCESSABLE_CONTENT
CRM_SOURCE_DIR = Path(__file__).parent.parent / "crm"
CRM_STATIC_DIR = CRM_SOURCE_DIR / "dist"
CLIENT_PANEL_SOURCE_DIR = Path(
    os.getenv("CLIENT_PANEL_SOURCE_DIR", str(Path(__file__).parent.parent.parent / "client_panel"))
).expanduser()
CLIENT_PANEL_STATIC_DIR = Path(
    os.getenv("CLIENT_PANEL_STATIC_DIR", str(CLIENT_PANEL_SOURCE_DIR / "dist"))
).expanduser()


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


class SpaStaticFiles(NoCacheStaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND and "." not in Path(path).name:
                return await super().get_response("index.html", scope)
            raise


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


# Startup / Shutdown

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise database, seed data, and register pgvector on startup."""
    import sys
    print("\n" + "="*60, flush=True)
    print(" ⏳ INITIALIZING AI MODELS (May take 1-3 minutes on first boot)", flush=True)
    print("    Downloading/Loading embedding weights from HuggingFace...", flush=True)
    print("="*60 + "\n", flush=True)
    
    logger.info("Starting AI Hub Runtime API...")
    
    # Preload RAG embedder and index into memory
    from agent import rag
    rag.preload()
    if config.ENSURE_DEFAULT_CLIENT_ON_STARTUP:
        admin_db.ensure_default_client()
    else:
        admin_db.init_admin_schema()
        logger.info("Default client startup seed disabled; keeping existing client list unchanged.")

    async def run_crawl_once(target_url: str, site_id: str, *, initial: bool = False) -> None:
        from agent.ingestion import sync_web_crawl

        phase = "startup" if initial else "periodic"
        logger.info("Starting %s crawl for %s...", phase, target_url)
        try:
            loop = asyncio.get_running_loop()
            func = functools.partial(
                sync_web_crawl,
                target_url,
                max_pages=config.CRAWL_MAX_PAGES,
                max_depth=config.CRAWL_MAX_DEPTH,
                site_id=site_id,
                reconcile_missing=True,
                source_name=CRAWLER_SOURCE_NAME,
            )
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
                await loop.run_in_executor(executor, func)
            logger.info("%s crawl completed for %s.", phase.capitalize(), target_url)
        except (RuntimeError, OSError, ValueError) as exc:
            logger.error("%s crawl failed: %s", phase.capitalize(), exc)

    async def periodic_crawl() -> None:
        target_url = config.CURRENT_URL
        site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
        if target_url:
            while True:
                await asyncio.sleep(CRAWLER_POLL_INTERVAL_SECONDS)
                await run_crawl_once(target_url, site_id)

    startup_target_url = config.CURRENT_URL
    startup_site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if startup_target_url and config.CRAWL_ON_STARTUP:
        await run_crawl_once(startup_target_url, startup_site_id, initial=True)
    elif config.CRAWL_ON_STARTUP:
        logger.info("Startup crawl enabled but CURRENT_URL is empty; skipping crawl.")
    else:
        logger.info("Startup crawl disabled.")

    crawler_task = None
    if config.CRAWL_PERIODIC_ENABLED and config.CURRENT_URL:
        crawler_task = asyncio.create_task(periodic_crawl())
    elif config.CRAWL_PERIODIC_ENABLED:
        logger.info("Periodic crawl enabled but CURRENT_URL is empty; skipping crawler task.")
    else:
        logger.info("Periodic crawl disabled.")

    logger.info("Startup complete. API ready.")
    yield

    if crawler_task:
        crawler_task.cancel()
    logger.info("Shutting down AI Hub Runtime API.")



# App

app = FastAPI(
    title="AI Hub Runtime API",
    description="Voice-enabled AI assistant runtime for independently hosted client websites.",
    version="1.0.0",
    lifespan=lifespan,
)

# Build an explicit CORS allowlist; wildcard CORS is not used for credentialed routes.
def _origin_from_url(value: str) -> str:
    raw = str(value or "").strip().strip("\"'")
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _allowed_cors_origins() -> list[str]:
    configured = [origin.strip().strip("\"'") for origin in config.CORS_ORIGINS if origin.strip()]
    if configured and configured != ["*"]:
        return list(dict.fromkeys(configured))

    candidates = [
        config.PUBLIC_STOREFRONT_ORIGIN,
        config.CLIENT_STORE_URL,
        config.CURRENT_URL,
        config.HUB_PUBLIC_URL,
        config.PUBLIC_API_URL,
        config.VOICE_ORB_API_URL,
    ]
    if config.DEPLOYMENT_MODE in {"local", "dev", "development"}:
        candidates.extend(
            [
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:5176",
                "http://127.0.0.1:8585",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://localhost:5176",
                "http://localhost:8585",
            ]
        )

    return list(dict.fromkeys(origin for origin in (_origin_from_url(value) for value in candidates) if origin))


PUBLIC_WIDGET_CORS_PATHS = {
    "/install.js",
    "/shopbot.js",
    "/shopbot-widget.js",
    "/shopbot-adapter.js",
    "/shopbot-frame",
    "/v1/shop",
    "/v1/shop/stream",
    "/v1/ws/shop",
    "/ws/chat",
}


def _is_public_widget_cors_path(path: str) -> bool:
    clean_path = "/" + str(path or "").strip("/")
    return clean_path in PUBLIC_WIDGET_CORS_PATHS or clean_path.startswith("/v1/widget/")


def _public_widget_cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin", "")
    requested_headers = request.headers.get("access-control-request-headers", "Accept, Content-Type")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": requested_headers,
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-crm-admin-token"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTracingMiddleware)


@app.middleware("http")
async def public_widget_cors_middleware(request: Request, call_next):
    """Allow installed widgets on any website to reach public widget endpoints."""
    origin = request.headers.get("origin")
    if origin and _is_public_widget_cors_path(request.url.path):
        headers = _public_widget_cors_headers(request)
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=headers)
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        return response
    return await call_next(request)


app.include_router(crm_api.router)
app.include_router(client_panel_api.router)
app.include_router(clients_router.router)
app.include_router(analytics_router.router)
app.include_router(ecommerce_router.router)
app.include_router(settings_router.router)


@app.get("/crm", include_in_schema=False)
async def redirect_crm_root(request: Request) -> RedirectResponse:
    """Redirect the bare CRM path to the static app root."""
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    return RedirectResponse(url=f"{prefix}/crm/")


@app.get("/client-panel", include_in_schema=False)
async def redirect_client_panel_root(request: Request) -> RedirectResponse:
    """Redirect the bare client-panel path to the static app root."""
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    return RedirectResponse(url=f"{prefix}/client-panel/")


if CRM_STATIC_DIR.exists():
    app.mount(
        "/crm",
        SpaStaticFiles(directory=CRM_STATIC_DIR, html=True),
        name="crm",
    )


if CLIENT_PANEL_STATIC_DIR.exists():
    app.mount(
        "/client-panel",
        SpaStaticFiles(directory=CLIENT_PANEL_STATIC_DIR, html=True),
        name="client_panel",
    )


# Endpoints


async def _build_runtime_turn_payload(
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
            conversation_history=_parse_conversation_history(conversation_history),
            page_context=parse_page_context(page_context),
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )

    return ShoppingTurnPayload(
        audio_bytes=audio_bytes,
        audio_filename=audio.filename or DEFAULT_AUDIO_FILENAME,
        conversation_history=_parse_conversation_history(conversation_history),
        page_context=parse_page_context(page_context),
    )


def _update_turn_log_state(state: TurnLogState, event: dict[str, Any]) -> TurnLogState:
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


def _stream_shop_events(
    *,
    site_id: str,
    session_id: str,
    text: str | None,
    skip_tts: bool,
    payload: ShoppingTurnPayload,
) -> Iterator[str]:
    started_at = turn_timer()
    state = TurnLogState(transcript=text or "")
    try:
        for event in orchestrator.run_stream(
            site_id=site_id,
            audio_bytes=payload.audio_bytes,
            text_input=text,
            audio_filename=payload.audio_filename,
            skip_tts=skip_tts,
            conversation_history=payload.conversation_history,
            page_context=payload.page_context,
        ):
            state = _update_turn_log_state(state, event)
            yield f"data: {json.dumps(event)}\n\n"
    finally:
        _print_turn_state(
            transport="legacy-sse",
            site_id=site_id,
            session_id=session_id,
            started_at=started_at,
            state=state,
        )


def _print_turn_state(
    *,
    transport: str,
    site_id: str,
    session_id: str,
    started_at: float,
    state: TurnLogState,
) -> None:
    print_turn_summary(
        transport=transport,
        site_id=site_id,
        started_at=started_at,
        transcript=state.transcript,
        response_text=state.response_text,
        ui_actions=state.ui_actions,
        latency_ms=state.latency_ms,
        status=state.status,
    )
    _record_usage_state(
        site_id=site_id,
        session_id=session_id,
        transport=transport,
        state=state,
    )


def _record_usage_state(*, site_id: str, session_id: str, transport: str, state: TurnLogState) -> None:
    _record_usage_safely(
        site_id=site_id,
        session_id=session_id,
        transport=transport,
        status=state.status,
        transcript=state.transcript,
        response_text=state.response_text,
        intent="",
        action_count=len(state.ui_actions),
        latency_ms=_total_latency_ms(state.latency_ms),
    )


def _record_usage_result(*, site_id: str, session_id: str, transport: str, result: dict[str, Any]) -> None:
    status_text = "error" if result.get("intent") == "error" else "ok"
    _record_usage_safely(
        site_id=site_id,
        session_id=session_id,
        transport=transport,
        status=status_text,
        transcript=str(result.get("transcript") or ""),
        response_text=str(result.get("response_text") or ""),
        intent=str(result.get("intent") or ""),
        action_count=len(result.get("ui_actions") or []),
        latency_ms=_total_latency_ms(result.get("latency_ms") or {}),
    )


def _record_usage_safely(
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
) -> None:
    try:
        admin_db.record_usage_event(
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


def _total_latency_ms(latency_ms: dict[str, Any]) -> float:
    raw_value = latency_ms.get("total_ms") if isinstance(latency_ms, dict) else 0
    try:
        return float(raw_value or 0)
    except (TypeError, ValueError):
        return 0.0


def _decode_audio_b64(audio_b64: Any) -> bytes | None:
    if audio_b64 in (None, ""):
        return None
    if not isinstance(audio_b64, str):
        raise ValueError("audio_b64 must be a base64 string.")
    return base64.b64decode(audio_b64, validate=True)


def _coerce_websocket_payload(raw_data: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ValueError("WebSocket payload must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("WebSocket payload must be a JSON object.")
    return payload


def _raise_if_client_disabled(site_id: str) -> None:
    if admin_db.is_client_widget_enabled(site_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CLIENT_DISABLED_MESSAGE)


def _raise_if_quota_exceeded(site_id: str, session_id: str) -> None:
    try:
        admin_db.assert_usage_allowed(site_id, session_id)
    except admin_db.TokenQuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc) or TOKEN_QUOTA_EXCEEDED_MESSAGE,
        ) from exc


@app.post("/v1/shop", response_model=ShopResponse, tags=["AI Runtime"])
async def shop(
    site_id: str = Form(config.DEFAULT_SITE_ID, description="Site ID for multi-tenancy"),
    audio: Optional[UploadFile] = File(
        None, description="Audio file (WAV, MP3, WebM, OGG)"
    ),
    text: Optional[str] = Form(
        None, description="Text input (for testing without audio)"
    ),
    skip_tts: bool = Form(False, description="Skip TTS to reduce latency (testing)"),
    conversation_history: Optional[str] = Form(
        None, description="JSON array of prior conversation turns"
    ),
    page_context: Optional[str] = Form(
        None, description="JSON object with privacy-safe browser page context"
    ),
    session_id: str = Form("", description="Browser conversation session ID"),
) -> ShopResponse:
    """
    **Main endpoint.** Send customer audio or text and receive website actions plus a voice response.

    Returns:
    - `transcript`: what the customer said
    - `response_text`: assistant response text
    - `ui_actions`: list of website control commands for the injected runtime
    - `audio_b64`: base64-encoded WAV of the spoken response
    """
    _raise_if_client_disabled(site_id)
    _raise_if_quota_exceeded(site_id, session_id)
    payload = await _build_runtime_turn_payload(
        audio=audio,
        text=text,
        conversation_history=conversation_history,
        page_context=page_context,
    )

    started_at = turn_timer()
    result = orchestrator.run(
        site_id=site_id,
        audio_bytes=payload.audio_bytes,
        text_input=text,
        audio_filename=payload.audio_filename,
        skip_tts=skip_tts,
        conversation_history=payload.conversation_history,
        page_context=payload.page_context,
    )
    print_turn_summary(
        transport="legacy-http",
        site_id=site_id,
        started_at=started_at,
        transcript=result.get("transcript", ""),
        response_text=result.get("response_text", ""),
        ui_actions=result.get("ui_actions", []),
        latency_ms=result.get("latency_ms", {}),
    )
    _record_usage_result(site_id=site_id, session_id=session_id, transport="legacy-http", result=result)

    return ShopResponse(**result)


@app.post("/v1/shop/stream", tags=["AI Runtime"])
async def shop_stream(
    site_id: str = Form(config.DEFAULT_SITE_ID, description="Site ID for multi-tenancy"),
    audio: Optional[UploadFile] = File(
        None, description="Audio file (WAV, MP3, WebM, OGG)"
    ),
    text: Optional[str] = Form(
        None, description="Text input (for testing without audio)"
    ),
    skip_tts: bool = Form(False, description="Skip TTS to reduce latency (testing)"),
    conversation_history: Optional[str] = Form(
        None, description="JSON array of prior conversation turns"
    ),
    page_context: Optional[str] = Form(
        None, description="JSON object with privacy-safe browser page context"
    ),
    session_id: str = Form("", description="Browser conversation session ID"),
) -> StreamingResponse:
    """Stream transcript, response, UI action, metric, and audio events for one assistant turn."""
    _raise_if_client_disabled(site_id)
    _raise_if_quota_exceeded(site_id, session_id)
    payload = await _build_runtime_turn_payload(
        audio=audio,
        text=text,
        conversation_history=conversation_history,
        page_context=page_context,
    )

    return StreamingResponse(
        _stream_shop_events(
            site_id=site_id,
            session_id=session_id,
            text=text,
            skip_tts=skip_tts,
            payload=payload,
        ),
        media_type="text/event-stream",
    )


@app.websocket("/v1/ws/shop")
async def websocket_shop(
    websocket: WebSocket,
    site_id: str = config.DEFAULT_SITE_ID,
    session_id: str = "",
) -> None:
    """Persistent one-script voice transport for spoke websites."""
    if not admin_db.is_client_widget_enabled(site_id):
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": CLIENT_DISABLED_MESSAGE})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws_shop_handler(websocket, site_id, session_id)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """Bi-directional WebSocket for real-time voice assistant turns."""
    await websocket.accept()
    try:
        while True:
            try:
                payload = _coerce_websocket_payload(await websocket.receive_text())
            except ValueError as exc:
                await websocket.send_json({"event": "error", "data": {"error": str(exc)}})
                continue

            text_input = payload.get("text")
            try:
                audio_bytes = _decode_audio_b64(payload.get("audio_b64"))
            except (binascii.Error, ValueError) as exc:
                await websocket.send_json({"event": "error", "data": {"error": str(exc)}})
                continue

            raw_history = payload.get("conversation_history", [])
            parsed_history = _parse_conversation_history(json.dumps(raw_history))
            site_id = payload.get("site_id", config.DEFAULT_SITE_ID)
            session_id = str(payload.get("session_id") or "")
            if not admin_db.is_client_widget_enabled(site_id):
                await websocket.send_json({"event": "error", "data": {"error": CLIENT_DISABLED_MESSAGE}})
                continue
            try:
                admin_db.assert_usage_allowed(site_id, session_id)
            except admin_db.TokenQuotaExceededError as exc:
                await websocket.send_json({"event": "error", "data": {"error": str(exc)}})
                continue

            started_at = turn_timer()
            state = TurnLogState(transcript=text_input or "")
            for event in orchestrator.run_stream(
                site_id=site_id,
                audio_bytes=audio_bytes,
                text_input=text_input,
                audio_filename=DEFAULT_AUDIO_FILENAME,
                skip_tts=payload.get("skip_tts", False),
                conversation_history=parsed_history,
            ):
                state = _update_turn_log_state(state, event)
                await websocket.send_json(event)
            _print_turn_state(
                transport="legacy-ws",
                site_id=site_id,
                session_id=session_id,
                started_at=started_at,
                state=state,
            )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


def _parse_conversation_history(raw_history: Optional[str]) -> list[dict[str, str]]:
    """Parse and sanitise browser-provided chat history before LLM use."""
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


def _parse_public_knowledge_ids(raw_ids: str) -> list[str]:
    """Parse exact knowledge IDs for public widget lookups."""
    seen: set[str] = set()
    parsed_ids: list[str] = []
    for raw_id in str(raw_ids or "").split(","):
        item_id = raw_id.strip().strip('"')
        if not item_id or item_id in seen:
            continue
        if len(item_id) > MAX_PUBLIC_KNOWLEDGE_ID_LENGTH:
            continue
        seen.add(item_id)
        parsed_ids.append(item_id)
        if len(parsed_ids) >= MAX_PUBLIC_KNOWLEDGE_IDS:
            break
    return parsed_ids


def _short_public_text(value: Any) -> str:
    text = str(value or "").strip()
    return text[:MAX_PUBLIC_KNOWLEDGE_TEXT_CHARS]


def _public_knowledge_item(item: dict[str, Any]) -> dict[str, Any]:
    """Return only browser-safe fields for a crawled knowledge item."""
    return {
        "id": str(item.get("id") or ""),
        "external_id": str(item.get("external_id") or ""),
        "entity_type": str(item.get("entity_type") or "knowledge_item"),
        "title": _short_public_text(item.get("title") or item.get("name")),
        "subtitle": _short_public_text(item.get("subtitle")),
        "summary": _short_public_text(item.get("summary")),
        "body": _short_public_text(item.get("body")),
        "url": str(item.get("url") or ""),
        "image_url": str(item.get("image_url") or ""),
        "attributes": item.get("attributes") or {},
        "pricing": item.get("pricing") or {},
        "availability": item.get("availability") or {},
        "location": item.get("location") or {},
        "contact": item.get("contact") or {},
        "policy": item.get("policy") or {},
        "risk_tags": item.get("risk_tags") or [],
    }


def _public_knowledge_items(items: list[dict[str, Any]], requested_ids: list[str]) -> list[dict[str, Any]]:
    """Order public knowledge rows the same way the widget requested them."""
    by_id = {str(item.get("id") or ""): _public_knowledge_item(item) for item in items}
    return [by_id[item_id] for item_id in requested_ids if item_id in by_id]


@app.get("/v1/knowledge", tags=["Knowledge"])
async def list_knowledge(site_id: str = config.DEFAULT_SITE_ID, limit: int = 50) -> dict[str, Any]:
    """Return generic knowledge rows for a tenant."""
    try:
        from db.knowledge import knowledge_preview, knowledge_stats

        safe_limit = max(1, min(int(limit), 500))
        return {
            "site_id": site_id,
            "stats": knowledge_stats(site_id),
            "items": knowledge_preview(site_id, limit=safe_limit),
        }
    except psycopg.Error as exc:
        logger.error("GET /v1/knowledge failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge items.") from exc


@app.get("/v1/knowledge/by-ids", response_model=list[KnowledgeItemResponse], tags=["Knowledge"])
async def list_knowledge_by_ids(ids: str, site_id: str = config.DEFAULT_SITE_ID) -> list[KnowledgeItemResponse]:
    """Fetch public knowledge records by exact IDs for widget-side entity rendering."""
    requested_ids = _parse_public_knowledge_ids(ids)
    if not requested_ids:
        return []
    try:
        from db.knowledge import get_knowledge_items_by_ids

        items = get_knowledge_items_by_ids(site_id, requested_ids)
        return [KnowledgeItemResponse(**item) for item in _public_knowledge_items(items, requested_ids)]
    except psycopg.Error as exc:
        logger.error("GET /v1/knowledge/by-ids failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge items by IDs.") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )
