"""Client and widget serving routes for the AI Hub runtime API."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

import config
from agent.action_helpers.action_readiness import action_readiness_for
from agent.adapters.adapter_discovery import build_discovery, render_adapter_code
from agent.action_helpers.barrier_policy import build_barrier_action_policy
from api.routes.client_widgets import (
    client_frame,
    client_registration,
    client_runtime_config,
    client_scripts,
    client_security,
    client_widget_events,
)
from api.routes.client_widgets.client_models import (
    MAX_DISCOVERY_LABEL_LENGTH,
    WidgetActionExecutionEventRequest,
    WidgetActionValidationRequest,
    WidgetInteractionEventRequest,
    WidgetPolicyEventRequest,
    WidgetRegisterRequest,
)
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)

GENERIC_VERTICAL_KEY = admin_db.DEFAULT_CLIENT_VERTICAL_KEY

router = APIRouter(tags=["Plugin"])


def _safe_site_id(raw: str) -> str:
    return admin_db._safe_site_id(raw or "site_1")


def _safe_script_base_url(raw: str) -> str:
    return client_scripts.safe_script_base_url(raw)


def _public_script_base_url(raw: str) -> str:
    return client_scripts.public_script_base_url(raw)


def _is_local_script_host(hostname: str) -> bool:
    return client_scripts.is_local_script_host(hostname)


def _request_public_base_url(request: Request | None = None) -> str:
    return client_scripts.request_public_base_url(request)


def _public_widget_base_url(request: Request | None = None) -> str:
    return client_scripts.public_widget_base_url(request)


def _load_plugin_script(script_name: str, *, site: str, api_base_url: str) -> str:
    return client_scripts.load_plugin_script(script_name, site=site, api_base_url=api_base_url)


def _load_widget_script(*, site: str, api_base_url: str) -> str:
    return client_scripts.load_widget_script(site=site, api_base_url=api_base_url)


def _load_adapter_script(*, site: str, api_base_url: str) -> str:
    return client_scripts.load_adapter_script(site=site, api_base_url=api_base_url)


def _disabled_widget_script(*, site: str) -> str:
    return client_scripts.disabled_widget_script(site=site)


def _client_scripts_can_load(site: str) -> bool:
    return client_scripts.client_scripts_can_load(site, client_store=admin_db)


def _script_url(*, api_base_url: str, script_name: str, site: str | None = None) -> str:
    return client_scripts.script_url(api_base_url=api_base_url, script_name=script_name, site=site)


def _render_install_script(*, site: str | None = None, api_base_url: str) -> str:
    return client_scripts.render_install_script(site=site, api_base_url=api_base_url)


def universal_install_script_tag(*, api_base_url: str | None = None) -> str:
    """Return the universal one-line installer for auto-onboarded client sites."""
    return client_scripts.universal_install_script_tag(api_base_url=api_base_url)


def _public_runtime_config(*, site: str, api_base_url: str) -> dict[str, Any]:
    return client_runtime_config.public_runtime_config(
        site=site,
        api_base_url=api_base_url,
        client_store=admin_db,
        build_barrier_policy=build_barrier_action_policy,
        build_action_readiness=action_readiness_for,
    )


def _safe_client_detail(site: str) -> dict[str, Any]:
    return client_runtime_config.safe_client_detail(site, admin_db)


def _safe_vertical_detail(vertical_key: str | None) -> dict[str, Any]:
    return client_runtime_config.safe_vertical_detail(vertical_key, admin_db)


def _install_asset_config(*, site: str, api_base_url: str) -> dict[str, str]:
    return client_runtime_config.install_asset_config(site=site, api_base_url=api_base_url)


def _runtime_vertical_config(vertical: dict[str, Any]) -> dict[str, Any]:
    return client_runtime_config.runtime_vertical_config(vertical, GENERIC_VERTICAL_KEY)


def _runtime_adapter_config(
    client: dict[str, Any],
    vertical_config: dict[str, Any],
    selectors: dict[str, Any],
) -> dict[str, Any]:
    return client_runtime_config.runtime_adapter_config(
        client,
        vertical_config,
        selectors,
        client_store=admin_db,
        build_barrier_policy=build_barrier_action_policy,
        build_action_readiness=action_readiness_for,
    )


def _durable_action_events_for_client(site_id: str) -> list[dict[str, Any]]:
    return client_runtime_config.durable_action_events_for_client(site_id, admin_db)


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    return client_runtime_config.dict_value(data, key)


def _list_value(data: dict[str, Any], key: str) -> list[Any]:
    return client_runtime_config.list_value(data, key)


def _validated_runtime_capabilities(raw: Any) -> dict[str, Any]:
    return client_runtime_config.validated_runtime_capabilities(raw)


def _bounded_capability_number(value: Any) -> int:
    return client_runtime_config.bounded_capability_number(value)


def _registration_vertical_decision(
    client: dict[str, Any],
    detected_vertical_key: str,
    confidence: float,
) -> dict[str, Any]:
    return client_registration.registration_vertical_decision(
        client,
        detected_vertical_key,
        confidence,
        generic_vertical_key=GENERIC_VERTICAL_KEY,
    )


def _clean_vertical_key(value: Any) -> str:
    return client_registration.clean_vertical_key(value, GENERIC_VERTICAL_KEY)


def _registration_vertical_config(
    discovery_config: dict[str, Any],
    runtime_capabilities: dict[str, Any],
    vertical_decision: dict[str, Any],
) -> dict[str, Any]:
    return client_registration.registration_vertical_config(
        discovery_config,
        runtime_capabilities,
        vertical_decision,
    )


def _process_widget_registration(req: WidgetRegisterRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    return client_registration.process_widget_registration(
        req,
        background_tasks,
        client_store=admin_db,
        build_discovery=build_discovery,
        safe_site_id=_safe_site_id,
        safe_script_base_url=_safe_script_base_url,
        validate_runtime_capabilities=_validated_runtime_capabilities,
        seed_generated_prompt_once=_seed_generated_prompt_once,
    )


def _process_action_validation_report(req: WidgetActionValidationRequest) -> dict[str, Any]:
    return client_widget_events.process_action_validation_report(
        req,
        client_store=admin_db,
        safe_site_id=_safe_site_id,
        safe_script_base_url=_safe_script_base_url,
        safe_client_detail=_safe_client_detail,
        dict_value=_dict_value,
    )


def _process_policy_event(req: WidgetPolicyEventRequest) -> dict[str, Any]:
    return client_widget_events.process_policy_event(
        req,
        client_store=admin_db,
        safe_site_id=_safe_site_id,
        safe_script_base_url=_safe_script_base_url,
        safe_client_detail=_safe_client_detail,
    )


def _process_action_execution_event(req: WidgetActionExecutionEventRequest) -> dict[str, Any]:
    return client_widget_events.process_action_execution_event(
        req,
        client_store=admin_db,
        safe_site_id=_safe_site_id,
        safe_script_base_url=_safe_script_base_url,
        safe_client_detail=_safe_client_detail,
    )


def _process_interaction_event(req: WidgetInteractionEventRequest) -> dict[str, Any]:
    return client_widget_events.process_interaction_event(
        req,
        client_store=admin_db,
        safe_site_id=_safe_site_id,
        safe_script_base_url=_safe_script_base_url,
        safe_client_detail=_safe_client_detail,
    )


def same_origin_public_url(url: str, origin: str) -> str:
    return client_widget_events.same_origin_public_url(url, origin)


def _ensure_registration_client(site_id: str, store_url: str, title: str, vertical_key: str) -> dict[str, Any]:
    return client_registration.ensure_registration_client(
        site_id,
        store_url,
        title,
        vertical_key,
        client_store=admin_db,
        safe_script_base_url=_safe_script_base_url,
    )


def _seed_generated_prompt_once(site_id: str, client: dict[str, Any], discovery: Any) -> None:
    try:
        profile = admin_db.get_client_prompt_profile(site_id)
    except LookupError:
        return
    if len(profile.get("versions") or []) > 1:
        return
    admin_db.save_client_prompt_profile(
        site_id,
        name=f"{client.get('name') or site_id} generated prompt",
        system_prompt=discovery.prompt,
        developer_rules=discovery.developer_rules,
        publish=False,
        changelog="Generated from one-line script discovery.",
    )


def _manual_registration_initialization_plan() -> dict[str, bool]:
    """Keep widget registration discovery-only.

    Heavy work must be started from CRM so opening a site with the widget cannot
    unexpectedly crawl, discover flows, or run setup jobs.
    """
    return client_registration.manual_registration_initialization_plan()


def _vertical_config_section(client: dict[str, Any], key: str) -> dict[str, Any]:
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    section = vertical_config.get(key)
    return section if isinstance(section, dict) else {}


def _render_embed_bootstrap(*, site: str, api_base_url: str) -> str:
    return client_scripts.render_embed_bootstrap(site=site, api_base_url=api_base_url)


@router.get("/v1/widget/config")
async def widget_config(
    request: Request,
    site_id: str = config.DEFAULT_SITE_ID,
    site: Optional[str] = None,
    shop: Optional[str] = None,
) -> dict[str, Any]:
    """Return public adapter/runtime config for one tenant."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    client_security.require_allowed_widget_origin(request, safe_site, admin_db.get_client_detail)
    return _public_runtime_config(site=safe_site, api_base_url=_public_widget_base_url(request))


