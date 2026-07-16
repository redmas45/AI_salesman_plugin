"""CRM admin readiness scan, crawl report, and capability routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _vertical_config(client: dict[str, Any]) -> dict[str, Any]:
    value = client.get("vertical_config")
    return value if isinstance(value, dict) else {}


@router.post("/scan/{site_id}")
async def crm_scan_site(site_id: str) -> dict[str, Any]:
    """Run a readiness scan for a client and persist the report."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        from agent.scanning.scanner import scan_site
        from api import crm as crm_api

        previous_client = client
        await crm_api._discover_and_save_client_flows(client, max_pages=6, save_regression=False)
        client = admin_db.get_client_detail(site_id)
        await crm_api._rehearse_and_save_client_flows(client, max_steps=24, previous_client=previous_client)
        client = admin_db.get_client_detail(site_id)
        report = await scan_site(
            client["store_url"],
            site_id,
            adapter_name=str(client.get("adapter_name") or ""),
            vertical_key=str(client.get("vertical_key") or ""),
            vertical_config=_vertical_config(client),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No readiness report found.")
    return {"report": report}


@router.get("/crawl-report/{site_id}")
async def crm_crawl_report(site_id: str) -> dict[str, Any]:
    """Return the latest crawl coverage report for a client."""
    report = admin_db.get_latest_crawl_report(site_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No crawl report found.")
    return {"report": report}


@router.get("/capabilities/{site_id}")
async def crm_capabilities(site_id: str) -> dict[str, Any]:
    """Return allowed actions and readiness summary for a client."""
    try:
        from agent.action_helpers.capabilities import capability_summary, get_allowed_actions

        allowed = get_allowed_actions(site_id)
        summary = capability_summary(site_id)
        return {"site_id": site_id, "allowed_actions": sorted(allowed), **summary}
    except Exception as exc:
        logger.error("Capabilities lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Capabilities lookup failed.") from exc
