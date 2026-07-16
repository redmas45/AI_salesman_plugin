"""Scoped APIs for external client panels."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

import config
from db.admin_domain import admin_facade as admin_db

router = APIRouter(prefix="/v1/client-panel", tags=["Client Panel"])

TOKEN_TTL_SECONDS = 60 * 60 * 12
MIN_TOKEN_SECRET_LENGTH = 16
NON_BLOCKING_READINESS_GAPS = frozenset({"variants"})


class ClientPanelLoginRequest(BaseModel):
    site_id: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=admin_db.MIN_CLIENT_PANEL_PASSWORD_LENGTH)


class ClientPanelTokenResponse(BaseModel):
    token: str
    client: dict[str, Any]


class TokenPolicyRequest(BaseModel):
    session_token_limit: int = Field(..., ge=1, le=1_000_000)


PUBLIC_CLIENT_FIELDS = {
    "site_id",
    "name",
    "store_url",
    "status",
    "plan",
    "vertical_key",
    "vertical_label",
    "session_token_limit",
    "token_limit",
    "usage",
    "quota",
    "catalog",
}


@router.post("/login", response_model=ClientPanelTokenResponse)
async def client_panel_login(req: ClientPanelLoginRequest) -> ClientPanelTokenResponse:
    try:
        client = admin_db.verify_client_panel_password(req.site_id, req.password)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return ClientPanelTokenResponse(token=_encode_token(client), client=_public_client(client))


@router.get("/me")
async def client_panel_me(authorization: str = Header(default="")) -> dict[str, Any]:
    site_id = _site_id_from_header(authorization)
    return {"client": _public_client(admin_db.get_client_detail(site_id))}


@router.get("/dashboard")
async def client_panel_dashboard(
    range: str = admin_db.ANALYTICS_DEFAULT_RANGE,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    site_id = _site_id_from_header(authorization)
    client = admin_db.get_client_detail(site_id)
    return {
        "client": _public_client(client),
        "analytics": admin_db.analytics_snapshot(range, site_id),
        "conversations": admin_db.conversation_log(range, site_id),
        "integration": _client_integration_summary(client),
    }


@router.patch("/token-policy")
async def update_token_policy(
    req: TokenPolicyRequest,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    site_id = _site_id_from_header(authorization)
    client = admin_db.update_client_session_token_limit(site_id, req.session_token_limit)
    return {"client": _public_client(client)}


def _site_id_from_header(authorization: str) -> str:
    token = _bearer_token(authorization)
    payload = _decode_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Client panel login required.")
    return str(payload["site_id"])


def _encode_token(client: dict[str, Any]) -> str:
    payload = {
        "site_id": client["site_id"],
        "auth_version": _client_auth_version(client),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
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
    try:
        client = admin_db.get_client_detail(str(payload["site_id"]))
    except LookupError:
        return None
    expected_version = _client_auth_version(client)
    supplied_version = str(payload.get("auth_version") or "")
    if not expected_version or not hmac.compare_digest(supplied_version, expected_version):
        return None
    return payload


def _bearer_token(authorization: str) -> str:
    if not authorization.lower().startswith("bearer "):
        return ""
    return authorization.split(" ", 1)[1].strip()


def _sign(body: str) -> str:
    secret = config.CLIENT_PANEL_TOKEN_SECRET
    if len(secret) < MIN_TOKEN_SECRET_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client panel token secret is not configured securely.",
        )
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return _b64(digest)


def _client_auth_version(client: dict[str, Any]) -> str:
    version = str(client.get("panel_auth_version") or "").strip()
    if version:
        return version
    return "configured" if client.get("panel_password_configured") else ""


def _public_client(client: dict[str, Any]) -> dict[str, Any]:
    """Return only the fields needed by the external client panel."""
    return {key: client.get(key) for key in PUBLIC_CLIENT_FIELDS if key in client}


def _client_integration_summary(client: dict[str, Any]) -> dict[str, Any]:
    readiness = _readiness_report(client)
    capabilities = _capability_rows(readiness)
    unsupported = [
        row
        for row in capabilities
        if (
            not row.get("supported")
            and row.get("blocking", True) is not False
            and not str(row.get("name", "")).startswith("expected_action:")
        )
    ]
    blocking_unsupported = [row for row in unsupported if not _is_non_blocking_readiness_gap(row)]
    informational_unsupported = [row for row in unsupported if _is_non_blocking_readiness_gap(row)]
    domain = next((row for row in capabilities if row.get("name") == "domain_action_coverage"), {})
    expected_rows = [row for row in capabilities if str(row.get("name", "")).startswith("expected_action:")]
    expected_supported = sum(1 for row in expected_rows if row.get("supported"))
    catalog = _dict_value(client.get("catalog"))
    vertical_config = _dict_value(client.get("vertical_config"))
    smoke = _dict_value(vertical_config.get("assistant_smoke_tests"))
    flow = _dict_value(vertical_config.get("flow"))
    rehearsal = _dict_value(vertical_config.get("rehearsal"))
    action_health = _dict_value(_dict_value(vertical_config.get("action_health")).get("summary"))
    active_records = _int_value(catalog.get("active_products"))
    missing_vectors = _int_value(catalog.get("missing_embeddings"))
    smoke_total = _int_value(smoke.get("total"))
    smoke_passed = _int_value(smoke.get("passed"))
    smoke_ok = bool(smoke_total and smoke_passed == smoke_total and str(smoke.get("status", "")).lower() == "ok")
    checks = [
        str(client.get("status", "")).lower() == "live",
        active_records > 0,
        active_records == 0 or missing_vectors < active_records,
        bool(domain.get("supported")),
        bool(expected_rows) and expected_supported == len(expected_rows),
        smoke_ok,
        _int_value(action_health.get("needs_repair")) == 0,
        bool(client.get("panel_password_configured")),
    ]
    base_score = round((sum(1 for item in checks if item) / len(checks)) * 100)
    score = max(0, base_score - min(len(blocking_unsupported) * 5, 25))
    return {
        "status": _integration_status(score, blocking_unsupported, active_records, smoke_total),
        "score": score,
        "next_action": _integration_next_action(client, blocking_unsupported, active_records, missing_vectors, smoke_total, smoke_ok),
        "active_records": active_records,
        "missing_vectors": missing_vectors,
        "domain_actions": {
            "supported": bool(domain.get("supported")),
            "evidence": str(domain.get("evidence") or "No domain action scan has been saved yet."),
            "covered": expected_supported,
            "total": len(expected_rows),
        },
        "readiness": {
            "supported": sum(1 for row in capabilities if row.get("supported")),
            "needs_work": len(blocking_unsupported),
            "unsupported": [
                {
                    "name": str(row.get("name") or ""),
                    "confidence": _float_value(row.get("confidence")),
                    "evidence": str(row.get("evidence") or "No scanner evidence saved."),
                }
                for row in blocking_unsupported[:8]
            ],
            "informational": [
                {
                    "name": str(row.get("name") or ""),
                    "confidence": _float_value(row.get("confidence")),
                    "evidence": str(row.get("evidence") or "No scanner evidence saved."),
                }
                for row in informational_unsupported[:8]
            ],
        },
        "prompt_tests": {
            "status": str(smoke.get("status") or "not_run"),
            "passed": smoke_passed,
            "failed": _int_value(smoke.get("failed")),
            "total": smoke_total,
            "message": str(smoke.get("message") or "Prompt smoke tests have not run yet."),
        },
        "automation": {
            "flow_graph": bool(flow),
            "flow_rehearsal": bool(rehearsal),
            "runtime_repairs_needed": _int_value(action_health.get("needs_repair")),
        },
    }


def _integration_status(score: int, unsupported: list[dict[str, Any]], active_records: int, smoke_total: int) -> str:
    if active_records <= 0 or smoke_total <= 0:
        return "pending"
    if score >= 90 and not unsupported:
        return "ready"
    if score >= 75:
        return "watch"
    return "needs_work"


def _integration_next_action(
    client: dict[str, Any],
    unsupported: list[dict[str, Any]],
    active_records: int,
    missing_vectors: int,
    smoke_total: int,
    smoke_ok: bool,
) -> str:
    if str(client.get("status", "")).lower() != "live":
        return "Ask AI Hub admin to enable this client before testing live traffic."
    if active_records <= 0:
        return "Ask AI Hub admin to refresh source data before expecting comparisons or recommendations."
    if missing_vectors > 0:
        return "Ask AI Hub admin to refresh vectors so retrieval can use every active record."
    if not smoke_total:
        return "Ask AI Hub admin to run assistant prompt smoke tests."
    if not smoke_ok:
        return "Ask AI Hub admin to review the failed prompt smoke test evidence."
    if unsupported:
        names = ", ".join(str(row.get("name") or "readiness check") for row in unsupported[:3])
        return f"Ask AI Hub admin to run setup or inspect these readiness checks: {names}."
    return "No blocking action from the client panel. Keep testing real customer prompts after site changes."


def _is_non_blocking_readiness_gap(row: dict[str, Any]) -> bool:
    return str(row.get("name") or "").strip().lower() in NON_BLOCKING_READINESS_GAPS


def _readiness_report(client: dict[str, Any]) -> dict[str, Any]:
    raw = client.get("readiness_report")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return _dict_value(value)
    return {}


def _capability_rows(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    rows = readiness.get("capabilities")
    if not isinstance(rows, list):
        return []
    return [_dict_value(row) for row in rows if isinstance(row, dict)]


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(number, 1.0)), 2)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
