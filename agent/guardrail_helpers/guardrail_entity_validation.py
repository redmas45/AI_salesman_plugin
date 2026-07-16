"""Product and entity ID validation helpers for output guardrails."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from agent.guardrail_helpers import guardrail_action_params
from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_COMPARE_ENTITIES,
    ACTION_OPEN_ENTITY_DETAIL,
    ACTION_REMOVE_FROM_CART,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_ENTITIES,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_SHOW_PRODUCTS,
    ACTION_UPDATE_CART_QUANTITY,
    ENTITY_ID_PARAM,
    ENTITY_IDS_PARAM,
    PRODUCT_ID_PARAM,
    PRODUCT_IDS_PARAM,
    QUANTITY_PARAM,
)

ProductExists = Callable[[str, int], bool]
CoerceProductId = Callable[[Any], int | None]
CleanEntityIds = Callable[[list[Any]], list[str]]
ValidEntityIds = Callable[[str, list[str], list[str] | None], list[str]]
CopySafeDisplayText = Callable[[dict, dict], None]


def validate_product_ids(
    action_type: str,
    params: dict,
    site_id: str,
    *,
    product_exists: ProductExists,
    coerce_product_id: CoerceProductId,
    logger: logging.Logger,
    allowed_product_ids: list[int] | None = None,
) -> dict | None:
    """Validate product actions and drop commands that target missing products."""
    if action_type in (ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON):
        return _validate_product_list_action(
            action_type,
            params,
            site_id,
            product_exists=product_exists,
            coerce_product_id=coerce_product_id,
            logger=logger,
            allowed_product_ids=allowed_product_ids,
        )

    if action_type in (
        ACTION_SHOW_PRODUCT_DETAIL,
        ACTION_ADD_TO_CART,
        ACTION_REMOVE_FROM_CART,
        ACTION_UPDATE_CART_QUANTITY,
    ):
        return _validate_single_product_action(
            action_type,
            params,
            site_id,
            product_exists=product_exists,
            coerce_product_id=coerce_product_id,
            logger=logger,
        )

    return params


def validate_entity_ids(
    action_type: str,
    params: dict,
    site_id: str,
    *,
    clean_entity_ids: CleanEntityIds,
    valid_entity_ids: ValidEntityIds,
    copy_safe_display_text: CopySafeDisplayText,
    logger: logging.Logger,
    allowed_entity_ids: list[str] | None = None,
) -> dict | None:
    """Validate generic record display actions against retrieved or tenant knowledge IDs."""
    if action_type in (ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES):
        return _validate_entity_list_action(
            action_type,
            params,
            site_id,
            clean_entity_ids=clean_entity_ids,
            valid_entity_ids=valid_entity_ids,
            copy_safe_display_text=copy_safe_display_text,
            logger=logger,
            allowed_entity_ids=allowed_entity_ids,
        )

    if action_type == ACTION_OPEN_ENTITY_DETAIL:
        raw_id = str(params.get(ENTITY_ID_PARAM) or params.get("id") or "").strip()
        valid_ids = valid_entity_ids(site_id, [raw_id], allowed_entity_ids)
        if not valid_ids:
            logger.warning(
                "Guardrail | entity_id=%r is invalid - removing action.",
                params.get(ENTITY_ID_PARAM) or params.get("id"),
            )
            return None
        return {ENTITY_ID_PARAM: valid_ids[0]}

    return params


def clean_entity_ids(raw_ids: list[Any]) -> list[str]:
    clean_ids: list[str] = []
    seen: set[str] = set()
    for raw_id in raw_ids:
        entity_id = (
            str(raw_id or "")
            .replace("\x00", "")
            .strip()[: guardrail_action_params.MAX_ACTION_PARAM_VALUE_LENGTH]
        )
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        clean_ids.append(entity_id)
    return clean_ids


def valid_entity_ids(
    site_id: str,
    entity_ids: list[str],
    allowed_entity_ids: list[str] | None = None,
    *,
    logger: logging.Logger,
) -> list[str]:
    if not entity_ids:
        return []

    if allowed_entity_ids is not None:
        allowed = {str(entity_id or "").strip() for entity_id in allowed_entity_ids}
        return [entity_id for entity_id in entity_ids if entity_id in allowed]

    try:
        from db.knowledge_base.knowledge_items import get_knowledge_items_by_ids

        items = get_knowledge_items_by_ids(site_id, entity_ids)
    except Exception as exc:
        logger.warning("Guardrail | entity ID lookup failed for %s: %s", site_id, exc)
        return []

    active_ids = {str(item.get("id") or "").strip() for item in items}
    return [entity_id for entity_id in entity_ids if entity_id in active_ids]


def copy_safe_display_text(params: dict, result: dict) -> None:
    for key in ("search_query", "title"):
        value = guardrail_action_params.clean_action_param_value(params.get(key))
        if isinstance(value, str) and value:
            result[key] = value


def coerce_product_id(value: Any) -> int | None:
    """Return a positive integer product ID, or None for malformed values."""
    if isinstance(value, bool):
        return None
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _validate_product_list_action(
    action_type: str,
    params: dict,
    site_id: str,
    *,
    product_exists: ProductExists,
    coerce_product_id: CoerceProductId,
    logger: logging.Logger,
    allowed_product_ids: list[int] | None,
) -> dict | None:
    raw_ids = params.get(PRODUCT_IDS_PARAM, [])
    if not isinstance(raw_ids, list):
        logger.warning(
            "Guardrail | %s product_ids is not a list - skipping.",
            action_type,
        )
        return None

    valid_ids = []
    for raw_id in raw_ids:
        pid = coerce_product_id(raw_id)
        if pid is None or not product_exists(site_id, pid):
            continue
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


def _validate_single_product_action(
    action_type: str,
    params: dict,
    site_id: str,
    *,
    product_exists: ProductExists,
    coerce_product_id: CoerceProductId,
    logger: logging.Logger,
) -> dict | None:
    pid = coerce_product_id(params.get(PRODUCT_ID_PARAM))
    if pid is None or not product_exists(site_id, pid):
        logger.warning(
            "Guardrail | product_id=%r is invalid - removing action.",
            params.get(PRODUCT_ID_PARAM),
        )
        return None

    result = {PRODUCT_ID_PARAM: str(pid)}
    if action_type in (ACTION_ADD_TO_CART, ACTION_UPDATE_CART_QUANTITY) and QUANTITY_PARAM in params:
        try:
            result[QUANTITY_PARAM] = int(params[QUANTITY_PARAM])
        except (ValueError, TypeError):
            logger.warning(
                "Guardrail | Invalid quantity for %s: %r",
                action_type,
                params[QUANTITY_PARAM],
            )
    return result


def _validate_entity_list_action(
    action_type: str,
    params: dict,
    site_id: str,
    *,
    clean_entity_ids: CleanEntityIds,
    valid_entity_ids: ValidEntityIds,
    copy_safe_display_text: CopySafeDisplayText,
    logger: logging.Logger,
    allowed_entity_ids: list[str] | None,
) -> dict | None:
    raw_ids = params.get(ENTITY_IDS_PARAM, [])
    if not isinstance(raw_ids, list):
        logger.warning(
            "Guardrail | %s entity_ids is not a list - skipping.",
            action_type,
        )
        return None

    clean_ids = clean_entity_ids(raw_ids)
    valid_ids = valid_entity_ids(site_id, clean_ids, allowed_entity_ids)
    if len(valid_ids) != len(clean_ids):
        logger.warning(
            "Guardrail | Removed %d invalid entity IDs from %s.",
            len(clean_ids) - len(valid_ids),
            action_type,
        )
    if not valid_ids:
        return None

    result = {
        ENTITY_IDS_PARAM: valid_ids[:4]
        if action_type == ACTION_COMPARE_ENTITIES
        else valid_ids
    }
    copy_safe_display_text(params, result)
    return result
