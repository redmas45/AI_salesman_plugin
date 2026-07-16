"""
Orchestrator — wires all pipeline stages together.

Pipeline:
  audio bytes
    → STT (Whisper via OpenAI)
    → Input Guardrails
    → RAG Retrieval (PostgreSQL + pgvector)
    → LLM Agent (OpenAI Chat Completions)
    → Output Guardrails
    → TTS (OpenAI tts-1)
    → structured response dict
"""

import logging
from typing import Any

from agent import (
    llm,
    product_turn_responses,
    rag,
    stt,
    tts,
)
from agent.orchestration import (
    orchestrator_action_compat,
    orchestrator_entrypoints,
    orchestrator_interaction_compat,
    orchestrator_product_compat,
    orchestrator_runtime_factories,
    orchestrator_site_context,
)
from agent.guardrail_helpers import guardrails
from agent.guardrail_helpers.guardrails import InputGuardrailError
from agent.action_helpers.lead_flow import (
    ensure_lead_flow_response as _ensure_lead_flow_response_impl,
    lead_flow_action_from_site_contract as _lead_flow_action_from_site_contract_impl,
    lead_flow_action_from_transcript as _lead_flow_action_from_transcript_impl,
    lead_flow_actions_for_site as _lead_flow_actions_for_site_impl,
    lead_flow_contract_match_score as _lead_flow_contract_match_score,
    lead_flow_contract_terms as _lead_flow_contract_terms,
    lead_flow_fallback_text as _lead_flow_fallback_text,
    looks_like_supported_flow_request as _looks_like_supported_flow_request,
)
from agent.prompts.ecommerce_prompt import format_cart_for_prompt
from agent.flows.flow_planner import plan_universal_flow
from agent.orchestration.orchestrator_inventory_runtime import OrchestratorInventoryRuntime
from agent.orchestration.orchestrator_navigation_runtime import OrchestratorNavigationRuntime
from agent.orchestration.orchestrator_turn_runtime import OrchestratorTurnRuntime
from agent.responses.sales_relevance import (
    answer_scope_for,
    bounded_unsupported_response,
    is_safe_cache_response,
    should_bypass_answer_cache,
    source_ids_and_urls,
)
from agent.responses import (
    conversation_shortcuts,
    inventory_claims,
    inventory_responses,
    navigation_intent,
    turn_runtime_responses,
)
from agent.runtime_helpers import retrieval_runtime, response_validation
from agent.flows import planned_flow_runtime
from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_NAVIGATE_TO,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_PRODUCTS,
    PRODUCT_ID_PARAM,
    PRODUCT_IDS_PARAM,
    QUANTITY_PARAM,
)
from db.core.database import (
    get_all_products,
    get_cart_items,
    get_user_profile,
    tenant_inventory_summary,
    update_user_preferences,
    get_db,
)
from db.client_domain.client_facade import get_client_detail, get_client_vertical_key
from db.cache.answer_cache import lookup_answer_cache, store_answer_cache

logger = logging.getLogger(__name__)

DEFAULT_AUDIO_FILENAME = orchestrator_site_context.DEFAULT_AUDIO_FILENAME
GENERIC_BLOCKED_RESPONSE = orchestrator_site_context.GENERIC_BLOCKED_RESPONSE
ECOMMERCE_BLOCKED_RESPONSE = orchestrator_site_context.ECOMMERCE_BLOCKED_RESPONSE
NON_ECOMMERCE_CART_CONTEXT = orchestrator_site_context.NON_ECOMMERCE_CART_CONTEXT
CAPABILITY_FILTER_SKIPPED = orchestrator_site_context.CAPABILITY_FILTER_SKIPPED
PIPELINE_RECOVERABLE_ERRORS = orchestrator_site_context.PIPELINE_RECOVERABLE_ERRORS
RetrievalContext = retrieval_runtime.RetrievalContext


globals().update(
    orchestrator_product_compat.exports(
        recoverable_errors=PIPELINE_RECOVERABLE_ERRORS,
        logger=logger,
    )
)


def _pipeline_runtime() -> Any:
    import sys

    return sys.modules[__name__]


globals().update(
    orchestrator_entrypoints.exports(
        runtime_provider=_pipeline_runtime,
        logger=logger,
        default_audio_filename=DEFAULT_AUDIO_FILENAME,
    )
)


def _turn_runtime() -> OrchestratorTurnRuntime:
    return orchestrator_runtime_factories.turn_runtime(_pipeline_runtime())


