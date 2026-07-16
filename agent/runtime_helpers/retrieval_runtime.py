"""Retrieval, cache, and history helpers for orchestrator runtime turns."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from agent.products.product_matching import ProductCatalogMatcher
from agent.products.product_response import normalize_lookup_text
from api.contracts.models import (
    ACTION_COMPARE_ENTITIES,
    ACTION_NAVIGATE_TO,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_ENTITIES,
    ACTION_SHOW_PRODUCTS,
    ACTION_SORT_ENTITIES,
    ACTION_SORT_PRODUCTS,
    PRODUCT_IDS_PARAM,
)


@dataclass(frozen=True)
class RetrievalContext:
    profile: dict[str, Any]
    price_constraints: dict[str, Any]
    products: list[dict[str, Any]]


def cached_answer_response(
    site_id: str,
    session_id: str,
    transcript: str,
    safe_transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    should_bypass_answer_cache: Callable[[str], bool],
    is_ecommerce_site: Callable[[str], bool],
    should_bypass_ecommerce_answer_cache: Callable[[str], bool],
    lookup_answer_cache: Callable[[str, str, str], dict[str, Any] | None],
    claims_no_matching_products: Callable[[Any], bool],
    enrich_cached_product_actions: Callable[[str, list[dict[str, Any]]], list[dict[str, Any]]],
    synthesize_audio_b64: Callable[[str, bool], tuple[str, float | None]],
    elapsed_ms: Callable[[float], float],
    ai_log: Callable[[str, Any], None],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> dict[str, Any] | None:
    if should_bypass_answer_cache(safe_transcript):
        return None
    if is_ecommerce_site(site_id) and should_bypass_ecommerce_answer_cache(safe_transcript):
        return None

    started_at = time.perf_counter()
    try:
        cached = lookup_answer_cache(site_id, safe_transcript, session_id)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | answer cache lookup skipped for %s: %s", site_id, exc)
        timings["cache_ms"] = elapsed_ms(started_at)
        return None
    timings["cache_ms"] = elapsed_ms(started_at)
    if not cached:
        return None

    response_text = str(cached.get("answer_text") or "").strip()
    if not response_text:
        return None
    if is_ecommerce_site(site_id) and claims_no_matching_products(response_text):
        return None

    ui_actions = cached.get("ui_actions") if isinstance(cached.get("ui_actions"), list) else []
    ui_actions = enrich_cached_product_actions(safe_transcript, ui_actions)
    audio_b64, tts_ms = synthesize_audio_b64(response_text, skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms
    timings["total_ms"] = elapsed_ms(start_time)

    source_ids = cached.get("source_ids") or []
    retrieval = {
        "source": cached_retrieval_source(ui_actions),
        "issue": "ok" if source_ids else "cache_hit",
        "cache_source": "answer_cache",
        "cache_hit": True,
        "match_type": cached.get("match_type") or "",
        "match_score": cached.get("match_score") or 0.0,
        "data_version": cached.get("data_version") or 0,
        "retrieved_count": len(source_ids),
        "retrieved_ids": source_ids,
        "source_ids": source_ids,
        "source_urls": cached.get("source_urls") or [],
        "answer_scope": cached.get("answer_scope") or "",
    }
    ai_log("assistant", response_text)
    ai_log("actions", ui_actions)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": cached_answer_intent(cached, ui_actions),
        "confidence": float(cached.get("confidence") or 0.95),
        "answer_scope": str(cached.get("answer_scope") or ""),
        "ui_actions": ui_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
        "retrieval": retrieval,
    }


def cached_answer_intent(cached: dict[str, Any], ui_actions: list[dict[str, Any]]) -> str:
    from agent.products.product_turn_responses import wants_source_answer

    for action in ui_actions:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action") or "").upper()
        if action_name == ACTION_SHOW_COMPARISON:
            return "product_compare"
        if action_name == ACTION_COMPARE_ENTITIES:
            return "compare"
        if action_name == ACTION_SHOW_PRODUCTS:
            question = str(cached.get("question") or cached.get("normalized_question") or "")
            return "product_detail" if wants_source_answer(question) else "product_search"
        if action_name == ACTION_SHOW_ENTITIES:
            return "discovery"
        if action_name == ACTION_NAVIGATE_TO:
            return "navigate"
        if action_name in {ACTION_SORT_PRODUCTS, ACTION_SORT_ENTITIES}:
            return "sort"
    return "answer_cache"


def enrich_cached_product_actions(
    safe_transcript: str,
    ui_actions: list[dict[str, Any]],
    *,
    ensure_product_display_search_queries: Callable[[dict[str, Any], str, list[dict]], None],
) -> list[dict[str, Any]]:
    if cached_retrieval_source(ui_actions) != "products":
        return ui_actions
    response = {
        "ui_actions": [
            dict(action)
            for action in ui_actions
            if isinstance(action, dict)
        ]
    }
    ensure_product_display_search_queries(response, safe_transcript, [])
    return response["ui_actions"]


def cached_retrieval_source(ui_actions: list[dict[str, Any]]) -> str:
    action_names = {
        str(action.get("action") or "").upper()
        for action in ui_actions
        if isinstance(action, dict)
    }
    if action_names & {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON}:
        return "products"
    if action_names & {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES, "OPEN_ENTITY_DETAIL"}:
        return "knowledge_items"
    return "answer_cache"


def maybe_store_answer_cache(
    site_id: str,
    session_id: str,
    safe_transcript: str,
    result: dict[str, Any],
    retrieved_items: list[dict[str, Any]],
    retrieval_evidence: dict[str, Any],
    *,
    is_safe_cache_response: Callable[[str, dict[str, Any], list[dict[str, Any]]], bool],
    source_ids_and_urls: Callable[[list[dict[str, Any]]], tuple[list[str], list[str]]],
    store_answer_cache: Callable[..., dict[str, Any] | None],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> None:
    if not is_safe_cache_response(safe_transcript, result, retrieved_items):
        retrieval_evidence["cache_write"] = "skipped"
        return
    source_ids, source_urls = source_ids_and_urls(retrieved_items)
    try:
        cached = store_answer_cache(
            site_id,
            session_id=session_id,
            question=safe_transcript,
            answer_text=str(result.get("response_text") or ""),
            answer_scope=str(result.get("answer_scope") or ""),
            cache_type="runtime_llm",
            source_ids=source_ids,
            source_urls=source_urls,
            ui_actions=result.get("ui_actions") if isinstance(result.get("ui_actions"), list) else [],
            confidence=float(result.get("confidence") or 0.0),
        )
        retrieval_evidence["cache_write"] = "stored" if cached else "skipped"
        if cached:
            retrieval_evidence["cache_data_version"] = cached.get("data_version")
    except recoverable_errors as exc:
        logger.warning("PIPELINE | answer cache write skipped for %s: %s", site_id, exc)
        retrieval_evidence["cache_write"] = "error"


def retrieval_evidence(
    site_id: str,
    ecommerce_runtime: bool,
    retrieved_items: list[dict[str, Any]],
    price_constraints: dict[str, Any] | None,
    *,
    inventory_summary: Callable[[str], dict[str, Any]],
    recoverable_errors: tuple[type[BaseException], ...],
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "source": "products" if ecommerce_runtime else "knowledge_items",
        "retrieved_count": len(retrieved_items),
        "retrieved_ids": [
            str(item.get("id"))
            for item in retrieved_items[:8]
            if item.get("id") is not None
        ],
        "retrieved_titles": [
            title
            for title in (retrieval_item_title(item) for item in retrieved_items[:5])
            if title
        ],
    }
    if price_constraints:
        evidence["price_constraints"] = dict(price_constraints)

    try:
        if ecommerce_runtime:
            stats = inventory_summary(site_id)
            evidence.update(
                {
                    "total_records": safe_int(stats.get("total_products")),
                    "active_records": safe_int(stats.get("active_products")),
                    "in_stock_records": safe_int(stats.get("in_stock_products")),
                    "missing_embeddings": safe_int(stats.get("missing_embeddings")),
                    "groups": safe_int(stats.get("total_categories")),
                }
            )
        else:
            from db.knowledge_base.knowledge_items import knowledge_stats

            stats = knowledge_stats(site_id)
            evidence.update(
                {
                    "total_records": safe_int(stats.get("total_items")),
                    "active_records": safe_int(stats.get("active_items")),
                    "missing_embeddings": safe_int(stats.get("missing_embeddings")),
                    "groups": safe_int(stats.get("entity_types")),
                }
            )
    except recoverable_errors as exc:
        evidence["stats_error"] = str(exc)

    evidence["issue"] = retrieval_issue(evidence)
    return evidence


def retrieval_item_title(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("title") or item.get("summary") or "").strip()[:120]


def retrieval_issue(evidence: dict[str, Any]) -> str:
    active = safe_int(evidence.get("active_records"))
    retrieved = safe_int(evidence.get("retrieved_count"))
    missing = safe_int(evidence.get("missing_embeddings"))
    if active <= 0:
        return "no_active_records"
    if retrieved <= 0:
        return "retrieval_returned_zero"
    if missing >= active:
        return "all_vectors_missing"
    if missing > 0:
        return "some_vectors_missing"
    return "ok"


def safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def safe_user_profile(
    site_id: str,
    *,
    get_user_profile: Callable[[str], dict[str, Any]],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> dict[str, Any]:
    try:
        return get_user_profile(site_id)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | user profile unavailable for %s: %s", site_id, exc)
        return {}


def profile_context(profile: dict[str, Any]) -> str:
    return (
        f"Address: {profile.get('address') or 'None'} | "
        f"Payment Method: {profile.get('payment_method') or 'None'} | "
        f"Preferences: {profile.get('preferences') or 'None'}"
    )


def augment_query_with_history(
    query: str,
    history: list[dict] | None,
    *,
    normalize_lookup_text: Callable[[Any], str],
    search_query_words: Callable[[Any], list[str]],
    logger: logging.Logger,
) -> str:
    if not history:
        return query

    normalized_query = normalize_lookup_text(query)
    query_terms = search_query_words(query)
    if not needs_history_product_context(normalized_query, query_terms):
        return query

    history_terms = recent_product_context_terms(
        history,
        query,
        normalize_lookup_text=normalize_lookup_text,
        search_query_words=search_query_words,
    )
    if not history_terms:
        return query

    augmented = f"{' '.join(history_terms[:4])}. {query}"
    logger.info("PIPELINE | Augmented RAG query with history: %s", augmented)
    return augmented


def needs_history_product_context(normalized_query: str, query_terms: list[str]) -> bool:
    if not normalized_query:
        return False
    if is_referential_product_followup(normalized_query):
        return True
    context_only_terms = {
        "affordable",
        "cheap",
        "cheaper",
        "cheapest",
        "costliest",
        "expensive",
        "least",
        "lowest",
        "more",
        "one",
        "other",
        "premium",
        "three",
        "two",
    }
    if query_terms and any(term not in context_only_terms and not term.isdigit() for term in query_terms):
        return False
    if len(normalized_query.split()) <= 5:
        return True
    return bool(
        re.search(
            r"\b(i don t know|dont know|not sure|budget|rupees?|rs|inr|under|below|less than|"
            r"other|another|more|else|those|these|it|them|same|any)\b",
            normalized_query,
        )
    )


def is_referential_product_followup(text: str) -> bool:
    return bool(
        re.search(
            r"\b(those|these|them|compared|shortlisted|the other|the cheaper|the cheapest|"
            r"the better|better value|best one|best option|which option|which one|that one|"
            r"this one|open it|add it|pick it)\b",
            text,
        )
        or re.search(r"\b(?:open|view|add|buy|choose|pick)\s+that\s+[a-z][a-z0-9-]{2,}\b", text)
    )


def history_message_is_context_free(text: str, terms: list[str]) -> bool:
    if not terms or is_referential_product_followup(text):
        return True
    if re.search(r"\bcompare\b.{0,50}\b(options?|items?|products?|them|those|these)\b", text):
        return True
    return bool(
        re.search(
            r"\b(prime minister|president|weather|temperature|forecast|capital of|latest news|"
            r"architecture|microarchitecture|transistor|instruction set|kernel|compiler|"
            r"return policy|returns page|shipping page)\b",
            text,
        )
    )


def recent_product_context_terms(
    history: list[dict] | None,
    current_query: str,
    *,
    normalize_lookup_text: Callable[[Any], str],
    search_query_words: Callable[[Any], list[str]],
) -> list[str]:
    current_normalized = normalize_lookup_text(current_query)
    for message in reversed(history or []):
        if message.get("role") != "user":
            continue
        content = str(message.get("content") or "").strip()
        if not content or normalize_lookup_text(content) == current_normalized:
            continue
        terms = search_query_words(content)
        normalized_content = normalize_lookup_text(content)
        if terms and not history_message_is_context_free(normalized_content, terms):
            return terms
    return []


def retrieve_context(
    site_id: str,
    safe_transcript: str,
    conversation_history: list | None,
    *,
    safe_user_profile: Callable[[str], dict[str, Any]],
    augment_query_with_history: Callable[[str, list[dict] | None], str],
    is_ecommerce_site: Callable[[str], bool],
    retrieve_generic_context: Callable[[str, str, dict[str, Any]], RetrievalContext],
    extract_price_constraints: Callable[[str], dict[str, Any]],
    retrieve_products: Callable[..., list[dict[str, Any]]],
    merge_products: Callable[[list[dict], list[dict], int | None], list[dict]],
    merge_history_products: Callable[[list[dict[str, Any]], list, str, str], list[dict[str, Any]]],
    exact_products_from_query: Callable[[str, str], list[dict]],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> RetrievalContext:
    profile = safe_user_profile(site_id)
    rag_query = augment_query_with_history(safe_transcript, conversation_history)
    if profile.get("preferences"):
        rag_query = f"{rag_query} (User preferences: {profile['preferences']})"

    if not is_ecommerce_site(site_id):
        return retrieve_generic_context(site_id, rag_query, profile)

    try:
        # Historical context helps retrieval, but an older budget must never
        # override an explicit limit in the current turn.
        price_constraints = extract_price_constraints(safe_transcript)
        retrieved_products = retrieve_products(
            rag_query,
            site_id=site_id,
            price_constraints=price_constraints,
        )
        history_products = merge_history_products(
            retrieved_products,
            conversation_history or [],
            site_id,
            safe_transcript,
        )
        exact_products = exact_products_from_query(rag_query, site_id)
        is_referential = is_referential_product_followup(str(safe_transcript or "").lower())
        referenced_products = [
            product for product in history_products if product.get("_history_context")
        ]
        if is_referential and referenced_products:
            products = referenced_products
        elif is_referential:
            products = merge_products(exact_products, history_products, None)
        else:
            products = merge_products(history_products, exact_products, None)
        if not is_referential:
            products = products_for_explicit_request(products, safe_transcript)
        products = products_within_price_constraints(products, price_constraints)
        return RetrievalContext(profile, price_constraints, products)
    except recoverable_errors as exc:
        logger.error("PIPELINE | RAG failed: %s", exc)
        return RetrievalContext(profile, {}, [])


def retrieve_generic_context(
    site_id: str,
    rag_query: str,
    profile: dict[str, Any],
    *,
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> RetrievalContext:
    try:
        from agent.retrieval.generic_rag import retrieve_knowledge

        items = retrieve_knowledge(rag_query, site_id=site_id)
        return RetrievalContext(profile, {}, items)
    except recoverable_errors as exc:
        logger.error("PIPELINE | Generic RAG failed: %s", exc)
        return RetrievalContext(profile, {}, [])


def merge_history_products(
    retrieved_products: list[dict[str, Any]],
    conversation_history: list,
    site_id: str,
    current_query: str,
    *,
    matcher: ProductCatalogMatcher,
) -> list[dict[str, Any]]:
    history_products = matcher.extract_products_from_history(
        conversation_history,
        site_id,
        expected_count=referential_product_count(current_query),
    )
    return matcher.merge(retrieved_products, history_products)


def referential_product_count(text: str) -> int | None:
    normalized = str(text or "").lower()
    if re.search(r"\b(both|(?:those|these|the)\s+(?:two|2))\b", normalized):
        return 2
    if re.search(r"\b(?:those|these|the)\s+(?:three|3)\b", normalized):
        return 3
    if re.search(r"\b(?:those|these|the)\s+(?:four|4)\b", normalized):
        return 4
    return None


def products_within_price_constraints(
    products: list[dict[str, Any]],
    constraints: dict[str, Any],
) -> list[dict[str, Any]]:
    if not constraints:
        return products
    minimum = _numeric_price(constraints.get("min_price"))
    maximum = _numeric_price(constraints.get("max_price"))
    return [
        product
        for product in products
        if _price_is_within(product.get("price"), minimum, maximum)
    ]


def products_for_explicit_request(
    products: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    terms = explicit_product_terms(query)
    if not terms:
        return products
    return [product for product in products if product_matches_any_term(product, terms)]


def explicit_product_terms(query: str) -> tuple[str, ...]:
    text = normalize_lookup_text(query)
    if not text:
        return ()
    patterns = (
        r"\b(?:show|find|recommend|suggest)\s+(?:me\s+)?(.+?)(?:\s+(?:under|below|within|from|with|rather than)\b|$)",
        r"\b(?:switch|return|back)\s+to\s+(.+?)(?:\s+and\b|\s+under\b|\s+below\b|$)",
    )
    phrases: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phrases.append(match.group(1))
    if not phrases:
        return ()

    ignored = {
        "a", "actual", "and", "best", "catalog", "category", "choices", "college",
        "few", "good", "in", "item", "items", "me", "mid", "office", "option",
        "options", "product", "products", "range", "rated", "reliable", "section",
        "some", "store", "strong", "suitable", "the", "well",
    }
    for phrase in phrases:
        terms: list[str] = []
        for token in phrase.split():
            clean = token.strip(" -")
            if clean in ignored or len(clean) < 3:
                continue
            if clean.endswith("ies") and len(clean) > 4:
                clean = f"{clean[:-3]}y"
            elif clean.endswith("s") and len(clean) > 4:
                clean = clean[:-1]
            if clean not in terms:
                terms.append(clean)
        if terms:
            return tuple(terms[:4])
    return ()


def product_matches_any_term(product: dict[str, Any], terms: tuple[str, ...]) -> bool:
    values = (
        product.get("name"),
        product.get("title"),
        product.get("brand"),
        product.get("category"),
        product.get("category_name"),
        product.get("category_slug"),
        product.get("description"),
        product.get("tags"),
    )
    search_text = normalize_lookup_text(" ".join(str(value or "") for value in values))
    return any(term in search_text for term in terms)


def _numeric_price(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _price_is_within(value: Any, minimum: float | None, maximum: float | None) -> bool:
    price = _numeric_price(value)
    if price is None:
        return False
    return (minimum is None or price >= minimum) and (maximum is None or price <= maximum)


def fallback_search_response(
    retrieved_products: list[dict[str, Any]],
    *,
    display_search_query_from_products: Callable[[list[dict]], str],
) -> dict[str, Any]:
    search_query = display_search_query_from_products(retrieved_products)
    return {
        "response_text": f"I had trouble processing that, but I found {len(retrieved_products)} products matching your search.",
        "intent": "search_fallback",
        "confidence": 1.0,
        "ui_actions": [
            {
                "action": ACTION_SHOW_PRODUCTS,
                "params": {
                    PRODUCT_IDS_PARAM: [str(product["id"]) for product in retrieved_products],
                    "search_query": search_query,
                },
            }
        ],
    }
