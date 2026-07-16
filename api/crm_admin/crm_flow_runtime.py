"""CRM crawl and flow background runtime helpers."""

from __future__ import annotations

import logging
from typing import Any

import config
from agent.ingestion_helpers.ingestion_facade import sync_web_crawl
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)


def run_client_crawl(site_id: str, store_url: str) -> None:
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


async def discover_and_save_client_flows(
    client: dict[str, Any],
    max_pages: int,
    *,
    save_regression: bool = True,
) -> dict[str, Any]:
    from agent.flows.flow_discovery import discover_site_flows

    flow_report = await discover_site_flows(
        str(client.get("store_url") or ""),
        str(client.get("site_id") or ""),
        vertical_key=str(client.get("vertical_key") or ""),
        max_pages=max_pages,
    )
    flow_dict = flow_report.to_dict()
    admin_db.save_client_flow_report(str(client.get("site_id") or ""), flow_dict)
    if save_regression:
        compare_and_save_client_flow_regression(client, flow_dict, {})
    return flow_dict


async def rehearse_and_save_client_flows(
    client: dict[str, Any],
    max_steps: int,
    *,
    previous_client: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from agent.flows.flow_rehearsal import rehearse_site_flows

    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    flow_report = vertical_config.get("flow") if isinstance(vertical_config.get("flow"), dict) else {}
    if not flow_report:
        raise LookupError(f"No flow report exists for {client.get('site_id')}.")
    rehearsal_report = await rehearse_site_flows(
        str(client.get("store_url") or ""),
        str(client.get("site_id") or ""),
        flow_report,
        max_steps=max_steps,
    )
    rehearsal_dict = rehearsal_report.to_dict()
    admin_db.save_client_rehearsal_report(str(client.get("site_id") or ""), rehearsal_dict)
    compare_and_save_client_flow_regression(previous_client or client, flow_report, rehearsal_dict)
    return rehearsal_dict


def compare_and_save_client_flow_regression(
    previous_client: dict[str, Any],
    current_flow: dict[str, Any],
    current_rehearsal: dict[str, Any],
) -> dict[str, Any]:
    from agent.flows.flow_regression import build_flow_regression_report

    previous_config = previous_client.get("vertical_config") if isinstance(previous_client.get("vertical_config"), dict) else {}
    previous_flow = previous_config.get("flow") if isinstance(previous_config.get("flow"), dict) else {}
    previous_rehearsal = previous_config.get("rehearsal") if isinstance(previous_config.get("rehearsal"), dict) else {}
    regression_report = build_flow_regression_report(
        previous_flow,
        current_flow,
        previous_rehearsal=previous_rehearsal,
        current_rehearsal=current_rehearsal,
        site_id=str(previous_client.get("site_id") or current_flow.get("site_id") or ""),
        site_url=str(previous_client.get("store_url") or current_flow.get("site_url") or ""),
    )
    regression_dict = regression_report.to_dict()
    admin_db.save_client_regression_report(
        str(previous_client.get("site_id") or current_flow.get("site_id") or ""),
        regression_dict,
    )
    return regression_dict
