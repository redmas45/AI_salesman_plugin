"""
FastAPI application — Voice Shopping Agent API.

Endpoints:
  POST /v1/shop          Main pipeline: audio/text → ui_actions + voice response
  GET  /v1/products      List all products (for frontend sync)
  GET  /health           Health check
"""

import asyncio
import base64
import binascii
import concurrent.futures
import datetime
import functools
import io
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Optional
from xml.sax.saxutils import escape

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import psycopg
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config
from agent import orchestrator
from api import crm as crm_api
from api.middleware import RequestTracingMiddleware
from api.turn_logging import print_turn_summary, turn_timer
from api.ws_shop import ws_shop_handler
from db import admin as admin_db


class ClientLogRequest(BaseModel):
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)

from api.models import (
    AddToCartRequest,
    CartItemResponse,
    CheckoutRequest,
    HealthResponse,
    ProductResponse,
    ShopResponse,
)
from db.database import (
    InvalidProductIdError,
    ProductNotFoundError,
    add_to_cart,
    catalog_source_preview,
    catalog_source_stats,
    catalog_sync_history,
    clear_cart,
    coerce_product_id,
    get_all_products,
    get_cart_items,
    get_user_profile,
    tenant_catalog_preview,
    tenant_catalog_stats,
    remove_from_cart,
    update_user_profile,
)

# Module-level logger — file handler is added inside lifespan() AFTER
# uvicorn has called its own logging.config.dictConfig(), so we don't
# conflict with its formatter configuration.
logger = logging.getLogger(__name__)
CLIENT_DISABLED_MESSAGE = "AI assistant is disabled for this client."
TOKEN_QUOTA_EXCEEDED_MESSAGE = "AI assistant token quota is exhausted for this client or session."
DISABLED_WIDGET_DOM_ID = "shopbot-widget"
DISABLED_WIDGET_BOOT_FLAG = "__shopbotBooted"
DISABLED_WIDGET_FRAME_FLAG = "__shopbotFrameLoaded"
DISABLED_WIDGET_REGISTRY = "__shopbotDisabledSites"

DEFAULT_AUDIO_FILENAME = "audio.wav"
CRAWLER_SOURCE_NAME = "custom_url_crawler"
CRAWLER_POLL_INTERVAL_SECONDS = 120
MAX_CONVERSATION_HISTORY_TURNS = 12
MAX_LOG_FIELD_CHARS = 80
MAX_LOG_VALUE_CHARS = 300
HTTP_UNPROCESSABLE_INPUT = status.HTTP_422_UNPROCESSABLE_CONTENT
CHECKOUT_EMPTY_VALUES = {"", "N/A", "Not Provided"}
CHECKOUT_DEFAULT_VALUE = "Not Provided"
INVOICE_BRAND_NAME = "AI-KART"
INVOICE_TITLE = "PREMIUM INVOICE"
INVOICE_FILENAME = "bill.pdf"
INVOICE_CURRENCY = "INR"
INVOICE_HEADER_COLOR = "#2c3e50"
INVOICE_TEXT_COLOR = "#34495e"
INVOICE_ACCENT_COLOR = "#1abc9c"
INVOICE_MUTED_COLOR = "#95a5a6"
INVOICE_TABLE_BACKGROUND = "#f8f9fa"
INVOICE_TABLE_GRID = "#dee2e6"
INVOICE_PAGE_MARGIN = 60
INVOICE_BORDER_MARGIN = 30
INVOICE_HEADER_HEIGHT = 100
INVOICE_HEADER_TOP_OFFSET = 130
INVOICE_TITLE_FONT_SIZE = 36
INVOICE_SUBTITLE_FONT_SIZE = 14
INVOICE_TABLE_COL_WIDTHS = [240, 90, 50, 110]
INVOICE_TOP_MARGIN = 150
CRM_STATIC_DIR = Path(__file__).parent.parent / "crm"


@dataclass(frozen=True)
class ShoppingTurnPayload:
    audio_bytes: bytes | None
    audio_filename: str
    conversation_history: list[dict[str, str]]


@dataclass(frozen=True)
class TurnLogState:
    transcript: str = ""
    response_text: str = ""
    ui_actions: list[Any] = field(default_factory=list)
    latency_ms: dict[str, float] = field(default_factory=dict)
    status: str = "ok"


