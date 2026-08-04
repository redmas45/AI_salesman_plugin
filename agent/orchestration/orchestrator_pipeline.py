"""Top-level orchestrator pipeline execution.

This module owns the long run/run_stream control flow while the public
agent.orchestrator facade keeps compatibility wrappers and monkeypatch targets.
"""

from __future__ import annotations

import time
from typing import Any, Generator, Optional

import config

from agent.orchestration.orchestrator_streaming import stream_final_result
from agent.orchestration.turn_plan import TurnOperation
from agent.runtime_helpers.grounding_validator import enforce_grounded_constraints

ACTION_NAVIGATE_TO = "NAVIGATE_TO"
NAVIGATION_INTENT = "navigate"


PAGE_RELATIVE_INTENTS = frozenset({"product_detail", "product_compare"})


def strip_unrequested_navigation(
    actions: Any,
    intent: Any,
    navigation_requested: bool = False,
) -> list[dict[str, Any]]:
    """Drop NAVIGATE_TO from turns that did not ask to go anywhere.

    Moving the customer to a different page is only ever correct when the turn's
    intent is navigation. A search, comparison, or page-relative answer that also
    navigates destroys the context the answer was about.

    This rule used to run only when ``PYTEST_CURRENT_TEST`` was set, so the suite
    proved an invariant the deployed pipeline never enforced. It is unconditional
    now: production and test take the identical path.
    """
    if not isinstance(actions, list):
        return []
    resolved_intent = str(intent or "")
    # A mixed turn ("show the cheapest women's item and take me there") is
    # classified by its primary intent, but the customer still asked to be moved.
    # Explicit navigation survives; only accidental navigation is dropped. A
    # page-relative answer is never navigated away from, whatever was asked.
    keep_navigation = resolved_intent == NAVIGATION_INTENT or (
        navigation_requested and resolved_intent not in PAGE_RELATIVE_INTENTS
    )
    if keep_navigation:
        return [action for action in actions if isinstance(action, dict)]
    return [
        action
        for action in actions
        if isinstance(action, dict) and str(action.get("action") or "").upper() != ACTION_NAVIGATE_TO
    ]


