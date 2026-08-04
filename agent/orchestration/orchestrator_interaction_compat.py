"""Interaction compatibility wrappers installed into agent.orchestrator."""

from __future__ import annotations

from typing import Any


def exports(runtime: Any) -> dict[str, Any]:
    def ensure_lead_flow_response(response: dict[str, Any], transcript: str, site_id: str) -> None:
        runtime._ensure_lead_flow_response_impl(
            response,
            transcript,
            site_id,
            action_for_transcript=runtime._lead_flow_action_from_transcript,
        )

    def lead_flow_action_from_transcript(transcript: str, site_id: str) -> str:
        return runtime._lead_flow_action_from_transcript_impl(
            transcript,
            site_id,
            allowed_actions_for_site=runtime._lead_flow_actions_for_site,
            action_configs_for_site=runtime._action_configs_for_site,
        )

    def lead_flow_action_from_site_contract(normalized_text: str, site_id: str, allowed_actions: set[str]) -> str:
        return runtime._lead_flow_action_from_site_contract_impl(
            normalized_text,
            site_id,
            allowed_actions,
            action_configs_for_site=runtime._action_configs_for_site,
        )

    def lead_flow_actions_for_site(site_id: str) -> set[str]:
        return runtime._lead_flow_actions_for_site_impl(
            site_id,
            vertical_key_for_site=runtime.get_client_vertical_key,
            recoverable_errors=runtime.PIPELINE_RECOVERABLE_ERRORS,
            logger=runtime.logger,
        )

    def prevent_false_empty_inventory_claim(response: dict[str, Any], transcript: str, site_id: str) -> None:
        runtime.inventory_claims.prevent_false_empty_inventory_claim(
            response,
            transcript,
            site_id,
            inventory_summary=runtime.tenant_inventory_summary,
            load_products=lambda current_site_id, limit: runtime.get_all_products(current_site_id, limit=limit),
            available_categories=runtime._available_category_names,
            recoverable_errors=runtime.PIPELINE_RECOVERABLE_ERRORS,
            logger=runtime.logger,
        )

    def needs_transcript_clarification(transcript: str) -> bool:
        return runtime.conversation_shortcuts.needs_transcript_clarification(
            transcript,
            normalize_text=runtime._normalize_lookup_text,
        )

    def clarification_response(
        transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any]:
        return runtime.conversation_shortcuts.clarification_response(
            transcript,
            skip_tts,
            timings,
            start_time,
            synthesize_audio=runtime._synthesize_audio_b64,
            ai_log=runtime._ai_log,
            elapsed_ms=runtime._ms,
        )

    def resolved_turn_context(
        site_id: str,
        safe_transcript: str,
        conversation_history: list | None = None,
        session_summary: str = "",
        recent_product_ids: tuple[str, ...] = (),
    ) -> Any:
        """Resolve the current turn against bounded recent conversation context.

        Shared by the sync and streaming pipelines so both behave identically.
        Uses the built-in product-type nouns plus a TTL-cached tenant brand list,
        so no full catalog load happens on a turn.
        """
        from agent.products.product_matching_lexical import BUILTIN_TYPE_NOUNS
        from agent.retrieval.catalog_vocabulary import catalog_brand_vocabulary
        from agent.retrieval.resolved_context import resolve_turn_context

        return resolve_turn_context(
            safe_transcript,
            history=list(conversation_history or []),
            session_summary=session_summary or "",
            recent_product_ids=tuple(recent_product_ids or ()),
            catalog_brands=catalog_brand_vocabulary(site_id),
            catalog_types=tuple(BUILTIN_TYPE_NOUNS),
        )

    def build_turn_plan(
        site_id: str,
        safe_transcript: str,
        *,
        session_id: str = "",
        conversation_history: list | None = None,
        session_summary: str = "",
        page_context: dict[str, Any] | None = None,
        ecommerce_runtime: bool = True,
    ) -> Any:
        """Resolve the one authoritative plan for this turn, before any shortcut.

        Uses the built-in product-type nouns plus the TTL-cached tenant brand
        list, so no catalog load happens on a turn and nothing here is specific
        to any one retailer.
        """
        from agent.orchestration.turn_plan import build_turn_plan as _build
        from agent.products.product_matching_lexical import BUILTIN_TYPE_NOUNS
        from agent.retrieval.catalog_vocabulary import catalog_brand_vocabulary

        return _build(
            safe_transcript,
            site_id=site_id,
            session_id=session_id,
            turn_id=runtime.new_action_turn_id() if hasattr(runtime, "new_action_turn_id") else "",
            vertical="ecommerce" if ecommerce_runtime else "generic",
            history=list(conversation_history or []),
            session_summary=session_summary or "",
            page_state=page_context,
            catalog_brands=catalog_brand_vocabulary(site_id) if ecommerce_runtime else (),
            catalog_types=tuple(BUILTIN_TYPE_NOUNS) if ecommerce_runtime else (),
        )

    def load_catalog_scan(site_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Deterministic, ordered catalog scan for counts and aggregates.

        ``get_all_products`` samples by category with ``RANDOM()``, which is right
        for "show me something" and wrong for any question whose answer is a fact
        about the whole catalog. One row beyond the cap is requested so a bounded
        scan is detectable rather than being reported as an exact total.
        """
        from agent.catalog.catalog_operations import CATALOG_SCAN_CAP

        scan_limit = int(limit or CATALOG_SCAN_CAP) + 1
        try:
            return list(runtime.get_catalog_records(site_id, limit=scan_limit))
        except runtime.PIPELINE_RECOVERABLE_ERRORS as exc:
            runtime.logger.warning("PIPELINE | deterministic catalog scan failed for %s: %s", site_id, exc)
            return list(runtime.get_all_products(site_id, limit=scan_limit))

    def catalog_aggregate_response(
        site_id: str,
        transcript: str,
        plan: Any,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any] | None:
        from agent.responses import catalog_answers

        return catalog_answers.catalog_aggregate_response(
            site_id,
            transcript,
            plan,
            skip_tts,
            timings,
            start_time,
            load_records=load_catalog_scan,
            synthesize_b64=runtime.tts.synthesize_b64,
            ai_log=runtime._ai_log,
            elapsed_ms=runtime._ms,
            recoverable_errors=runtime.PIPELINE_RECOVERABLE_ERRORS,
            logger=runtime.logger,
        )

    def ecommerce_clarification_response(
        transcript: str,
        safe_transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
        *,
        site_id: str = "",
        conversation_history: list | None = None,
        session_summary: str = "",
        plan: Any = None,
    ) -> dict[str, Any] | None:
        """Ask one clarification only when the RESOLVED turn is still insufficient.

        Resolution folds in recent conversation context, so a category, brand,
        recipient, or budget the customer already supplied is never re-asked.

        When the caller supplies the turn's plan, that decision is taken from it
        rather than resolved a second time - two independent resolutions of the
        same turn is exactly the contradiction the plan exists to prevent.
        """
        if plan is not None:
            if not plan.needs_clarification:
                return None
            question = plan.clarification_question
        else:
            resolved = resolved_turn_context(
                site_id,
                safe_transcript,
                conversation_history=conversation_history,
                session_summary=session_summary,
            )
            if not resolved.should_ask_clarification():
                return None
            question = resolved.clarification_question()
        return runtime.conversation_shortcuts.clarification_response(
            transcript,
            skip_tts,
            timings,
            start_time,
            synthesize_audio=runtime._synthesize_audio_b64,
            ai_log=runtime._ai_log,
            elapsed_ms=runtime._ms,
            message=question,
        )

    def navigation_intent_response(
        site_id: str,
        transcript: str,
        safe_transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
        page_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return runtime._navigation_runtime().navigation_intent_response(
            site_id,
            transcript,
            safe_transcript,
            skip_tts,
            timings,
            start_time,
            page_context,
        )

    def sort_intent_response(
        site_id: str,
        transcript: str,
        safe_transcript: str,
        ecommerce_runtime: bool,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any] | None:
        return runtime._navigation_runtime().sort_intent_response(
            site_id,
            transcript,
            safe_transcript,
            ecommerce_runtime,
            skip_tts,
            timings,
            start_time,
        )

    def vertical_entity_plural(site_id: str) -> str:
        return runtime._navigation_runtime().vertical_entity_plural(site_id)

    def navigation_page_from_transcript(
        site_id: str,
        transcript: str,
        page_context: dict[str, Any] | None = None,
        *,
        require_specific_match: bool = False,
    ) -> str:
        return runtime._navigation_runtime().navigation_page_from_transcript(
            site_id,
            transcript,
            page_context,
            require_specific_match=require_specific_match,
        )

    def lead_flow_should_own_navigation_text(text: str, site_id: str) -> bool:
        return runtime._navigation_runtime().lead_flow_should_own_navigation_text(text, site_id)

    def navigation_route_terms(site_id: str, page_context: dict[str, Any] | None = None) -> list[tuple[str, str]]:
        return runtime._navigation_runtime().navigation_route_terms(site_id, page_context)

    def client_navigation_route_map(site_id: str, page_context: dict[str, Any] | None = None) -> dict[str, str]:
        return runtime._navigation_runtime().client_navigation_route_map(site_id, page_context)

    def inventory_runtime() -> Any:
        return runtime.orchestrator_runtime_factories.inventory_runtime(runtime._pipeline_runtime())

    def greeting_response(
        transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any]:
        return runtime._inventory_runtime().greeting_response(transcript, skip_tts, timings, start_time)

    def inventory_type_count_response(
        site_id: str,
        transcript: str,
        item_type: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any]:
        return runtime._inventory_runtime().inventory_type_count_response(
            site_id,
            transcript,
            item_type,
            skip_tts,
            timings,
            start_time,
        )

    def inventory_stats_response(
        site_id: str,
        transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any]:
        return runtime._inventory_runtime().inventory_stats_response(
            site_id,
            transcript,
            skip_tts,
            timings,
            start_time,
        )

    def error_response(message: str, timings: dict) -> dict[str, Any]:
        return runtime._inventory_runtime().error_response(message, timings)

    def guardrail_response(
        message: str,
        transcript: str,
        skip_tts: bool,
        timings: dict,
    ) -> dict[str, Any]:
        return runtime._inventory_runtime().guardrail_response(message, transcript, skip_tts, timings)

    def extract_products_from_history(history: list[dict], site_id: str) -> list[dict]:
        return runtime.PRODUCT_CATALOG_MATCHER.extract_products_from_history(history, site_id)

    return {
        "_ensure_lead_flow_response": ensure_lead_flow_response,
        "_lead_flow_action_from_transcript": lead_flow_action_from_transcript,
        "_lead_flow_action_from_site_contract": lead_flow_action_from_site_contract,
        "_lead_flow_actions_for_site": lead_flow_actions_for_site,
        "_prevent_false_empty_inventory_claim": prevent_false_empty_inventory_claim,
        "_claims_store_inventory_empty": runtime.inventory_claims.claims_store_inventory_empty,
        "_mentions_cart_or_tray": runtime.inventory_claims.mentions_cart_or_tray,
        "_wants_comparison": runtime.product_turn_responses.wants_comparison,
        "_is_simple_greeting": runtime.conversation_shortcuts.is_simple_greeting,
        "_needs_transcript_clarification": needs_transcript_clarification,
        "_clarification_response": clarification_response,
        "_ecommerce_clarification_response": ecommerce_clarification_response,
        "_resolved_turn_context": resolved_turn_context,
        "_build_turn_plan": build_turn_plan,
        "_load_catalog_scan": load_catalog_scan,
        "_catalog_aggregate_response": catalog_aggregate_response,
        "_navigation_intent_response": navigation_intent_response,
        "_navigation_response_label": runtime.navigation_intent.navigation_response_label,
        "_sort_intent_response": sort_intent_response,
        "_sort_key_from_transcript": runtime.navigation_intent.sort_key_from_transcript,
        "_looks_like_sort_request": runtime.navigation_intent.looks_like_sort_request,
        "_sort_response_text": runtime.navigation_intent.sort_response_text,
        "_vertical_entity_plural": vertical_entity_plural,
        "_navigation_page_from_transcript": navigation_page_from_transcript,
        "_lead_flow_should_own_navigation_text": lead_flow_should_own_navigation_text,
        "_looks_like_navigation_request": runtime.navigation_intent.looks_like_navigation_request,
        "_looks_like_discovered_navigation_request": runtime.navigation_intent.looks_like_discovered_navigation_request,
        "_looks_like_route_interest_request": runtime.navigation_intent.looks_like_route_interest_request,
        "_navigation_route_terms": navigation_route_terms,
        "_navigation_match_rank": runtime.navigation_intent.navigation_match_rank,
        "_client_navigation_route_map": client_navigation_route_map,
        "_navigation_route_map_from_config": runtime.navigation_intent.navigation_route_map_from_config,
        "_add_navigation_route": runtime.navigation_intent.add_navigation_route,
        "_observed_navigation_path": runtime.navigation_intent.observed_navigation_path,
        "_same_origin_path": runtime.navigation_intent.same_origin_path,
        "_safe_config_list": runtime.navigation_intent.safe_config_list,
        "_route_page_key": runtime.navigation_intent.route_page_key,
        "_route_last_segment": runtime.navigation_intent.route_last_segment,
        "_safe_page_key": runtime.navigation_intent.safe_page_key,
        "_navigation_term_matches": runtime.navigation_intent.navigation_term_matches,
        "_normalize_navigation_text": runtime.navigation_intent.normalize_navigation_text,
        "_is_inventory_stats_query": runtime.inventory_responses.is_inventory_stats_query,
        "_extract_inventory_type_query": runtime.inventory_responses.extract_inventory_type_query,
        "_clean_inventory_type_term": runtime.inventory_responses.clean_inventory_type_term,
        "_inventory_runtime": inventory_runtime,
        "_greeting_response": greeting_response,
        "_inventory_type_count_response": inventory_type_count_response,
        "_matching_inventory_products": runtime.PRODUCT_CATALOG_MATCHER.matching_inventory_products,
        "_product_search_text": runtime.PRODUCT_CATALOG_MATCHER.product_search_text,
        "_available_category_names": runtime.PRODUCT_CATALOG_MATCHER.available_category_names,
        "_pluralize": runtime.inventory_responses.pluralize,
        "_inventory_stats_response": inventory_stats_response,
        "_error_response": error_response,
        "_guardrail_response": guardrail_response,
        "_extract_products_from_history": extract_products_from_history,
    }
