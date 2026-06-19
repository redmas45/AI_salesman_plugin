"""FastAPI routes for the AI Hub CRM admin panel."""

from __future__ import annotations

import logging
import os
import hmac
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

import config
from agent.ingestion import sync_web_crawl
from db import admin as admin_db

logger = logging.getLogger(__name__)

ADMIN_TOKEN_HEADER = "x-crm-admin-token"
MAX_CLIENT_NAME_LENGTH = 120
MAX_SITE_ID_LENGTH = 80
MAX_URL_LENGTH = 500
MAX_ADAPTER_NAME_LENGTH = 160
MAX_PLAN_LENGTH = 80
MIN_ADMIN_TOKEN_LENGTH = 12


class ClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_CLIENT_NAME_LENGTH)
    store_url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)
    site_id: str | None = Field(default=None, max_length=MAX_SITE_ID_LENGTH)
    deploy_mode: str = Field(default=admin_db.DEFAULT_DEPLOY_MODE, max_length=40)
    plan: str = Field(default=admin_db.DEFAULT_PLAN, max_length=MAX_PLAN_LENGTH)
    adapter_name: str = Field(
        default=admin_db.DEFAULT_ADAPTER_NAME,
        max_length=MAX_ADAPTER_NAME_LENGTH,
    )


class ClientStatusRequest(BaseModel):
    enabled: bool


class ClientTokenLimitsRequest(BaseModel):
    token_limit: int = Field(..., ge=1, le=admin_db.MAX_CLIENT_TOKEN_LIMIT)
    session_token_limit: int = Field(..., ge=1, le=admin_db.MAX_SESSION_TOKEN_LIMIT)


class ClientPanelPasswordRequest(BaseModel):
    password: str | None = Field(default=None, min_length=admin_db.MIN_CLIENT_PANEL_PASSWORD_LENGTH, max_length=160)
    auto_generate: bool = False


class SettingsUpdateRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class AnalyticsSummaryRequest(BaseModel):
    range: str = Field(default=admin_db.ANALYTICS_DEFAULT_RANGE, max_length=20)
    site_id: str = Field(default="", max_length=MAX_SITE_ID_LENGTH)


def require_admin_token(request: Request) -> None:
    """Require a configured admin token for every CRM admin API request."""
    expected_token = os.getenv("CRM_ADMIN_TOKEN", "").strip()
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM admin token is not configured.",
        )
    if len(expected_token) < MIN_ADMIN_TOKEN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM admin token is configured but too short.",
        )

    provided_token = request.headers.get(ADMIN_TOKEN_HEADER, "").strip()
    if hmac.compare_digest(provided_token, expected_token):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="CRM admin token is required.",
    )


router = APIRouter(
    prefix="/v1/admin",
    tags=["CRM Admin"],
    dependencies=[Depends(require_admin_token)],
)


@router.get("/overview")
async def crm_overview() -> dict[str, Any]:
    """Return dashboard metrics, clients, health, and recent activity."""
    try:
        return admin_db.overview()
    except Exception as exc:
        logger.error("CRM overview failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load CRM overview.") from exc


@router.get("/clients")
async def crm_clients() -> dict[str, list[dict[str, Any]]]:
    """Return all active CRM clients."""
    try:
        return {"clients": admin_db.list_clients()}
    except Exception as exc:
        logger.error("CRM clients failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load CRM clients.") from exc


@router.post("/clients", status_code=status.HTTP_201_CREATED)
async def crm_create_client(req: ClientCreateRequest) -> dict[str, Any]:
    """Create a client tenant and return its embed script."""
    try:
        client = admin_db.create_client(
            name=req.name,
            store_url=req.store_url,
            site_id=req.site_id,
            deploy_mode=req.deploy_mode,
            plan=req.plan,
            adapter_name=req.adapter_name,
        )
        return {"client": client}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM create client failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create client.") from exc