def run_pipeline(
    runtime: Any,
    *,
    site_id: str,
    audio_bytes: Optional[bytes],
    text_input: Optional[str],
    audio_filename: str,
    skip_tts: bool,
    conversation_history: Optional[list],
    page_context: Optional[dict[str, Any]],
    session_summary: str,
    session_id: str = "",
) -> dict[str, Any]:
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    transcript, transcript_error = runtime._resolve_transcript(
        audio_bytes=audio_bytes,
        text_input=text_input,
        audio_filename=audio_filename,
        timings=timings,
    )
    if transcript_error:
        return runtime._error_response(transcript_error, timings)

    if config.LOG_CONVERSATION_CONTENT:
        runtime.logger.info("PIPELINE | transcript: %r", transcript[:120])
        runtime.print(f'Input received: "{transcript}"')
    else:
        runtime.logger.info("PIPELINE | transcript received (%d characters)", len(transcript))
    runtime._ai_log("user", transcript)

    # Stage 2: Input Guardrails
    t = time.perf_counter()
    try:
        safe_transcript = runtime.guardrails.validate_input(transcript)
    except runtime.InputGuardrailError as exc:
        return runtime._guardrail_response(str(exc), transcript, skip_tts, timings)
    timings["guardrail_input_ms"] = runtime._ms(t)

    if runtime._is_simple_greeting(safe_transcript):
        return runtime._greeting_response(transcript, skip_tts, timings, t0)

    if runtime._needs_transcript_clarification(safe_transcript):
        return runtime._clarification_response(transcript, skip_tts, timings, t0)

    ecommerce_runtime = runtime._is_ecommerce_site(site_id)

    # ONE authoritative plan, resolved before any shortcut may answer. Shortcuts
    # consume plan.operation instead of re-parsing the customer, which is what
    # stopped the inventory browse from stealing budgeted searches and gift
    # recommendations.
    plan = runtime._build_turn_plan(
        site_id,
        safe_transcript,
        session_id=session_id,
        conversation_history=conversation_history,
        session_summary=session_summary,
        page_context=page_context,
        ecommerce_runtime=ecommerce_runtime,
    )

    if plan.allows_shortcut(TurnOperation.SORT):
        sort_response = runtime._sort_intent_response(
            site_id, transcript, safe_transcript, ecommerce_runtime, skip_tts, timings, t0
        )
        if sort_response:
            return sort_response

    if plan.allows_shortcut(TurnOperation.NAVIGATE):
        navigation_response = runtime._navigation_intent_response(
            site_id, transcript, safe_transcript, skip_tts, timings, t0, page_context=page_context
        )
        if navigation_response:
            return navigation_response

    if ecommerce_runtime and plan.operation == TurnOperation.AGGREGATE:
        aggregate_response = runtime._catalog_aggregate_response(
            site_id, transcript, plan, skip_tts, timings, t0
        )
        if aggregate_response:
            return aggregate_response

    if ecommerce_runtime and plan.allows_shortcut(TurnOperation.INVENTORY_COUNT):
        if runtime._is_inventory_stats_query(safe_transcript):
            return runtime._inventory_stats_response(site_id, transcript, skip_tts, timings, t0)
        inventory_type = runtime._extract_inventory_type_query(safe_transcript)
        if inventory_type:
            return runtime._inventory_type_count_response(
                site_id, transcript, inventory_type, skip_tts, timings, t0
            )

    constraint_signature = plan.cache_key_component() if plan.cache_eligible else ""
    if ecommerce_runtime:
        # Resolve this turn against bounded recent context ONCE, then reuse it for
        # the clarification decision and for cache identity so the sync and
        # streaming pipelines behave identically.
        clarification = runtime._ecommerce_clarification_response(
            transcript,
            safe_transcript,
            skip_tts,
            timings,
            t0,
            site_id=site_id,
            conversation_history=conversation_history,
            session_summary=session_summary,
            plan=plan,
        )
        if clarification:
            return clarification

    navigation_requested = plan.navigation_requested

    cached_response = None
    if plan.cache_eligible:
        cached_response = runtime._cached_answer_response(
            site_id,
            transcript,
            safe_transcript,
            skip_tts,
            timings,
            t0,
            session_id=session_id,
            constraint_signature=constraint_signature,
        )
    if cached_response:
        cached_response["ui_actions"] = strip_unrequested_navigation(
            cached_response.get("ui_actions"),
            cached_response.get("intent"),
            navigation_requested=navigation_requested,
        )
        return cached_response

    # Stage 3: RAG Retrieval
    t = time.perf_counter()
    # Retrieval consumes the resolved plan's price constraints rather than
    # re-parsing the turn, so a corrected or inherited ceiling cannot be lost
    # between the plan and the search.
    retrieval_context = runtime._retrieve_context(
        site_id, safe_transcript, conversation_history, plan.price_constraints()
    )
    profile = retrieval_context.profile
    price_constraints = retrieval_context.price_constraints
    retrieved_products = retrieval_context.products
    timings["rag_ms"] = runtime._ms(t)

    unsupported_text = runtime.bounded_unsupported_response(safe_transcript, retrieved_products)
    if unsupported_text:
        return runtime._policy_boundary_response(
            transcript,
            unsupported_text,
            skip_tts,
            timings,
            t0,
            retrieval=runtime._retrieval_evidence(site_id, ecommerce_runtime, retrieved_products, price_constraints),
        )

    planned_response = runtime._planned_flow_response(
        site_id=site_id,
        transcript=transcript,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        ecommerce_runtime=ecommerce_runtime,
        price_constraints=price_constraints,
        conversation_history=conversation_history or [],
        page_context=page_context,
        skip_tts=skip_tts,
        timings=timings,
        start_time=t0,
    )
    if planned_response:
        planned_response["ui_actions"] = strip_unrequested_navigation(
            planned_response.get("ui_actions"),
            planned_response.get("intent"),
            navigation_requested=navigation_requested,
        )
        # A planned flow used to return before the grounding validator ran, so its
        # products were never re-checked against the turn's hard constraints.
        planned_response = enforce_grounded_constraints(
            planned_response, retrieved_products, price_constraints
        )
        return planned_response

    runtime.logger.info(
        "PIPELINE | RAG returned %d products (price_filter=%s)",
        len(retrieved_products),
        price_constraints or "none",
    )
    runtime.print(f"🔍 RAG FOUND: {len(retrieved_products)} products")
    if price_constraints:
        runtime.print(f"   💰 Price filter active: {price_constraints}")
    for i, p in enumerate(retrieved_products[:5]):
        runtime.print(
            f"   [{i + 1}] id={p.get('id')} | {p.get('name', '?')[:50]} | ₹{p.get('price', '?')}"
        )

    # Stage 4: LLM Agent
    t = time.perf_counter()
    cart_context = runtime._cart_context_for_site(site_id, ecommerce_runtime)
    profile_context = runtime._profile_context(profile)

    llm_response = runtime.llm.generate_response(
        site_id,
        safe_transcript,
        retrieved_products,
        conversation_history=conversation_history or [],
        price_constraints=price_constraints,
        cart_context=cart_context,
        profile_context=profile_context,
        page_context=page_context,
        session_summary=session_summary,
    )

    llm_response = runtime._normalize_llm_response(llm_response, retrieved_products)
    runtime._persist_preference_actions(site_id, llm_response.get("ui_actions", []))

    timings["llm_ms"] = runtime._ms(t)

    # Stage 5: Output Guardrails
    t = time.perf_counter()
    validated = runtime._validate_agent_response(
        llm_response,
        site_id=site_id,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        blocked_text=runtime._blocked_text_for_site(ecommerce_runtime),
        page_context=page_context,
    )
    timings["guardrail_output_ms"] = runtime._ms(t)

    # Final deterministic guarantee: no actioned product may violate the hard
    # price constraint, even if an upstream filter was bypassed (slice 8).
    validated = enforce_grounded_constraints(validated, retrieved_products, price_constraints)

    final_actions = runtime._add_variant_ids_to_cart_actions(site_id, validated.get("ui_actions", []))
    final_actions = runtime._enrich_action_params_from_context(
        site_id,
        safe_transcript,
        conversation_history or [],
        final_actions,
    )
    filter_report = runtime._apply_capability_filter_result(site_id, final_actions)
    final_actions = filter_report["actions"]
    final_actions = strip_unrequested_navigation(
        final_actions, validated.get("intent"), navigation_requested=navigation_requested
    )
    validated["response_text"] = runtime._align_response_with_action_filter(validated["response_text"], filter_report)
    validated["response_text"] = runtime._align_response_with_enriched_action_params(validated["response_text"], final_actions)
    validated["response_text"] = runtime._neutralize_pending_action_claims(validated["response_text"], final_actions)
    validated["ui_actions"] = final_actions
    validated["answer_scope"] = runtime.answer_scope_for(
        safe_transcript,
        retrieved_products,
        final_actions,
        llm_scope=str(validated.get("answer_scope") or ""),
    )
    retrieval_evidence = runtime._retrieval_evidence(
        site_id,
        ecommerce_runtime,
        retrieved_products,
        price_constraints,
    )
    if plan.cache_eligible:
        runtime._maybe_store_answer_cache(
            site_id,
            safe_transcript,
            validated,
            retrieved_products,
            retrieval_evidence,
            session_id=session_id,
            constraint_signature=constraint_signature,
        )
    else:
        retrieval_evidence["cache_write"] = "skipped_turn_plan"

    runtime.print(f'🧠 LLM RESPONSE: "{validated["response_text"][:150]}"')
    runtime.print(
        f"   Intent: {validated.get('intent', '?')} | Confidence: {validated.get('confidence', '?')}"
    )
    runtime.print(f"   UI Actions: {validated.get('ui_actions', [])}")

    audio_b64, tts_ms = runtime._synthesize_audio_b64(validated["response_text"], skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms

    timings["total_ms"] = runtime._ms(t0)
    runtime.logger.info("PIPELINE | Done in %.0fms", timings["total_ms"])
    runtime.print(
        f"🔊 TTS: {'Generated audio' if audio_b64 else 'No audio (failed or skipped)'}"
    )
    runtime.print(f"⏱️  Total: {timings['total_ms']:.0f}ms")
    runtime.print(f"{'=' * 60}\n")

    runtime._ai_log("assistant", validated["response_text"])
    runtime._ai_log("actions", final_actions)

    return {
        "transcript": transcript,
        "response_text": validated["response_text"],
        "intent": validated.get("intent", "unknown"),
        "confidence": validated.get("confidence", 0.0),
        "answer_scope": validated.get("answer_scope", ""),
        "ui_actions": final_actions,
        "action_filter": filter_report,
        "audio_b64": audio_b64,
        "latency_ms": timings,
        "retrieval": retrieval_evidence,
    }



def run_stream_pipeline(
    runtime: Any,
    *,
    site_id: str,
    audio_bytes: Optional[bytes],
    text_input: Optional[str],
    audio_filename: str,
    skip_tts: bool,
    conversation_history: Optional[list],
    page_context: Optional[dict[str, Any]],
    session_summary: str,
    session_id: str = "",
) -> Generator[dict[str, Any], None, None]:
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    transcript, transcript_error = runtime._resolve_transcript(
        audio_bytes=audio_bytes,
        text_input=text_input,
        audio_filename=audio_filename,
        timings=timings,
    )
    if transcript_error:
        yield {"event": "error", "data": {"error": transcript_error}}
        return

    runtime._ai_log("user", transcript)
    yield {"event": "transcript", "data": {"transcript": transcript}}

    # Stage 2: Input Guardrails
    t = time.perf_counter()
    try:
        safe_transcript = runtime.guardrails.validate_input(transcript)
    except runtime.InputGuardrailError as exc:
        msg = str(exc)
        yield {"event": "actions", "data": {"ui_actions": []}}
        yield {"event": "response", "data": {"response_text": msg}}

        audio_b64, tts_ms = runtime._synthesize_audio_b64(msg, skip_tts)
        if tts_ms is not None:
            timings["tts_ms"] = tts_ms
        timings["total_ms"] = runtime._ms(t0)
        yield {"event": "audio", "data": {"response_text": msg, "audio_b64": audio_b64}}
        yield {"event": "metrics", "data": {"latency_ms": timings}}
        return
    timings["guardrail_input_ms"] = runtime._ms(t)

    if runtime._is_simple_greeting(safe_transcript):
        result = runtime._greeting_response(transcript, skip_tts, timings, t0)
        yield from stream_final_result(result)
        return

    ecommerce_runtime = runtime._is_ecommerce_site(site_id)

    # Identical resolution to the sync pipeline: one plan, resolved before any
    # shortcut, so both transports interpret the customer the same way.
    plan = runtime._build_turn_plan(
        site_id,
        safe_transcript,
        session_id=session_id,
        conversation_history=conversation_history,
        session_summary=session_summary,
        page_context=page_context,
        ecommerce_runtime=ecommerce_runtime,
    )

    if plan.allows_shortcut(TurnOperation.SORT):
        sort_response = runtime._sort_intent_response(
            site_id, transcript, safe_transcript, ecommerce_runtime, skip_tts, timings, t0
        )
        if sort_response:
            yield from stream_final_result(sort_response)
            return

    if plan.allows_shortcut(TurnOperation.NAVIGATE):
        navigation_response = runtime._navigation_intent_response(
            site_id, transcript, safe_transcript, skip_tts, timings, t0, page_context=page_context
        )
        if navigation_response:
            yield from stream_final_result(navigation_response)
            return

    if ecommerce_runtime and plan.operation == TurnOperation.AGGREGATE:
        aggregate_response = runtime._catalog_aggregate_response(
            site_id, transcript, plan, skip_tts, timings, t0
        )
        if aggregate_response:
            yield from stream_final_result(aggregate_response)
            return

    if ecommerce_runtime and plan.allows_shortcut(TurnOperation.INVENTORY_COUNT):
        if runtime._is_inventory_stats_query(safe_transcript):
            result = runtime._inventory_stats_response(site_id, transcript, skip_tts, timings, t0)
            yield from stream_final_result(result)
            return
        inventory_type = runtime._extract_inventory_type_query(safe_transcript)
        if inventory_type:
            result = runtime._inventory_type_count_response(
                site_id, transcript, inventory_type, skip_tts, timings, t0
            )
            yield from stream_final_result(result)
            return

    constraint_signature = plan.cache_key_component() if plan.cache_eligible else ""
    if ecommerce_runtime:
        # Resolve this turn against bounded recent context ONCE, then reuse it for
        # the clarification decision and for cache identity so the sync and
        # streaming pipelines behave identically.
        clarification = runtime._ecommerce_clarification_response(
            transcript,
            safe_transcript,
            skip_tts,
            timings,
            t0,
            site_id=site_id,
            conversation_history=conversation_history,
            session_summary=session_summary,
            plan=plan,
        )
        if clarification:
            yield from stream_final_result(clarification)
            return

    navigation_requested = plan.navigation_requested

    cached_response = None
    if plan.cache_eligible:
        cached_response = runtime._cached_answer_response(
            site_id,
            transcript,
            safe_transcript,
            skip_tts,
            timings,
            t0,
            session_id=session_id,
            constraint_signature=constraint_signature,
        )
    if cached_response:
        cached_response["ui_actions"] = strip_unrequested_navigation(
            cached_response.get("ui_actions"),
            cached_response.get("intent"),
            navigation_requested=navigation_requested,
        )
        yield from stream_final_result(cached_response)
        return

    # Stage 3: RAG
    t = time.perf_counter()
    # Retrieval consumes the resolved plan's price constraints rather than
    # re-parsing the turn, so a corrected or inherited ceiling cannot be lost
    # between the plan and the search.
    retrieval_context = runtime._retrieve_context(
        site_id, safe_transcript, conversation_history, plan.price_constraints()
    )
    profile = retrieval_context.profile
    price_constraints = retrieval_context.price_constraints
    retrieved_products = retrieval_context.products
    timings["rag_ms"] = runtime._ms(t)

    unsupported_text = runtime.bounded_unsupported_response(safe_transcript, retrieved_products)
    if unsupported_text:
        result = runtime._policy_boundary_response(
            transcript,
            unsupported_text,
            skip_tts,
            timings,
            t0,
            retrieval=runtime._retrieval_evidence(site_id, ecommerce_runtime, retrieved_products, price_constraints),
        )
        yield from stream_final_result(result)
        return

    planned_response = runtime._planned_flow_response(
        site_id=site_id,
        transcript=transcript,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        ecommerce_runtime=ecommerce_runtime,
        price_constraints=price_constraints,
        conversation_history=conversation_history or [],
        page_context=page_context,
        skip_tts=skip_tts,
        timings=timings,
        start_time=t0,
    )
    if planned_response:
        planned_response["ui_actions"] = strip_unrequested_navigation(
            planned_response.get("ui_actions"),
            planned_response.get("intent"),
            navigation_requested=navigation_requested,
        )
        planned_response = enforce_grounded_constraints(
            planned_response, retrieved_products, price_constraints
        )
        yield from stream_final_result(planned_response)
        return

    # Stage 4: LLM
    t = time.perf_counter()
    profile_context = runtime._profile_context(profile)
    cart_context = runtime._cart_context_for_site(site_id, ecommerce_runtime)
    llm_response = runtime.llm.generate_response(
        site_id,
        safe_transcript,
        retrieved_products,
        conversation_history=conversation_history or [],
        price_constraints=price_constraints,
        cart_context=cart_context,
        profile_context=profile_context,
        page_context=page_context,
        session_summary=session_summary,
    )
    llm_response = runtime._normalize_llm_response(llm_response, retrieved_products)
    runtime._persist_preference_actions(site_id, llm_response.get("ui_actions", []))
    timings["llm_ms"] = runtime._ms(t)

    # Stage 5: Output Guardrails
    t = time.perf_counter()
    validated = runtime._validate_agent_response(
        llm_response,
        site_id=site_id,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        blocked_text=runtime._blocked_text_for_site(ecommerce_runtime),
        page_context=page_context,
    )
    timings["guardrail_output_ms"] = runtime._ms(t)

    # Final deterministic guarantee: no actioned product may violate the hard
    # price constraint, even if an upstream filter was bypassed (slice 8).
    validated = enforce_grounded_constraints(validated, retrieved_products, price_constraints)

    final_actions = runtime._add_variant_ids_to_cart_actions(site_id, validated.get("ui_actions", []))
    final_actions = runtime._enrich_action_params_from_context(
        site_id,
        safe_transcript,
        conversation_history or [],
        final_actions,
    )
    filter_report = runtime._apply_capability_filter_result(site_id, final_actions)
    final_actions = filter_report["actions"]
    final_actions = strip_unrequested_navigation(
        final_actions, validated.get("intent"), navigation_requested=navigation_requested
    )
    validated["response_text"] = runtime._align_response_with_action_filter(validated["response_text"], filter_report)
    validated["response_text"] = runtime._align_response_with_enriched_action_params(validated["response_text"], final_actions)
    validated["response_text"] = runtime._neutralize_pending_action_claims(validated["response_text"], final_actions)
    validated["ui_actions"] = final_actions
    validated["answer_scope"] = runtime.answer_scope_for(
        safe_transcript,
        retrieved_products,
        final_actions,
        llm_scope=str(validated.get("answer_scope") or ""),
    )
    retrieval_evidence = runtime._retrieval_evidence(
        site_id,
        ecommerce_runtime,
        retrieved_products,
        price_constraints,
    )
    if plan.cache_eligible:
        runtime._maybe_store_answer_cache(
            site_id,
            safe_transcript,
            validated,
            retrieved_products,
            retrieval_evidence,
            session_id=session_id,
            constraint_signature=constraint_signature,
        )
    else:
        retrieval_evidence["cache_write"] = "skipped_turn_plan"
    runtime._ai_log("assistant", validated["response_text"])
    runtime._ai_log("actions", final_actions)

    # Time-to-first-text: when the customer first sees a textual answer (slice 13).
    timings["first_text_ms"] = runtime._ms(t0)
    timings["response_chars"] = len(str(validated.get("response_text") or ""))

    # Yield actions so UI can update immediately
    yield {"event": "actions", "data": {"ui_actions": final_actions}}
    yield {"event": "response", "data": {"response_text": validated["response_text"], "answer_scope": validated.get("answer_scope", "")}}

    audio_b64, tts_ms = runtime._synthesize_audio_b64(validated["response_text"], skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms
    timings["total_ms"] = runtime._ms(t0)

    # Yield audio
    yield {
        "event": "audio",
        "data": {
            "response_text": validated["response_text"],
            "audio_b64": audio_b64,
            "latency_ms": timings,
            "retrieval": retrieval_evidence,
            "answer_scope": validated.get("answer_scope", ""),
        },
    }
    yield {"event": "metrics", "data": {"latency_ms": timings, "retrieval": retrieval_evidence}}
