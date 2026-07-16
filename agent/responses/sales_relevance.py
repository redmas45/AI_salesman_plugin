"""Sales relevance, answer scope, and cache-safety policy."""

from __future__ import annotations

import re
from typing import Any

from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_CHECKOUT,
    ACTION_CLEAR_CART,
    ACTION_COMPARE_ENTITIES,
    ACTION_FILTER_PRODUCTS,
    ACTION_NAVIGATE_TO,
    ACTION_REMOVE_FROM_CART,
    ACTION_RUN_DOM_SEQUENCE,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_ENTITIES,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_SHOW_PRODUCTS,
    ACTION_SORT_ENTITIES,
    ACTION_SORT_PRODUCTS,
    ACTION_UPDATE_CART_QUANTITY,
)

SCOPE_GROUNDED_FACT = "grounded_fact"
SCOPE_BUYING_GUIDANCE = "buying_guidance"
SCOPE_WEBSITE_ACTION = "website_action"
SCOPE_UNSUPPORTED = "unsupported_or_offsite"

CACHEABLE_SCOPES = {SCOPE_GROUNDED_FACT, SCOPE_BUYING_GUIDANCE}

SAFE_CACHE_ACTIONS = {
    ACTION_SHOW_PRODUCTS,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_ENTITIES,
    ACTION_COMPARE_ENTITIES,
    ACTION_FILTER_PRODUCTS,
    ACTION_SORT_PRODUCTS,
    ACTION_SORT_ENTITIES,
    ACTION_NAVIGATE_TO,
    ACTION_SHOW_PRODUCT_DETAIL,
    "OPEN_ENTITY_DETAIL",
}

SIDE_EFFECT_ACTIONS = {
    ACTION_ADD_TO_CART,
    ACTION_REMOVE_FROM_CART,
    ACTION_UPDATE_CART_QUANTITY,
    ACTION_CLEAR_CART,
    ACTION_CHECKOUT,
    ACTION_RUN_DOM_SEQUENCE,
    "START_QUOTE",
    "START_BOOKING",
    "START_APPLICATION",
    "REQUEST_APPOINTMENT",
    "BOOK_APPOINTMENT_REQUEST",
    "REQUEST_TEST_DRIVE",
    "REQUEST_VIEWING",
    "REQUEST_CONSULTATION",
    "REQUEST_ESTIMATE",
    "REQUEST_SITE_VISIT",
    "START_TICKET_PURCHASE",
    "START_ENROLLMENT",
    "REQUEST_COUNSELOR_CALLBACK",
    "REQUEST_CALLBACK",
    "CAPTURE_LEAD",
    "CONTACT_AGENT",
    "HANDOFF_TO_AGENT",
}

BUYING_TERMS = {
    "buy",
    "purchase",
    "recommend",
    "best",
    "better",
    "compare",
    "difference",
    "price",
    "cost",
    "premium",
    "coverage",
    "stock",
    "available",
    "availability",
    "features",
    "spec",
    "specs",
    "benefit",
    "plan",
    "option",
}

DEEP_OFFSITE_TERMS = {
    "architecture",
    "microarchitecture",
    "transistor",
    "instruction set",
    "kernel",
    "compiler",
    "die shot",
    "semiconductor",
    "chip fabrication",
    "teardown",
    "source code",
    "reverse engineer",
    "circuit diagram",
    "schematic",
    "benchmark internals",
    "research paper",
    "molecular chemistry",
    "receptor pathway",
    "receptor pathways",
    "pharmacodynamics",
}

CLEARLY_UNRELATED_PATTERNS = (
    r"\bwho\s+(?:is|was)\s+(?:the\s+)?(?:prime minister|president|chief minister|king|queen)\b",
    r"\b(?:weather|temperature|forecast)\s+(?:in|for|at)\b",
    r"\b(?:what|how)(?:\s+is|\s+will|\s+s)?\b.{0,35}\b(?:weather|temperature|forecast)\b",
    r"\b(?:weather|forecast)\b.{0,30}\b(?:today|tomorrow|this week|next week)\b",
    r"\b(?:latest|breaking)\s+(?:news|headlines?|sports scores?)\b",
    r"\bwhat\s+is\s+the\s+capital\s+of\b",
    r"\b(?:solve|differentiate|integrate)\s+(?:this\s+)?(?:equation|expression|function)\b",
)


def answer_scope_for(
    query: str,
    retrieved_items: list[dict[str, Any]] | None = None,
    ui_actions: list[dict[str, Any]] | None = None,
    *,
    llm_scope: str = "",
) -> str:
    """Classify the assistant answer without exposing private reasoning."""
    clean_llm_scope = str(llm_scope or "").strip()
    if clean_llm_scope == SCOPE_UNSUPPORTED and not is_unsupported_or_offsite(
        query,
        retrieved_items or [],
    ):
        clean_llm_scope = ""
    if clean_llm_scope in {
        SCOPE_GROUNDED_FACT,
        SCOPE_BUYING_GUIDANCE,
        SCOPE_WEBSITE_ACTION,
        SCOPE_UNSUPPORTED,
    }:
        return clean_llm_scope

    actions = _action_names(ui_actions)
    if actions & SIDE_EFFECT_ACTIONS:
        return SCOPE_WEBSITE_ACTION
    if is_unsupported_or_offsite(query, retrieved_items or []):
        return SCOPE_UNSUPPORTED
    if retrieved_items:
        return SCOPE_GROUNDED_FACT
    if _has_buying_language(query):
        return SCOPE_BUYING_GUIDANCE
    if actions:
        return SCOPE_WEBSITE_ACTION
    return SCOPE_GROUNDED_FACT


