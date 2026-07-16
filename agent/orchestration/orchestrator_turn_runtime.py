"""Bound retrieval, cache, and response-validation runtime for orchestrator turns."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from agent.runtime_helpers import retrieval_runtime, response_validation


@dataclass(frozen=True)
class OrchestratorTurnRuntime:
    recoverable_errors: tuple[type[BaseException], ...]
    logger: logging.Logger
    should_bypass_answer_cache: Callable[[str], bool]
    is_ecommerce_site: Callable[[str], bool]
    should_bypass_ecommerce_answer_cache: Callable[[str], bool]
    lookup_answer_cache: Callable[[str, str, str], dict[str, Any] | None]
    claims_no_matching_products: Callable[[Any], bool]
    enrich_cached_product_actions: Callable[[str, list[dict[str, Any]]], list[dict[str, Any]]]
    synthesize_audio_b64: Callable[[str, bool], tuple[str, float | None]]
    elapsed_ms: Callable[[float], float]
    ai_log: Callable[[str, Any], None]
    is_safe_cache_response: Callable[[str, dict[str, Any], list[dict[str, Any]]], bool]
    source_ids_and_urls: Callable[[list[dict[str, Any]]], tuple[list[str], list[str]]]
    store_answer_cache: Callable[..., dict[str, Any] | None]
    inventory_summary: Callable[[str], dict[str, Any]]
    transcribe: Callable[..., str]
    get_user_profile: Callable[[str], dict[str, Any]]
    normalize_lookup_text: Callable[[Any], str]
    search_query_words: Callable[[Any], list[str]]
    safe_user_profile_func: Callable[[str], dict[str, Any]]
    augment_query_with_history_func: Callable[[str, list[dict] | None], str]
    retrieve_generic_context_func: Callable[[str, str, dict[str, Any]], retrieval_runtime.RetrievalContext]
    extract_price_constraints: Callable[[str], dict[str, Any]]
    retrieve_products: Callable[..., list[dict[str, Any]]]
    merge_products: Callable[[list[dict], list[dict], int | None], list[dict]]
    merge_history_products: Callable[[list[dict[str, Any]], list, str, str], list[dict[str, Any]]]
    exact_products_from_query: Callable[[str, str, int], list[dict]]
    display_search_query_from_products: Callable[[list[dict]], str]
    fallback_search_response: Callable[[list[dict[str, Any]]], dict[str, Any]]
    update_user_preferences: Callable[[str, Any], Any]
    validate_output: Callable[..., dict[str, Any]]
    blocked_response: Callable[[str], dict[str, Any]]
    repair_navigation_actions_func: Callable[[dict[str, Any], str, str, dict[str, Any] | None], None]
    override_hallucinated_product_search_func: Callable[[dict[str, Any], list[str]], None]
    ecommerce_recoveries: list[Callable[[dict[str, Any], str, list[dict[str, Any]]], None]]
    empty_inventory_recovery: Callable[[dict[str, Any], str, str], None]
    product_display_query_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None]
    product_grounding_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None]
    generic_comparison_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None]
    entity_answer_recovery: Callable[[dict[str, Any], str, list[dict[str, Any]]], None]
    suppress_lead_recovery: Callable[[dict[str, Any], str, list[str]], bool]
    lead_flow_recovery: Callable[[dict[str, Any], str, str], None]
    align_removed_actions: Callable[[dict[str, Any], str, str, list[str], dict[str, Any] | None], None]
    neutralize_pending_claims: Callable[[str, list[dict[str, Any]]], str]
    navigation_page_from_transcript: Callable[..., str]

    def cached_answer_response(
        self,
        site_id: str,
        session_id: str,
        transcript: str,
        safe_transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any] | None:
        return retrieval_runtime.cached_answer_response(
            site_id,
            session_id,
            transcript,
            safe_transcript,
            skip_tts,
            timings,
            start_time,
            should_bypass_answer_cache=self.should_bypass_answer_cache,
            is_ecommerce_site=self.is_ecommerce_site,
            should_bypass_ecommerce_answer_cache=self.should_bypass_ecommerce_answer_cache,
            lookup_answer_cache=self.lookup_answer_cache,
            claims_no_matching_products=self.claims_no_matching_products,
            enrich_cached_product_actions=self.enrich_cached_product_actions,
            synthesize_audio_b64=self.synthesize_audio_b64,
            elapsed_ms=self.elapsed_ms,
            ai_log=self.ai_log,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def maybe_store_answer_cache(
        self,
        site_id: str,
        session_id: str,
        safe_transcript: str,
        result: dict[str, Any],
        retrieved_items: list[dict[str, Any]],
        retrieval_evidence: dict[str, Any],
    ) -> None:
        return retrieval_runtime.maybe_store_answer_cache(
            site_id,
            session_id,
            safe_transcript,
            result,
            retrieved_items,
            retrieval_evidence,
            is_safe_cache_response=self.is_safe_cache_response,
            source_ids_and_urls=self.source_ids_and_urls,
            store_answer_cache=self.store_answer_cache,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def retrieval_evidence(
        self,
        site_id: str,
        ecommerce_runtime: bool,
        retrieved_items: list[dict[str, Any]],
        price_constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return retrieval_runtime.retrieval_evidence(
            site_id,
            ecommerce_runtime,
            retrieved_items,
            price_constraints,
            inventory_summary=self.inventory_summary,
            recoverable_errors=self.recoverable_errors,
        )

    def resolve_transcript(
        self,
        *,
        audio_bytes: bytes | None,
        text_input: str | None,
        audio_filename: str,
        timings: dict[str, float],
    ) -> tuple[str | None, str | None]:
        from agent.responses import turn_runtime_responses

        return turn_runtime_responses.resolve_transcript(
            audio_bytes=audio_bytes,
            text_input=text_input,
            audio_filename=audio_filename,
            timings=timings,
            transcribe=self.transcribe,
            elapsed_ms=self.elapsed_ms,
        )

    def safe_user_profile(self, site_id: str) -> dict[str, Any]:
        return retrieval_runtime.safe_user_profile(
            site_id,
            get_user_profile=self.get_user_profile,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def augment_query_with_history(self, query: str, history: list[dict] | None) -> str:
        return retrieval_runtime.augment_query_with_history(
            query,
            history,
            normalize_lookup_text=self.normalize_lookup_text,
            search_query_words=self.search_query_words,
            logger=self.logger,
        )

    def recent_product_context_terms(self, history: list[dict] | None, current_query: str) -> list[str]:
        return retrieval_runtime.recent_product_context_terms(
            history,
            current_query,
            normalize_lookup_text=self.normalize_lookup_text,
            search_query_words=self.search_query_words,
        )

    def retrieve_context(
        self,
        site_id: str,
        safe_transcript: str,
        conversation_history: list | None,
    ) -> retrieval_runtime.RetrievalContext:
        return retrieval_runtime.retrieve_context(
            site_id,
            safe_transcript,
            conversation_history,
            safe_user_profile=self.safe_user_profile_func,
            augment_query_with_history=self.augment_query_with_history_func,
            is_ecommerce_site=self.is_ecommerce_site,
            retrieve_generic_context=self.retrieve_generic_context,
            extract_price_constraints=self.extract_price_constraints,
            retrieve_products=self.retrieve_products,
            merge_products=self.merge_products,
            merge_history_products=self.merge_history_products,
            exact_products_from_query=self.exact_products_from_query,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def retrieve_generic_context(
        self,
        site_id: str,
        rag_query: str,
        profile: dict[str, Any],
    ) -> retrieval_runtime.RetrievalContext:
        return self.retrieve_generic_context_func(site_id, rag_query, profile)

    def normalize_llm_response(
        self,
        llm_response: dict[str, Any],
        retrieved_products: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return response_validation.normalize_llm_response(
            llm_response,
            retrieved_products,
            fallback_search_response=self.fallback_search_response,
            logger=self.logger,
        )

    def persist_preference_actions(self, site_id: str, actions: list[dict[str, Any]]) -> None:
        return response_validation.persist_preference_actions(
            site_id,
            actions,
            update_user_preferences=self.update_user_preferences,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def validate_agent_response(
        self,
        response: dict[str, Any],
        *,
        site_id: str,
        safe_transcript: str,
        retrieved_products: list[dict[str, Any]],
        blocked_text: str,
        page_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return response_validation.validate_agent_response(
            response,
            site_id=site_id,
            safe_transcript=safe_transcript,
            retrieved_products=retrieved_products,
            blocked_text=blocked_text,
            page_context=page_context,
            validate_output=self.validate_output,
            blocked_response=self.blocked_response,
            repair_navigation_actions=self.repair_navigation_actions_func,
            is_ecommerce_site=self.is_ecommerce_site,
            override_hallucinated_product_search=self.override_hallucinated_product_search_func,
            ecommerce_recoveries=self.ecommerce_recoveries,
            empty_inventory_recovery=self.empty_inventory_recovery,
            product_display_query_recovery=self.product_display_query_recovery,
            product_grounding_recovery=self.product_grounding_recovery,
            generic_comparison_recovery=self.generic_comparison_recovery,
            entity_answer_recovery=self.entity_answer_recovery,
            suppress_lead_recovery=self.suppress_lead_recovery,
            lead_flow_recovery=self.lead_flow_recovery,
            align_removed_actions=self.align_removed_actions,
            neutralize_pending_claims=self.neutralize_pending_claims,
            logger=self.logger,
        )

    def repair_navigation_actions(
        self,
        response: dict[str, Any],
        site_id: str,
        transcript: str,
        page_context: dict[str, Any] | None = None,
    ) -> None:
        return response_validation.repair_navigation_actions(
            response,
            site_id,
            transcript,
            page_context,
            navigation_page_from_transcript=self.navigation_page_from_transcript,
        )

    def override_hallucinated_product_search(
        self,
        validated: dict[str, Any],
        original_actions: list[str],
    ) -> None:
        return response_validation.override_hallucinated_product_search(
            validated,
            original_actions,
            logger=self.logger,
        )
