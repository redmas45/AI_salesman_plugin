"""Product runtime bootstrap and compatibility exports for agent.orchestrator."""

from __future__ import annotations

import logging
from typing import Any

from agent import product_turn_responses
from agent.responses import cart_responses
from agent.orchestration.orchestrator_product_runtime import OrchestratorProductRuntime
from agent.products.product_matching import ProductCatalogMatcher
from agent.products.product_response import (
    ProductCatalogFormatter,
    ProductDisplayGrounder,
    ProductSearchQueryCleaner,
    normalize_lookup_text as product_normalize_lookup_text,
    numeric_value as product_numeric_value,
    phrase_in_text as product_phrase_in_text,
)


def _load_catalog_products(site_id: str, limit: int) -> list[dict[str, Any]]:
    from db.core.database import get_all_products as load_all_products

    return load_all_products(site_id, limit=limit)


def _load_catalog_products_by_ids(site_id: str, product_ids: list[int]) -> list[dict[str, Any]]:
    from db.core.database import get_products_by_ids

    return get_products_by_ids(site_id, product_ids)


def exports(
    *,
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> dict[str, Any]:
    query_cleaner = ProductSearchQueryCleaner()
    formatter = ProductCatalogFormatter()
    display_grounder = ProductDisplayGrounder(formatter)
    matcher = ProductCatalogMatcher(
        load_all_products=_load_catalog_products,
        load_products_by_ids=_load_catalog_products_by_ids,
        recoverable_errors=recoverable_errors,
        logger=logger,
    )
    product_runtime = OrchestratorProductRuntime(
        matcher=matcher,
        formatter=formatter,
        query_cleaner=query_cleaner,
        display_grounder=display_grounder,
    )
    return {
        "_load_catalog_products": _load_catalog_products,
        "_load_catalog_products_by_ids": _load_catalog_products_by_ids,
        "PRODUCT_QUERY_CLEANER": query_cleaner,
        "PRODUCT_CATALOG_FORMATTER": formatter,
        "PRODUCT_DISPLAY_GROUNDER": display_grounder,
        "PRODUCT_CATALOG_MATCHER": matcher,
        "PRODUCT_TURN_RUNTIME": product_runtime,
        "_merge_products": product_runtime.merge_products,
        "_exact_products_from_query": product_runtime.exact_products_from_query,
        "_phrase_in_text": product_phrase_in_text,
        "_normalize_lookup_text": product_normalize_lookup_text,
        "_promote_comparison_action": product_turn_responses.promote_comparison_action,
        "_ensure_named_comparison_response": product_runtime.ensure_named_comparison_response,
        "_ensure_generic_comparison_response": product_runtime.ensure_generic_comparison_response,
        "_ensure_product_answer_response": product_runtime.ensure_product_answer_response,
        "_ensure_product_search_display_action": product_runtime.ensure_product_search_display_action,
        "_coerce_recommendation_to_product_search": product_runtime.coerce_recommendation_to_product_search,
        "_is_recommendation_request": product_turn_responses.is_recommendation_request,
        "_asks_to_add_choice": product_turn_responses.asks_to_add_choice,
        "_prevent_false_no_matching_product_claim": product_runtime.prevent_false_no_matching_product_claim,
        "_ensure_product_display_search_queries": product_runtime.ensure_product_display_search_queries,
        "_normalized_product_action_search_query": product_runtime.normalized_product_action_search_query,
        "_ground_product_display_response": product_runtime.ground_product_display_response,
        "_products_selected_by_display_action": product_runtime.products_selected_by_display_action,
        "_product_search_fallback_text": product_runtime.product_search_fallback_text,
        "_display_search_query": product_runtime.display_search_query,
        "_search_query_words": product_runtime.search_query_words,
        "_should_bypass_ecommerce_answer_cache": product_runtime.should_bypass_ecommerce_answer_cache,
        "_display_search_query_from_products": product_runtime.display_search_query_from_products,
        "_claims_no_matching_products": product_turn_responses.claims_no_matching_products,
        "_ensure_entity_answer_response": product_runtime.ensure_entity_answer_response,
        "_wants_source_answer": product_turn_responses.wants_source_answer,
        "_answer_target_products": product_runtime.answer_target_products,
        "_product_answer_fallback_text": product_runtime.product_answer_fallback_text,
        "_product_fact_parts": product_runtime.product_fact_parts,
        "_product_comparison_fact_text": product_runtime.product_comparison_fact_text,
        "_entity_answer_fallback_text": product_runtime.entity_answer_fallback_text,
        "_entity_display_name": product_turn_responses.entity_display_name,
        "_entity_fact_text": product_runtime.entity_fact_text,
        "_entity_comparison_fact_text": product_runtime.entity_comparison_fact_text,
        "_entity_availability_text": product_turn_responses.entity_availability_text,
        "_entity_location_text": product_turn_responses.entity_location_text,
        "_looks_priced_entity": product_turn_responses.looks_priced_entity,
        "_ensure_cart_request_response": product_runtime.ensure_cart_request_response,
        "_wants_cart_add": cart_responses.wants_cart_add,
        "_cart_target_product": product_runtime.cart_target_product,
        "_ordinal_index": cart_responses.ordinal_index,
        "_cart_quantity": cart_responses.cart_quantity,
        "_product_stock": product_runtime.product_stock,
        "_product_price": product_runtime.product_price,
        "_numeric_value": product_numeric_value,
        "_product_display_name": product_runtime.product_display_name,
        "_cart_confirmation_text": product_runtime.cart_confirmation_text,
        "_comparison_fallback_text": product_runtime.comparison_fallback_text,
        "_generic_comparison_fallback_text": product_runtime.generic_comparison_fallback_text,
    }