@router.post("/v1/widget/register")
async def widget_register(
    request: Request,
    req: WidgetRegisterRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Register one script-installed page and generate adapter config."""
    client_security.require_claimed_browser_origin(request, req.origin, _safe_script_base_url)
    return _process_widget_registration(req, background_tasks)


@router.post("/v1/widget/action-report")
async def widget_action_report(request: Request, req: WidgetActionValidationRequest) -> dict[str, Any]:
    """Accept non-destructive browser validation of generated adapter actions."""
    client_security.require_claimed_browser_origin(request, req.origin, _safe_script_base_url)
    return _process_action_validation_report(req)


@router.post("/v1/widget/policy-event")
async def widget_policy_event(request: Request, req: WidgetPolicyEventRequest) -> dict[str, Any]:
    """Accept browser runtime evidence when action policy blocks execution."""
    client_security.require_claimed_browser_origin(request, req.origin, _safe_script_base_url)
    return _process_policy_event(req)


@router.post("/v1/widget/action-event")
async def widget_action_event(request: Request, req: WidgetActionExecutionEventRequest) -> dict[str, Any]:
    """Accept browser runtime evidence for executed adapter actions."""
    client_security.require_claimed_browser_origin(request, req.origin, _safe_script_base_url)
    return _process_action_execution_event(req)


@router.post("/v1/widget/interaction-event")
async def widget_interaction_event(request: Request, req: WidgetInteractionEventRequest) -> dict[str, Any]:
    """Accept privacy-safe browser interaction metadata for adapter learning."""
    client_security.require_claimed_browser_origin(request, req.origin, _safe_script_base_url)
    return _process_interaction_event(req)


@router.get("/v1/widget/status")
async def widget_status(
    site_id: str = config.DEFAULT_SITE_ID,
    site: Optional[str] = None,
    shop: Optional[str] = None,
) -> dict[str, Any]:
    """Return the public widget availability state for one tenant."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    return {
        "site_id": safe_site,
        "enabled": admin_db.is_client_widget_enabled(safe_site),
    }


