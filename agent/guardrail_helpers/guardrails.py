"""
Safety guardrails for input and output validation.

Input guardrails:  Applied to raw STT transcript before LLM call.
Output guardrails: Applied to LLM response before returning to client.
"""

import logging
import json
from typing import Any

import config
from agent.guardrail_helpers import (
    guardrail_action_params,
    guardrail_dom_sequences,
    guardrail_entity_validation,
    guardrail_navigation,
    input_guardrails,
)
from agent.actions.registry import is_supported_action
from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_CLEAR_CART,
    ACTION_CLEAR_FILTERS,
    ACTION_FILTER_PRODUCTS,
    ACTION_COMPARE_ENTITIES,
    ACTION_OPEN_ENTITY_DETAIL,
    ACTION_NAVIGATE_TO,
    ACTION_REMOVE_FROM_CART,
    ACTION_RUN_DOM_SEQUENCE,
    ACTION_SHOW_ENTITIES,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_SHOW_PRODUCTS,
    ACTION_SORT_ENTITIES,
    ACTION_SORT_PRODUCTS,
    ACTION_UPDATE_CART_QUANTITY,
)
from db.core.database import product_exists

logger = logging.getLogger(__name__)

_VALID_NAV_PAGES = {
    "home",
    "cart",
    "checkout",
    "support",
    "frequently-asked-questions",
    "shipping-policy",
    "return-policy",
    "category/beauty",
    "category/fragrances",
    "category/furniture",
    "category/groceries",
}

_VALID_SORTS = {"price_asc", "price_desc", "rating", "newest"}
_VALID_FILTER_KEYS = {
    "category",
    "color",
    "max_price",
    "min_price",
    "min_rating",
    "brand",
    "tags",
}
# ═══════════════════════════════════════════════════════════════════════════════
# INPUT GUARDRAILS
# ═══════════════════════════════════════════════════════════════════════════════


class InputGuardrailError(Exception):
    """Raised when the input fails safety checks."""


def validate_input(transcript: str) -> str:
    """
    Run all input safety checks on a raw transcript.

    Args:
        transcript: Raw text from STT.

    Returns:
        Sanitised transcript (PII redacted).

    Raises:
        InputGuardrailError: If the input is unsafe.
    """
    return input_guardrails.validate_input(
        transcript,
        max_transcript_chars=config.MAX_TRANSCRIPT_CHARS,
        error_type=InputGuardrailError,
        logger=logger,
    )



# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT GUARDRAILS
# ═══════════════════════════════════════════════════════════════════════════════


class OutputGuardrailError(Exception):
    """Raised when the LLM output fails safety checks."""


