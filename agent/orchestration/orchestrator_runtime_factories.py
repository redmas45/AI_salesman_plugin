"""Runtime factory wiring for the orchestrator compatibility facade."""

from __future__ import annotations

from types import ModuleType

from agent.orchestration.orchestrator_action_runtime import OrchestratorActionRuntime
from agent.orchestration.orchestrator_inventory_runtime import OrchestratorInventoryRuntime
from agent.orchestration.orchestrator_navigation_runtime import OrchestratorNavigationRuntime
from agent.orchestration.orchestrator_turn_runtime import OrchestratorTurnRuntime
from agent.flows import planned_flow_runtime


def turn_runtime(runtime: ModuleType) -> OrchestratorTurnRuntime:
    return OrchestratorTurnRuntime(
        recoverable_errors=runtime.PIPELINE_RECOVERABLE_ERRORS,
        logger=runtime.logger,
        should_bypass_answer_cache=runtime.should_bypass_answer_cache,
        is_ecommerce_site=runtime._is_ecommerce_site,
        should_bypass_ecommerce_answer_cache=runtime._should_bypass_ecommerce_answer_cache,
        lookup_answer_cache=runtime.lookup_answer_cache,
        claims_no_matching_products=runtime._claims_no_matching_products,
        enrich_cached_product_actions=runtime._enrich_cached_product_actions,
        synthesize_audio_b64=runtime._synthesize_audio_b64,
        elapsed_ms=runtime._ms,
        ai_log=runtime._ai_log,
        is_safe_cache_response=runtime.is_safe_cache_response,
        source_ids_and_urls=runtime.source_ids_and_urls,
        store_answer_cache=runtime.store_answer_cache,
        inventory_summary=runtime.tenant_inventory_summary,
        transcribe=runtime.stt.transcribe,
        get_user_profile=runtime.get_user_profile,
        normalize_lookup_text=runtime._normalize_lookup_text,
        search_query_words=runtime._search_query_words,
        safe_user_profile_func=runtime._safe_user_profile,
        augment_query_with_history_func=runtime._augment_query_with_history,
        retrieve_generic_context_func=runtime._retrieve_generic_context,
        extract_price_constraints=runtime.rag.extract_price_constraints,
        retrieve_products=runtime.rag.retrieve,
        merge_products=runtime._merge_products,
        merge_history_products=runtime._merge_history_products,
        exact_products_from_query=runtime._exact_products_from_query,
        display_search_query_from_products=runtime._display_search_query_from_products,
        fallback_search_response=runtime._fallback_search_response,
        update_user_preferences=runtime.update_user_preferences,
        validate_output=runtime.guardrails.validate_output,
        blocked_response=runtime._blocked_response,
        repair_navigation_actions_func=runtime._repair_navigation_actions,
        override_hallucinated_product_search_func=runtime._override_hallucinated_product_search,
        ecommerce_recoveries=[
            runtime._ensure_named_comparison_response,
            lambda validated, transcript, products: runtime._promote_comparison_action(
                validated,
                transcript,
                products,
            ),
            runtime._prevent_false_no_matching_product_claim,
            runtime._coerce_recommendation_to_product_search,
            runtime._ensure_product_answer_response,
            runtime._ensure_cart_request_response,
            runtime._ensure_product_search_display_action,
        ],
        empty_inventory_recovery=runtime._prevent_false_empty_inventory_claim,
        product_display_query_recovery=runtime._ensure_product_display_search_queries,
        product_grounding_recovery=runtime._ground_product_display_response,
        generic_comparison_recovery=runtime._ensure_generic_comparison_response,
        entity_answer_recovery=runtime._ensure_entity_answer_response,
        suppress_lead_recovery=runtime._suppress_lead_recovery_after_removed_navigation,
        lead_flow_recovery=runtime._ensure_lead_flow_response,
        align_removed_actions=runtime._align_response_when_actions_removed,
        neutralize_pending_claims=runtime._neutralize_pending_action_claims,
        navigation_page_from_transcript=runtime._navigation_page_from_transcript,
    )


def planned_runtime(runtime: ModuleType) -> planned_flow_runtime.PlannedFlowRuntime:
    return planned_flow_runtime.PlannedFlowRuntime(
        planner=runtime.plan_universal_flow,
        add_variant_ids_to_cart_actions=runtime._add_variant_ids_to_cart_actions,
        enrich_action_params_from_context=runtime._enrich_action_params_from_context,
        apply_capability_filter_result=runtime._apply_capability_filter_result,
        ensure_product_display_search_queries=runtime._ensure_product_display_search_queries,
        align_response_with_action_filter=runtime._align_response_with_action_filter,
        align_response_with_enriched_action_params=runtime._align_response_with_enriched_action_params,
        neutralize_pending_action_claims=runtime._neutralize_pending_action_claims,
        retrieval_evidence=runtime._retrieval_evidence,
        answer_scope_for=runtime.answer_scope_for,
        synthesize_audio_b64=runtime._synthesize_audio_b64,
        elapsed_ms=runtime._ms,
        ai_log=runtime._ai_log,
    )


def action_runtime(runtime: ModuleType) -> OrchestratorActionRuntime:
    return OrchestratorActionRuntime(
        recoverable_errors=runtime.PIPELINE_RECOVERABLE_ERRORS,
        capability_filter_skipped=runtime.CAPABILITY_FILTER_SKIPPED,
        get_db=runtime.get_db,
        get_client_detail=runtime.get_client_detail,
        lead_flow_fallback_text=runtime._lead_flow_fallback_text,
        normalize_lookup_text=runtime._normalize_lookup_text,
        normalize_navigation_text=runtime._normalize_navigation_text,
        navigation_unavailable_text=runtime._navigation_unavailable_text,
        logger=runtime.logger,
    )


def navigation_runtime(runtime: ModuleType) -> OrchestratorNavigationRuntime:
    return OrchestratorNavigationRuntime(
        recoverable_errors=runtime.PIPELINE_RECOVERABLE_ERRORS,
        get_client_detail=runtime.get_client_detail,
        get_client_vertical_key=runtime.get_client_vertical_key,
        is_ecommerce_site=runtime._is_ecommerce_site,
        lead_flow_action_from_transcript_func=runtime._lead_flow_action_from_transcript,
        synthesize_b64=runtime.tts.synthesize_b64,
        ai_log=runtime._ai_log,
        elapsed_ms=runtime._ms,
        logger=runtime.logger,
    )


def inventory_runtime(runtime: ModuleType) -> OrchestratorInventoryRuntime:
    return OrchestratorInventoryRuntime(
        recoverable_errors=runtime.PIPELINE_RECOVERABLE_ERRORS,
        load_products=lambda current_site_id, limit: runtime.get_all_products(current_site_id, limit=limit),
        matching_inventory_products=runtime._matching_inventory_products,
        available_category_names=runtime._available_category_names,
        inventory_summary=runtime.tenant_inventory_summary,
        synthesize_b64=runtime.tts.synthesize_b64,
        guardrail_audio=runtime._guardrail_audio_b64,
        ai_log=runtime._ai_log,
        elapsed_ms=runtime._ms,
        logger=runtime.logger,
    )
