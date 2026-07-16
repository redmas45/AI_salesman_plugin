"""Entity and source-answer recovery helpers for product turns."""

from __future__ import annotations

import re
from typing import Any

from agent.responses import cart_responses, entity_turn_responses
from agent.products.product_response import ProductCatalogFormatter, normalize_lookup_text, phrase_in_text
from api.contracts.models import ACTION_COMPARE_ENTITIES, ACTION_SHOW_ENTITIES, ENTITY_IDS_PARAM


def claims_no_matching_products(value: Any) -> bool:
    text = normalize_lookup_text(value)
    patterns = (
        r"\b(couldn t|could not|can t|cannot|don t|do not|didn t|did not)\b.{0,45}\b(find|have|see|locate)\b",
        r"\b(no|not any|nothing)\b.{0,35}\b(match|matching|available|found|specific)\b",
        r"\b(out of stock|not available|unavailable)\b",
        r"\b(sorry for the confusion|apologies).*?(couldn t|could not|can t|cannot|don t)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def ensure_entity_answer_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_items: list[dict],
    formatter: ProductCatalogFormatter,
) -> None:
    if not wants_source_answer(transcript) or wants_comparison(transcript):
        return
    if any(
        action.get("action") in {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES, "OPEN_ENTITY_DETAIL"}
        for action in response.get("ui_actions", [])
    ):
        return

    selected = [item for item in retrieved_items if item.get("id") is not None][:4]
    if not selected:
        return

    response["intent"] = "discovery"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    response["ui_actions"] = [
        {"action": ACTION_SHOW_ENTITIES, "params": {ENTITY_IDS_PARAM: [str(item["id"]) for item in selected]}}
    ]
    response["response_text"] = entity_answer_fallback_text(selected, formatter)


def wants_source_answer(text: str) -> bool:
    normalized = normalize_lookup_text(text)
    if not normalized:
        return False
    patterns = (
        r"\bwhy\b",
        r"\bshould i\b",
        r"\brecommend\b",
        r"\btell me about\b",
        r"\bdetails?\b",
        r"\bfacts?\b",
        r"\bfeatures?\b",
        r"\bspecs?\b",
        r"\bspecifications?\b",
        r"\bprice\b",
        r"\bcost\b",
        r"\bpremium\b",
        r"\bcoverage\b",
        r"\bin stock\b",
        r"\bavailable\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def answer_target_products(
    transcript: str,
    products: list[dict],
    formatter: ProductCatalogFormatter,
) -> list[dict]:
    candidates = [product for product in products if product.get("id")]
    if not candidates:
        return []

    targeted = cart_responses.cart_target_product(transcript, candidates, formatter)
    if targeted:
        return [targeted]

    normalized = normalize_lookup_text(transcript)
    for product in candidates:
        name = normalize_lookup_text(product.get("name") or product.get("title") or "")
        if name and phrase_in_text(name, normalized):
            return [product]

    if len(candidates) == 1:
        return candidates
    return candidates[:3]


def entity_answer_fallback_text(items: list[dict], formatter: ProductCatalogFormatter) -> str:
    return entity_turn_responses.answer_fallback_text(items, formatter)


def entity_display_name(item: dict) -> str:
    return entity_turn_responses.display_name(item)


def entity_fact_text(item: dict, formatter: ProductCatalogFormatter) -> str:
    return entity_turn_responses.fact_text(item, formatter)


def entity_comparison_fact_text(item: dict, formatter: ProductCatalogFormatter) -> str:
    return entity_turn_responses.comparison_fact_text(item, formatter)


def entity_availability_text(item: dict) -> str:
    return entity_turn_responses.availability_text(item)


def entity_location_text(item: dict) -> str:
    return entity_turn_responses.location_text(item)


def looks_priced_entity(item: dict) -> bool:
    return entity_turn_responses.looks_priced(item)


def generic_comparison_fallback_text(items: list[dict], formatter: ProductCatalogFormatter) -> str:
    return entity_turn_responses.comparison_fallback_text(items, formatter)


def wants_comparison(transcript: str) -> bool:
    text = (transcript or "").lower()
    if re.search(r"\b(open|view|inspect|see)\b", text) and re.search(
        r"\b(cheaper|cheapest|first|second|third|one|item|product)\b",
        text,
    ):
        return False
    tokens = ("compare", "comparison", "difference", "better", "versus", " vs ")
    return any(token in text for token in tokens)