@dataclass(frozen=True)
class CheckoutProfile:
    address: str
    payment_method: str


# Startup / Shutdown


import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise database, seed data, and register pgvector on startup."""
    logger.info("Starting Voice Shopping Agent API...")
    
    # Preload RAG embedder and index into memory
    from agent import rag
    rag.preload()
    admin_db.ensure_default_client()

    from agent.ingestion import sync_web_crawl
    
    async def run_crawl_once(target_url: str, site_id: str, *, initial: bool = False) -> None:
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

    crawler_task = None
    if config.CRAWL_PERIODIC_ENABLED:
        crawler_task = asyncio.create_task(periodic_crawl())

    logger.info("Startup complete. API ready.")
    yield

    if crawler_task:
        crawler_task.cancel()
    logger.info("Shutting down Voice Shopping Agent API.")



# App

app = FastAPI(
    title="Voice Shopping Agent API",
    description="Voice-enabled AI shopping assistant powered by OpenAI.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for demo; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if config.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestTracingMiddleware)
app.include_router(crm_api.router)


@app.get("/crm", include_in_schema=False)
async def redirect_crm_root(request: Request) -> RedirectResponse:
    """Redirect the bare CRM path to the static app root."""
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    return RedirectResponse(url=f"{prefix}/crm/")


if CRM_STATIC_DIR.exists():
    app.mount(
        "/crm",
        StaticFiles(directory=CRM_STATIC_DIR, html=True),
        name="crm",
    )


@app.get("/v1/widget/status", tags=["Plugin"])
async def widget_status(
    site_id: str = config.DEFAULT_SITE_ID,
    site: Optional[str] = None,
    shop: Optional[str] = None,
) -> dict[str, Any]:
    """Return the public widget availability state for one tenant."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    return {
        "site_id": safe_site,
        "enabled": admin_db.is_client_widget_enabled(safe_site),
    }

# Endpoints

@app.get("/health", response_model=HealthResponse, tags=["Utility"])
async def health() -> HealthResponse:
    """Check API and model configuration health."""
    return HealthResponse(
        status="ok",
        models={
            "stt": f"{config.STT_PROVIDER}:{config.GROQ_STT_MODEL if config.STT_PROVIDER == 'groq' else config.STT_MODEL}",
            "llm": config.LLM_MODEL,
            "tts": (
                f"groq:{config.GROQ_TTS_MODEL} / {config.GROQ_TTS_VOICE}"
                if config.TTS_PROVIDER == "groq"
                else f"openai:{config.TTS_MODEL} / {config.TTS_VOICE}"
            ),
            "embedding": config.EMBEDDING_MODEL,
        },
    )

@app.post("/v1/catalog/crawler/run", tags=["Utility"])
async def trigger_crawler() -> dict[str, str]:
    """Manually trigger the crawler."""
    from agent.ingestion import sync_web_crawl
    
    target_url = config.CURRENT_URL
    site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if not target_url:
        return {"status": "error", "message": "No CURRENT_URL configured."}

    logger.info("Manual crawler trigger requested for %s...", target_url)

    def run_sync() -> None:
        try:
            sync_web_crawl(
                target_url,
                max_pages=config.CRAWL_MAX_PAGES,
                max_depth=config.CRAWL_MAX_DEPTH,
                site_id=site_id,
                reconcile_missing=True,
                source_name=CRAWLER_SOURCE_NAME,
            )
        except (RuntimeError, OSError, ValueError) as exc:
            logger.error("Manual crawl failed: %s", exc)

    loop = asyncio.get_running_loop()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, run_sync)
    
    return {"status": "ok", "message": "Crawler started in background."}

@app.post("/v1/client-log", tags=["Utility"])
async def client_log(req: ClientLogRequest) -> dict[str, str]:
    """Receive browser-side diagnostics from the injected widget."""
    safe_event = str(req.event)[:MAX_LOG_FIELD_CHARS]
    safe_payload = {
        str(key)[:MAX_LOG_FIELD_CHARS]: str(value)[:MAX_LOG_VALUE_CHARS]
        for key, value in (req.payload or {}).items()
    }
    logger.info("CLIENT | %s | %s", safe_event, safe_payload)
    return {"status": "ok"}


