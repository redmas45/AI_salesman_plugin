"""FastAPI application for the AI Hub runtime API."""

import binascii
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

import config
from agent.orchestration import orchestrator_facade as orchestrator
from api.crm_admin import crm_router as crm_api
from api.client_panels import panel_routes as client_panel_api
from api.runtime.action_truth import annotate_ui_actions, new_action_turn_id
from api.runtime import app_lifespan, client_panel_static, cors_policy, runtime_payloads, runtime_security
from api.runtime.middleware import RateLimitMiddleware, RequestTracingMiddleware, SecurityHeadersMiddleware
from api.runtime.static_files import SpaStaticFiles
from api.runtime.turn_logging import print_turn_summary, turn_timer
from api.routes import clients as clients_router
from api.routes import analytics as analytics_router
from api.routes import ecommerce as ecommerce_router
from api.routes import knowledge as knowledge_router
from api.routes import settings as settings_router
from api.runtime.ws_shop import ws_shop_handler
from db.admin_domain import admin_facade as admin_db
from db.runtime.session_memory import get_session_summary, update_session_summary

from api.contracts.models import ShopResponse

# Module-level logger — file handler is added inside lifespan() AFTER
# uvicorn has called its own logging.config.dictConfig(), so we don't
# conflict with its formatter configuration.
logger = logging.getLogger(__name__)
CLIENT_DISABLED_MESSAGE = "AI assistant is disabled for this client."
TOKEN_QUOTA_EXCEEDED_MESSAGE = "AI assistant token quota is exhausted for this client or session."

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CRM_SOURCE_DIR = PROJECT_ROOT / "crm"
CRM_STATIC_DIR = CRM_SOURCE_DIR / "dist"
CLIENT_PANEL_SOURCE_DIR = Path(
    os.getenv("CLIENT_PANEL_SOURCE_DIR", str(PROJECT_ROOT / "client-panel"))
).expanduser()
CLIENT_PANEL_STATIC_DIR = Path(
    os.getenv("CLIENT_PANEL_STATIC_DIR", str(CLIENT_PANEL_SOURCE_DIR / "dist"))
).expanduser()
CLIENT_PANEL_PUBLIC_PATH = "/client_panel"
CLIENT_PANEL_LEGACY_PATH = "/client-panel"


ShoppingTurnPayload = runtime_payloads.ShoppingTurnPayload
TurnLogState = runtime_payloads.TurnLogState


