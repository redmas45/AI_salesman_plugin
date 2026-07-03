"""
Safety guardrails for input and output validation.

Input guardrails:  Applied to raw STT transcript before LLM call.
Output guardrails: Applied to LLM response before returning to client.
"""

import logging
import json
import re
from typing import Any

import config
from agent.actions.registry import is_supported_action
from agent.navigation_aliases import is_generic_route_alias, route_alias_key, semantic_route_alias_keys
from api.models import (
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
    ENTITY_ID_PARAM,
    ENTITY_IDS_PARAM,
    PAGE_PARAM,
    PRODUCT_ID_PARAM,
    PRODUCT_IDS_PARAM,
    QUANTITY_PARAM,
)
from db.database import product_exists

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
_MAX_ACTION_PARAM_KEYS = 20
_MAX_ACTION_PARAM_VALUE_LENGTH = 500
_SAFE_ACTION_PARAM_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,79}$")
_BLOCKED_ACTION_PARAM_KEYS = frozenset({"__proto__", "constructor", "prototype"})

_DOM_SEQUENCE_STEPS_PARAM = "steps"
_DOM_SEQUENCE_MAX_STEPS = 30
_DOM_SEQUENCE_MAX_STRING_LENGTH = 500
_DOM_SEQUENCE_MAX_WAIT_MS = 5000
_DOM_SEQUENCE_ALLOWED_OPERATIONS = {
    "check",
    "click",
    "fill",
    "focus",
    "navigate",
    "scroll",
    "select",
    "set_value",
    "submit",
    "uncheck",
    "wait",
    "wait_for",
}
_DOM_SEQUENCE_SELECTOR_OPERATIONS = {
    "check",
    "fill",
    "focus",
    "select",
    "set_value",
    "submit",
    "uncheck",
    "wait_for",
}


# Prompt Injection Patterns

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(everything|all|your\s+instructions?)",
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"act\s+as\s+(if\s+you\s+are|a|an)",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    r"developer\s+mode",
    r"override\s+(system|instructions?|prompt)",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"print\s+(your\s+)?(system\s+)?prompt",
    r"show\s+(me\s+)?(your\s+)?(instructions?|prompt|rules)",
    r"disregard\s+(all\s+)?(previous|prior)",
]

_COMPILED_INJECTION = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


# Offensive Content Patterns

_OFFENSIVE_WORDS = [
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "dick",
    "pussy",
    "cunt",
    "nigger",
    "faggot",
    "retard",
]

_OFFENSIVE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _OFFENSIVE_WORDS) + r")\b",
    re.IGNORECASE,
)


