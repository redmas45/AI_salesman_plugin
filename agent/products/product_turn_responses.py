"""Product and entity response recovery helpers for orchestrator turns."""

from __future__ import annotations

import re
from typing import Any

from agent.responses import cart_responses
from agent.products.product_response import (
    ProductCatalogFormatter,
    ProductDisplayGrounder,
    ProductSearchQueryCleaner,
    normalize_lookup_text,
)
from agent.products.product_turn_entity_responses import (
    answer_target_products,
    claims_no_matching_products,
    ensure_entity_answer_response,
    entity_answer_fallback_text,
    entity_availability_text,
    entity_comparison_fact_text,
    entity_display_name,
    entity_fact_text,
    entity_location_text,
    generic_comparison_fallback_text,
    looks_priced_entity,
    wants_comparison,
    wants_source_answer,
)
from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_COMPARE_ENTITIES,
    ACTION_NAVIGATE_TO,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_SHOW_PRODUCTS,
    ENTITY_IDS_PARAM,
    PRODUCT_IDS_PARAM,
    PRODUCT_ID_PARAM,
)


def promote_comparison_action(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict] | None = None,
) -> None:
    if not wants_comparison(transcript):
        return

    actions = response.get("ui_actions", [])
    requested_limit = comparison_product_limit(transcript)
    for action in actions:
        if action.get("action") != ACTION_SHOW_COMPARISON:
            continue
        product_ids = action.get("params", {}).get(PRODUCT_IDS_PARAM, [])
        if isinstance(product_ids, list) and len(product_ids) >= 2:
            action["params"][PRODUCT_IDS_PARAM] = product_ids[:requested_limit]
            return
        fallback_ids = [str(product["id"]) for product in retrieved_products or [] if product.get("id")][:4]
        if len(fallback_ids) >= 2:
            action["params"] = {PRODUCT_IDS_PARAM: fallback_ids}
        return

    for action in actions:
        if action.get("action") == ACTION_SHOW_PRODUCTS:
            product_ids = action.get("params", {}).get(PRODUCT_IDS_PARAM, [])
            if isinstance(product_ids, list) and len(product_ids) >= 2:
                action["action"] = ACTION_SHOW_COMPARISON
                action["params"] = {PRODUCT_IDS_PARAM: product_ids[:requested_limit]}
                response["intent"] = "product_compare"
                return

    fallback_ids = [str(product["id"]) for product in retrieved_products or [] if product.get("id")][
        :requested_limit
    ]
    if len(fallback_ids) < 2:
        return
    response["intent"] = "product_compare"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.88)
    response["ui_actions"] = [
        {"action": ACTION_SHOW_COMPARISON, "params": {PRODUCT_IDS_PARAM: fallback_ids}}
    ]


def ensure_named_comparison_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    formatter: ProductCatalogFormatter,
) -> None:
    if not wants_comparison(transcript):
        return
    if any(action.get("action") == ACTION_SHOW_COMPARISON for action in response.get("ui_actions", [])):
        return

    exact_products = [product for product in retrieved_products if product.get("_exact_name_match")]
    if len(exact_products) < 2:
        return

    selected = exact_products[:4]
    product_ids = [str(product["id"]) for product in selected]
    response["intent"] = "product_compare"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
    response["ui_actions"] = [
        {"action": ACTION_SHOW_COMPARISON, "params": {PRODUCT_IDS_PARAM: product_ids}}
    ]
    response["response_text"] = comparison_fallback_text(selected, formatter)


def ensure_generic_comparison_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_items: list[dict],
    formatter: ProductCatalogFormatter,
) -> None:
    if not wants_comparison(transcript):
        return
    if any(action.get("action") == ACTION_COMPARE_ENTITIES for action in response.get("ui_actions", [])):
        return

    comparable_items = [item for item in retrieved_items if item.get("id") is not None]
    if len(comparable_items) < 2:
        return

    selected = comparable_items[:comparison_product_limit(transcript)]
    entity_ids = [str(item["id"]) for item in selected]
    response["intent"] = "compare"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.88)
    response["ui_actions"] = [
        {"action": ACTION_COMPARE_ENTITIES, "params": {ENTITY_IDS_PARAM: entity_ids}}
    ]
    response["response_text"] = generic_comparison_fallback_text(selected, formatter)


