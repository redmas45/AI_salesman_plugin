"""FastAPI routes for the AI Hub CRM admin panel."""

from __future__ import annotations

import logging
import os
import hmac
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

import config
from agent.adapter_discovery import render_adapter_code
from agent.client_initialization import run_assistant_smoke_tests, run_widget_initialization
from agent.ingestion import sync_web_crawl
from agent.provider_status import check_openai_runtime_quota, provider_usage_status
from agent.tenant_isolation import build_tenant_isolation_audit
from api.routes.clients import _public_runtime_config, _public_widget_base_url, universal_install_script_tag
from db import admin as admin_db

logger = logging.getLogger(__name__)

ADMIN_TOKEN_HEADER = "x-crm-admin-token"
MAX_CLIENT_NAME_LENGTH = 120
MAX_SITE_ID_LENGTH = 80
MAX_URL_LENGTH = 500
MAX_ADAPTER_NAME_LENGTH = 160
MAX_PLAN_LENGTH = 80
MAX_VERTICAL_KEY_LENGTH = 80
MIN_ADMIN_TOKEN_LENGTH = 12


class ClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_CLIENT_NAME_LENGTH)
    store_url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)
    site_id: str | None = Field(default=None, max_length=MAX_SITE_ID_LENGTH)
    deploy_mode: str = Field(default=admin_db.DEFAULT_DEPLOY_MODE, max_length=40)
    plan: str = Field(default=admin_db.DEFAULT_PLAN, max_length=MAX_PLAN_LENGTH)
    vertical_key: str = Field(
        default=admin_db.DEFAULT_CLIENT_VERTICAL_KEY,
        max_length=MAX_VERTICAL_KEY_LENGTH,
    )
    adapter_name: str = Field(
        default=admin_db.DEFAULT_ADAPTER_NAME,
        max_length=MAX_ADAPTER_NAME_LENGTH,
    )


class ClientVerticalRequest(BaseModel):
    vertical_key: str = Field(..., min_length=1, max_length=MAX_VERTICAL_KEY_LENGTH)


class PromptProfileSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    system_prompt: str = Field(..., min_length=1, max_length=12000)
    developer_rules: str = Field(default="", max_length=12000)
    publish: bool = False
    changelog: str = Field(default="", max_length=500)


class AdapterActionsSaveRequest(BaseModel):
    actions: dict[str, Any] = Field(default_factory=dict)


class AdapterActionReviewRequest(BaseModel):
    candidate: dict[str, Any] = Field(default_factory=dict)
    decision: str = Field(..., min_length=1, max_length=20)
    action_name: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=500)


class AdapterActionProposalReviewRequest(BaseModel):
    proposal: dict[str, Any] = Field(default_factory=dict)
    decision: str = Field(..., min_length=1, max_length=20)
    note: str = Field(default="", max_length=500)


class FlowRepairProposalReviewRequest(BaseModel):
    proposal: dict[str, Any] = Field(default_factory=dict)
    decision: str = Field(..., min_length=1, max_length=20)
    note: str = Field(default="", max_length=500)


class FlowDiscoveryRequest(BaseModel):
    max_pages: int = Field(default=6, ge=1, le=20)


class FlowRehearsalRequest(BaseModel):
    max_steps: int = Field(default=24, ge=1, le=80)


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


