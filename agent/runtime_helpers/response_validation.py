"""LLM response normalization and validation helpers."""

from __future__ import annotations

import logging
from typing import Any, Callable

from agent.guardrail_helpers.guardrails import OutputGuardrailError
from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_COMPARE_ENTITIES,
    ACTION_FILTER_PRODUCTS,
    ACTION_NAVIGATE_TO,
    ACTION_REMOVE_FROM_CART,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_ENTITIES,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_SHOW_PRODUCTS,
    ACTION_UPDATE_CART_QUANTITY,
    ACTION_UPDATE_PREFERENCES,
    ENTITY_IDS_PARAM,
    PRODUCT_ID_PARAM,
    PRODUCT_IDS_PARAM,
)


def normalize_llm_response(
    llm_response: dict[str, Any],
    retrieved_products: list[dict[str, Any]],
    *,
    fallback_search_response: Callable[[list[dict[str, Any]]], dict[str, Any]],
    logger: logging.Logger,
) -> dict[str, Any]:
    normalized = dict(llm_response)
    normalized["ui_actions"] = normalize_product_action_ids(normalized.get("ui_actions"))
    normalized["ui_actions"] = fill_missing_entity_list_ids(
        normalized.get("ui_actions"),
        retrieved_products,
    )
    normalized["ui_actions"] = drop_empty_filter_actions(normalized["ui_actions"])
    if not retrieved_products and normalized.get("intent") == "product_search":
        normalized["ui_actions"] = []
        normalized["intent"] = "out_of_stock"
    if normalized.get("intent") == "out_of_stock":
        normalized["ui_actions"] = []
    if normalized.get("intent") == "error" and retrieved_products:
        logger.info("PIPELINE | LLM failed, falling back to local FAISS search results.")
        return fallback_search_response(retrieved_products)
    return normalized


def normalize_product_action_ids(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        next_action = dict(action)
        params = dict(action.get("params")) if isinstance(action.get("params"), dict) else {}
        action_name = str(action.get("action") or "").upper()
        if action_name in {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON}:
            raw_ids = params.get(PRODUCT_IDS_PARAM)
            if isinstance(raw_ids, list):
                params[PRODUCT_IDS_PARAM] = [clean_model_id(value) for value in raw_ids]
        if action_name in {
            ACTION_ADD_TO_CART,
            ACTION_REMOVE_FROM_CART,
            ACTION_SHOW_PRODUCT_DETAIL,
            ACTION_UPDATE_CART_QUANTITY,
        } and PRODUCT_ID_PARAM in params:
            params[PRODUCT_ID_PARAM] = clean_model_id(params[PRODUCT_ID_PARAM])
        next_action["params"] = params
        normalized.append(next_action)
    return normalized


def clean_model_id(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip().strip("\"'").strip()


def drop_empty_filter_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []

    clean_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action") or "").upper()
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        if action_name == ACTION_FILTER_PRODUCTS and not has_meaningful_filter_params(params):
            continue
        clean_actions.append(action)
    return clean_actions


def has_meaningful_filter_params(params: dict[str, Any]) -> bool:
    return any(value not in (None, "", [], {}) for value in params.values())


def fill_missing_entity_list_ids(
    actions: Any,
    retrieved_products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []

    entity_ids = [str(item.get("id")) for item in retrieved_products if item.get("id") is not None]
    if not entity_ids:
        return actions_with_valid_entity_ids(actions)

    filled_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        next_action = dict(action)
        action_name = str(next_action.get("action") or "").upper()
        params = next_action.get("params")
        next_params = dict(params) if isinstance(params, dict) else {}
        if action_name in {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES} and not isinstance(
            next_params.get(ENTITY_IDS_PARAM),
            list,
        ):
            next_params[ENTITY_IDS_PARAM] = entity_ids
            next_action["params"] = next_params
        filled_actions.append(next_action)
    return filled_actions


def actions_with_valid_entity_ids(actions: list[Any]) -> list[dict[str, Any]]:
    clean_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action") or "").upper()
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        if action_name in {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES} and not isinstance(
            params.get(ENTITY_IDS_PARAM),
            list,
        ):
            continue
        clean_actions.append(action)
    return clean_actions


def persist_preference_actions(
    site_id: str,
    actions: list[dict[str, Any]],
    *,
    update_user_preferences: Callable[[str, Any], Any],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> None:
    for action in actions:
        if action.get("action") != ACTION_UPDATE_PREFERENCES:
            continue
        preferences = action.get("params", {}).get("preferences")
        if not preferences:
            continue
        try:
            update_user_preferences(site_id, preferences)
        except recoverable_errors as exc:
            logger.warning("PIPELINE | failed to update preferences: %s", exc)


def validate_agent_response(
    response: dict[str, Any],
    *,
    site_id: str,
    safe_transcript: str,
    retrieved_products: list[dict[str, Any]],
    blocked_text: str,
    page_context: dict[str, Any] | None,
    validate_output: Callable[..., dict[str, Any]],
    blocked_response: Callable[[str], dict[str, Any]],
    repair_navigation_actions: Callable[[dict[str, Any], str, str, dict[str, Any] | None], None],
    is_ecommerce_site: Callable[[str], bool],
    override_hallucinated_product_search: Callable[[dict[str, Any], list[str]], None],
    ecommerce_recoveries: list[Callable[[dict[str, Any], str, list[dict[str, Any]]], None]],
    empty_inventory_recovery: Callable[[dict[str, Any], str, str], None],
    product_display_query_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None],
    product_grounding_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None],
    generic_comparison_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None],
    entity_answer_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None],
    suppress_lead_recovery: Callable[[dict[str, Any], str, list[str]], bool],
    lead_flow_recovery: Callable[[dict[str, Any], str, str], None],
    align_removed_actions: Callable[[dict[str, Any], str, str, list[str], dict[str, Any] | None], None],
    neutralize_pending_claims: Callable[[str, list[dict[str, Any]]], str],
    logger: logging.Logger,
) -> dict[str, Any]:
    original_actions = [
        str(action.get("action") or "").upper()
        for action in response.get("ui_actions", [])
        if isinstance(action, dict)
    ]
    try:
        repair_navigation_actions(response, site_id, safe_transcript, page_context)
        validated = validate_output(
            response,
            site_id,
            [product["id"] for product in retrieved_products],
            allowed_entity_ids=[str(item["id"]) for item in retrieved_products if item.get("id") is not None],
            runtime_context=page_context,
        )
        if is_ecommerce_site(site_id):
            override_hallucinated_product_search(validated, original_actions)
    except OutputGuardrailError as exc:
        logger.error("PIPELINE | Output guardrail blocked response: %s", exc)
        validated = blocked_response(blocked_text)

    if is_ecommerce_site(site_id):
        for recovery in ecommerce_recoveries:
            recovery(validated, safe_transcript, retrieved_products)
        empty_inventory_recovery(validated, safe_transcript, site_id)
        product_grounding_recovery(validated, safe_transcript, retrieved_products)
        product_display_query_recovery(validated, safe_transcript, retrieved_products)
    else:
        generic_comparison_recovery(validated, safe_transcript, retrieved_products)
        entity_answer_recovery(validated, safe_transcript, retrieved_products)
        if not suppress_lead_recovery(validated, safe_transcript, original_actions):
            lead_flow_recovery(validated, safe_transcript, site_id)

    validated["ui_actions"] = drop_empty_filter_actions(validated.get("ui_actions"))
    align_removed_actions(validated, safe_transcript, site_id, original_actions, page_context)
    validated["response_text"] = neutralize_pending_claims(
        str(validated.get("response_text") or ""),
        validated.get("ui_actions", []),
    )
    return validated