@router.get("/mayabot-frame")
async def serve_plugin_frame(
    request: Request,
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
    parent_origin: Optional[str] = None,
) -> Response:
    """Serve a standalone orb frame for external website modes."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    script_path = f"{_public_widget_base_url(request)}/mayabot-widget.js?site={safe_site}"
    if parent_origin:
        script_path += f"&parent_origin={parent_origin}"

    if not admin_db.is_client_widget_enabled(safe_site):
        return Response(
            content=client_frame.EMPTY_WIDGET_FRAME_HTML,
            media_type="text/html",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    return Response(
        content=client_frame.render_widget_frame_html(script_path),
        media_type="text/html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/mayabot-widget.js")
async def serve_plugin_widget(
    request: Request,
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the full widget app for direct use or inside the external embed frame."""
    explicit_site = site or site_id or shop
    safe_site = _safe_site_id(explicit_site) if explicit_site else ""
    safe_api = _public_widget_base_url(request)
    js_code = (
        _load_widget_script(site=safe_site, api_base_url=safe_api)
        if _client_scripts_can_load(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/mayabot-adapter.js")
async def serve_plugin_adapter(
    request: Request,
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the client-side adapter runtime used by the one-line installer."""
    explicit_site = site or site_id or shop
    safe_site = _safe_site_id(explicit_site) if explicit_site else ""
    safe_api = _public_widget_base_url(request)
    js_code = (
        _load_adapter_script(site=safe_site, api_base_url=safe_api)
        if _client_scripts_can_load(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/mayabot.js")
async def serve_plugin(
    request: Request,
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the public widget loader — inlined directly (no iframe).

    The iframe-based bootstrap (_render_embed_bootstrap) fails with free-tier
    ngrok because the interstitial "Visit Site" page blocks iframe loading.
    Serving the full widget JS directly avoids this issue entirely.
    """
    explicit_site = site or site_id or shop
    safe_site = _safe_site_id(explicit_site) if explicit_site else ""
    safe_api = _public_widget_base_url(request)
    js_code = (
        _load_widget_script(site=safe_site, api_base_url=safe_api)
        if _client_scripts_can_load(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/install.js")
async def serve_install_script(
    request: Request,
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the single script clients paste into their website."""
    explicit_site = site or site_id or shop
    safe_site = _safe_site_id(explicit_site) if explicit_site else ""
    safe_api = _public_widget_base_url(request)
    js_code = (
        _render_install_script(site=safe_site or None, api_base_url=safe_api)
        if _client_scripts_can_load(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )
