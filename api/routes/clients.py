"""Client and widget serving routes for the AI Hub runtime API."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

import config
from agent.action_readiness import action_readiness_for
from agent.adapter_discovery import build_discovery, render_adapter_code
from agent.barrier_policy import build_barrier_action_policy
from agent.sales_intake import sanitize_intake_questions
from db import admin as admin_db

logger = logging.getLogger(__name__)

CLIENT_DISABLED_MESSAGE = "AI assistant is disabled for this client."
DISABLED_WIDGET_DOM_ID = "mayabot-widget"
DISABLED_WIDGET_BOOT_FLAG = "__mayabotBooted"
DISABLED_WIDGET_FRAME_FLAG = "__mayabotFrameLoaded"
DISABLED_WIDGET_REGISTRY = "__mayabotDisabledSites"
INSTALL_REGISTRY_FLAG = "__aihubInstallLoadedSites"
ADAPTER_SCRIPT_NAME = "mayabot-adapter.js"
WIDGET_SCRIPT_NAME = "mayabot.js"
PLUGIN_DIR = Path(__file__).parent.parent.parent / "plugin"
RUNTIME_CONFIG_VERSION = 1
GENERIC_VERTICAL_KEY = admin_db.DEFAULT_CLIENT_VERTICAL_KEY
GENERIC_TO_VERTICAL_CONFIDENCE = 0.6
EXISTING_VERTICAL_SWITCH_CONFIDENCE = 0.86
MAX_DISCOVERY_ELEMENTS = 80
MAX_DISCOVERY_TEXT_LENGTH = 3000
MAX_DISCOVERY_HTML_LENGTH = 6000
MAX_DISCOVERY_LABEL_LENGTH = 160
MAX_DISCOVERY_SELECTOR_LENGTH = 260
MAX_DISCOVERY_HREF_LENGTH = 600
MAX_RUNTIME_CAPABILITY_TEXT_LENGTH = 240
MAX_RUNTIME_CAPABILITY_NUMBER = 10000
RUNTIME_CAPABILITY_BOOL_KEYS = frozenset({
    "script_loaded",
    "secure_context",
    "top_level_window",
    "fetch_api",
    "permissions_api",
    "media_devices_api",
    "get_user_media_api",
    "cookies_enabled",
    "shadow_dom_api",
    "custom_elements_api",
    "mutation_observer_api",
})
RUNTIME_CAPABILITY_TEXT_KEYS = frozenset({
    "reported_at",
    "origin",
    "url",
    "protocol",
    "document_ready_state",
    "microphone_permission",
    "session_storage",
    "local_storage",
    "language",
    "user_agent",
})
RUNTIME_CAPABILITY_NUMBER_KEYS = frozenset({"iframe_count"})

router = APIRouter(tags=["Plugin"])


DISCOVERY_ELEMENT_FIELD_LIMITS = {
    "label": MAX_DISCOVERY_LABEL_LENGTH,
    "selector": MAX_DISCOVERY_SELECTOR_LENGTH,
    "href": MAX_DISCOVERY_HREF_LENGTH,
    "input_selector": MAX_DISCOVERY_SELECTOR_LENGTH,
    "submit_selector": MAX_DISCOVERY_SELECTOR_LENGTH,
}


class DiscoveryElement(BaseModel):
    label: str = Field(default="", max_length=MAX_DISCOVERY_LABEL_LENGTH)
    selector: str = Field(default="", max_length=MAX_DISCOVERY_SELECTOR_LENGTH)
    href: str = Field(default="", max_length=MAX_DISCOVERY_HREF_LENGTH)
    input_selector: str = Field(default="", max_length=MAX_DISCOVERY_SELECTOR_LENGTH)
    submit_selector: str = Field(default="", max_length=MAX_DISCOVERY_SELECTOR_LENGTH)
    fields: list[dict[str, Any]] = Field(default_factory=list, max_length=20)

    @field_validator("label", "selector", "href", "input_selector", "submit_selector", mode="before")
    @classmethod
    def trim_browser_discovery_text(cls, value: Any, info: Any) -> str:
        limit = DISCOVERY_ELEMENT_FIELD_LIMITS.get(info.field_name, MAX_DISCOVERY_LABEL_LENGTH)
        return str(value or "").strip()[:limit]


class WidgetRegisterRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    title: str = Field(default="", max_length=180)
    text_sample: str = Field(default="", max_length=MAX_DISCOVERY_TEXT_LENGTH)
    html_sample: str = Field(default="", max_length=MAX_DISCOVERY_HTML_LENGTH)
    buttons: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    links: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    forms: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    platform_hints: dict[str, Any] = Field(default_factory=dict)
    barrier_hints: dict[str, Any] = Field(default_factory=dict)
    runtime_capabilities: dict[str, Any] = Field(default_factory=dict)


class WidgetActionValidationRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    validated_at: str = Field(default="", max_length=80)
    actions: dict[str, Any] = Field(default_factory=dict)


class WidgetPolicyEventRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    occurred_at: str = Field(default="", max_length=80)
    action: str = Field(..., min_length=1, max_length=80)
    status: str = Field(default="blocked", max_length=40)
    reason: str = Field(default="", max_length=240)
    policy: dict[str, Any] = Field(default_factory=dict)


class WidgetActionExecutionEventRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    occurred_at: str = Field(default="", max_length=80)
    request_id: str = Field(default="", max_length=80)
    turn_id: str = Field(default="", max_length=80)
    sequence: int = Field(default=0, ge=0, le=100)
    action: str = Field(..., min_length=1, max_length=80)
    status: str = Field(default="unknown", max_length=40)
    stage: str = Field(default="", max_length=80)
    reason: str = Field(default="", max_length=240)
    duration_ms: float = Field(default=0.0, ge=0)
    param_keys: list[str] = Field(default_factory=list, max_length=20)
    requested_url: str = Field(default="", max_length=600)
    final_url: str = Field(default="", max_length=600)
    evidence: dict[str, Any] = Field(default_factory=dict)


class WidgetInteractionEventRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    occurred_at: str = Field(default="", max_length=80)
    event_type: str = Field(..., min_length=1, max_length=40)
    label: str = Field(default="", max_length=180)
    selector: str = Field(default="", max_length=260)
    tag: str = Field(default="", max_length=40)
    href: str = Field(default="", max_length=600)
    form: dict[str, Any] = Field(default_factory=dict)


def _safe_site_id(raw: str) -> str:
    return admin_db._safe_site_id(raw or "site_1")


def _safe_script_base_url(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip().strip("\"'")
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        return raw.rstrip("/")
    return ""


def _public_script_base_url(raw: str) -> str:
    safe_url = _safe_script_base_url(raw)
    if not safe_url:
        return ""
    parsed_url = urlparse(safe_url)
    hostname = (parsed_url.hostname or "").lower()
    if parsed_url.scheme == "http" and not _is_local_script_host(hostname):
        return f"https://{safe_url[len('http://'):]}"
    return safe_url


def _is_local_script_host(hostname: str) -> bool:
    return (
        hostname == "localhost"
        or hostname.startswith("127.")
        or hostname.startswith("10.")
        or hostname.startswith("192.168.")
        or hostname in {"0.0.0.0", "::1"}
        or hostname.startswith("172.16.")
        or hostname.startswith("172.17.")
        or hostname.startswith("172.18.")
        or hostname.startswith("172.19.")
        or hostname.startswith("172.2")
        or hostname.startswith("172.30.")
        or hostname.startswith("172.31.")
    )


def _request_public_base_url(request: Request | None = None) -> str:
    if request is None:
        return ""

    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip()
    forwarded_prefix = request.headers.get("x-forwarded-prefix", "").strip().rstrip("/")
    scheme = forwarded_proto or request.url.scheme
    host = forwarded_host or request.headers.get("host", "") or request.url.netloc
    return _public_script_base_url(f"{scheme}://{host}{forwarded_prefix}") if scheme and host else ""


def _public_widget_base_url(request: Request | None = None) -> str:
    return (
        _request_public_base_url(request)
        or _public_script_base_url(os.environ.get("HUB_PUBLIC_URL", ""))
        or _public_script_base_url(os.environ.get("PUBLIC_API_URL", ""))
        or _public_script_base_url(config.PUBLIC_API_URL)
        or _public_script_base_url(config.HUB_PUBLIC_URL)
        or _public_script_base_url(config.VOICE_ORB_API_URL or "")
    )


def _load_plugin_script(script_name: str, *, site: str, api_base_url: str) -> str:
    plugin_path = PLUGIN_DIR / script_name
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail="Plugin script not found.")

    with open(plugin_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    js_code = js_code.replace('"__AI_PUBLIC_API_URL__"', json.dumps(api_base_url))
    js_code = js_code.replace('"__AI_DEFAULT_SITE_ID__"', json.dumps(site))
    return js_code


def _load_widget_script(*, site: str, api_base_url: str) -> str:
    return _load_plugin_script(WIDGET_SCRIPT_NAME, site=site, api_base_url=api_base_url)


def _load_adapter_script(*, site: str, api_base_url: str) -> str:
    return _load_plugin_script(ADAPTER_SCRIPT_NAME, site=site, api_base_url=api_base_url)


def _disabled_widget_script(*, site: str) -> str:
    return f"""