# Startup / Shutdown

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise runtime dependencies and manage background tasks."""
    async with app_lifespan.runtime_lifespan(app):
        yield



# App

app = FastAPI(
    title="AI Hub Runtime API",
    description="Voice-enabled AI assistant runtime for independently hosted client websites.",
    version="1.0.0",
    lifespan=lifespan,
)

def _allowed_cors_origins() -> list[str]:
    """Compatibility wrapper for tests and existing imports."""
    return cors_policy.allowed_cors_origins()


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
    if origin and cors_policy.is_public_widget_cors_path(request.url.path):
        headers = cors_policy.public_widget_cors_headers(request)
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
app.include_router(knowledge_router.router)
app.include_router(settings_router.router)


@app.get("/crm", include_in_schema=False)
async def redirect_crm_root(request: Request) -> RedirectResponse:
    """Redirect the bare CRM path to the static app root."""
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    return RedirectResponse(url=f"{prefix}/crm/")


if CRM_STATIC_DIR.exists():
    app.mount(
        "/crm",
        SpaStaticFiles(directory=CRM_STATIC_DIR, html=True),
        name="crm",
    )


client_panel_static.register_client_panel_static_routes(
    app,
    public_path=CLIENT_PANEL_PUBLIC_PATH,
    legacy_path=CLIENT_PANEL_LEGACY_PATH,
    static_dir=CLIENT_PANEL_STATIC_DIR,
)


# Endpoints


async def _build_runtime_turn_payload(
    *,
    audio: UploadFile | None,
    text: str | None,
    conversation_history: str | None,
    page_context: str | None = None,
) -> ShoppingTurnPayload:
    return await runtime_payloads.build_runtime_turn_payload(
        audio=audio,
        text=text,
        conversation_history=conversation_history,
        page_context=page_context,
    )


def _update_turn_log_state(state: TurnLogState, event: dict[str, Any]) -> TurnLogState:
    return runtime_payloads.update_turn_log_state(state, event)


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
    action_turn_id = new_action_turn_id()
    session_summary = get_session_summary(site_id, session_id)
    try:
        for event in orchestrator.run_stream(
            site_id=site_id,
            audio_bytes=payload.audio_bytes,
            text_input=text,
            audio_filename=payload.audio_filename,
            skip_tts=skip_tts,
            conversation_history=payload.conversation_history,
            page_context=payload.page_context,
            session_summary=session_summary,
            session_id=session_id,
        ):
            if event.get("event") == "actions":
                data = event.get("data") if isinstance(event.get("data"), dict) else {}
                event = {
                    **event,
                    "data": {
                        **data,
                        "ui_actions": annotate_ui_actions(data.get("ui_actions"), turn_id=action_turn_id),
                    },
                }
            state = _update_turn_log_state(state, event)
            yield f"data: {json.dumps(event)}\n\n"
    finally:
        _print_turn_state(
            transport="legacy-sse",
            site_id=site_id,
            session_id=session_id,
            started_at=started_at,
            state=state,
            history=payload.conversation_history,
        )


def _print_turn_state(
    *,
    transport: str,
    site_id: str,
    session_id: str,
    started_at: float,
    state: TurnLogState,
    history: list[dict[str, str]] | None = None,
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
    update_session_summary(
        site_id,
        session_id,
        history=history or [],
        transcript=state.transcript,
        response_text=state.response_text,
    )


def _record_usage_state(*, site_id: str, session_id: str, transport: str, state: TurnLogState) -> None:
    runtime_payloads.record_usage_state(
        site_id=site_id,
        session_id=session_id,
        transport=transport,
        state=state,
        usage_recorder=admin_db,
        logger=logger,
    )


def _record_usage_result(
    *,
    site_id: str,
    session_id: str,
    transport: str,
    result: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> None:
    runtime_payloads.record_usage_result(
        site_id=site_id,
        session_id=session_id,
        transport=transport,
        history=history or [],
        result=result,
        usage_recorder=admin_db,
        update_session_summary=update_session_summary,
        logger=logger,
    )


def _decode_audio_b64(audio_b64: Any) -> bytes | None:
    return runtime_payloads.decode_audio_b64(audio_b64)


def _coerce_websocket_payload(raw_data: str) -> dict[str, Any]:
    return runtime_payloads.coerce_websocket_payload(raw_data)


@app.post("/v1/shop", response_model=ShopResponse, tags=["AI Runtime"])
async def shop(
    request: Request,
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
    site_id = runtime_payloads.runtime_site_id(site_id, admin_db)
    runtime_security.require_runtime_origin(request, site_id, admin_db.get_client_detail)
    runtime_payloads.raise_if_client_disabled(site_id, admin_db, CLIENT_DISABLED_MESSAGE)
    runtime_payloads.raise_if_quota_exceeded(site_id, session_id, admin_db, TOKEN_QUOTA_EXCEEDED_MESSAGE)
    payload = await _build_runtime_turn_payload(
        audio=audio,
        text=text,
        conversation_history=conversation_history,
        page_context=page_context,
    )

    started_at = turn_timer()
    session_summary = get_session_summary(site_id, session_id)
    result = orchestrator.run(
        site_id=site_id,
        audio_bytes=payload.audio_bytes,
        text_input=text,
        audio_filename=payload.audio_filename,
        skip_tts=skip_tts,
        conversation_history=payload.conversation_history,
        page_context=payload.page_context,
        session_summary=session_summary,
        session_id=session_id,
    )
    result["ui_actions"] = annotate_ui_actions(result.get("ui_actions"), turn_id=new_action_turn_id())
    print_turn_summary(
        transport="legacy-http",
        site_id=site_id,
        started_at=started_at,
        transcript=result.get("transcript", ""),
        response_text=result.get("response_text", ""),
        ui_actions=result.get("ui_actions", []),
        latency_ms=result.get("latency_ms", {}),
    )
    _record_usage_result(
        site_id=site_id,
        session_id=session_id,
        transport="legacy-http",
        result=result,
        history=payload.conversation_history,
    )

    return ShopResponse(**result)


@app.post("/v1/shop/stream", tags=["AI Runtime"])
async def shop_stream(
    request: Request,
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
    site_id = runtime_payloads.runtime_site_id(site_id, admin_db)
    runtime_security.require_runtime_origin(request, site_id, admin_db.get_client_detail)
    runtime_payloads.raise_if_client_disabled(site_id, admin_db, CLIENT_DISABLED_MESSAGE)
    runtime_payloads.raise_if_quota_exceeded(site_id, session_id, admin_db, TOKEN_QUOTA_EXCEEDED_MESSAGE)
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
    site_id = runtime_payloads.runtime_site_id(site_id, admin_db)
    if not runtime_security.runtime_origin_is_allowed(
        site_id, websocket.headers.get("origin", ""), admin_db.get_client_detail
    ):
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Origin is not allowed for this client."})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
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
            parsed_history = runtime_payloads.parse_conversation_history(json.dumps(raw_history))
            site_id = runtime_payloads.runtime_site_id(payload.get("site_id", config.DEFAULT_SITE_ID), admin_db)
            session_id = str(payload.get("session_id") or "")
            if not runtime_security.runtime_origin_is_allowed(
                site_id, websocket.headers.get("origin", ""), admin_db.get_client_detail
            ):
                await websocket.send_json({"event": "error", "data": {"error": "Origin is not allowed for this client."}})
                continue
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
            session_summary = get_session_summary(site_id, session_id)
            for event in orchestrator.run_stream(
                site_id=site_id,
                audio_bytes=audio_bytes,
                text_input=text_input,
                audio_filename=runtime_payloads.DEFAULT_AUDIO_FILENAME,
                skip_tts=payload.get("skip_tts", False),
                conversation_history=parsed_history,
                session_summary=session_summary,
                session_id=session_id,
            ):
                state = _update_turn_log_state(state, event)
                await websocket.send_json(event)
            _print_turn_state(
                transport="legacy-ws",
                site_id=site_id,
                session_id=session_id,
                started_at=started_at,
                state=state,
                history=parsed_history,
            )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )
