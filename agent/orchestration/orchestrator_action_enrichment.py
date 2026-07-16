"""Action parameter and variant enrichment for orchestrator responses."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

import psycopg

from agent.action_helpers import action_params
from api.contracts.models import ACTION_ADD_TO_CART, PRODUCT_ID_PARAM

ProductConnectionFactory = Callable[[str], Any]
ClientDetailLoader = Callable[[str], dict[str, Any]]
RecoverableErrors = tuple[type[BaseException], ...]


def add_variant_ids_to_cart_actions(
    site_id: str,
    actions: list[dict[str, Any]],
    *,
    get_db: ProductConnectionFactory,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    for action in actions:
        if action.get("action") != ACTION_ADD_TO_CART:
            continue
        product_id = action.get("params", {}).get(PRODUCT_ID_PARAM)
        if not product_id:
            continue
        try:
            with get_db(site_id) as conn:
                row = conn.execute(
                    "SELECT variant_id FROM products WHERE id = %s",
                    (product_id,),
                ).fetchone()
        except psycopg.Error as exc:
            logger.warning("PIPELINE | variant lookup failed for %s: %s", product_id, exc)
            continue
        if row and row["variant_id"]:
            action["params"]["variant_id"] = str(row["variant_id"])
    return actions


def enrich_action_params_from_context(
    site_id: str,
    transcript: str,
    conversation_history: list,
    actions: list[dict[str, Any]],
    *,
    get_client_detail: ClientDetailLoader,
    recoverable_errors: RecoverableErrors,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    """Fill obvious action params from conversation facts before capability filtering."""
    if not actions:
        return actions

    action_configs = action_configs_for_site(
        site_id,
        get_client_detail=get_client_detail,
        recoverable_errors=recoverable_errors,
        logger=logger,
    )
    context_text = action_params.action_param_context_text(transcript, conversation_history)

    enriched_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            enriched_actions.append(action)
            continue
        action_name = str(action.get("action") or "").upper()
        facts = action_params.action_param_facts_from_text(
            context_text,
            action_config=action_configs.get(action_name) or {},
        )
        if not facts:
            enriched_actions.append(action)
            continue
        enriched_actions.append(enriched_action_with_facts(action, facts))
    return enriched_actions


def enriched_action_with_facts(action: dict[str, Any], facts: dict[str, str]) -> dict[str, Any]:
    params = action.get("params") if isinstance(action.get("params"), dict) else {}
    enriched_params = dict(params)
    changed = False
    for key, value in facts.items():
        if action_params.action_param_has_value(enriched_params, key):
            continue
        enriched_params[key] = value
        changed = True
    if not changed:
        return action
    updated = dict(action)
    updated["params"] = enriched_params
    return updated


def action_configs_for_site(
    site_id: str,
    *,
    get_client_detail: ClientDetailLoader,
    recoverable_errors: RecoverableErrors,
    logger: logging.Logger,
) -> dict[str, dict[str, Any]]:
    try:
        client = get_client_detail(site_id)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | action config lookup skipped: %s", exc)
        return {}
    vertical_config = client.get("vertical_config") if isinstance(client, dict) else {}
    actions = vertical_config.get("actions") if isinstance(vertical_config, dict) else {}
    if not isinstance(actions, dict):
        return {}
    return {
        str(action_name or "").upper(): config
        for action_name, config in actions.items()
        if str(action_name or "").strip() and isinstance(config, dict)
    }


def legacy_extract_money_like_value(text: str) -> str:
    match = re.search(
        r"(?:\u20b9|rs\.?|inr|\$|usd)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:k|lakh|lakhs|crore|cr)?\b",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else ""