async def _build_shopping_turn_payload(
    *,
    audio: UploadFile | None,
    text: str | None,
    conversation_history: str | None,
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


@app.post("/v1/shop", response_model=ShopResponse, tags=["Shopping Agent"])
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
    session_id: str = Form("", description="Browser conversation session ID"),
) -> ShopResponse:
    """
    **Main endpoint.** Send customer audio or text → receive UI actions + voice response.

    - **audio**: Upload a recorded audio clip of the customer's voice.
    - **text**: Alternatively, send plain text (useful for debugging).
    - **skip_tts**: Set to `true` to skip speech synthesis (faster, text-only response).

    Returns:
    - `transcript` — what the customer said
    - `response_text` — what ShopBot says back
    - `ui_actions` — list of website control commands for the frontend
    - `audio_b64` — base64-encoded WAV of the spoken response
    """
    _raise_if_client_disabled(site_id)
    _raise_if_quota_exceeded(site_id, session_id)
    payload = await _build_shopping_turn_payload(
        audio=audio,
        text=text,
        conversation_history=conversation_history,
    )

    started_at = turn_timer()
    result = orchestrator.run(
        site_id=site_id,
        audio_bytes=payload.audio_bytes,
        text_input=text,
        audio_filename=payload.audio_filename,
        skip_tts=skip_tts,
        conversation_history=payload.conversation_history,
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


@app.post("/v1/shop/stream", tags=["Shopping Agent"])
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
    session_id: str = Form("", description="Browser conversation session ID"),
) -> StreamingResponse:
    """
    **Streaming endpoint.** Send customer audio or text → receive SSE events for transcript, ui_actions, and audio.
    """
    _raise_if_client_disabled(site_id)
    _raise_if_quota_exceeded(site_id, session_id)
    payload = await _build_shopping_turn_payload(
        audio=audio,
        text=text,
        conversation_history=conversation_history,
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
    """Bi-directional WebSocket for real-time voice shopping."""
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


@app.get("/v1/products", response_model=list[ProductResponse], tags=["Products"])
async def list_products(
    site_id: str = config.DEFAULT_SITE_ID, category: Optional[str] = None, limit: int = 50, offset: int = 0
) -> list[ProductResponse]:
    """
    Return active products in the catalog with pagination, optionally filtered by category.
    The frontend uses this to build its product grid dynamically.
    """
    try:
        if category:
            from db.database import get_products_by_category

            products = get_products_by_category(site_id, category, limit=limit)
        else:
            products = get_all_products(site_id, limit=limit, offset=offset)
        return [ProductResponse(**p) for p in products]
    except psycopg.Error as exc:
        logger.error("GET /v1/products failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch products.")


@app.get("/v1/products/by-ids", response_model=list[ProductResponse], tags=["Products"])
async def list_products_by_ids(ids: str, site_id: str = config.DEFAULT_SITE_ID) -> list[ProductResponse]:
    """Fetch specific products by a comma-separated list of IDs."""
    try:
        id_list = []
        for raw_id in ids.split(","):
            raw_id = raw_id.strip().strip('"')
            if raw_id:
                try:
                    id_list.append(coerce_product_id(raw_id))
                except InvalidProductIdError:
                    continue
        from db.database import get_products_by_ids

        products = get_products_by_ids(site_id, id_list)
        return [ProductResponse(**p) for p in products]
    except psycopg.Error as exc:
        logger.error("GET /v1/products/by-ids failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch products by IDs.")


@app.get("/v1/categories", tags=["Products"])
async def list_categories(site_id: str = config.DEFAULT_SITE_ID) -> list[dict[str, str]]:
    """Return all active category names and slugs from the database."""
    try:
        from db.database import get_db
        with get_db(site_id) as conn:
            rows = conn.execute("SELECT name, slug FROM categories ORDER BY name ASC").fetchall()
            return [{"name": r["name"], "slug": r["slug"]} for r in rows]
    except psycopg.Error as exc:
        logger.error("GET /v1/categories failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch categories.")


@app.get("/v1/catalog/status", tags=["Products"])
async def catalog_status(site_id: str = config.DEFAULT_SITE_ID) -> dict[str, Any]:
    """Return catalog/RAG sync status for a tenant site."""
    try:
        source_stats = catalog_source_stats(site_id)
        preview_source = source_stats[0]["source_name"] if source_stats else "custom_url_crawler"
        return {
            "site_id": site_id,
            "catalog": tenant_catalog_stats(site_id),
            "sources": source_stats,
            "recent_sync_runs": catalog_sync_history(site_id, limit=8),
            "catalog_preview": tenant_catalog_preview(site_id, limit=12),
            "source_preview": catalog_source_preview(site_id, preview_source, limit=12)
            if source_stats
            else [],
        }
    except psycopg.Error as exc:
        logger.error("GET /v1/catalog/status failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch catalog status.")


@app.get("/v1/cart", response_model=list[CartItemResponse], tags=["Cart"])
async def get_cart(site_id: str = config.DEFAULT_SITE_ID) -> list[CartItemResponse]:
    """Return all items currently in the shopping cart."""
    try:
        items = get_cart_items(site_id)
        return [CartItemResponse(**item) for item in items]
    except psycopg.Error as exc:
        logger.error("GET /v1/cart failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch cart.")


@app.post("/v1/cart/add", tags=["Cart"])
async def api_add_to_cart(req: AddToCartRequest) -> dict[str, Any]:
    """Add a product to the cart."""
    try:
        cart_id = add_to_cart(req.site_id, req.product_id, req.quantity)
        return {"status": "ok", "cart_id": cart_id}
    except InvalidProductIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except psycopg.Error as exc:
        logger.error("POST /v1/cart/add failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to add to cart.")


@app.post("/v1/cart/update", tags=["Cart"])
async def api_update_cart(req: AddToCartRequest) -> dict[str, str]:
    """Update the quantity of a product in the cart."""
    try:
        from db.database import update_cart_quantity

        success = update_cart_quantity(req.site_id, req.product_id, req.quantity)
        if not success:
            raise HTTPException(status_code=404, detail="Product not found in cart.")
        return {"status": "ok"}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        logger.error("POST /v1/cart/update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update cart.")


@app.delete("/v1/cart/{cart_id}", tags=["Cart"])
async def api_remove_from_cart(cart_id: int, site_id: str = config.DEFAULT_SITE_ID) -> dict[str, str]:
    """Remove a product from the cart."""
    try:
        success = remove_from_cart(site_id, cart_id)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found in cart.")
        return {"status": "ok"}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        logger.error("DELETE /v1/cart/{cart_id} failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to remove from cart.")


@app.delete("/v1/cart", tags=["Cart"])
async def api_clear_cart(site_id: str = config.DEFAULT_SITE_ID) -> dict[str, str]:
    """Clear the entire shopping cart."""
    try:
        clear_cart(site_id)
        return {"status": "ok"}
    except psycopg.Error as exc:
        logger.error("DELETE /v1/cart failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to clear cart.")


def _checkout_items(req: CheckoutRequest) -> list[dict[str, Any]]:
    if not req.items:
        return get_cart_items(req.site_id)
    return [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "quantity": item.quantity,
        }
        for item in req.items
    ]