def _cached_answer_response(
    site_id: str,
    transcript: str,
    safe_transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    session_id: str = "",
) -> dict[str, Any] | None:
    return _turn_runtime().cached_answer_response(
        site_id,
        session_id,
        transcript,
        safe_transcript,
        skip_tts,
        timings,
        start_time,
    )


_cached_answer_intent = retrieval_runtime.cached_answer_intent


def _enrich_cached_product_actions(
    safe_transcript: str,
    ui_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return retrieval_runtime.enrich_cached_product_actions(
        safe_transcript,
        ui_actions,
        ensure_product_display_search_queries=_ensure_product_display_search_queries,
    )


_cached_retrieval_source = retrieval_runtime.cached_retrieval_source


def _policy_boundary_response(
    transcript: str,
    response_text: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    retrieval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return turn_runtime_responses.policy_boundary_response(
        transcript,
        response_text,
        skip_tts,
        timings,
        start_time,
        retrieval=retrieval,
        synthesize_audio=_synthesize_audio_b64,
        elapsed_ms=_ms,
        ai_log=_ai_log,
    )


def _maybe_store_answer_cache(
    site_id: str,
    safe_transcript: str,
    result: dict[str, Any],
    retrieved_items: list[dict[str, Any]],
    retrieval_evidence: dict[str, Any],
    *,
    session_id: str = "",
) -> None:
    return _turn_runtime().maybe_store_answer_cache(
        site_id,
        session_id,
        safe_transcript,
        result,
        retrieved_items,
        retrieval_evidence,
    )


def _retrieval_evidence(
    site_id: str,
    ecommerce_runtime: bool,
    retrieved_items: list[dict[str, Any]],
    price_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _turn_runtime().retrieval_evidence(
        site_id,
        ecommerce_runtime,
        retrieved_items,
        price_constraints,
    )


_retrieval_item_title = retrieval_runtime.retrieval_item_title


_retrieval_issue = retrieval_runtime.retrieval_issue


_safe_int = retrieval_runtime.safe_int


def _resolve_transcript(
    *,
    audio_bytes: bytes | None,
    text_input: str | None,
    audio_filename: str,
    timings: dict[str, float],
) -> tuple[str | None, str | None]:
    return _turn_runtime().resolve_transcript(
        audio_bytes=audio_bytes,
        text_input=text_input,
        audio_filename=audio_filename,
        timings=timings,
    )


def _safe_user_profile(site_id: str) -> dict[str, Any]:
    return _turn_runtime().safe_user_profile(site_id)


_profile_context = retrieval_runtime.profile_context


def _augment_query_with_history(query: str, history: list[dict] | None) -> str:
    return _turn_runtime().augment_query_with_history(query, history)


_needs_history_product_context = retrieval_runtime.needs_history_product_context


def _recent_product_context_terms(history: list[dict] | None, current_query: str) -> list[str]:
    return _turn_runtime().recent_product_context_terms(history, current_query)


def _retrieve_context(
    site_id: str,
    safe_transcript: str,
    conversation_history: list | None,
) -> RetrievalContext:
    return _turn_runtime().retrieve_context(site_id, safe_transcript, conversation_history)


def _retrieve_generic_context(
    site_id: str,
    rag_query: str,
    profile: dict[str, Any],
) -> RetrievalContext:
    return retrieval_runtime.retrieve_generic_context(
        site_id,
        rag_query,
        profile,
        recoverable_errors=PIPELINE_RECOVERABLE_ERRORS,
        logger=logger,
    )


def _planned_flow_response(
    *,
    site_id: str,
    transcript: str,
    safe_transcript: str,
    retrieved_products: list[dict[str, Any]],
    ecommerce_runtime: bool,
    price_constraints: dict[str, Any],
    conversation_history: list,
    page_context: dict[str, Any] | None,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
) -> dict[str, Any] | None:
    return planned_flow_runtime.planned_flow_response(
        site_id=site_id,
        transcript=transcript,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        ecommerce_runtime=ecommerce_runtime,
        price_constraints=price_constraints,
        conversation_history=conversation_history,
        skip_tts=skip_tts,
        timings=timings,
        start_time=start_time,
        deps=_planned_flow_runtime(),
    )


def _planned_flow_runtime() -> planned_flow_runtime.PlannedFlowRuntime:
    return orchestrator_runtime_factories.planned_runtime(_pipeline_runtime())


def _is_ecommerce_site(site_id: str) -> bool:
    return orchestrator_site_context.is_ecommerce_site(
        site_id,
        get_client_vertical_key=get_client_vertical_key,
        recoverable_errors=PIPELINE_RECOVERABLE_ERRORS,
        logger=logger,
    )


def _cart_context_for_site(site_id: str, ecommerce_runtime: bool) -> str:
    return orchestrator_site_context.cart_context_for_site(
        site_id,
        ecommerce_runtime,
        get_cart_items=get_cart_items,
        format_cart_for_prompt=format_cart_for_prompt,
        recoverable_errors=PIPELINE_RECOVERABLE_ERRORS,
        logger=logger,
    )


def _blocked_text_for_site(ecommerce_runtime: bool) -> str:
    return orchestrator_site_context.blocked_text_for_site(ecommerce_runtime)


def _merge_history_products(
    retrieved_products: list[dict[str, Any]],
    conversation_history: list,
    site_id: str,
    current_query: str,
) -> list[dict[str, Any]]:
    return retrieval_runtime.merge_history_products(
        retrieved_products,
        conversation_history,
        site_id,
        current_query,
        matcher=PRODUCT_CATALOG_MATCHER,
    )


def _fallback_search_response(retrieved_products: list[dict[str, Any]]) -> dict[str, Any]:
    return retrieval_runtime.fallback_search_response(
        retrieved_products,
        display_search_query_from_products=_display_search_query_from_products,
    )


def _normalize_llm_response(
    llm_response: dict[str, Any],
    retrieved_products: list[dict[str, Any]],
) -> dict[str, Any]:
    return _turn_runtime().normalize_llm_response(llm_response, retrieved_products)


def _drop_empty_filter_actions(actions: Any) -> list[dict[str, Any]]:
    return response_validation.drop_empty_filter_actions(actions)


def _has_meaningful_filter_params(params: dict[str, Any]) -> bool:
    return response_validation.has_meaningful_filter_params(params)


def _fill_missing_entity_list_ids(
    actions: Any,
    retrieved_products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return response_validation.fill_missing_entity_list_ids(actions, retrieved_products)


def _persist_preference_actions(site_id: str, actions: list[dict[str, Any]]) -> None:
    return _turn_runtime().persist_preference_actions(site_id, actions)


def _validate_agent_response(
    response: dict[str, Any],
    *,
    site_id: str,
    safe_transcript: str,
    retrieved_products: list[dict[str, Any]],
    blocked_text: str,
    page_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _turn_runtime().validate_agent_response(
        response,
        site_id=site_id,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        blocked_text=blocked_text,
        page_context=page_context,
    )


def _repair_navigation_actions(
    response: dict[str, Any],
    site_id: str,
    transcript: str,
    page_context: dict[str, Any] | None = None,
) -> None:
    return _turn_runtime().repair_navigation_actions(response, site_id, transcript, page_context)


def _override_hallucinated_product_search(
    validated: dict[str, Any],
    original_actions: list[str],
) -> None:
    return _turn_runtime().override_hallucinated_product_search(validated, original_actions)


def _blocked_response(response_text: str) -> dict[str, Any]:
    return turn_runtime_responses.blocked_response(response_text)


def _synthesize_audio_b64(response_text: str, skip_tts: bool) -> tuple[str, float | None]:
    return turn_runtime_responses.synthesize_audio_b64(
        response_text,
        skip_tts,
        synthesize_b64=tts.synthesize_b64,
        elapsed_ms=_ms,
        logger=logger,
    )


def _navigation_unavailable_text(site_id: str, transcript: str, page_context: dict[str, Any] | None = None) -> str:
    return _navigation_runtime().navigation_unavailable_text(site_id, transcript, page_context)


_navigation_target_phrase = navigation_intent.navigation_target_phrase


def _available_navigation_labels(site_id: str, page_context: dict[str, Any] | None = None) -> list[str]:
    return _navigation_runtime().available_navigation_labels(site_id, page_context)


_human_join = navigation_intent.human_join


def _guardrail_audio_b64(message: str, skip_tts: bool) -> str:
    return turn_runtime_responses.guardrail_audio_b64(
        message,
        skip_tts,
        synthesize_audio=_synthesize_audio_b64,
    )


def _navigation_runtime() -> OrchestratorNavigationRuntime:
    return orchestrator_runtime_factories.navigation_runtime(_pipeline_runtime())




globals().update(orchestrator_action_compat.exports(_pipeline_runtime()))
globals().update(orchestrator_interaction_compat.exports(_pipeline_runtime()))