def validate_output(
    response: dict[str, Any],
    site_id: str,
    allowed_product_ids: list[int] | None = None,
    allowed_entity_ids: list[str] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate and sanitise the LLM's structured response.

    Args:
        response: Parsed LLM response dict.
        site_id: Site identifier to validate product existence against.
        allowed_product_ids: Optional list of IDs that were in the LLM's RAG context.

    Returns:
        Validated (possibly modified) response dict.

    Raises:
        OutputGuardrailError: If the output is fundamentally unsafe.
    """
    # response_text checks
    response_text = str(response.get("response_text", ""))

    if not response_text.strip():
        response["response_text"] = (
            "I'm here to help! What would you like to shop for today?"
        )

    if len(response_text) > config.MAX_RESPONSE_CHARS:
        logger.warning("Guardrail | Response too long, truncating.")
        response["response_text"] = (
            response_text[: config.MAX_RESPONSE_CHARS - 3] + "..."
        )

    if input_guardrails.contains_offensive_content(response_text):
        logger.error("Guardrail | Offensive content in LLM response — blocking.")
        raise OutputGuardrailError("LLM generated offensive content.")

    # ui_actions checks
    actions = response.get("ui_actions", [])

    if not isinstance(actions, list):
        logger.warning("Guardrail | ui_actions is not a list — resetting.")
        response["ui_actions"] = []
        return response

    # Cap number of actions
    if len(actions) > config.MAX_UI_ACTIONS:
        logger.warning(
            "Guardrail | Too many UI actions (%d), capping at %d.",
            len(actions),
            config.MAX_UI_ACTIONS,
        )
        actions = actions[: config.MAX_UI_ACTIONS]

    adapter_contract = _adapter_contract(site_id, runtime_context)
    validated_actions = []
    for action in actions:
        if not isinstance(action, dict):
            continue

        action_type = str(action.get("action", "")).upper()
        params = action.get("params", {})
        if not isinstance(params, dict):
            logger.warning(
                "Guardrail | Params for %s are not an object - skipping.", action_type
            )
            continue

        # Alias common hallucinated actions
        if action_type == "SHOW_CART":
            action_type = "NAVIGATE_TO"
            params = {"page": "cart"}

        # Action type whitelist
        if not is_supported_action(action_type):
            logger.warning(
                "Guardrail | Unknown UI action type: %r — skipping.", action_type
            )
            continue

        # Validate product IDs exist in DB (prevent hallucinated products)
        if action_type in (
            ACTION_SHOW_PRODUCTS,
            ACTION_SHOW_COMPARISON,
            ACTION_SHOW_PRODUCT_DETAIL,
            ACTION_ADD_TO_CART,
            ACTION_REMOVE_FROM_CART,
            ACTION_UPDATE_CART_QUANTITY,
        ):
            params = _validate_product_ids(action_type, params, site_id, allowed_product_ids)
            if params is None:
                continue

        if action_type in (ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES, ACTION_OPEN_ENTITY_DETAIL):
            params = _validate_entity_ids(action_type, params, site_id, allowed_entity_ids)
            if params is None:
                continue

        # Validate price ranges make sense
        if action_type == ACTION_FILTER_PRODUCTS:
            params = _validate_filter_params(params)
            if not params:
                continue

        if action_type == ACTION_NAVIGATE_TO:
            params = _validate_navigation_params(params, adapter_contract.get("routes", {}))
            if params is None:
                continue

        if action_type in (ACTION_SORT_PRODUCTS, ACTION_SORT_ENTITIES):
            params = _validate_sort_params(params)
            if params is None:
                continue

        if action_type == ACTION_RUN_DOM_SEQUENCE:
            params = _validate_dom_sequence_params(params)
            if params is None:
                continue

        if action_type == ACTION_CLEAR_FILTERS:
            params = {}

        if action_type == ACTION_CLEAR_CART:
            params = {}

        if action_type != ACTION_NAVIGATE_TO and action_type in adapter_contract.get("actions", {}):
            params = _validate_adapter_action_params(
                params,
                adapter_contract["actions"][action_type],
            )
            if params is None:
                continue

        validated_actions.append({"action": action_type, "params": params})

    response["ui_actions"] = validated_actions
    return response


def _validate_product_ids(
    action_type: str, params: dict, site_id: str, allowed_product_ids: list[int] | None = None
) -> dict | None:
    return guardrail_entity_validation.validate_product_ids(
        action_type,
        params,
        site_id,
        product_exists=product_exists,
        coerce_product_id=_coerce_product_id,
        logger=logger,
        allowed_product_ids=allowed_product_ids,
    )


def _validate_entity_ids(
    action_type: str,
    params: dict,
    site_id: str,
    allowed_entity_ids: list[str] | None = None,
) -> dict | None:
    return guardrail_entity_validation.validate_entity_ids(
        action_type,
        params,
        site_id,
        clean_entity_ids=_clean_entity_ids,
        valid_entity_ids=_valid_entity_ids,
        copy_safe_display_text=_copy_safe_display_text,
        logger=logger,
        allowed_entity_ids=allowed_entity_ids,
    )


def _clean_entity_ids(raw_ids: list[Any]) -> list[str]:
    return guardrail_entity_validation.clean_entity_ids(raw_ids)


def _valid_entity_ids(
    site_id: str,
    entity_ids: list[str],
    allowed_entity_ids: list[str] | None = None,
) -> list[str]:
    return guardrail_entity_validation.valid_entity_ids(
        site_id,
        entity_ids,
        allowed_entity_ids,
        logger=logger,
    )


def _copy_safe_display_text(params: dict, result: dict) -> None:
    guardrail_entity_validation.copy_safe_display_text(params, result)


def _validate_filter_params(params: dict) -> dict:
    """Sanitise filter parameters and drop unsupported keys."""
    params = dict(params)

    # Drop any keys not in the whitelist
    for key in list(params.keys()):
        if key not in _VALID_FILTER_KEYS:
            del params[key]

    for key in ("max_price", "min_price"):
        val = params.get(key)
        if val is not None:
            try:
                params[key] = max(0.0, float(val))
            except (TypeError, ValueError):
                del params[key]

    if "min_rating" in params:
        try:
            params["min_rating"] = max(0.0, min(5.0, float(params["min_rating"])))
        except (TypeError, ValueError):
            del params["min_rating"]

    return params


def _validate_navigation_params(params: dict, adapter_routes: dict[str, str] | None = None) -> dict | None:
    """Validate navigation targets for the frontend router."""
    result = guardrail_navigation.validate_navigation_params(
        params,
        valid_pages=_VALID_NAV_PAGES,
        adapter_routes=adapter_routes,
    )
    if result is not None:
        return result
    page = str(params.get("page", "")).strip().lower().strip("/")
    logger.warning("Guardrail | Invalid navigation page: %r - skipping.", page)
    return None


def _adapter_route_target(page: str, adapter_routes: dict[str, str]) -> str:
    return guardrail_navigation.adapter_route_target(page, adapter_routes)


def _clean_same_origin_path(value: Any) -> str:
    return guardrail_navigation.clean_same_origin_path(value)


def _validate_sort_params(params: dict) -> dict | None:
    """Validate supported product sort options."""
    sort_by = str(params.get("sort_by", "")).strip().lower()
    if sort_by not in _VALID_SORTS:
        logger.warning("Guardrail | Invalid sort option: %r - skipping.", sort_by)
        return None
    return {"sort_by": sort_by}


def _validate_dom_sequence_params(params: dict) -> dict | None:
    return guardrail_dom_sequences.validate_dom_sequence_params(params, logger)


def _validate_adapter_action_params(params: dict, action_config: dict[str, Any]) -> dict | None:
    return guardrail_action_params.validate_adapter_action_params(params, action_config)


_safe_action_params = guardrail_action_params.safe_action_params


_adapter_param_keys = guardrail_action_params.adapter_param_keys


_clean_action_param_key = guardrail_action_params.clean_action_param_key


_normalize_action_param_key = guardrail_action_params.normalize_action_param_key


_clean_action_param_value = guardrail_action_params.clean_action_param_value


def _adapter_contract(site_id: str, runtime_context: dict[str, Any] | None = None) -> dict[str, Any]:
    vertical_config = _client_vertical_config(site_id)
    actions = vertical_config.get("actions")
    route_map = _navigation_route_map(vertical_config)
    route_map.update(_navigation_route_map(runtime_context or {}))
    return {
        "actions": {
            str(name or "").strip().upper(): config
            for name, config in (actions or {}).items()
            if isinstance(config, dict)
        } if isinstance(actions, dict) else {},
        "routes": route_map,
    }


def _navigation_route_map(vertical_config: dict[str, Any]) -> dict[str, str]:
    return guardrail_navigation.navigation_route_map(vertical_config)


def _add_route_alias(routes: dict[str, str], alias: Any, raw_path: Any) -> None:
    guardrail_navigation.add_route_alias(routes, alias, raw_path)


def _route_alias_key(value: Any) -> str:
    return guardrail_navigation.route_alias_key(value)


def _observed_navigation_path(value: Any, origin: Any = "") -> str:
    return guardrail_navigation.observed_navigation_path(value, origin)


def _safe_list(value: Any) -> list[Any]:
    return guardrail_navigation.safe_list(value)


def _client_vertical_config(site_id: str) -> dict[str, Any]:
    try:
        from db.admin_domain import admin_facade as admin_db

        client = admin_db._client_row(site_id)
    except Exception as exc:
        logger.debug("Guardrail | adapter contract lookup failed for %s: %s", site_id, exc)
        return {}
    raw_config = (client or {}).get("vertical_config_json")
    if isinstance(raw_config, dict):
        return raw_config
    try:
        parsed = json.loads(str(raw_config or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _coerce_product_id(value: Any) -> int | None:
    """Return a positive integer product ID, or None for malformed values."""
    if isinstance(value, bool):
        return None
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None