def _provided_checkout_value(value: str | None) -> bool:
    return bool(value and value.strip() not in CHECKOUT_EMPTY_VALUES)


def _resolve_checkout_field(candidate: str | None, stored_value: Any) -> str:
    if _provided_checkout_value(candidate):
        return str(candidate).strip()
    stored_text = str(stored_value or "").strip()
    if stored_text and stored_text not in CHECKOUT_EMPTY_VALUES:
        return stored_text
    return CHECKOUT_DEFAULT_VALUE


def _resolve_checkout_profile(req: CheckoutRequest) -> CheckoutProfile:
    profile = get_user_profile(req.site_id)
    return CheckoutProfile(
        address=_resolve_checkout_field(req.address, profile.get("address")),
        payment_method=_resolve_checkout_field(
            req.payment_method,
            profile.get("payment_method"),
        ),
    )


def _draw_invoice_page(canvas: Any, _doc: Any) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(INVOICE_HEADER_COLOR))
    canvas.setLineWidth(2)
    canvas.rect(
        INVOICE_BORDER_MARGIN,
        INVOICE_BORDER_MARGIN,
        letter[0] - (INVOICE_BORDER_MARGIN * 2),
        letter[1] - (INVOICE_BORDER_MARGIN * 2),
    )
    canvas.setFillColor(colors.HexColor(INVOICE_HEADER_COLOR))
    canvas.rect(
        INVOICE_BORDER_MARGIN,
        letter[1] - INVOICE_HEADER_TOP_OFFSET,
        letter[0] - (INVOICE_BORDER_MARGIN * 2),
        INVOICE_HEADER_HEIGHT,
        fill=1,
        stroke=0,
    )
    canvas.setFont("Helvetica-Bold", INVOICE_TITLE_FONT_SIZE)
    canvas.setFillColor(colors.white)
    canvas.drawString(INVOICE_PAGE_MARGIN, letter[1] - 85, INVOICE_BRAND_NAME)
    canvas.setFont("Helvetica", INVOICE_SUBTITLE_FONT_SIZE)
    canvas.drawString(INVOICE_PAGE_MARGIN, letter[1] - 110, INVOICE_TITLE)
    canvas.restoreState()


