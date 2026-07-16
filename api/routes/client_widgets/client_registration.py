"""Widget registration processing helpers."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from fastapi import BackgroundTasks, HTTPException

from api.routes.client_widgets.client_models import WidgetRegisterRequest

GENERIC_TO_VERTICAL_CONFIDENCE = 0.6
EXISTING_VERTICAL_SWITCH_CONFIDENCE = 0.86


class ClientRegistrationStore(Protocol):
    DEFAULT_ADAPTER_NAME: str
    DEFAULT_CLIENT_VERTICAL_KEY: str
    DEFAULT_DEPLOY_MODE: str
    DEFAULT_PLAN: str

    def get_client_detail(self, site_id: str) -> dict[str, Any]: ...

    def discover_available_client(self, **kwargs: Any) -> dict[str, Any]: ...

    def update_client_discovery_config(self, site_id: str, **kwargs: Any) -> dict[str, Any]: ...

    def save_site_selectors(self, site_id: str, **kwargs: Any) -> Any: ...


DiscoveryBuilder = Callable[[dict[str, Any]], Any]
SiteIdSanitizer = Callable[[str], str]
OriginSanitizer = Callable[[str], str]
PromptSeeder = Callable[[str, dict[str, Any], Any], None]
RuntimeCapabilityValidator = Callable[[Any], dict[str, Any]]


def process_widget_registration(
    req: WidgetRegisterRequest,
    background_tasks: BackgroundTasks,
    *,
    client_store: ClientRegistrationStore,
    build_discovery: DiscoveryBuilder,
    safe_site_id: SiteIdSanitizer,
    safe_script_base_url: OriginSanitizer,
    validate_runtime_capabilities: RuntimeCapabilityValidator,
    seed_generated_prompt_once: PromptSeeder,
) -> dict[str, Any]:
    payload = req.model_dump()
    discovery = build_discovery(payload)
    safe_site = safe_site_id(req.site_id)
    store_url = safe_script_base_url(req.origin) or safe_script_base_url(req.url)
    if not store_url:
        raise HTTPException(status_code=400, detail="Registration origin must be http or https.")

    client = ensure_registration_client(
        safe_site,
        store_url,
        req.title,
        discovery.vertical_key,
        client_store=client_store,
        safe_script_base_url=safe_script_base_url,
    )
    vertical_decision = registration_vertical_decision(
        client,
        discovery.vertical_key,
        discovery.confidence,
        generic_vertical_key=client_store.DEFAULT_CLIENT_VERTICAL_KEY,
    )
    vertical_config = registration_vertical_config(
        discovery.vertical_config,
        validate_runtime_capabilities(req.runtime_capabilities),
        vertical_decision,
    )
    client = client_store.update_client_discovery_config(
        safe_site,
        vertical_key=vertical_decision["applied_vertical_key"],
        vertical_config=vertical_config,
        adapter_name="generated_adapter.js",
    )
    client_store.save_site_selectors(
        safe_site,
        selectors=discovery.selectors,
        confidence=discovery.confidence,
        validated=discovery.confidence >= 0.65,
    )
    if vertical_decision["apply_generated_actions"]:
        seed_generated_prompt_once(safe_site, client, discovery)
    initialization_plan = manual_registration_initialization_plan()
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


def registration_vertical_decision(
    client: dict[str, Any],
    detected_vertical_key: str,
    confidence: float,
    *,
    generic_vertical_key: str,
) -> dict[str, Any]:
    current_key = clean_vertical_key(client.get("vertical_key"), generic_vertical_key)
    detected_key = clean_vertical_key(detected_vertical_key, generic_vertical_key)
    safe_confidence = max(0.0, min(float(confidence or 0.0), 1.0))

    if current_key == detected_key:
        reason = "same_vertical"
        applied_key = current_key
    elif current_key == generic_vertical_key and safe_confidence >= GENERIC_TO_VERTICAL_CONFIDENCE:
        reason = "generic_upgraded_from_confident_discovery"
        applied_key = detected_key
    elif detected_key == generic_vertical_key:
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


def clean_vertical_key(value: Any, generic_vertical_key: str) -> str:
    text = str(value or "").strip().lower()
    return text or generic_vertical_key


def registration_vertical_config(
    discovery_config: dict[str, Any],
    runtime_capabilities: dict[str, Any],
    vertical_decision: dict[str, Any],
) -> dict[str, Any]:
    vertical_config = dict(discovery_config)
    if not vertical_decision.get("apply_generated_actions"):
        vertical_config.pop("actions", None)
        vertical_config.pop("prompt_suggestions", None)
        vertical_config.pop("intake_questions", None)

    discovery_meta = dict_value(vertical_config, "discovery")
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


def ensure_registration_client(
    site_id: str,
    store_url: str,
    title: str,
    vertical_key: str,
    *,
    client_store: ClientRegistrationStore,
    safe_script_base_url: OriginSanitizer,
) -> dict[str, Any]:
    name = str(title or site_id.replace("_", " ").title()).strip()[:120] or site_id
    try:
        client = client_store.get_client_detail(site_id)
    except LookupError:
        return client_store.discover_available_client(
            name=name,
            store_url=store_url,
            site_id=site_id,
            deploy_mode=client_store.DEFAULT_DEPLOY_MODE,
            plan=client_store.DEFAULT_PLAN,
            adapter_name="generated_adapter.js",
            vertical_key=vertical_key,
        )
    current_origin = safe_script_base_url(str(client.get("allowed_origin") or client.get("store_url") or ""))
    next_origin = safe_script_base_url(store_url)
    if current_origin and next_origin and next_origin != current_origin:
        raise HTTPException(
            status_code=403,
            detail="This client is already bound to a different website origin.",
        )
    return client


def manual_registration_initialization_plan() -> dict[str, bool]:
    return {"crawl": False, "flow": False, "rehearsal": False}


def dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}
