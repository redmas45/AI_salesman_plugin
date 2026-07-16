"""FastAPI routes for the AI Hub CRM admin panel."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from agent.adapters.adapter_discovery import render_adapter_code
from agent.client_setup.client_initialization_runtime import run_assistant_smoke_tests, run_widget_initialization
from agent.providers.provider_status import check_azure_openai_runtime, provider_usage_status
from agent.security.tenant_isolation import build_tenant_isolation_audit
from api.crm_admin import crm_admin_guard
from api.crm_admin import crm_client_operation_routes
from api.crm_admin import crm_flow_routes
from api.crm_admin import crm_flow_runtime
from api.crm_admin import crm_operations
from api.crm_admin import crm_scan_routes
from api.crm_admin.crm_models import (
    AdapterActionProposalReviewRequest,
    AdapterActionReviewRequest,
    AdapterActionsSaveRequest,
    AnalyticsSummaryRequest,
    ClientCreateRequest,
    ClientVerticalRequest,
    FlowRepairProposalReviewRequest,
    PromptProfileSaveRequest,
    SettingsUpdateRequest,
)
from api.routes.clients import _public_runtime_config, _public_widget_base_url, universal_install_script_tag
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)


def require_admin_token(request: Request) -> None:
    crm_admin_guard.require_admin_token(request)


router = APIRouter(
    prefix="/v1/admin",
    tags=["CRM Admin"],
    dependencies=[Depends(require_admin_token)],
)
router.include_router(crm_flow_routes.router)
router.include_router(crm_scan_routes.router)
router.include_router(crm_client_operation_routes.router)


def _expire_stale_setup_runs() -> None:
    crm_admin_guard.expire_stale_setup_runs()


def _client_adapter_payload(site_id: str) -> dict[str, Any]:
    runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
    return {
        "runtime_config": runtime_config,
        "adapter_code": render_adapter_code(runtime_config),
    }


@router.get("/overview")
async def crm_overview() -> dict[str, Any]:
    """Return dashboard metrics, clients, health, and recent activity."""
    try:
        _expire_stale_setup_runs()
        return admin_db.overview()
    except Exception as exc:
        logger.error("CRM overview failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load CRM overview.") from exc


@router.get("/provider-usage")
async def crm_provider_usage() -> dict[str, Any]:
    """Return AI provider quota, cost, and local token usage status."""
    try:
        return {"provider_usage": provider_usage_status()}
    except Exception as exc:
        logger.error("CRM provider usage failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load provider usage.") from exc


@router.post("/provider-usage/check")
async def crm_check_provider_usage() -> dict[str, Any]:
    """Run a live provider quota check and return the refreshed status."""
    try:
        return {"provider_usage": check_azure_openai_runtime()}
    except Exception as exc:
        logger.error("CRM provider usage check failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to check provider usage.") from exc


@router.get("/clients")
async def crm_clients() -> dict[str, list[dict[str, Any]]]:
    """Return all active CRM clients."""
    try:
        _expire_stale_setup_runs()
        return {"clients": admin_db.list_clients()}
    except Exception as exc:
        logger.error("CRM clients failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load CRM clients.") from exc


@router.get("/verticals")
async def crm_verticals() -> dict[str, Any]:
    """Return built-in vertical definitions for client setup."""
    return {
        "default_vertical_key": admin_db.DEFAULT_CLIENT_VERTICAL_KEY,
        "verticals": admin_db.list_verticals(),
    }


@router.get("/verticals/{vertical_key}")
async def crm_vertical_detail(vertical_key: str) -> dict[str, Any]:
    """Return one built-in vertical definition."""
    try:
        return {"vertical": admin_db.get_vertical_detail(vertical_key)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/installer")
async def crm_universal_installer() -> dict[str, str]:
    """Return the universal installer script used for automatic client onboarding."""
    api_base_url = _public_widget_base_url()
    return {
        "script_tag": universal_install_script_tag(api_base_url=api_base_url),
        "script_url": f"{api_base_url}/install.js",
        "mode": "universal_auto_onboarding",
    }


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
            vertical_key=req.vertical_key,
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
        _expire_stale_setup_runs()
        return {"client": admin_db.get_client_detail(site_id)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM client detail failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load client.") from exc


@router.get("/clients/{site_id}/operation-status")
async def crm_client_operation_status(site_id: str) -> dict[str, Any]:
    """Return backend-backed operation status for one client."""
    try:
        _expire_stale_setup_runs()
        client = admin_db.get_client_detail(site_id)
        return _client_operation_status(client)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM operation status failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load operation status.") from exc


@router.get("/clients/{site_id}/knowledge")
async def crm_client_knowledge(site_id: str, limit: int = 50) -> dict[str, Any]:
    """Return generic knowledge rows for one client."""
    try:
        from db.knowledge_base.knowledge_items import knowledge_preview, knowledge_stats

        safe_limit = max(1, min(int(limit), 500))
        return {
            "stats": knowledge_stats(site_id),
            "items": knowledge_preview(site_id, safe_limit),
        }
    except Exception as exc:
        logger.error("CRM knowledge lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load knowledge items.") from exc


@router.get("/clients/{site_id}/answer-cache")
async def crm_client_answer_cache(site_id: str, limit: int = 20) -> dict[str, Any]:
    """Return tenant-local answer cache stats and recent reusable answers."""
    try:
        from db.cache.answer_cache import answer_cache_summary

        safe_limit = max(1, min(int(limit), 100))
        return {"answer_cache": answer_cache_summary(site_id, limit=safe_limit)}
    except Exception as exc:
        logger.error("CRM answer cache lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load answer cache.") from exc


@router.get("/clients/{site_id}/isolation-audit")
async def crm_client_isolation_audit(site_id: str) -> dict[str, Any]:
    """Return explicit tenant/RAG isolation checks for one client."""
    try:
        from db.knowledge_base.knowledge_items import knowledge_preview, knowledge_stats

        client = admin_db.get_client_detail(site_id)
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        prompt_profile = admin_db.get_client_prompt_profile(site_id)
        knowledge = {
            "stats": knowledge_stats(site_id),
            "items": knowledge_preview(site_id, 10),
        }
        answer_cache = admin_db._safe_answer_cache_summary(site_id)
        return {
            "audit": build_tenant_isolation_audit(
                site_id=site_id,
                client=client,
                runtime_config=runtime_config,
                prompt_profile=prompt_profile,
                knowledge=knowledge,
                answer_cache=answer_cache,
            )
        }
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM isolation audit failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to run isolation audit.") from exc


@router.get("/clients/{site_id}/adapter")
async def crm_client_adapter(site_id: str) -> dict[str, Any]:
    """Return generated adapter runtime config and readable code for one client."""
    try:
        return _client_adapter_payload(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM adapter lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load adapter config.") from exc


@router.patch("/clients/{site_id}/adapter/actions")
async def crm_save_client_adapter_actions(site_id: str, req: AdapterActionsSaveRequest) -> dict[str, Any]:
    """Replace the generated adapter action map with CRM-reviewed actions."""
    try:
        admin_db.update_client_adapter_actions(site_id, req.actions)
        return _client_adapter_payload(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM adapter action save failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to save adapter actions.") from exc


@router.post("/clients/{site_id}/adapter/action-candidates/review")
async def crm_review_client_adapter_action(site_id: str, req: AdapterActionReviewRequest) -> dict[str, Any]:
    """Approve or reject one discovered adapter action candidate."""
    try:
        admin_db.review_client_action_candidate(
            site_id,
            req.candidate,
            decision=req.decision,
            action_name=req.action_name,
            note=req.note,
        )
        return _client_adapter_payload(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM adapter action review failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to review adapter action candidate.") from exc


@router.post("/clients/{site_id}/adapter/action-proposals/refresh")
async def crm_refresh_client_adapter_action_proposals(site_id: str) -> dict[str, Any]:
    """Refresh CRM-reviewable adapter action repair proposals."""
    try:
        admin_db.refresh_client_action_proposals(site_id)
        return _client_adapter_payload(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM adapter action proposal refresh failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to refresh adapter action proposals.") from exc


@router.post("/clients/{site_id}/adapter/action-proposals/review")
async def crm_review_client_adapter_action_proposal(
    site_id: str,
    req: AdapterActionProposalReviewRequest,
) -> dict[str, Any]:
    """Approve or reject one adapter action repair proposal."""
    try:
        admin_db.review_client_action_proposal(site_id, req.proposal, decision=req.decision, note=req.note)
        return _client_adapter_payload(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM adapter action proposal review failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to review adapter action proposal.") from exc


@router.post("/clients/{site_id}/adapter/flow-repair-proposals/review")
async def crm_review_client_flow_repair_proposal(
    site_id: str,
    req: FlowRepairProposalReviewRequest,
) -> dict[str, Any]:
    """Approve or reject one flow-level repair proposal."""
    try:
        admin_db.review_client_flow_repair_proposal(site_id, req.proposal, decision=req.decision, note=req.note)
        return _client_adapter_payload(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow repair proposal review failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to review flow repair proposal.") from exc


@router.get("/clients/{site_id}/prompt-profile")
async def crm_client_prompt_profile(site_id: str) -> dict[str, Any]:
    """Return the prompt profile and versions for one client."""
    try:
        return admin_db.get_client_prompt_profile(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM prompt profile lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load prompt profile.") from exc


@router.post("/clients/{site_id}/prompt-profile")
async def crm_save_client_prompt_profile(site_id: str, req: PromptProfileSaveRequest) -> dict[str, Any]:
    """Save a draft or published prompt version for one client."""
    try:
        return admin_db.save_client_prompt_profile(
            site_id,
            name=req.name,
            system_prompt=req.system_prompt,
            developer_rules=req.developer_rules,
            publish=req.publish,
            changelog=req.changelog,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM prompt profile save failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to save prompt profile.") from exc


@router.post("/prompt-versions/{version_id}/publish")
async def crm_publish_prompt_version(version_id: str) -> dict[str, Any]:
    """Publish an existing prompt version."""
    try:
        return admin_db.publish_prompt_version(version_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM prompt publish failed for %s: %s", version_id, exc)
        raise HTTPException(status_code=500, detail="Failed to publish prompt version.") from exc


@router.patch("/clients/{site_id}/vertical")
async def crm_client_vertical(site_id: str, req: ClientVerticalRequest) -> dict[str, Any]:
    """Update the vertical metadata used by a client workspace."""
    try:
        return {"client": admin_db.update_client_vertical(site_id, req.vertical_key)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM vertical update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update client vertical.") from exc


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


# ── Priority Crawler Report endpoints ───────────────────────────────────────


# ── Runtime Capability Engine endpoints ─────────────────────────────────────


def _client_operation_status(client: dict[str, Any]) -> dict[str, Any]:
    return crm_operations.client_operation_status(client)


def _run_client_crawl(site_id: str, store_url: str) -> None:
    crm_flow_runtime.run_client_crawl(site_id, store_url)


async def _discover_and_save_client_flows(
    client: dict[str, Any],
    max_pages: int,
    *,
    save_regression: bool = True,
) -> dict[str, Any]:
    return await crm_flow_runtime.discover_and_save_client_flows(client, max_pages, save_regression=save_regression)


async def _rehearse_and_save_client_flows(
    client: dict[str, Any],
    max_steps: int,
    *,
    previous_client: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await crm_flow_runtime.rehearse_and_save_client_flows(client, max_steps=max_steps, previous_client=previous_client)
