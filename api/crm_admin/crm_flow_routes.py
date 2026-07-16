"""CRM admin routes for client flow discovery, rehearsal, and regression."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from api.crm_admin import crm_flow_runtime
from api.crm_admin.crm_models import FlowDiscoveryRequest, FlowRehearsalRequest
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _vertical_config(client: dict[str, Any]) -> dict[str, Any]:
    value = client.get("vertical_config")
    return value if isinstance(value, dict) else {}


def _runtime_adapter_payload(site_id: str, artifact_key: str, artifact: dict[str, Any]) -> dict[str, Any]:
    from api import crm as crm_api

    runtime_config = crm_api._public_runtime_config(
        site=site_id,
        api_base_url=crm_api._public_widget_base_url(),
    )
    return {
        artifact_key: artifact,
        "runtime_config": runtime_config,
        "adapter_code": crm_api.render_adapter_code(runtime_config),
    }


@router.get("/clients/{site_id}/flows")
async def crm_client_flows(site_id: str) -> dict[str, Any]:
    """Return the latest server-side website flow graph for one client."""
    try:
        client = admin_db.get_client_detail(site_id)
        flow = _vertical_config(client).get("flow")
        if not isinstance(flow, dict) or not flow:
            raise LookupError(f"No flow report exists for {site_id}.")
        return {"flow": flow}
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load flow report.") from exc


@router.post("/clients/{site_id}/flows/discover")
async def crm_discover_client_flows(site_id: str, req: FlowDiscoveryRequest) -> dict[str, Any]:
    """Run server-side browser flow discovery and persist the report."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        flow = await crm_flow_runtime.discover_and_save_client_flows(client, req.max_pages)
        return _runtime_adapter_payload(site_id, "flow", flow)
    except Exception as exc:
        logger.error("CRM flow discovery failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to discover website flows.") from exc


@router.get("/clients/{site_id}/flows/regression")
async def crm_client_flow_regression(site_id: str) -> dict[str, Any]:
    """Return the latest flow regression report for one client."""
    try:
        client = admin_db.get_client_detail(site_id)
        regression = _vertical_config(client).get("regression")
        if not isinstance(regression, dict) or not regression:
            raise LookupError(f"No flow regression report exists for {site_id}.")
        return {"regression": regression}
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow regression lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load flow regression report.") from exc


@router.get("/clients/{site_id}/flows/rehearsal")
async def crm_client_flow_rehearsal(site_id: str) -> dict[str, Any]:
    """Return the latest safe flow rehearsal report for one client."""
    try:
        client = admin_db.get_client_detail(site_id)
        rehearsal = _vertical_config(client).get("rehearsal")
        if not isinstance(rehearsal, dict) or not rehearsal:
            raise LookupError(f"No flow rehearsal report exists for {site_id}.")
        return {"rehearsal": rehearsal}
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow rehearsal lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load flow rehearsal report.") from exc


@router.post("/clients/{site_id}/flows/rehearse")
async def crm_rehearse_client_flows(site_id: str, req: FlowRehearsalRequest) -> dict[str, Any]:
    """Safely rehearse discovered flow targets and persist the report."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        rehearsal = await crm_flow_runtime.rehearse_and_save_client_flows(client, req.max_steps)
        return _runtime_adapter_payload(site_id, "rehearsal", rehearsal)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow rehearsal failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to rehearse website flows.") from exc