# PII Patterns
_PII_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "[PHONE]"),
    (re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"), "[EMAIL]"),
]


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
    if not transcript or not transcript.strip():
        raise InputGuardrailError("Empty transcript received.")

    # Length check
    if len(transcript) > config.MAX_TRANSCRIPT_CHARS:
        logger.warning(
            "Guardrail | Transcript too long (%d chars), truncating.", len(transcript)
        )
        transcript = transcript[: config.MAX_TRANSCRIPT_CHARS]

    # Prompt injection detection
    for pattern in _COMPILED_INJECTION:
        if pattern.search(transcript):
            logger.warning(
                "Guardrail | Prompt injection detected: %r", transcript[:100]
            )
            raise InputGuardrailError(
                "Whoops! I'm just a simple sales assistant, so I can't do that. But I can definitely help you find some amazing deals on our store!"
            )

    # Offensive input
    if _OFFENSIVE_PATTERN.search(transcript):
        logger.warning("Guardrail | Offensive input detected.")
        raise InputGuardrailError(
            "Let's keep things family-friendly while we shop! 😊 What were you looking to buy today?"
        )

    # Redact PII
    for pattern, replacement in _PII_PATTERNS:
        transcript = pattern.sub(replacement, transcript)

    return transcript


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

    if _OFFENSIVE_PATTERN.search(response_text):
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
    """Validate product actions and drop commands that target missing products."""
    if action_type in (ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON):
        raw_ids = params.get(PRODUCT_IDS_PARAM, [])
        if not isinstance(raw_ids, list):
            logger.warning(
                "Guardrail | %s product_ids is not a list - skipping.",
                action_type,
            )
            return None

        valid_ids = []
        for raw_id in raw_ids:
            pid = _coerce_product_id(raw_id)
            if pid is not None and product_exists(site_id, pid):
                # If we have strict allowed IDs from RAG, ensure the ID was actually shown to the LLM
                if allowed_product_ids is not None and pid not in allowed_product_ids:
                    continue
                valid_ids.append(str(pid))

        if len(valid_ids) != len(raw_ids):
            logger.warning(
                "Guardrail | Removed %d invalid product IDs from %s.",
                len(raw_ids) - len(valid_ids),
                action_type,
            )
        if not valid_ids:
            return None
        if action_type == ACTION_SHOW_COMPARISON:
            return {PRODUCT_IDS_PARAM: valid_ids[:4]}
        return {PRODUCT_IDS_PARAM: valid_ids}

    if action_type in (
        ACTION_SHOW_PRODUCT_DETAIL,
        ACTION_ADD_TO_CART,
        ACTION_REMOVE_FROM_CART,
        ACTION_UPDATE_CART_QUANTITY,
    ):
        pid = _coerce_product_id(params.get(PRODUCT_ID_PARAM))
        if pid is None or not product_exists(site_id, pid):
            logger.warning(
                "Guardrail | product_id=%r is invalid - removing action.",
                params.get(PRODUCT_ID_PARAM),
            )
            return None

        result = {PRODUCT_ID_PARAM: str(pid)}
        if (
            action_type in (ACTION_ADD_TO_CART, ACTION_UPDATE_CART_QUANTITY)
            and QUANTITY_PARAM in params
        ):
            try:
                result[QUANTITY_PARAM] = int(params[QUANTITY_PARAM])
            except (ValueError, TypeError):
                logger.warning("Guardrail | Invalid quantity for %s: %r", action_type, params[QUANTITY_PARAM])
        return result

    return params


def _validate_entity_ids(
    action_type: str,
    params: dict,
    site_id: str,
    allowed_entity_ids: list[str] | None = None,
) -> dict | None:
    """Validate generic record display actions against retrieved or tenant knowledge IDs."""
    if action_type in (ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES):
        raw_ids = params.get(ENTITY_IDS_PARAM, [])
        if not isinstance(raw_ids, list):
            logger.warning(
                "Guardrail | %s entity_ids is not a list - skipping.",
                action_type,
            )
            return None

        clean_ids = _clean_entity_ids(raw_ids)
        valid_ids = _valid_entity_ids(site_id, clean_ids, allowed_entity_ids)
        if len(valid_ids) != len(clean_ids):
            logger.warning(
                "Guardrail | Removed %d invalid entity IDs from %s.",
                len(clean_ids) - len(valid_ids),
                action_type,
            )
        if not valid_ids:
            return None

        result = {ENTITY_IDS_PARAM: valid_ids[:4] if action_type == ACTION_COMPARE_ENTITIES else valid_ids}
        _copy_safe_display_text(params, result)
        return result

    if action_type == ACTION_OPEN_ENTITY_DETAIL:
        raw_id = str(params.get(ENTITY_ID_PARAM) or params.get("id") or "").strip()
        valid_ids = _valid_entity_ids(site_id, [raw_id], allowed_entity_ids)
        if not valid_ids:
            logger.warning(
                "Guardrail | entity_id=%r is invalid - removing action.",
                params.get(ENTITY_ID_PARAM) or params.get("id"),
            )
            return None
        return {ENTITY_ID_PARAM: valid_ids[0]}

    return params


def _clean_entity_ids(raw_ids: list[Any]) -> list[str]:
    clean_ids: list[str] = []
    seen: set[str] = set()
    for raw_id in raw_ids:
        entity_id = str(raw_id or "").replace("\x00", "").strip()[:_MAX_ACTION_PARAM_VALUE_LENGTH]
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        clean_ids.append(entity_id)
    return clean_ids


