"""CRM admin routes for client lifecycle and setup operations."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

import config
from api.crm_admin.crm_models import ClientPanelPasswordRequest, ClientStatusRequest, ClientTokenLimitsRequest
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _crm_module():
    from api import crm as crm_api

    return crm_api


@router.delete("/clients/{site_id}")
async def crm_remove_client(site_id: str) -> dict[str, str]:
    """Hide a client from CRM lists without dropping tenant data."""
    try:
        admin_db.remove_client(site_id)
        return {"status": "ok"}
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM remove client failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to remove client.") from exc


@router.post("/clients/{site_id}/available")
async def crm_move_client_to_available(site_id: str) -> dict[str, Any]:
    """Move a client back to the Available board without deleting tenant data."""
    try:
        client = admin_db.move_client_to_available(site_id)
        return {"status": "available", "client": client}
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM move client to available failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to move client to available.") from exc


@router.post("/clients/{site_id}/activate")
async def crm_activate_client(site_id: str) -> dict[str, Any]:
    """Move a discovered client into the current roster without starting integration work."""
    try:
        client = admin_db.activate_client(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM activate client failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to activate client.") from exc

    return {
        "client": client,
        "status": "activated",
        "message": "Client moved to Current. Run Crawl now or Run setup when the source site is live.",
    }


@router.patch("/clients/{site_id}/status")
async def crm_client_status(site_id: str, req: ClientStatusRequest) -> dict[str, Any]:
    """Enable or disable a client tenant."""
    try:
        return {"client": admin_db.set_client_enabled(site_id, req.enabled)}
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM client panel password revoke failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to revoke client panel password.") from exc


@router.post("/clients/{site_id}/crawl")
async def crm_trigger_client_crawl(site_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Start crawler ingestion for a specific client."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if str(client.get("status") or "") == admin_db.CLIENT_STATUS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move this client to Current before starting a crawl.",
        )

    admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_RUNNING, "Crawler queued.")
    background_tasks.add_task(_crm_module()._run_client_crawl, site_id, client["store_url"])
    return {"status": "ok", "message": "Crawler started in background."}


@router.post("/clients/{site_id}/auto-integrate")
async def crm_trigger_client_auto_integration(site_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Queue the non-destructive AI Hub setup pipeline for one client."""
    crm_api = _crm_module()
    try:
        crm_api._expire_stale_setup_runs()
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if str(client.get("status") or "") == admin_db.CLIENT_STATUS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move this client to Current before starting setup.",
        )

    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    initialization = vertical_config.get("initialization") if isinstance(vertical_config.get("initialization"), dict) else {}
    if str(initialization.get("status") or "").lower() == admin_db.SETUP_STATUS_RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup run is already running. Stop it before starting another setup.",
        )

    admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_RUNNING, "Setup run queued.")
    background_tasks.add_task(
        crm_api.run_widget_initialization,
        site_id,
        str(client.get("store_url") or ""),
        vertical_key=str(client.get("vertical_key") or admin_db.DEFAULT_CLIENT_VERTICAL_KEY),
        run_crawl=True,
        run_flow=True,
        run_rehearsal=True,
        crawl_max_pages=config.CRAWL_MAX_PAGES,
        crawl_max_depth=config.CRAWL_MAX_DEPTH,
        run_readiness=True,
        run_smoke_tests=True,
    )
    return {
        "status": "queued",
        "message": "Setup run queued: crawl, flow discovery, rehearsal, regression, readiness scan, and assistant smoke tests.",
    }


@router.post("/clients/{site_id}/auto-integrate/cancel")
async def crm_cancel_client_auto_integration(site_id: str) -> dict[str, Any]:
    """Request a cooperative stop for the active setup pipeline."""
    try:
        _crm_module()._expire_stale_setup_runs()
        client = admin_db.request_client_setup_cancel(site_id)
        return {
            "status": "cancel_requested",
            "message": "Setup stop requested. The current stage will stop at the next safe checkpoint.",
            "client": client,
        }
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM setup cancel failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to stop setup run.") from exc


@router.post("/clients/{site_id}/assistant-smoke-tests")
async def crm_run_client_assistant_smoke_tests(site_id: str) -> dict[str, Any]:
    """Run assistant prompt smoke tests without re-crawling or overwriting initialization evidence."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if str(client.get("status") or "") == admin_db.CLIENT_STATUS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move this client to Current before running assistant smoke tests.",
        )

    report = _crm_module().run_assistant_smoke_tests(
        site_id,
        str(client.get("vertical_key") or admin_db.DEFAULT_CLIENT_VERTICAL_KEY),
    )
    updated_client = admin_db.save_client_assistant_smoke_report(site_id, report)
    return {
        "status": report.get("status", "unknown"),
        "message": report.get("message", "Assistant smoke tests completed."),
        "report": report,
        "client": updated_client,
    }