def comparison_product_limit(transcript: str) -> int:
    text = normalize_lookup_text(transcript)
    if re.search(r"\b(two|2|both)\b", text):
        return 2
    if re.search(r"\b(three|3)\b", text):
        return 3
    if re.search(r"\b(four|4)\b", text):
        return 4
    return 4


def ensure_product_answer_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    formatter: ProductCatalogFormatter,
    query_cleaner: ProductSearchQueryCleaner,
) -> None:
    if not wants_source_answer(transcript) or wants_comparison(transcript) or cart_responses.wants_cart_add(transcript):
        return
    if any(action.get("action") in {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON} for action in response.get("ui_actions", [])):
        return

    selected = answer_target_products(transcript, retrieved_products, formatter)
    if not selected:
        return

    product_ids = [str(product["id"]) for product in selected if product.get("id")]
    if not product_ids:
        return

    response["intent"] = "product_detail" if len(selected) == 1 else "product_search"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    response["ui_actions"] = [
        {
            "action": ACTION_SHOW_PRODUCTS,
            "params": {
                PRODUCT_IDS_PARAM: product_ids[:6],
                "search_query": display_search_query(transcript, query_cleaner, selected),
            },
        }
    ]
    response["response_text"] = product_answer_fallback_text(selected, formatter)


def ensure_product_search_display_action(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    formatter: ProductCatalogFormatter,
    query_cleaner: ProductSearchQueryCleaner,
) -> None:
    if str(response.get("intent") or "") != "product_search":
        return
    if wants_source_answer(transcript) or wants_comparison(transcript) or cart_responses.wants_cart_add(transcript):
        return
    if any(
        action.get("action") in {
            ACTION_ADD_TO_CART,
            ACTION_SHOW_COMPARISON,
            ACTION_SHOW_PRODUCTS,
            "SHOW_PRODUCT_DETAIL",
        }
        for action in response.get("ui_actions", [])
        if isinstance(action, dict)
    ):
        return

    selected = [product for product in retrieved_products if product.get("id") is not None][:8]
    if not selected:
        return

    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    response["ui_actions"] = [
        {
            "action": ACTION_SHOW_PRODUCTS,
            "params": {
                PRODUCT_IDS_PARAM: [str(product["id"]) for product in selected],
                "search_query": display_search_query(transcript, query_cleaner, selected),
            },
        }
    ]
    response["response_text"] = product_search_fallback_text(retrieved_products, formatter)


def coerce_recommendation_to_product_search(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    formatter: ProductCatalogFormatter,
    query_cleaner: ProductSearchQueryCleaner,
) -> None:
    if not retrieved_products:
        return
    if not is_recommendation_request(transcript):
        return
    if cart_responses.wants_cart_add(transcript):
        return

    actions = response.get("ui_actions") if isinstance(response.get("ui_actions"), list) else []
    response["ui_actions"] = [
        action
        for action in actions
        if isinstance(action, dict) and str(action.get("action") or "").upper() != ACTION_ADD_TO_CART
    ]
    response["intent"] = "product_search"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    if asks_to_add_choice(response.get("response_text")) or not response["ui_actions"]:
        selected = [product for product in retrieved_products if product.get("id") is not None][:8]
        if not selected:
            return
        response["ui_actions"] = [
            {
                "action": ACTION_SHOW_PRODUCTS,
                "params": {
                    PRODUCT_IDS_PARAM: [str(product["id"]) for product in selected],
                    "search_query": display_search_query(transcript, query_cleaner, selected),
                },
            }
        ]
        response["response_text"] = product_search_fallback_text(retrieved_products, formatter)


def is_recommendation_request(text: str) -> bool:
    normalized = normalize_lookup_text(text)
    return bool(re.search(r"\b(recommend|suggest|advice|advise|options?|something|best|budget)\b", normalized))


def asks_to_add_choice(text: Any) -> bool:
    normalized = normalize_lookup_text(text)
    return bool(re.search(r"\bwhich one\b.{0,40}\b(add|cart|buy)\b", normalized))


