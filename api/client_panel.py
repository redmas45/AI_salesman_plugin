"""Scoped APIs for external client panels."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

import config
from db import admin as admin_db

router = APIRouter(prefix="/v1/client-panel", tags=["Client Panel"])

TOKEN_TTL_SECONDS = 60 * 60 * 12


class ClientPanelLoginRequest(BaseModel):
    site_id: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=6)


class ClientPanelTokenResponse(BaseModel):
    token: str
    client: dict[str, Any]


class TokenPolicyRequest(BaseModel):
    session_token_limit: int = Field(..., ge=1, le=1_000_000)


@router.post("/login", response_model=ClientPanelTokenResponse)
async def client_panel_login(req: ClientPanelLoginRequest) -> ClientPanelTokenResponse:
    try:
        client = admin_db.verify_client_panel_password(req.site_id, req.password)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return ClientPanelTokenResponse(token=_encode_token(client["site_id"]), client=client)


@router.get("/me")
async def client_panel_me(authorization: str = Header(default="")) -> dict[str, Any]:
    site_id = _site_id_from_header(authorization)
    return {"client": admin_db.get_client_detail(site_id)}


@router.get("/dashboard")
async def client_panel_dashboard(
    range: str = admin_db.ANALYTICS_DEFAULT_RANGE,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    site_id = _site_id_from_header(authorization)
    return {
        "client": admin_db.get_client_detail(site_id),
        "analytics": admin_db.analytics_snapshot(range, site_id),
        "conversations": admin_db.conversation_log(range, site_id),
    }


@router.patch("/token-policy")
async def update_token_policy(
    req: TokenPolicyRequest,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    site_id = _site_id_from_header(authorization)
    client = admin_db.update_client_session_token_limit(site_id, req.session_token_limit)
    return {"client": client}


def _site_id_from_header(authorization: str) -> str:
    token = _bearer_token(authorization)
    payload = _decode_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Client panel login required.")
    return str(payload["site_id"])


def _encode_token(site_id: str) -> str:
    payload = {"site_id": site_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_sign(body)}"


def _decode_token(token: str) -> dict[str, Any] | None:
    parts = token.split(".", 1)
    if len(parts) != 2:
        return None
    body, signature = parts
    if not hmac.compare_digest(_sign(body), signature):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    if not payload.get("site_id"):
        return None
    return payload


def _bearer_token(authorization: str) -> str:
    if not authorization.lower().startswith("bearer "):
        return ""
    return authorization.split(" ", 1)[1].strip()


def _sign(body: str) -> str:
    secret = os.getenv("CLIENT_PANEL_TOKEN_SECRET") or os.getenv("CRM_ADMIN_TOKEN") or config.OPENAI_API_KEY or "client-panel-dev-secret"
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return _b64(digest)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