(function () {{
  var siteId = {json.dumps(site)};
  var widget = document.getElementById({json.dumps(DISABLED_WIDGET_DOM_ID)});
  if (widget) widget.remove();
  window[{json.dumps(DISABLED_WIDGET_BOOT_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_FRAME_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] = window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] || {{}};
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}][siteId] = true;
  console.info("[AI Hub Widget] " + {json.dumps(CLIENT_DISABLED_MESSAGE)} + " Site: " + siteId);
}})();
"""


def _client_scripts_can_load(site: str) -> bool:
    if not site:
        return True
    try:
        client = admin_db.get_client_detail(site)
    except LookupError:
        return True
    return str(client.get("status") or "").strip().lower() != admin_db.CLIENT_STATUS_DISABLED


def _script_url(*, api_base_url: str, script_name: str, site: str | None = None) -> str:
    if site:
        return f"{api_base_url}/{script_name}?site={site}"
    return f"{api_base_url}/{script_name}"


def _render_install_script(*, site: str | None = None, api_base_url: str) -> str:
    adapter_url = _script_url(api_base_url=api_base_url, script_name=ADAPTER_SCRIPT_NAME, site=site)
    widget_url = _script_url(api_base_url=api_base_url, script_name=WIDGET_SCRIPT_NAME, site=site)
    return f"""
(function () {{
  var siteId = {json.dumps(site or "")};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var loadedSites = window[{json.dumps(INSTALL_REGISTRY_FLAG)}] || {{}};
  var installKey = siteId || "auto:" + window.location.origin + ":" + window.location.pathname.split("/").slice(0, 2).join("/");
  if (loadedSites[installKey]) return;
  loadedSites[installKey] = true;
  window[{json.dumps(INSTALL_REGISTRY_FLAG)}] = loadedSites;

  function loadScript(src, onload) {{
    var script = document.createElement("script");
    script.defer = true;
    script.src = src;
    if (siteId) script.setAttribute("data-site-id", siteId);
    script.setAttribute("data-aihub-universal", siteId ? "false" : "true");
    script.setAttribute("data-api-url", apiBaseUrl);
    script.onload = onload || function () {{}};
    script.onerror = function () {{
      console.error("[AIHub] Failed to load " + src);
    }};
    (document.head || document.documentElement).appendChild(script);
  }}

  loadScript({json.dumps(adapter_url)}, function () {{
    loadScript({json.dumps(widget_url)});
  }});
}})();
"""


def universal_install_script_tag(*, api_base_url: str | None = None) -> str:
    """Return the universal one-line installer for auto-onboarded client sites."""
    safe_api = (api_base_url or _public_widget_base_url()).rstrip("/")
    return f'<script defer src="{safe_api}/install.js"></script>'


def _public_runtime_config(*, site: str, api_base_url: str) -> dict[str, Any]:
    client = _safe_client_detail(site)
    vertical = _safe_vertical_detail(client.get("vertical_key"))
    selectors = admin_db.get_site_selectors(site) or {}
    vertical_config = client.get("vertical_config")
    if not isinstance(vertical_config, dict):
        vertical_config = {}

    return {
        "version": RUNTIME_CONFIG_VERSION,
        "site_id": site,
        "enabled": admin_db.is_client_widget_enabled(site),
        "api_base_url": api_base_url,
        "install": _install_asset_config(site=site, api_base_url=api_base_url),
        "vertical": _runtime_vertical_config(vertical),
        "adapter": _runtime_adapter_config(client, vertical_config, selectors),
    }


def _safe_client_detail(site: str) -> dict[str, Any]:
    try:
        return admin_db.get_client_detail(site)
    except LookupError:
        return {
            "site_id": site,
            "name": site,
            "adapter_name": admin_db.DEFAULT_ADAPTER_NAME,
            "vertical_key": admin_db.DEFAULT_CLIENT_VERTICAL_KEY,
            "vertical_config": {},
        }


def _safe_vertical_detail(vertical_key: str | None) -> dict[str, Any]:
    try:
        return admin_db.get_vertical_detail(vertical_key or admin_db.DEFAULT_CLIENT_VERTICAL_KEY)
    except ValueError:
        return admin_db.get_vertical_detail(admin_db.DEFAULT_CLIENT_VERTICAL_KEY)


def _install_asset_config(*, site: str, api_base_url: str) -> dict[str, str]:
    return {
        "adapter_script": _script_url(api_base_url=api_base_url, script_name=ADAPTER_SCRIPT_NAME, site=site),
        "widget_script": _script_url(api_base_url=api_base_url, script_name=WIDGET_SCRIPT_NAME, site=site),
    }


def _runtime_vertical_config(vertical: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": vertical.get("key") or GENERIC_VERTICAL_KEY,
        "label": vertical.get("label") or "Generic",
        "risk_level": vertical.get("risk_level") or "low",
        "action_types": vertical.get("action_types") or [],
        "entity_types": vertical.get("entity_types") or [],
    }


def _runtime_adapter_config(
    client: dict[str, Any],
    vertical_config: dict[str, Any],
    selectors: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": client.get("adapter_name") or admin_db.DEFAULT_ADAPTER_NAME,
        "mode": "generated-runtime",
        "platform": vertical_config.get("platform") or "auto",
        "routes": _dict_value(vertical_config, "routes"),
        "actions": _dict_value(vertical_config, "actions"),
        "action_policy": build_barrier_action_policy(
            vertical_config,
            str(client.get("vertical_key") or admin_db.DEFAULT_CLIENT_VERTICAL_KEY),
        ),
        "action_events": _durable_action_events_for_client(str(client.get("site_id") or "")),
        "action_health": _dict_value(vertical_config, "action_health"),
        "action_proposals": _list_value(vertical_config, "action_proposals"),
        "action_proposal_reviews": _list_value(vertical_config, "action_proposal_reviews"),
        "action_repairs": _list_value(vertical_config, "action_repairs"),
        "action_reviews": _list_value(vertical_config, "action_reviews"),
        "flow_repair_proposals": _list_value(vertical_config, "flow_repair_proposals"),
        "flow_repair_reviews": _list_value(vertical_config, "flow_repair_reviews"),
        "policy_events": _list_value(vertical_config, "policy_events"),
        "interaction_events": _list_value(vertical_config, "interaction_events"),
        "action_candidates": _list_value(vertical_config, "action_candidates"),
        "prompt_suggestions": _list_value(vertical_config, "prompt_suggestions"),
        "intake_questions": sanitize_intake_questions(vertical_config.get("intake_questions")),
        "action_readiness": action_readiness_for(
            vertical_config,
            str(client.get("vertical_key") or admin_db.DEFAULT_CLIENT_VERTICAL_KEY),
        ),
        "discovery": _dict_value(vertical_config, "discovery"),
        "validation": _dict_value(vertical_config, "validation"),
        "initialization": _dict_value(vertical_config, "initialization"),
        "flow": _dict_value(vertical_config, "flow"),
        "barriers": _dict_value(vertical_config, "barriers"),
        "rehearsal": _dict_value(vertical_config, "rehearsal"),
        "regression": _dict_value(vertical_config, "regression"),
        "runtime_capabilities": _dict_value(vertical_config, "runtime_capabilities"),
        "selectors": selectors.get("selectors") or _dict_value(vertical_config, "selectors"),
        "selector_confidence": float(selectors.get("confidence") or 0),
        "selector_validated": bool(selectors.get("validated")),
    }


def _durable_action_events_for_client(site_id: str) -> list[dict[str, Any]]:
    if not site_id:
        return []
    try:
        return admin_db.list_client_action_events({site_id}, limit=80).get(site_id, [])
    except Exception as exc:
        logger.warning("Runtime action evidence lookup failed for %s: %s", site_id, exc)
        return []


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _list_value(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value[:20] if isinstance(value, list) else []


def _validated_runtime_capabilities(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}

    capabilities: dict[str, Any] = {}
    for key in RUNTIME_CAPABILITY_BOOL_KEYS:
        if key in raw:
            capabilities[key] = bool(raw.get(key))
    for key in RUNTIME_CAPABILITY_TEXT_KEYS:
        if key in raw:
            capabilities[key] = str(raw.get(key) or "").strip()[:MAX_RUNTIME_CAPABILITY_TEXT_LENGTH]
    for key in RUNTIME_CAPABILITY_NUMBER_KEYS:
        if key in raw:
            capabilities[key] = _bounded_capability_number(raw.get(key))
    return capabilities


def _bounded_capability_number(value: Any) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(numeric, MAX_RUNTIME_CAPABILITY_NUMBER))


def _registration_vertical_decision(
    client: dict[str, Any],
    detected_vertical_key: str,
    confidence: float,
) -> dict[str, Any]:
    current_key = _clean_vertical_key(client.get("vertical_key"))
    detected_key = _clean_vertical_key(detected_vertical_key)
    safe_confidence = max(0.0, min(float(confidence or 0.0), 1.0))

    if current_key == detected_key:
        reason = "same_vertical"
        applied_key = current_key
    elif current_key == GENERIC_VERTICAL_KEY and safe_confidence >= GENERIC_TO_VERTICAL_CONFIDENCE:
        reason = "generic_upgraded_from_confident_discovery"
        applied_key = detected_key
    elif detected_key == GENERIC_VERTICAL_KEY:
        reason = "kept_existing_vertical_after_generic_discovery"
        applied_key = current_key
    elif safe_confidence >= EXISTING_VERTICAL_SWITCH_CONFIDENCE:
        reason = "switched_after_high_confidence_discovery"
        applied_key = detected_key
    else:
        reason = "kept_existing_vertical_after_low_confidence_discovery"
        applied_key = current_key

    return {
        "previous_vertical_key": current_key,
        "detected_vertical_key": detected_key,
        "applied_vertical_key": applied_key,
        "confidence": round(safe_confidence, 3),
        "reason": reason,
        "apply_generated_actions": applied_key == detected_key,
    }


def _clean_vertical_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text or GENERIC_VERTICAL_KEY


def _registration_vertical_config(
    discovery_config: dict[str, Any],
    runtime_capabilities: dict[str, Any],
    vertical_decision: dict[str, Any],
) -> dict[str, Any]:
    vertical_config = dict(discovery_config)
    if not vertical_decision.get("apply_generated_actions"):
        vertical_config.pop("actions", None)
        vertical_config.pop("prompt_suggestions", None)
        vertical_config.pop("intake_questions", None)

    discovery_meta = _dict_value(vertical_config, "discovery")
    discovery_meta.update(
        {
            "previous_vertical_key": vertical_decision["previous_vertical_key"],
            "detected_vertical_key": vertical_decision["detected_vertical_key"],
            "applied_vertical_key": vertical_decision["applied_vertical_key"],
            "vertical_decision": vertical_decision["reason"],
            "confidence": vertical_decision["confidence"],
        }
    )
    vertical_config["discovery"] = discovery_meta
    vertical_config["runtime_capabilities"] = runtime_capabilities
    return vertical_config


def _process_widget_registration(req: WidgetRegisterRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    payload = req.model_dump()
    discovery = build_discovery(payload)
    safe_site = _safe_site_id(req.site_id)
    store_url = _safe_script_base_url(req.origin) or _safe_script_base_url(req.url)
    if not store_url:
        raise HTTPException(status_code=400, detail="Registration origin must be http or https.")

    client = _ensure_registration_client(safe_site, store_url, req.title, discovery.vertical_key)
    vertical_decision = _registration_vertical_decision(client, discovery.vertical_key, discovery.confidence)
    vertical_config = _registration_vertical_config(
        discovery.vertical_config,
        _validated_runtime_capabilities(req.runtime_capabilities),
        vertical_decision,
    )
    client = admin_db.update_client_discovery_config(
        safe_site,
        vertical_key=vertical_decision["applied_vertical_key"],
        vertical_config=vertical_config,
        adapter_name="generated_adapter.js",
    )
    admin_db.save_site_selectors(
        safe_site,
        selectors=discovery.selectors,
        confidence=discovery.confidence,
        validated=discovery.confidence >= 0.65,
    )
    if vertical_decision["apply_generated_actions"]:
        _seed_generated_prompt_once(safe_site, client, discovery)
    initialization_plan = _manual_registration_initialization_plan()
    return {
        "site_id": safe_site,
        "vertical_key": vertical_decision["applied_vertical_key"],
        "detected_vertical_key": discovery.vertical_key,
        "vertical_decision": vertical_decision["reason"],
        "confidence": discovery.confidence,
        "actions": sorted(vertical_config.get("actions", {}).keys()),
        "crawl_scheduled": initialization_plan["crawl"],
        "flow_scheduled": initialization_plan["flow"],
        "rehearsal_scheduled": initialization_plan["rehearsal"],
    }


def _process_action_validation_report(req: WidgetActionValidationRequest) -> dict[str, Any]:
    safe_site = _safe_site_id(req.site_id)
    origin = _safe_script_base_url(req.origin)
    if not origin:
        raise HTTPException(status_code=400, detail="Validation origin must be http or https.")
    client = _safe_client_detail(safe_site)
    allowed_origin = _safe_script_base_url(str(client.get("allowed_origin") or ""))
    if allowed_origin and allowed_origin != origin:
        raise HTTPException(status_code=403, detail="Validation origin is not allowed for this client.")
    report = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "validated_at": req.validated_at,
        "actions": req.actions,
    }
    admin_db.save_adapter_validation_report(safe_site, report)
    validation = _dict_value(admin_db.get_client_detail(safe_site).get("vertical_config") or {}, "validation")
    return {
        "site_id": safe_site,
        "summary": validation.get("summary") or {},
    }


def _process_policy_event(req: WidgetPolicyEventRequest) -> dict[str, Any]:
    safe_site = _safe_site_id(req.site_id)
    origin = _safe_script_base_url(req.origin)
    if not origin:
        raise HTTPException(status_code=400, detail="Policy event origin must be http or https.")
    client = _safe_client_detail(safe_site)
    allowed_origin = _safe_script_base_url(str(client.get("allowed_origin") or ""))
    if allowed_origin and allowed_origin != origin:
        raise HTTPException(status_code=403, detail="Policy event origin is not allowed for this client.")
    event = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "occurred_at": req.occurred_at,
        "action": req.action,
        "status": req.status,
        "reason": req.reason,
        "policy": req.policy,
    }
    admin_db.save_client_policy_event(safe_site, event)
    return {"site_id": safe_site, "status": "ok"}


def _process_action_execution_event(req: WidgetActionExecutionEventRequest) -> dict[str, Any]:
    safe_site = _safe_site_id(req.site_id)
    origin = _safe_script_base_url(req.origin)
    if not origin:
        raise HTTPException(status_code=400, detail="Action event origin must be http or https.")
    client = _safe_client_detail(safe_site)
    allowed_origin = _safe_script_base_url(str(client.get("allowed_origin") or ""))
    if allowed_origin and allowed_origin != origin:
        raise HTTPException(status_code=403, detail="Action event origin is not allowed for this client.")
    event = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "occurred_at": req.occurred_at,
        "request_id": req.request_id,
        "turn_id": req.turn_id,
        "sequence": req.sequence,
        "action": req.action,
        "status": req.status,
        "stage": req.stage,
        "reason": req.reason,
        "duration_ms": req.duration_ms,
        "param_keys": req.param_keys,
        "requested_url": same_origin_public_url(req.requested_url, origin) if req.requested_url else "",
        "final_url": same_origin_public_url(req.final_url, origin) if req.final_url else "",
        "evidence": req.evidence,
    }
    admin_db.save_client_action_event(safe_site, event)
    return {"site_id": safe_site, "status": "ok"}


def _process_interaction_event(req: WidgetInteractionEventRequest) -> dict[str, Any]:
    safe_site = _safe_site_id(req.site_id)
    origin = _safe_script_base_url(req.origin)
    if not origin:
        raise HTTPException(status_code=400, detail="Interaction origin must be http or https.")
    client = _safe_client_detail(safe_site)
    allowed_origin = _safe_script_base_url(str(client.get("allowed_origin") or ""))
    if allowed_origin and allowed_origin != origin:
        raise HTTPException(status_code=403, detail="Interaction origin is not allowed for this client.")
    event = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "occurred_at": req.occurred_at,
        "event_type": req.event_type,
        "label": req.label,
        "selector": req.selector,
        "tag": req.tag,
        "href": req.href,
        "form": req.form,
    }
    admin_db.save_client_interaction_event(safe_site, event)
    return {"site_id": safe_site, "status": "ok"}


def same_origin_public_url(url: str, origin: str) -> str:
    clean_url = str(url or "").strip()[:600]
    try:
        parsed = urlparse(clean_url)
    except ValueError:
        return origin
    if not parsed.scheme or not parsed.netloc:
        return origin
    if f"{parsed.scheme}://{parsed.netloc}" != origin:
        return origin
    return clean_url


def _ensure_registration_client(site_id: str, store_url: str, title: str, vertical_key: str) -> dict[str, Any]:
    name = str(title or site_id.replace("_", " ").title()).strip()[:120] or site_id
    try:
        client = admin_db.get_client_detail(site_id)
    except LookupError:
        return admin_db.discover_available_client(
            name=name,
            store_url=store_url,
            site_id=site_id,
            deploy_mode=admin_db.DEFAULT_DEPLOY_MODE,
            plan=admin_db.DEFAULT_PLAN,
            adapter_name="generated_adapter.js",
            vertical_key=vertical_key,
        )
    current_origin = _safe_script_base_url(str(client.get("allowed_origin") or client.get("store_url") or ""))
    next_origin = _safe_script_base_url(store_url)
    if next_origin and next_origin != current_origin:
        existing_vertical_key = str(client.get("vertical_key") or vertical_key).strip() or vertical_key
        return admin_db.discover_available_client(
            name=str(client.get("name") or name).strip()[:120] or name,
            store_url=store_url,
            site_id=site_id,
            deploy_mode=str(client.get("deploy_mode") or admin_db.DEFAULT_DEPLOY_MODE),
            plan=str(client.get("plan") or admin_db.DEFAULT_PLAN),
            adapter_name="generated_adapter.js",
            vertical_key=existing_vertical_key,
        )
    return client


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
    return {"crawl": False, "flow": False, "rehearsal": False}


def _vertical_config_section(client: dict[str, Any], key: str) -> dict[str, Any]:
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    section = vertical_config.get(key)
    return section if isinstance(section, dict) else {}


def _render_embed_bootstrap(*, site: str, api_base_url: str) -> str:
    return f"""
(function () {{
  if (window.__mayabotFrameLoaded) return;
  window.__mayabotFrameLoaded = true;

  var currentScript = document.currentScript;
  var scriptUrl = currentScript && currentScript.src ? new URL(currentScript.src, window.location.href) : null;
  var siteId = {json.dumps(site)};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var parentOrigin = window.location.origin;
  var frameUrl = new URL(apiBaseUrl + "/mayabot-frame");
  frameUrl.searchParams.set("site", siteId);
  frameUrl.searchParams.set("parent_origin", parentOrigin);

  var frame = document.createElement("iframe");
  frame.src = frameUrl.toString();
  frame.title = "AI Hub Voice Widget";
  frame.setAttribute("allow", "microphone");
  frame.setAttribute("aria-label", "AI Hub Voice Widget");
  frame.style.position = "fixed";
  frame.style.left = "50%";
  frame.style.bottom = "12px";
  frame.style.transform = "translateX(-50%)";
  frame.style.width = "360px";
  frame.style.height = "180px";
  frame.style.maxWidth = "calc(100vw - 24px)";
  frame.style.maxHeight = "calc(100vh - 24px)";
  frame.style.border = "0";
  frame.style.background = "transparent";
  frame.style.zIndex = "2147483647";
  frame.style.overflow = "hidden";
  frame.style.colorScheme = "light";

  function clamp(value, fallback, maxCss) {{
    var numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric <= 0) return fallback;
    return Math.min(numeric, maxCss);
  }}

  window.addEventListener("message", function (event) {{
    if (event.origin !== new URL(apiBaseUrl).origin) return;
    var data = event.data || {{}};
    if (data.source !== "mayabot-frame") return;

    if (data.type === "mayabot:frame-size") {{
      var width = clamp(data.width, 360, Math.max(320, window.innerWidth - 24));
      var height = clamp(data.height, 180, Math.max(180, window.innerHeight - 24));
      frame.style.width = width + "px";
      frame.style.height = height + "px";
      return;
    }}

    if (data.type === "mayabot:navigate" && data.path) {{
      try {{
        var targetUrl = new URL(data.path, window.location.href);
        if (targetUrl.origin === window.location.origin) {{
          window.location.href = targetUrl.pathname + targetUrl.search + targetUrl.hash;
        }}
      }} catch (_err) {{}}
    }}
  }});

  function mountFrame(retries) {{
    if (document.body) {{
      document.body.appendChild(frame);
      return;
    }}
    if (retries > 100) {{
      return;
    }}
    setTimeout(function () {{ mountFrame(retries + 1); }}, 50);
  }}

  mountFrame(0);
}})();
"""


@router.get("/v1/widget/config")
async def widget_config(
    request: Request,
    site_id: str = config.DEFAULT_SITE_ID,
    site: Optional[str] = None,
    shop: Optional[str] = None,
) -> dict[str, Any]:
    """Return public adapter/runtime config for one tenant."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    return _public_runtime_config(site=safe_site, api_base_url=_public_widget_base_url(request))