def prevent_false_no_matching_product_claim(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    query_cleaner: ProductSearchQueryCleaner,
) -> None:
    if not retrieved_products:
        return
    if not claims_no_matching_products(response.get("response_text")):
        return

    selected = retrieved_products[:8]
    product_ids = [str(product.get("id")) for product in selected if product.get("id")]
    if not product_ids:
        return
    names = [str(product.get("name") or product.get("title") or "").strip() for product in selected[:3]]
    shown_names = ", ".join(name for name in names if name)
    response["intent"] = "product_search"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.92)
    response["response_text"] = f"I found {len(retrieved_products)} matching products"
    if shown_names:
        response["response_text"] += f": {shown_names}"
    response["response_text"] += "."
    response["ui_actions"] = [
        {
            "action": ACTION_SHOW_PRODUCTS,
            "params": {
                PRODUCT_IDS_PARAM: product_ids,
                "search_query": display_search_query(transcript, query_cleaner, selected),
            },
        }
    ]


def ensure_product_display_search_queries(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    formatter: ProductCatalogFormatter,
    query_cleaner: ProductSearchQueryCleaner,
) -> None:
    actions = response.get("ui_actions")
    if not isinstance(actions, list):
        return

    detail_target = explicit_product_detail_target(transcript, retrieved_products, formatter)
    if detail_target:
        response["intent"] = "product_detail"
        response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
        response["response_text"] = product_answer_fallback_text([detail_target], formatter)
        response["ui_actions"] = [
            {
                "action": ACTION_SHOW_PRODUCT_DETAIL,
                "params": {PRODUCT_ID_PARAM: str(detail_target["id"])},
            }
        ]
        return

    actions = promote_explicit_product_detail_action(actions, transcript)
    actions = coherent_product_display_actions(actions)
    response["ui_actions"] = actions

    for action in actions:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action") or "").upper()
        if action_name == ACTION_SHOW_COMPARISON:
            continue
        if action_name == ACTION_SHOW_PRODUCTS:
            params = action.get("params") if isinstance(action.get("params"), dict) else {}
            action_products = products_selected_by_ids(params.get(PRODUCT_IDS_PARAM), retrieved_products)
            search_query = normalized_product_action_search_query(
                params.get("search_query"),
                transcript,
                action_products or retrieved_products,
                query_cleaner,
            )
            action["params"] = {
                **params,
                "search_query": search_query,
            }

def promote_explicit_product_detail_action(
    actions: list[Any],
    transcript: str,
) -> list[dict[str, Any]]:
    text = normalize_lookup_text(transcript)
    wants_open_detail = bool(
        re.search(r"\b(open|show|view|see)\b.{0,45}\b(details?|product page|item page)\b", text)
        or re.search(
            r"\b(open|view|see)\b.{0,60}\b(cheaper|cheapest|compared|first|second|third|that one|this one)\b",
            text,
        )
    )
    if not wants_open_detail:
        return [action for action in actions if isinstance(action, dict)]

    promoted: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        product_ids = params.get(PRODUCT_IDS_PARAM)
        if action.get("action") == ACTION_SHOW_PRODUCTS and isinstance(product_ids, list) and len(product_ids) == 1:
            promoted.append(
                {"action": ACTION_SHOW_PRODUCT_DETAIL, "params": {PRODUCT_ID_PARAM: str(product_ids[0])}}
            )
            continue
        promoted.append(action)
    return promoted


def explicit_product_detail_target(
    transcript: str,
    retrieved_products: list[dict],
    formatter: ProductCatalogFormatter,
) -> dict | None:
    text = normalize_lookup_text(transcript)
    wants_selection = bool(
        re.search(r"\b(open|view|inspect|see)\b", text)
        and re.search(
            r"\b(cheaper|cheapest|first|second|third|compared|that one|this one)\b",
            text,
        )
    )
    if not wants_selection:
        return None
    return cart_responses.cart_target_product(text, retrieved_products, formatter)


def coherent_product_display_actions(actions: list[Any]) -> list[dict[str, Any]]:
    """Keep one coherent product-display path for a single assistant turn."""
    has_comparison = any(
        isinstance(action, dict) and str(action.get("action") or "").upper() == ACTION_SHOW_COMPARISON
        for action in actions
    )
    if not has_comparison:
        return [action for action in actions if isinstance(action, dict)]

    coherent_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action") or "").upper()
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        if action_name == ACTION_SHOW_PRODUCTS:
            continue
        if action_name == ACTION_NAVIGATE_TO and str(params.get("page") or "").startswith("shop?q="):
            continue
        coherent_actions.append(action)
    return coherent_actions