def should_bypass_answer_cache(query: str, ui_actions: list[dict[str, Any]] | None = None) -> bool:
    """Return True when a turn can change website/customer state."""
    actions = _action_names(ui_actions)
    if actions & SIDE_EFFECT_ACTIONS:
        return True

    text = _norm(query)
    if not text:
        return True
    patterns = (
        r"\b(add|put|place|remove|delete|clear|empty|update|change)\b.{0,36}\b(cart|basket|bag|checkout|quantity)\b",
        r"\b(checkout|pay|payment|complete purchase|buy now|order now)\b",
        r"\b(start|get|show|generate)\b.{0,26}\b(quote|application|booking|reservation|ticket)\b",
        r"\b(book|reserve|apply|enroll|register|schedule)\b",
        r"\b(call me|callback|contact me|send my details|submit|sign me up)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def is_safe_cache_response(
    query: str,
    result: dict[str, Any],
    retrieved_items: list[dict[str, Any]] | None = None,
) -> bool:
    """Decide whether a completed assistant turn can be reused for this tenant/version."""
    if should_bypass_answer_cache(query, result.get("ui_actions")):
        return False
    response_text = str(result.get("response_text") or "").strip()
    if len(response_text) < 8:
        return False
    scope = str(result.get("answer_scope") or "")
    if scope not in CACHEABLE_SCOPES:
        return False
    actions = _action_names(result.get("ui_actions"))
    if actions and not actions <= SAFE_CACHE_ACTIONS:
        return False
    if is_unsupported_or_offsite(query, retrieved_items or []):
        return False
    return bool(retrieved_items) or _has_buying_language(query)


def bounded_unsupported_response(query: str, retrieved_items: list[dict[str, Any]] | None = None) -> str:
    """Return a bounded answer when the query asks for off-site depth not present in data."""
    if is_clearly_unrelated(query):
        return (
            "I am here to help with this website's products, services, and buying journey rather than general "
            "trivia or live information. Tell me what you are considering, and I will help you narrow it down."
        )
    if not is_unsupported_or_offsite(query, retrieved_items or []):
        return ""
    return (
        "I can help with buying-relevant details that this website provides, but that deeper technical detail "
        "is not in the site data I have. I can still compare the listed options by the published specs, price, "
        "availability, reviews, coverage, or other website-confirmed facts."
    )


def is_unsupported_or_offsite(query: str, retrieved_items: list[dict[str, Any]]) -> bool:
    text = _norm(query)
    if not text:
        return False
    if is_clearly_unrelated(text):
        return True
    if not any(_phrase(term, text) for term in DEEP_OFFSITE_TERMS):
        return False
    return not retrieval_supports_query_detail(query, retrieved_items)


def is_clearly_unrelated(query: str) -> bool:
    """Identify narrow, high-confidence general-assistant requests."""
    text = _norm(query)
    return any(re.search(pattern, text) for pattern in CLEARLY_UNRELATED_PATTERNS)


def retrieval_supports_query_detail(query: str, retrieved_items: list[dict[str, Any]]) -> bool:
    """Check whether retrieved source rows explicitly contain the requested deep terms."""
    text = _norm(query)
    if not text or not retrieved_items:
        return False
    requested = {term for term in DEEP_OFFSITE_TERMS if _phrase(term, text)}
    if not requested:
        return bool(retrieved_items)
    source_text = _norm(" ".join(_item_text(item) for item in retrieved_items[:8]))
    return any(_phrase(term, source_text) for term in requested)


def source_ids_and_urls(items: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    urls: list[str] = []
    for item in items[:12]:
        item_id = str(item.get("id") or "").strip()
        url = str(item.get("url") or item.get("source_url") or "").strip()
        if item_id and item_id not in ids:
            ids.append(item_id)
        if url and url not in urls:
            urls.append(url)
    return ids, urls


def _has_buying_language(query: str) -> bool:
    text = _norm(query)
    return any(_phrase(term, text) for term in BUYING_TERMS)


def _action_names(actions: Any) -> set[str]:
    if not isinstance(actions, list):
        return set()
    names: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            continue
        name = str(action.get("action") or "").strip().upper()
        if name:
            names.add(name)
    return names


def _item_text(item: dict[str, Any]) -> str:
    values = [
        item.get("name"),
        item.get("title"),
        item.get("subtitle"),
        item.get("summary"),
        item.get("body"),
        item.get("description"),
        item.get("brand"),
        item.get("category"),
        item.get("category_name"),
        item.get("attributes"),
        item.get("pricing"),
        item.get("availability"),
        item.get("policy"),
        item.get("tags"),
    ]
    return " ".join(str(value or "") for value in values)


def _norm(value: Any) -> str:
    text = re.sub(r"[^a-z0-9\s-]+", " ", str(value or "").lower())
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _phrase(needle: str, haystack: str) -> bool:
    clean_needle = _norm(needle)
    clean_haystack = _norm(haystack)
    return bool(clean_needle and re.search(rf"\b{re.escape(clean_needle)}\b", clean_haystack))