def _expire_stale_setup_runs() -> None:
    try:
        expired = admin_db.expire_stale_client_initialization_runs(config.SETUP_RUN_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("CRM stale setup sweep failed: %s", exc)
        return
    if expired:
        logger.warning("CRM marked %s stale setup run(s) as timed out.", expired)


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
        return {"provider_usage": check_openai_runtime_quota()}
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
        from db.knowledge import knowledge_preview, knowledge_stats

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
        from db.answer_cache import answer_cache_summary

        safe_limit = max(1, min(int(limit), 100))
        return {"answer_cache": answer_cache_summary(site_id, limit=safe_limit)}
    except Exception as exc:
        logger.error("CRM answer cache lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load answer cache.") from exc


@router.get("/clients/{site_id}/isolation-audit")
async def crm_client_isolation_audit(site_id: str) -> dict[str, Any]:
    """Return explicit tenant/RAG isolation checks for one client."""
    try:
        from db.knowledge import knowledge_preview, knowledge_stats

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
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
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
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
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
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
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
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
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
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
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
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow repair proposal review failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to review flow repair proposal.") from exc


@router.get("/clients/{site_id}/flows")
async def crm_client_flows(site_id: str) -> dict[str, Any]:
    """Return the latest server-side website flow graph for one client."""
    try:
        client = admin_db.get_client_detail(site_id)
        vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
        flow = vertical_config.get("flow") if isinstance(vertical_config.get("flow"), dict) else {}
        if not flow:
            raise LookupError(f"No flow report exists for {site_id}.")
        return {"flow": flow}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load flow report.") from exc


@router.post("/clients/{site_id}/flows/discover")
async def crm_discover_client_flows(site_id: str, req: FlowDiscoveryRequest) -> dict[str, Any]:
    """Run server-side browser flow discovery and persist the report."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        flow = await _discover_and_save_client_flows(client, req.max_pages)
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "flow": flow,
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
    except Exception as exc:
        logger.error("CRM flow discovery failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to discover website flows.") from exc


@router.get("/clients/{site_id}/flows/regression")
async def crm_client_flow_regression(site_id: str) -> dict[str, Any]:
    """Return the latest flow regression report for one client."""
    try:
        client = admin_db.get_client_detail(site_id)
        vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
        regression = vertical_config.get("regression") if isinstance(vertical_config.get("regression"), dict) else {}
        if not regression:
            raise LookupError(f"No flow regression report exists for {site_id}.")
        return {"regression": regression}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow regression lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load flow regression report.") from exc


@router.get("/clients/{site_id}/flows/rehearsal")
async def crm_client_flow_rehearsal(site_id: str) -> dict[str, Any]:
    """Return the latest safe flow rehearsal report for one client."""
    try:
        client = admin_db.get_client_detail(site_id)
        vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
        rehearsal = vertical_config.get("rehearsal") if isinstance(vertical_config.get("rehearsal"), dict) else {}
        if not rehearsal:
            raise LookupError(f"No flow rehearsal report exists for {site_id}.")
        return {"rehearsal": rehearsal}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow rehearsal lookup failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load flow rehearsal report.") from exc


@router.post("/clients/{site_id}/flows/rehearse")
async def crm_rehearse_client_flows(site_id: str, req: FlowRehearsalRequest) -> dict[str, Any]:
    """Safely rehearse discovered flow targets and persist the report."""
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        rehearsal = await _rehearse_and_save_client_flows(client, req.max_steps)
        runtime_config = _public_runtime_config(site=site_id, api_base_url=_public_widget_base_url())
        return {
            "rehearsal": rehearsal,
            "runtime_config": runtime_config,
            "adapter_code": render_adapter_code(runtime_config),
        }
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM flow rehearsal failed for %s: %s", site_id, exc)
        raise HTTPException(status_code=500, detail="Failed to rehearse website flows.") from exc


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


@router.delete("/clients/{site_id}")
async def crm_remove_client(site_id: str) -> dict[str, str]:
    """Hide a client from CRM lists without dropping tenant data."""
    try:
        admin_db.remove_client(site_id)
        return {"status": "ok"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CRM move client to available failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to move client to available.") from exc


@router.post("/clients/{site_id}/activate")
async def crm_activate_client(site_id: str) -> dict[str, Any]:
    """Move a discovered client into the current roster without starting integration work."""
    try:
        client = admin_db.activate_client(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
    if str(client.get("status") or "") == admin_db.CLIENT_STATUS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move this client to Current before starting a crawl.",
        )

    admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_RUNNING, "Crawler queued.")
    background_tasks.add_task(_run_client_crawl, site_id, client["store_url"])
    return {"status": "ok", "message": "Crawler started in background."}


@router.post("/clients/{site_id}/auto-integrate")
async def crm_trigger_client_auto_integration(site_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Queue the non-destructive AI Hub setup pipeline for one client."""
    try:
        _expire_stale_setup_runs()
        client = admin_db.get_client_detail(site_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
        run_widget_initialization,
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
        _expire_stale_setup_runs()
        client = admin_db.request_client_setup_cancel(site_id)
        return {
            "status": "cancel_requested",
            "message": "Setup stop requested. The current stage will stop at the next safe checkpoint.",
            "client": client,
        }
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if str(client.get("status") or "") == admin_db.CLIENT_STATUS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move this client to Current before running assistant smoke tests.",
        )

    report = run_assistant_smoke_tests(
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
        previous_client = client
        await _discover_and_save_client_flows(client, max_pages=6, save_regression=False)
        client = admin_db.get_client_detail(site_id)
        await _rehearse_and_save_client_flows(client, max_steps=24, previous_client=previous_client)
        client = admin_db.get_client_detail(site_id)
        from agent.scanner import scan_site
        report = await scan_site(
            client["store_url"],
            site_id,
            adapter_name=str(client.get("adapter_name") or ""),
            vertical_key=str(client.get("vertical_key") or ""),
            vertical_config=client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {},
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


def _client_operation_status(client: dict[str, Any]) -> dict[str, Any]:
    site_id = str(client.get("site_id") or "")
    vertical_config = _dict_value(client.get("vertical_config"))
    return {
        "site_id": site_id,
        "generated_at": _utc_now(),
        "operations": {
            "crawl": _crawl_operation_status(client),
            "readiness": _readiness_operation_status(client),
            "integration": _integration_operation_status(client, vertical_config),
        },
    }


def _crawl_operation_status(client: dict[str, Any]) -> dict[str, Any]:
    site_id = str(client.get("site_id") or "")
    raw_status = str(client.get("last_crawl_status") or admin_db.CRAWL_STATUS_NOT_STARTED).lower()
    message = str(client.get("last_crawl_message") or "")
    updated_at = str(client.get("last_crawl_at") or "")
    report = admin_db.get_latest_crawl_report(site_id) or {}
    status = {
        admin_db.CRAWL_STATUS_RUNNING: "running",
        admin_db.CRAWL_STATUS_OK: "complete",
        admin_db.CRAWL_STATUS_ERROR: "failed",
    }.get(raw_status, "pending")
    stages = [
        _operation_stage("crawl_queue", "Queueing crawl job", "pending", "Waiting for crawl request."),
        _operation_stage("crawl_connect", "Connecting to website", "pending", "Waiting for crawler."),
        _operation_stage("crawl_pages", "Reading pages and routes", "pending", "Waiting for crawler."),
        _operation_stage("crawl_extract", "Extracting records and metadata", "pending", "Waiting for crawler."),
        _operation_stage("crawl_store", "Updating knowledge store", "pending", "Waiting for crawler."),
        _operation_stage("crawl_report", "Refreshing crawl report", "pending", "Waiting for crawler."),
    ]
    if status == "running":
        stages[0] = _operation_stage("crawl_queue", "Queueing crawl job", "complete", "Crawler accepted the request.", completed_at=updated_at)
        stages[1] = _operation_stage("crawl_connect", "Connecting to website", "running", message or "Crawler is connecting to the source website.", started_at=updated_at)
    elif status == "complete":
        pages = int(report.get("pages_visited") or 0)
        products = int(report.get("product_count") or 0)
        duration = float(report.get("duration_ms") or 0.0)
        stages = [
            _operation_stage("crawl_queue", "Queueing crawl job", "complete", "Crawler accepted the request.", completed_at=updated_at),
            _operation_stage("crawl_connect", "Connecting to website", "complete", "Website connection completed.", completed_at=updated_at),
            _operation_stage("crawl_pages", "Reading pages and routes", "complete", f"{pages} pages visited.", completed_at=updated_at),
            _operation_stage("crawl_extract", "Extracting records and metadata", "complete", f"{products} records extracted.", completed_at=updated_at),
            _operation_stage("crawl_store", "Updating knowledge store", "complete", "Knowledge/catalog data refreshed.", completed_at=updated_at),
            _operation_stage("crawl_report", "Refreshing crawl report", "complete", "Crawl report saved.", completed_at=str(report.get("created_at") or updated_at), duration_ms=duration),
        ]
    elif status == "failed":
        stages[0] = _operation_stage("crawl_queue", "Queueing crawl job", "complete", "Crawler accepted the request.", completed_at=updated_at)
        stages[1] = _operation_stage("crawl_connect", "Connecting to website", "failed", message or "Crawler failed.", completed_at=updated_at)
    return _operation(
        "crawl",
        "Crawler run",
        status,
        message or _operation_message(status, "Crawler"),
        stages,
        result_tab="crawl",
        started_at=updated_at if raw_status == admin_db.CRAWL_STATUS_RUNNING else "",
        completed_at=updated_at if status in {"complete", "failed"} else "",
        logs=_stage_logs(stages),
    )


def _readiness_operation_status(client: dict[str, Any]) -> dict[str, Any]:
    site_id = str(client.get("site_id") or "")
    report = admin_db.get_readiness_report(site_id) or {}
    scanned_at = str(report.get("scanned_at") or "")
    capabilities = report.get("capabilities") if isinstance(report.get("capabilities"), list) else []
    supported = sum(
        1
        for item in capabilities
        if isinstance(item, dict) and (item.get("supported") or item.get("blocking") is False)
    )
    total = len(capabilities)
    if not report:
        return _operation(
            "readiness",
            "Readiness scan",
            "pending",
            "No readiness scan has been saved yet.",
            [
                _operation_stage("readiness_context", "Preparing client context", "pending", "Waiting for scan."),
                _operation_stage("readiness_evidence", "Loading latest adapter evidence", "pending", "Waiting for scan."),
                _operation_stage("readiness_scan", "Scanning website capabilities", "pending", "Waiting for scan."),
                _operation_stage("readiness_compare", "Comparing domain action contract", "pending", "Waiting for scan."),
                _operation_stage("readiness_save", "Saving readiness report", "pending", "Waiting for scan."),
            ],
            result_tab="readiness",
        )
    stages = [
        _operation_stage("readiness_context", "Preparing client context", "complete", "Client context loaded.", completed_at=scanned_at),
        _operation_stage("readiness_evidence", "Loading latest adapter evidence", "complete", "Adapter evidence loaded.", completed_at=scanned_at),
        _operation_stage("readiness_scan", "Scanning website capabilities", "complete", f"{supported}/{total} checks supported.", completed_at=scanned_at),
        _operation_stage("readiness_compare", "Comparing domain action contract", "complete", "Action contract compared.", completed_at=scanned_at),
        _operation_stage("readiness_save", "Saving readiness report", "complete", "Readiness report saved.", completed_at=scanned_at),
    ]
    return _operation(
        "readiness",
        "Readiness scan",
        "complete",
        f"{supported}/{total} readiness checks supported.",
        stages,
        result_tab="readiness",
        completed_at=scanned_at,
        logs=_stage_logs(stages),
    )


def _integration_operation_status(client: dict[str, Any], vertical_config: dict[str, Any]) -> dict[str, Any]:
    initialization = _dict_value(vertical_config.get("initialization"))
    raw_stages = initialization.get("stages") if isinstance(initialization.get("stages"), list) else []
    if not initialization:
        stages = [
            _operation_stage("integration_queue", "Queueing setup run", "pending", "Waiting for setup run."),
            _operation_stage("crawl", "Crawling source website", "pending", "Waiting for setup run."),
            _operation_stage("flow_discovery", "Discovering routes and actions", "pending", "Waiting for setup run."),
            _operation_stage("flow_rehearsal", "Validating adapter behavior", "pending", "Waiting for setup run."),
            _operation_stage("assistant_smoke_tests", "Running prompt checks", "pending", "Waiting for setup run."),
            _operation_stage("integration_save", "Saving evidence", "pending", "Waiting for setup run."),
        ]
        return _operation(
            "integration",
            "Setup run",
            "pending",
            "No setup run has been saved yet.",
            stages,
            result_tab="integration",
        )
    stages = [_integration_stage_from_saved(stage) for stage in raw_stages if isinstance(stage, dict)]
    if not stages:
        stages = [_operation_stage("integration_queue", "Queueing setup run", "running", "Setup run accepted.")]
    if all(stage["status"] != "running" for stage in stages):
        stages.append(_operation_stage("integration_save", "Saving evidence", "complete", "Setup evidence saved.", completed_at=str(initialization.get("completed_at") or "")))
    status = _normalize_operation_status(str(initialization.get("status") or "unknown"), stages)
    message = str(initialization.get("error") or "") or _operation_message(status, "Setup run")
    if status == "running" and initialization.get("cancel_requested"):
        message = "Setup stop requested. Waiting for the current stage checkpoint."
    return _operation(
        "integration",
        "Setup run",
        status,
        message,
        stages,
        result_tab="integration",
        started_at=str(initialization.get("started_at") or ""),
        completed_at=str(initialization.get("completed_at") or ""),
        duration_ms=float(initialization.get("duration_ms") or 0.0),
        logs=_stage_logs(stages),
    )


def _integration_stage_from_saved(stage: dict[str, Any]) -> dict[str, Any]:
    name = str(stage.get("name") or "stage")
    return _operation_stage(
        name,
        _integration_stage_label(name),
        _normalize_stage_status(str(stage.get("status") or "unknown")),
        str(stage.get("message") or ""),
        started_at=str(stage.get("started_at") or ""),
        completed_at=str(stage.get("completed_at") or ""),
        duration_ms=float(stage.get("duration_ms") or 0.0),
        detail={key: value for key, value in stage.items() if key not in {"name", "status", "message", "started_at", "completed_at", "duration_ms"}},
    )


def _integration_stage_label(name: str) -> str:
    return {
        "crawl": "Crawling source website",
        "flow_discovery": "Discovering routes and actions",
        "flow_rehearsal": "Validating adapter behavior",
        "flow_regression": "Comparing flow changes",
        "readiness_scan": "Scanning readiness",
        "assistant_smoke_tests": "Running prompt checks",
        "integration_save": "Saving evidence",
        "integration_queue": "Queueing setup run",
    }.get(name, name.replace("_", " ").title())


def _normalize_stage_status(status: str) -> str:
    normalized = status.lower()
    if normalized in {"ok", "complete", "completed", "success", "passed"}:
        return "complete"
    if normalized in {"failed", "error", "canceled", "cancelled", "timed_out", "timeout"}:
        return "failed"
    if normalized == "running":
        return "running"
    if normalized == "skipped":
        return "skipped"
    return "pending"


def _normalize_operation_status(raw_status: str, stages: list[dict[str, Any]]) -> str:
    normalized = raw_status.lower()
    if any(stage["status"] == "running" for stage in stages) or normalized == "running":
        return "running"
    if any(stage["status"] == "failed" for stage in stages) or normalized in {"failed", "error", "canceled", "cancelled", "timed_out", "timeout"}:
        return "failed"
    if stages and all(stage["status"] in {"complete", "skipped"} for stage in stages):
        return "complete"
    if normalized in {"ok", "complete", "completed", "success"}:
        return "complete"
    return "pending"


def _operation(
    kind: str,
    label: str,
    status: str,
    message: str,
    stages: list[dict[str, Any]],
    *,
    result_tab: str,
    started_at: str = "",
    completed_at: str = "",
    duration_ms: float = 0.0,
    logs: list[str] | None = None,
) -> dict[str, Any]:
    progress = _operation_progress(stages)
    return {
        "kind": kind,
        "label": label,
        "status": status,
        "message": message,
        "progress": progress,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": max(0.0, float(duration_ms or 0.0)),
        "result_tab": result_tab,
        "stages": stages,
        "logs": logs or [],
    }


def _operation_stage(
    name: str,
    label: str,
    status: str,
    message: str,
    *,
    started_at: str = "",
    completed_at: str = "",
    duration_ms: float = 0.0,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "status": status,
        "message": message,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": max(0.0, float(duration_ms or 0.0)),
        "detail": detail or {},
    }


def _operation_progress(stages: list[dict[str, Any]]) -> int:
    if not stages:
        return 0
    complete_weight = sum(1 for stage in stages if stage.get("status") in {"complete", "skipped"})
    running_weight = 0.5 if any(stage.get("status") == "running" for stage in stages) else 0
    return min(100, int(((complete_weight + running_weight) / len(stages)) * 100))


def _operation_message(status: str, label: str) -> str:
    if status == "running":
        return f"{label} is running."
    if status == "complete":
        return f"{label} completed."
    if status == "failed":
        return f"{label} failed."
    return f"{label} has not started."


def _stage_logs(stages: list[dict[str, Any]]) -> list[str]:
    logs: list[str] = []
    for stage in stages:
        status = str(stage.get("status") or "unknown")
        label = str(stage.get("label") or stage.get("name") or "Stage")
        message = str(stage.get("message") or "")
        logs.append(f"{label}: {status}{f' - {message}' if message else ''}")
    return logs


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


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


async def _discover_and_save_client_flows(
    client: dict[str, Any],
    max_pages: int,
    *,
    save_regression: bool = True,
) -> dict[str, Any]:
    from agent.flow_discovery import discover_site_flows

    flow_report = await discover_site_flows(
        str(client.get("store_url") or ""),
        str(client.get("site_id") or ""),
        vertical_key=str(client.get("vertical_key") or ""),
        max_pages=max_pages,
    )
    flow_dict = flow_report.to_dict()
    admin_db.save_client_flow_report(str(client.get("site_id") or ""), flow_dict)
    if save_regression:
        _compare_and_save_client_flow_regression(client, flow_dict, {})
    return flow_dict


async def _rehearse_and_save_client_flows(
    client: dict[str, Any],
    max_steps: int,
    *,
    previous_client: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from agent.flow_rehearsal import rehearse_site_flows

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
    _compare_and_save_client_flow_regression(previous_client or client, flow_report, rehearsal_dict)
    return rehearsal_dict


def _compare_and_save_client_flow_regression(
    previous_client: dict[str, Any],
    current_flow: dict[str, Any],
    current_rehearsal: dict[str, Any],
) -> dict[str, Any]:
    from agent.flow_regression import build_flow_regression_report

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
    admin_db.save_client_regression_report(str(previous_client.get("site_id") or current_flow.get("site_id") or ""), regression_dict)
    return regression_dict