@router.get("/clients/{site_id}")
async def crm_client_detail(site_id: str) -> dict[str, Any]:
    """Return one client and its tenant catalog summary."""
    try:
        return {"client": admin_db.get_client_detail(site_id)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM client detail failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load client.") from exc


@router.delete("/clients/{site_id}")
async def crm_remove_client(site_id: str) -> dict[str, str]:
    """Soft-delete a client without dropping its tenant schema."""
    try:
        admin_db.remove_client(site_id)
        return {"status": "ok"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM remove client failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to remove client.") from exc


@router.patch("/clients/{site_id}/status")
async def crm_client_status(site_id: str, req: ClientStatusRequest) -> dict[str, Any]:
    """Enable or disable a client tenant."""
    try:
        return {"client": admin_db.set_client_enabled(site_id, req.enabled)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM status update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update client status.") from exc


@router.patch("/clients/{site_id}/token-limits")
async def crm_client_token_limits(site_id: str, req: ClientTokenLimitsRequest) -> dict[str, Any]:
    """Update total client and per-session token limits for one tenant."""
    if req.session_token_limit > req.token_limit:
        raise HTTPException(
            status_code=400,
            detail="Session token limit cannot be greater than the client token limit.",
        )
    try:
        client = admin_db.update_client_token_limits(
            site_id,
            token_limit=req.token_limit,
            session_token_limit=req.session_token_limit,
        )
        return {"client": client}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM token limit update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update token limits.") from exc


@router.patch("/clients/{site_id}/panel-password")
async def crm_client_panel_password(site_id: str, req: ClientPanelPasswordRequest) -> dict[str, Any]:
    """Set or auto-generate the client-panel login password for one tenant."""
    password = admin_db.generate_client_panel_password() if req.auto_generate else str(req.password or "")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required unless auto_generate is true.")
    try:
        client = admin_db.update_client_panel_password(site_id, password)
        return {
            "client": client,
            "generated_password": password if req.auto_generate else "",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM client panel password update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update client panel password.") from exc


@router.delete("/clients/{site_id}/panel-password")
async def crm_revoke_client_panel_password(site_id: str) -> dict[str, Any]:
    """Revoke client-panel password login until a new password is set."""
    try:
        client = admin_db.revoke_client_panel_password(site_id)
        return {"client": client, "status": "ok"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM client panel password revoke failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to revoke client panel password.") from exc


@router.post("/clients/{site_id}/crawl")
async def crm_trigger_client_crawl(site_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Start crawler ingestion for a specific client."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_RUNNING, "Crawler queued.")
    background_tasks.add_task(_run_client_crawl, site_id, client["store_url"])
    return {"status": "ok", "message": "Crawler started in background."}


@router.get("/settings")
async def crm_settings() -> dict[str, Any]:
    """Return editable AI Hub settings."""
    try:
        return admin_db.settings_snapshot()
    except Exception as exc:
        logger.error("CRM settings failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load settings.") from exc


@router.get("/conversations")
async def crm_conversations(range: str = admin_db.ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Return date-grouped customer conversation logs."""
    try:
        return admin_db.conversation_log(range, site_id)
    except Exception as exc:
        logger.error("CRM conversations failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load conversations.") from exc


@router.get("/analytics")
async def crm_analytics(range: str = admin_db.ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Return analytics metrics for the selected range."""
    try:
        return admin_db.analytics_snapshot(range, site_id)
    except Exception as exc:
        logger.error("CRM analytics failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load analytics.") from exc


@router.post("/analytics/summary")
async def crm_analytics_summary(req: AnalyticsSummaryRequest) -> dict[str, Any]:
    """Generate a concise analytics summary with OpenAI when configured."""
    try:
        return admin_db.generate_analytics_summary(req.range, req.site_id)
    except Exception as exc:
        logger.error("CRM analytics summary failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate analytics summary.") from exc


@router.patch("/settings")
async def crm_update_settings(req: SettingsUpdateRequest) -> dict[str, Any]:
    """Persist whitelisted settings to .env."""
    try:
        return admin_db.update_settings(req.values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM settings update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update settings.") from exc


# ── AI Readiness Scanner endpoints ──────────────────────────────────────────


@router.post("/scan/{site_id}")
async def crm_scan_site(site_id: str) -> dict[str, Any]:
    """Run a readiness scan for a client and persist the report."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        from agent.scanner import scan_site
        report = await scan_site(
            client["store_url"],
            site_id,
            adapter_name=str(client.get("adapter_name") or ""),
        )
        report_dict = report.to_dict()
        admin_db.save_readiness_report(site_id, report_dict)
        return {"report": report_dict}
    except Exception as exc:
        logger.error("Readiness scan failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Readiness scan failed.") from exc


@router.get("/scan/{site_id}")
async def crm_get_scan(site_id: str) -> dict[str, Any]:
    """Return the saved readiness report for a client."""
    report = admin_db.get_readiness_report(site_id)
    if not report:
        raise HTTPException(status_code=404, detail="No readiness report found.")
    return {"report": report}


# ── Priority Crawler Report endpoints ───────────────────────────────────────


@router.get("/crawl-report/{site_id}")
async def crm_crawl_report(site_id: str) -> dict[str, Any]:
    """Return the latest crawl coverage report for a client."""
    report = admin_db.get_latest_crawl_report(site_id)
    if not report:
        raise HTTPException(status_code=404, detail="No crawl report found.")
    return {"report": report}


# ── Runtime Capability Engine endpoints ─────────────────────────────────────


@router.get("/capabilities/{site_id}")
async def crm_capabilities(site_id: str) -> dict[str, Any]:
    """Return allowed actions and readiness summary for a client."""
    try:
        from agent.capabilities import get_allowed_actions, capability_summary
        allowed = get_allowed_actions(site_id)
        summary = capability_summary(site_id)
        return {"site_id": site_id, "allowed_actions": sorted(allowed), **summary}
    except Exception as exc:
        logger.error("Capabilities lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Capabilities lookup failed.") from exc


def _run_client_crawl(site_id: str, store_url: str) -> None:
    """Execute a client crawl and persist the outcome for CRM status."""
    try:
        sync_web_crawl(
            store_url,
            max_pages=config.CRAWL_MAX_PAGES,
            max_depth=config.CRAWL_MAX_DEPTH,
            site_id=site_id,
            reconcile_missing=True,
            source_name="crm_crawler",
        )
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_OK, "Crawler completed.")
    except Exception as exc:
        logger.error("CRM crawler failed for %s: %s", site_id, exc)
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_ERROR, str(exc))
