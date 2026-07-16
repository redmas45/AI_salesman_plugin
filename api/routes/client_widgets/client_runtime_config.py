"""Public runtime config assembly for widget clients."""

from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

from agent.action_helpers.sales_intake import sanitize_intake_questions
from api.routes.client_widgets import client_scripts
from api.routes.client_widgets.client_models import (
    MAX_RUNTIME_CAPABILITY_NUMBER,
    MAX_RUNTIME_CAPABILITY_TEXT_LENGTH,
    RUNTIME_CAPABILITY_BOOL_KEYS,
    RUNTIME_CAPABILITY_NUMBER_KEYS,
    RUNTIME_CAPABILITY_TEXT_KEYS,
)

logger = logging.getLogger(__name__)

RUNTIME_CONFIG_VERSION = 1


class ClientStore(Protocol):
    DEFAULT_ADAPTER_NAME: str
    DEFAULT_CLIENT_VERTICAL_KEY: str

    def get_client_detail(self, site: str) -> dict[str, Any]: ...

    def get_vertical_detail(self, vertical_key: str) -> dict[str, Any]: ...

    def get_site_selectors(self, site: str) -> dict[str, Any] | None: ...

    def is_client_widget_enabled(self, site: str) -> bool: ...

    def list_client_action_events(self, site_ids: set[str], *, limit: int = 500) -> dict[str, list[dict[str, Any]]]: ...


BarrierPolicyBuilder = Callable[[dict[str, Any], str], dict[str, Any]]
ActionReadinessBuilder = Callable[[dict[str, Any], str], Any]


def public_runtime_config(
    *,
    site: str,
    api_base_url: str,
    client_store: ClientStore,
    build_barrier_policy: BarrierPolicyBuilder,
    build_action_readiness: ActionReadinessBuilder,
) -> dict[str, Any]:
    client = safe_client_detail(site, client_store)
    vertical = safe_vertical_detail(client.get("vertical_key"), client_store)
    selectors = client_store.get_site_selectors(site) or {}
    vertical_config = client.get("vertical_config")
    if not isinstance(vertical_config, dict):
        vertical_config = {}

    return {
        "version": RUNTIME_CONFIG_VERSION,
        "site_id": site,
        "enabled": client_store.is_client_widget_enabled(site),
        "api_base_url": api_base_url,
        "install": install_asset_config(site=site, api_base_url=api_base_url),
        "vertical": runtime_vertical_config(vertical, client_store.DEFAULT_CLIENT_VERTICAL_KEY),
        "adapter": runtime_adapter_config(
            client,
            vertical_config,
            selectors,
            client_store=client_store,
            build_barrier_policy=build_barrier_policy,
            build_action_readiness=build_action_readiness,
        ),
    }


def safe_client_detail(site: str, client_store: ClientStore) -> dict[str, Any]:
    try:
        return client_store.get_client_detail(site)
    except LookupError:
        return {
            "site_id": site,
            "name": site,
            "adapter_name": client_store.DEFAULT_ADAPTER_NAME,
            "vertical_key": client_store.DEFAULT_CLIENT_VERTICAL_KEY,
            "vertical_config": {},
        }


def safe_vertical_detail(vertical_key: str | None, client_store: ClientStore) -> dict[str, Any]:
    try:
        return client_store.get_vertical_detail(vertical_key or client_store.DEFAULT_CLIENT_VERTICAL_KEY)
    except ValueError:
        return client_store.get_vertical_detail(client_store.DEFAULT_CLIENT_VERTICAL_KEY)


def install_asset_config(*, site: str, api_base_url: str) -> dict[str, str]:
    return {
        "adapter_script": client_scripts.script_url(
            api_base_url=api_base_url,
            script_name=client_scripts.ADAPTER_SCRIPT_NAME,
            site=site,
        ),
        "widget_script": client_scripts.script_url(
            api_base_url=api_base_url,
            script_name=client_scripts.WIDGET_SCRIPT_NAME,
            site=site,
        ),
    }


def runtime_vertical_config(vertical: dict[str, Any], generic_vertical_key: str) -> dict[str, Any]:
    return {
        "key": vertical.get("key") or generic_vertical_key,
        "label": vertical.get("label") or "Generic",
        "risk_level": vertical.get("risk_level") or "low",
        "action_types": vertical.get("action_types") or [],
        "entity_types": vertical.get("entity_types") or [],
    }


def runtime_adapter_config(
    client: dict[str, Any],
    vertical_config: dict[str, Any],
    selectors: dict[str, Any],
    *,
    client_store: ClientStore,
    build_barrier_policy: BarrierPolicyBuilder,
    build_action_readiness: ActionReadinessBuilder,
) -> dict[str, Any]:
    vertical_key = str(client.get("vertical_key") or client_store.DEFAULT_CLIENT_VERTICAL_KEY)
    return {
        "name": client.get("adapter_name") or client_store.DEFAULT_ADAPTER_NAME,
        "mode": "generated-runtime",
        "platform": vertical_config.get("platform") or "auto",
        "routes": dict_value(vertical_config, "routes"),
        "actions": dict_value(vertical_config, "actions"),
        "action_policy": build_barrier_policy(vertical_config, vertical_key),
        "action_events": durable_action_events_for_client(str(client.get("site_id") or ""), client_store),
        "action_health": dict_value(vertical_config, "action_health"),
        "action_proposals": list_value(vertical_config, "action_proposals"),
        "action_proposal_reviews": list_value(vertical_config, "action_proposal_reviews"),
        "action_repairs": list_value(vertical_config, "action_repairs"),
        "action_reviews": list_value(vertical_config, "action_reviews"),
        "flow_repair_proposals": list_value(vertical_config, "flow_repair_proposals"),
        "flow_repair_reviews": list_value(vertical_config, "flow_repair_reviews"),
        "policy_events": list_value(vertical_config, "policy_events"),
        "interaction_events": list_value(vertical_config, "interaction_events"),
        "action_candidates": list_value(vertical_config, "action_candidates"),
        "prompt_suggestions": list_value(vertical_config, "prompt_suggestions"),
        "intake_questions": sanitize_intake_questions(vertical_config.get("intake_questions")),
        "action_readiness": build_action_readiness(vertical_config, vertical_key),
        "discovery": dict_value(vertical_config, "discovery"),
        "validation": dict_value(vertical_config, "validation"),
        "initialization": dict_value(vertical_config, "initialization"),
        "flow": dict_value(vertical_config, "flow"),
        "barriers": dict_value(vertical_config, "barriers"),
        "rehearsal": dict_value(vertical_config, "rehearsal"),
        "regression": dict_value(vertical_config, "regression"),
        "runtime_capabilities": dict_value(vertical_config, "runtime_capabilities"),
        "selectors": selectors.get("selectors") or dict_value(vertical_config, "selectors"),
        "selector_confidence": float(selectors.get("confidence") or 0),
        "selector_validated": bool(selectors.get("validated")),
    }


def durable_action_events_for_client(site_id: str, client_store: ClientStore) -> list[dict[str, Any]]:
    if not site_id:
        return []
    try:
        return client_store.list_client_action_events({site_id}, limit=80).get(site_id, [])
    except Exception as exc:
        logger.warning("Runtime action evidence lookup failed for %s: %s", site_id, exc)
        return []


def dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def list_value(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value[:20] if isinstance(value, list) else []


def validated_runtime_capabilities(raw: Any) -> dict[str, Any]:
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
            capabilities[key] = bounded_capability_number(raw.get(key))
    return capabilities


def bounded_capability_number(value: Any) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(numeric, MAX_RUNTIME_CAPABILITY_NUMBER))