def normalized_product_action_search_query(
    raw_query: Any,
    transcript: str,
    retrieved_products: list[dict],
    query_cleaner: ProductSearchQueryCleaner,
) -> str:
    raw_text = str(raw_query or "").strip()
    if raw_text:
        cleaned = display_search_query(raw_text, query_cleaner, retrieved_products)
        if cleaned and cleaned != "products":
            if len(retrieved_products) == 1 and cleaned in product_category_queries(
                retrieved_products[0],
                query_cleaner,
            ):
                product_name_query = display_search_query(
                    str(retrieved_products[0].get("name") or retrieved_products[0].get("title") or ""),
                    query_cleaner,
                )
                if product_name_query and product_name_query != "products":
                    return product_name_query
            return cleaned
    if len(retrieved_products) == 1 and not query_cleaner.search_query_words(transcript):
        product_name_query = display_search_query(
            str(retrieved_products[0].get("name") or retrieved_products[0].get("title") or ""),
            query_cleaner,
        )
        if product_name_query and product_name_query != "products":
            return product_name_query
    return display_search_query(transcript, query_cleaner, retrieved_products)


def products_selected_by_ids(raw_ids: Any, products: list[dict]) -> list[dict]:
    if not isinstance(raw_ids, list):
        return []
    selected_ids = {str(product_id) for product_id in raw_ids if product_id is not None}
    selected: list[dict] = []
    seen_ids: set[str] = set()
    for product in products:
        product_id = str(product.get("id"))
        if product_id not in selected_ids or product_id in seen_ids:
            continue
        seen_ids.add(product_id)
        selected.append(product)
    return selected


def product_category_queries(
    product: dict,
    query_cleaner: ProductSearchQueryCleaner,
) -> set[str]:
    queries: set[str] = set()
    for key in ("subcategory", "category_name", "category"):
        value = str(product.get(key) or "").strip()
        if not value:
            continue
        query = display_search_query(value, query_cleaner)
        if query and query != "products":
            queries.add(query)
    return queries


def ground_product_display_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    grounder: ProductDisplayGrounder,
) -> None:
    grounder.ground_response(
        response,
        transcript,
        retrieved_products,
        wants_comparison=wants_comparison,
        wants_source_answer=wants_source_answer,
    )


def products_selected_by_display_action(
    action: dict[str, Any],
    retrieved_products: list[dict],
    grounder: ProductDisplayGrounder,
) -> list[dict]:
    return grounder.products_selected_by_display_action(action, retrieved_products)


def product_search_fallback_text(products: list[dict], formatter: ProductCatalogFormatter) -> str:
    return formatter.search_text(products)


def display_search_query(
    transcript: str,
    query_cleaner: ProductSearchQueryCleaner,
    products: list[dict] | None = None,
) -> str:
    return query_cleaner.display_search_query(transcript, products)


def search_query_words(value: Any, query_cleaner: ProductSearchQueryCleaner) -> list[str]:
    return query_cleaner.search_query_words(value)


def should_bypass_ecommerce_answer_cache(
    transcript: str,
    query_cleaner: ProductSearchQueryCleaner,
) -> bool:
    return query_cleaner.should_bypass_ecommerce_answer_cache(transcript)


def display_search_query_from_products(
    products: list[dict],
    query_cleaner: ProductSearchQueryCleaner,
) -> str:
    return query_cleaner.display_search_query_from_products(products)


def product_answer_fallback_text(products: list[dict], formatter: ProductCatalogFormatter) -> str:
    return formatter.answer_text(products)


def product_fact_parts(product: dict, formatter: ProductCatalogFormatter) -> list[str]:
    return formatter.fact_parts(product)


def product_comparison_fact_text(product: dict, formatter: ProductCatalogFormatter) -> str:
    return formatter.comparison_fact_text(product)


def comparison_fallback_text(products: list[dict], formatter: ProductCatalogFormatter) -> str:
    return formatter.comparison_text(products)