def _valid_entity_ids(
    site_id: str,
    entity_ids: list[str],
    allowed_entity_ids: list[str] | None = None,
) -> list[str]:
    if not entity_ids:
        return []

    if allowed_entity_ids is not None:
        allowed = {str(entity_id or "").strip() for entity_id in allowed_entity_ids}
        return [entity_id for entity_id in entity_ids if entity_id in allowed]

    try:
        from db.knowledge import get_knowledge_items_by_ids

        items = get_knowledge_items_by_ids(site_id, entity_ids)
    except Exception as exc:
        logger.warning("Guardrail | entity ID lookup failed for %s: %s", site_id, exc)
        return []

    active_ids = {str(item.get("id") or "").strip() for item in items}
    return [entity_id for entity_id in entity_ids if entity_id in active_ids]


def _copy_safe_display_text(params: dict, result: dict) -> None:
    for key in ("search_query", "title"):
        value = _clean_action_param_value(params.get(key))
        if isinstance(value, str) and value:
            result[key] = value


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
    page = str(params.get("page", "")).strip().lower().strip("/")
    if page in _VALID_NAV_PAGES or page.startswith("category/") or page.startswith("shop?q="):
        return {"page": page}
    route_target = _adapter_route_target(page, adapter_routes or {})
    if route_target:
        return {"page": route_target}
    logger.warning("Guardrail | Invalid navigation page: %r - skipping.", page)
    return None


def _adapter_route_target(page: str, adapter_routes: dict[str, str]) -> str:
    if not page:
        return ""
    normalized_page = page.strip("/")
    normalized_page_key = _route_alias_key(normalized_page)
    for key, path in adapter_routes.items():
        route_key = str(key or "").strip().lower().strip("/")
        route_path = _clean_same_origin_path(path)
        if (normalized_page == route_key or normalized_page_key == route_key) and route_path:
            return route_path.strip("/") or route_key
        if route_path and normalized_page == route_path.strip("/"):
            return route_path.strip("/")
    return ""


def _clean_same_origin_path(value: Any) -> str:
    path = str(value or "").strip()
    lowered = path.lower()
    if (
        not path
        or path.startswith("//")
        or lowered.startswith(("http://", "https://", "javascript:", "data:"))
    ):
        return ""
    return path if path.startswith("/") else f"/{path}"


def _validate_sort_params(params: dict) -> dict | None:
    """Validate supported product sort options."""
    sort_by = str(params.get("sort_by", "")).strip().lower()
    if sort_by not in _VALID_SORTS:
        logger.warning("Guardrail | Invalid sort option: %r - skipping.", sort_by)
        return None
    return {"sort_by": sort_by}


def _validate_dom_sequence_params(params: dict) -> dict | None:
    """Validate a generated same-origin DOM operation sequence."""
    raw_steps = params.get(_DOM_SEQUENCE_STEPS_PARAM)
    if not isinstance(raw_steps, list):
        logger.warning("Guardrail | RUN_DOM_SEQUENCE steps must be a list.")
        return None

    steps = []
    for raw_step in raw_steps[:_DOM_SEQUENCE_MAX_STEPS]:
        step = _validate_dom_sequence_step(raw_step)
        if step is not None:
            steps.append(step)

    if not steps:
        logger.warning("Guardrail | RUN_DOM_SEQUENCE had no valid steps.")
        return None
    return {_DOM_SEQUENCE_STEPS_PARAM: steps}


def _validate_adapter_action_params(params: dict, action_config: dict[str, Any]) -> dict | None:
    """Keep privacy/safety-safe params needed by generated adapter actions."""
    action_type = str(action_config.get("type") or "").lower()
    if action_type in {"click", "navigate"}:
        return _safe_action_params(params, allowed_keys=_adapter_param_keys(action_config), allow_open=False)
    if action_type in {"form", "sequence"}:
        allowed_keys = _adapter_param_keys(action_config)
        return _safe_action_params(params, allowed_keys=allowed_keys, allow_open=not allowed_keys)
    return _safe_action_params(params, allowed_keys=set(), allow_open=True)


def _safe_action_params(params: dict, *, allowed_keys: set[str], allow_open: bool) -> dict | None:
    clean_params: dict[str, Any] = {}
    for raw_key, raw_value in list(params.items())[:_MAX_ACTION_PARAM_KEYS]:
        key = _clean_action_param_key(raw_key)
        if not key:
            continue
        if allowed_keys and _normalize_action_param_key(key) not in allowed_keys:
            continue
        if not allowed_keys and not allow_open:
            continue
        value = _clean_action_param_value(raw_value)
        if value is None:
            continue
        clean_params[key] = value
    return clean_params


def _adapter_param_keys(action_config: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for raw_key in action_config.get("fields") or []:
        key = _normalize_action_param_key(raw_key)
        if key:
            keys.add(key)
    for raw_step in action_config.get("steps") or []:
        if not isinstance(raw_step, dict):
            continue
        for field in ("param", "parameter", "name"):
            key = _normalize_action_param_key(raw_step.get(field))
            if key:
                keys.add(key)
    return keys


def _clean_action_param_key(value: Any) -> str:
    key = str(value or "").strip()
    if key in _BLOCKED_ACTION_PARAM_KEYS or not _SAFE_ACTION_PARAM_KEY.match(key):
        return ""
    return key


def _normalize_action_param_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _clean_action_param_value(value: Any) -> str | int | float | bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return None
    text = value.replace("\x00", "").strip()[:_MAX_ACTION_PARAM_VALUE_LENGTH]
    if text.lower().startswith(("javascript:", "data:")):
        return None
    return text


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
    routes: dict[str, str] = {}
    raw_routes = vertical_config.get("routes")
    if isinstance(raw_routes, dict):
        for name, path in raw_routes.items():
            _add_route_alias(routes, name, path)

    raw_actions = vertical_config.get("actions")
    if isinstance(raw_actions, dict):
        for _action_name, config in raw_actions.items():
            if not isinstance(config, dict):
                continue
            if str(config.get("type") or "").lower() not in {"navigate", "route"}:
                continue
            path = _observed_navigation_path(config.get("path") or config.get("page_path") or config.get("pagePath"))
            if not path:
                continue
            _add_route_alias(routes, config.get("label"), path)

    for candidate in _safe_list(vertical_config.get("action_candidates")):
        if not isinstance(candidate, dict):
            continue
        path = _observed_navigation_path(candidate.get("path"), candidate.get("origin"))
        if not path:
            continue
        if str(candidate.get("type") or "").lower() not in {"navigate", "route"} and str(candidate.get("kind") or "").lower() != "route":
            continue
        _add_route_alias(routes, candidate.get("label"), path)

    for event in _safe_list(vertical_config.get("interaction_events")):
        if not isinstance(event, dict):
            continue
        path = _observed_navigation_path(event.get("href"), event.get("origin"))
        if not path:
            continue
        _add_route_alias(routes, event.get("label"), path)
        _add_route_alias(routes, event.get("matched_label"), path)

    origin = vertical_config.get("url") or vertical_config.get("origin")
    for link in _safe_list(vertical_config.get("links")):
        if not isinstance(link, dict):
            continue
        path = _observed_navigation_path(link.get("href"), origin)
        if not path:
            continue
        _add_route_alias(routes, link.get("label"), path)
        _add_route_alias(routes, link.get("text"), path)

    return routes


def _add_route_alias(routes: dict[str, str], alias: Any, raw_path: Any) -> None:
    path = _observed_navigation_path(raw_path)
    key = _route_alias_key(alias)
    if is_generic_route_alias(key):
        return
    if key and path:
        routes.setdefault(key, path)
        routes.setdefault(path.strip("/").lower(), path)
        last_segment = path.split("?", 1)[0].split("#", 1)[0].strip("/").split("/")[-1]
        if last_segment:
            routes.setdefault(_route_alias_key(last_segment), path)
        for semantic_alias in semantic_route_alias_keys(key, last_segment):
            routes.setdefault(semantic_alias, path)


def _route_alias_key(value: Any) -> str:
    return route_alias_key(value)


def _observed_navigation_path(value: Any, origin: Any = "") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower().startswith(("http://", "https://")):
        try:
            from urllib.parse import urlparse

            parsed = urlparse(text)
            if origin:
                parsed_origin = urlparse(str(origin))
                if (parsed.scheme, parsed.netloc) != (parsed_origin.scheme, parsed_origin.netloc):
                    return ""
            return _clean_same_origin_path(f"{parsed.path or '/'}{('?' + parsed.query) if parsed.query else ''}{('#' + parsed.fragment) if parsed.fragment else ''}")
        except Exception:
            return ""
    return _clean_same_origin_path(text)


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _client_vertical_config(site_id: str) -> dict[str, Any]:
    try:
        from db import admin as admin_db

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


def _validate_dom_sequence_step(raw_step: Any) -> dict | None:
    if not isinstance(raw_step, dict):
        return None

    operation = _clean_dom_sequence_text(
        raw_step.get("op") or raw_step.get("type") or raw_step.get("action"),
        limit=40,
    ).lower()
    if operation not in _DOM_SEQUENCE_ALLOWED_OPERATIONS:
        return None

    step = {"op": operation}
    _copy_dom_sequence_common_fields(raw_step, step)
    if not _copy_dom_sequence_operation_fields(raw_step, step):
        return None
    return step


def _copy_dom_sequence_common_fields(raw_step: dict, step: dict) -> None:
    if raw_step.get("optional") is True:
        step["optional"] = True
    for key in ("label", "text", "name", "param", "parameter"):
        value = _clean_dom_sequence_text(raw_step.get(key))
        if value:
            step[key] = value


def _copy_dom_sequence_operation_fields(raw_step: dict, step: dict) -> bool:
    operation = step["op"]
    if operation == "navigate":
        return _copy_dom_sequence_path(raw_step, step)
    if operation == "wait":
        step["ms"] = _clean_dom_sequence_wait(raw_step.get("ms") or raw_step.get("timeout_ms"))
        return True
    if operation in {"click", "scroll"}:
        return _copy_dom_sequence_target(raw_step, step, require_selector=False)

    return _copy_dom_sequence_target(raw_step, step, require_selector=operation in _DOM_SEQUENCE_SELECTOR_OPERATIONS)


def _copy_dom_sequence_target(raw_step: dict, step: dict, require_selector: bool) -> bool:
    selector = _clean_dom_sequence_selector(raw_step.get("selector"))
    if selector:
        step["selector"] = selector
    if require_selector and not selector:
        return False

    value = _clean_dom_sequence_text(raw_step.get("value"))
    if value:
        step["value"] = value
    if step["op"] == "wait_for" and selector:
        step["ms"] = _clean_dom_sequence_wait(raw_step.get("ms") or raw_step.get("timeout_ms"))
    if step["op"] == "scroll":
        _copy_dom_sequence_scroll_fields(raw_step, step)
    return bool(selector or step.get("label") or step.get("text") or step["op"] == "scroll")


def _copy_dom_sequence_scroll_fields(raw_step: dict, step: dict) -> None:
    target = _clean_dom_sequence_text(raw_step.get("to"), limit=20).lower()
    if target in {"top", "bottom"}:
        step["to"] = target
    for key in ("x", "y"):
        if raw_step.get(key) is not None:
            step[key] = _clean_dom_sequence_number(raw_step.get(key))


def _copy_dom_sequence_path(raw_step: dict, step: dict) -> bool:
    path = _clean_dom_sequence_path(raw_step.get("path") or raw_step.get("url") or raw_step.get("href"))
    if not path:
        return False
    step["path"] = path
    return True


def _clean_dom_sequence_path(value: Any) -> str:
    path = _clean_dom_sequence_text(value)
    lowered = path.lower()
    if not path or lowered.startswith(("http://", "https://", "javascript:", "data:")):
        return ""
    return path


def _clean_dom_sequence_selector(value: Any) -> str:
    selector = _clean_dom_sequence_text(value)
    if not selector or _has_control_characters(selector):
        return ""
    return selector


def _clean_dom_sequence_text(value: Any, limit: int = _DOM_SEQUENCE_MAX_STRING_LENGTH) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _clean_dom_sequence_wait(value: Any) -> int:
    try:
        wait_ms = int(value)
    except (TypeError, ValueError):
        return 100
    return max(0, min(wait_ms, _DOM_SEQUENCE_MAX_WAIT_MS))


def _clean_dom_sequence_number(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _has_control_characters(value: str) -> bool:
    return any(ord(char) < 32 for char in value)


def _coerce_product_id(value: Any) -> int | None:
    """Return a positive integer product ID, or None for malformed values."""
    if isinstance(value, bool):
        return None
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None