def repair_navigation_actions(
    response: dict[str, Any],
    site_id: str,
    transcript: str,
    page_context: dict[str, Any] | None,
    *,
    navigation_page_from_transcript: Callable[..., str],
) -> None:
    actions = response.get("ui_actions")
    if not isinstance(actions, list):
        return

    candidates = [transcript, str(response.get("response_text") or "")]
    for action in actions:
        if not isinstance(action, dict):
            continue
        if str(action.get("action") or "").upper() != ACTION_NAVIGATE_TO:
            continue
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        if str(params.get("page") or "").strip():
            continue
        repaired_page = repaired_navigation_page(
            site_id,
            candidates,
            page_context,
            navigation_page_from_transcript=navigation_page_from_transcript,
        )
        if repaired_page:
            action["params"] = {**params, "page": repaired_page}


def repaired_navigation_page(
    site_id: str,
    candidates: list[str],
    page_context: dict[str, Any] | None,
    *,
    navigation_page_from_transcript: Callable[..., str],
) -> str:
    for candidate in candidates:
        page = navigation_page_from_transcript(
            site_id,
            candidate,
            page_context,
            require_specific_match=True,
        )
        if page:
            return page
    return ""


def override_hallucinated_product_search(
    validated: dict[str, Any],
    original_actions: list[str],
    *,
    logger: logging.Logger,
) -> None:
    validated_actions = [action.get("action") for action in validated.get("ui_actions", [])]
    if ACTION_SHOW_PRODUCTS not in original_actions or ACTION_SHOW_PRODUCTS in validated_actions:
        return
    logger.warning(
        "PIPELINE | Detected LLM hallucination: SHOW_PRODUCTS was completely blocked. Overriding response."
    )
    validated["intent"] = "out_of_stock"
    validated["ui_actions"] = []
    validated["response_text"] = (
        "I'm sorry, I couldn't find any products matching your request in our current inventory."
    )