@router.post("/v1/widget/register")
async def widget_register(req: WidgetRegisterRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Register one script-installed page and generate adapter config."""
    return _process_widget_registration(req, background_tasks)


@router.post("/v1/widget/action-report")
async def widget_action_report(req: WidgetActionValidationRequest) -> dict[str, Any]:
    """Accept non-destructive browser validation of generated adapter actions."""
    return _process_action_validation_report(req)


@router.post("/v1/widget/policy-event")
async def widget_policy_event(req: WidgetPolicyEventRequest) -> dict[str, Any]:
    """Accept browser runtime evidence when action policy blocks execution."""
    return _process_policy_event(req)


@router.post("/v1/widget/action-event")
async def widget_action_event(req: WidgetActionExecutionEventRequest) -> dict[str, Any]:
    """Accept browser runtime evidence for executed adapter actions."""
    return _process_action_execution_event(req)


@router.post("/v1/widget/interaction-event")
async def widget_interaction_event(req: WidgetInteractionEventRequest) -> dict[str, Any]:
    """Accept privacy-safe browser interaction metadata for adapter learning."""
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
            content="<!doctype html><html><body></body></html>",
            media_type="text/html",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Hub Widget</title>
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: transparent;
      }}
      body {{
        position: relative;
      }}
    </style>
  </head>
  <body>
    <script src="{script_path}"></script>
  </body>
</html>"""

    return Response(
        content=html_doc,
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