def _invoice_metadata_elements(styles: dict[str, Any]) -> list[Any]:
    now = datetime.datetime.now()
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor(INVOICE_TEXT_COLOR),
        alignment=2,
    )
    metadata = f"<b>Date:</b> {now:%B %d, %Y}<br/><b>Invoice #:</b> INV-{int(now.timestamp())}"
    return [Paragraph(metadata, meta_style), Spacer(1, 20)]


def _invoice_customer_elements(styles: dict[str, Any], profile: CheckoutProfile) -> list[Any]:
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor(INVOICE_HEADER_COLOR),
    )
    customer_html = (
        f"<b>Billed To:</b><br/>{escape(profile.address)}<br/><br/>"
        f"<b>Payment Method:</b><br/>{escape(profile.payment_method)}"
    )
    return [Paragraph(customer_html, info_style), Spacer(1, 30)]


def _short_invoice_item_name(name: Any) -> str:
    item_name = str(name or "")
    return item_name[:50] + ("..." if len(item_name) > 50 else "")


def _format_invoice_money(value: float) -> str:
    return f"{INVOICE_CURRENCY} {value:.2f}"


def _invoice_table_data(items: list[dict[str, Any]]) -> list[list[str]]:
    rows = [["Description", "Unit Price", "Qty", "Total"]]
    total_amount = 0.0
    for item in items:
        item_price = float(item["price"])
        item_quantity = int(item["quantity"])
        item_total = item_price * item_quantity
        total_amount += item_total
        rows.append(
            [
                _short_invoice_item_name(item["name"]),
                _format_invoice_money(item_price),
                str(item_quantity),
                _format_invoice_money(item_total),
            ]
        )
    rows.extend(
        [
            ["", "", "Subtotal:", _format_invoice_money(total_amount)],
            ["", "", "Tax (0%):", _format_invoice_money(0.0)],
            ["", "", "Grand Total:", _format_invoice_money(total_amount)],
        ]
    )
    return rows


def _invoice_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INVOICE_HEADER_COLOR)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("TOPPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -4), colors.HexColor(INVOICE_TABLE_BACKGROUND)),
            ("GRID", (0, 0), (-1, -4), 1, colors.HexColor(INVOICE_TABLE_GRID)),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ("TOPPADDING", (0, 1), (-1, -1), 10),
            ("FONTNAME", (2, -3), (3, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (2, -1), (3, -1), colors.HexColor(INVOICE_ACCENT_COLOR)),
            ("FONTSIZE", (2, -1), (3, -1), 13),
            ("LINEABOVE", (2, -3), (3, -3), 1, colors.HexColor(INVOICE_HEADER_COLOR)),
            ("LINEABOVE", (2, -1), (3, -1), 2, colors.HexColor(INVOICE_HEADER_COLOR)),
        ]
    )


def _invoice_items_element(items: list[dict[str, Any]]) -> Table:
    table = Table(_invoice_table_data(items), colWidths=INVOICE_TABLE_COL_WIDTHS)
    table.setStyle(_invoice_table_style())
    return table


def _invoice_footer_elements(styles: dict[str, Any]) -> list[Any]:
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        alignment=1,
        textColor=colors.HexColor(INVOICE_MUTED_COLOR),
        fontSize=10,
        fontName="Helvetica-Oblique",
    )
    footer = f"Thank you for choosing {INVOICE_BRAND_NAME}.<br/>This is an automatically generated receipt."
    return [Spacer(1, 60), Paragraph(footer, footer_style)]


def _invoice_elements(items: list[dict[str, Any]], profile: CheckoutProfile) -> list[Any]:
    styles = getSampleStyleSheet()
    return [
        *_invoice_metadata_elements(styles),
        *_invoice_customer_elements(styles, profile),
        _invoice_items_element(items),
        *_invoice_footer_elements(styles),
    ]


def _build_invoice_pdf(items: list[dict[str, Any]], profile: CheckoutProfile) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=INVOICE_PAGE_MARGIN,
        leftMargin=INVOICE_PAGE_MARGIN,
        topMargin=INVOICE_TOP_MARGIN,
        bottomMargin=INVOICE_PAGE_MARGIN,
    )
    document.build(
        _invoice_elements(items, profile),
        onFirstPage=_draw_invoice_page,
        onLaterPages=_draw_invoice_page,
    )
    return buffer.getvalue()


def _invoice_response(pdf_bytes: bytes) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={INVOICE_FILENAME}"},
    )


@app.post("/v1/cart/checkout", tags=["Cart"])
async def api_checkout_cart(req: CheckoutRequest) -> Response:
    """Generate a PDF bill and clear the cart."""
    try:
        items = _checkout_items(req)
        if not items:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        profile = _resolve_checkout_profile(req)
        update_user_profile(req.site_id, profile.address, profile.payment_method)
        pdf_bytes = _build_invoice_pdf(items, profile)
        from db.database import checkout_cart

        checkout_cart(req.site_id)
        return _invoice_response(pdf_bytes)

    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid checkout item data.") from exc
    except psycopg.Error as exc:
        logger.error("POST /v1/cart/checkout failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process checkout.") from exc



def vectorize_site_catalog(site_id: str) -> None:
    logger.info("Background Vectorization started for site %s...", site_id)
    try:
        from db.database import get_db
        from agent.rag import _embed, _product_to_text
        
        with get_db(site_id) as conn:
            rows = conn.execute(
                "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON p.category_id = c.id WHERE p.embedding IS NULL"
            ).fetchall()
            
            if not rows:
                logger.info("No products need vectorization for site %s", site_id)
                return
                
            logger.info("Vectorizing %d products for site %s...", len(rows), site_id)
            texts = []
            for row in rows:
                texts.append(_product_to_text(dict(row)))
                
            embeddings = _embed(texts)
            
            for i, row in enumerate(rows):
                conn.execute(
                    "UPDATE products SET embedding = %s WHERE id = %s",
                    (embeddings[i], row["id"])
                )
            logger.info("Vectorization complete for site %s.", site_id)
    except (psycopg.Error, RuntimeError) as exc:
        logger.error("Background Vectorization failed for site %s: %s", site_id, exc)




def _safe_site_id(raw: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", (raw or "").strip().lower())[:80] or "site_1"


def _safe_script_base_url(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip().strip("\"'")
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        return raw.rstrip("/")
    return ""


def _public_widget_base_url() -> str:
    return (
        _safe_script_base_url(os.environ.get("PUBLIC_API_URL", ""))
        or _safe_script_base_url(config.PUBLIC_API_URL)
        or _safe_script_base_url(config.VOICE_ORB_API_URL or "")
    )


def _load_widget_script(*, site: str, api_base_url: str) -> str:
    plugin_path = Path(__file__).parent.parent / "plugin" / "shopbot.js"
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail="Plugin script not found.")

    with open(plugin_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    js_code = js_code.replace('"__AI_PUBLIC_API_URL__"', json.dumps(api_base_url))
    js_code = js_code.replace('"__AI_DEFAULT_SITE_ID__"', json.dumps(site))
    return js_code


def _disabled_widget_script(*, site: str) -> str:
    return f"""
(function () {{
  var siteId = {json.dumps(site)};
  var widget = document.getElementById({json.dumps(DISABLED_WIDGET_DOM_ID)});
  if (widget) widget.remove();
  window[{json.dumps(DISABLED_WIDGET_BOOT_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_FRAME_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] = window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] || {{}};
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}][siteId] = true;
  console.info("[ShopBot] " + {json.dumps(CLIENT_DISABLED_MESSAGE)} + " Site: " + siteId);
}})();
"""


def _render_embed_bootstrap(*, site: str, api_base_url: str) -> str:
    return f"""
(function () {{
  if (window.__shopbotFrameLoaded) return;
  window.__shopbotFrameLoaded = true;

  var currentScript = document.currentScript;
  var scriptUrl = currentScript && currentScript.src ? new URL(currentScript.src, window.location.href) : null;
  var siteId = {json.dumps(site)};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var parentOrigin = window.location.origin;
  var frameUrl = new URL(apiBaseUrl + "/shopbot-frame");
  frameUrl.searchParams.set("site", siteId);
  frameUrl.searchParams.set("parent_origin", parentOrigin);

  var frame = document.createElement("iframe");
  frame.src = frameUrl.toString();
  frame.title = "ShopBot Voice Orb";
  frame.setAttribute("allow", "microphone");
  frame.setAttribute("aria-label", "ShopBot Voice Orb");
  frame.style.position = "fixed";
  frame.style.left = "50%";
  frame.style.bottom = "12px";
  frame.style.transform = "translateX(-50%)";
  frame.style.width = "360px";
  frame.style.height = "180px";
  frame.style.maxWidth = "calc(100vw - 24px)";
  frame.style.maxHeight = "calc(100vh - 24px)";
  frame.style.border = "0";
  frame.style.background = "transparent";
  frame.style.zIndex = "2147483647";
  frame.style.overflow = "hidden";
  frame.style.colorScheme = "light";

  function clamp(value, fallback, maxCss) {{
    var numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric <= 0) return fallback;
    return Math.min(numeric, maxCss);
  }}

  window.addEventListener("message", function (event) {{
    if (event.origin !== new URL(apiBaseUrl).origin) return;
    var data = event.data || {{}};
    if (data.source !== "shopbot-frame") return;

    if (data.type === "shopbot:frame-size") {{
      var width = clamp(data.width, 360, Math.max(320, window.innerWidth - 24));
      var height = clamp(data.height, 180, Math.max(180, window.innerHeight - 24));
      frame.style.width = width + "px";
      frame.style.height = height + "px";
      return;
    }}

    if (data.type === "shopbot:navigate" && data.path) {{
      try {{
        var targetUrl = new URL(data.path, window.location.href);
        if (targetUrl.origin === window.location.origin) {{
          window.location.href = targetUrl.pathname + targetUrl.search + targetUrl.hash;
        }}
      }} catch (_err) {{}}
    }}
  }});

  function mountFrame(retries) {{
    if (document.body) {{
      document.body.appendChild(frame);
      return;
    }}
    if (retries > 100) {{
      return;
    }}
    setTimeout(function () {{ mountFrame(retries + 1); }}, 50);
  }}

  mountFrame(0);
}})();
"""


@app.get("/shopbot-frame", tags=["Plugin"])
async def serve_plugin_frame(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
    parent_origin: Optional[str] = None,
) -> Response:
    """Serve a standalone orb frame for external website modes."""
    from fastapi.responses import Response

    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    script_path = f"{_public_widget_base_url()}/shopbot-widget.js?site={safe_site}"
    if parent_origin:
        script_path += f"&parent_origin={parent_origin}"

    if not admin_db.is_client_widget_enabled(safe_site):
        return Response(
            content="<!doctype html><html><body></body></html>",
            media_type="text/html",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ShopBot</title>
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: transparent;
      }}
      body {{
        position: relative;
      }}
    </style>
  </head>
  <body>
    <script src="{script_path}"></script>
  </body>
</html>"""

    return Response(
        content=html_doc,
        media_type="text/html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/shopbot-widget.js", tags=["Plugin"])
async def serve_plugin_widget(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the full widget app for direct use or inside the external embed frame."""
    from fastapi.responses import Response

    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = (
        _load_widget_script(site=safe_site, api_base_url=safe_api)
        if admin_db.is_client_widget_enabled(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/shopbot.js", tags=["Plugin"])
async def serve_plugin(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the public widget loader — inlined directly (no iframe).

    The iframe-based bootstrap (_render_embed_bootstrap) fails with free-tier
    ngrok because the interstitial "Visit Site" page blocks iframe loading.
    Serving the full widget JS directly avoids this issue entirely.
    """
    from fastapi.responses import Response

    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = (
        _load_widget_script(site=safe_site, api_base_url=safe_api)
        if admin_db.is_client_widget_enabled(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


# Entry point

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )

