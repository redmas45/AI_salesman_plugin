"""Runtime execution for deterministic planned website flows."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class PlannedFlowRuntime:
    planner: Callable[..., dict[str, Any] | None]
    add_variant_ids_to_cart_actions: Callable[[str, list[dict[str, Any]]], list[dict[str, Any]]]
    enrich_action_params_from_context: Callable[[str, str, list, list[dict[str, Any]]], list[dict[str, Any]]]
    apply_capability_filter_result: Callable[[str, list[dict[str, Any]]], dict[str, Any]]
    ensure_product_display_search_queries: Callable[[dict[str, Any], str, list[dict[str, Any]]], None]
    align_response_with_action_filter: Callable[[str, dict[str, Any]], str]
    align_response_with_enriched_action_params: Callable[[str, list[dict[str, Any]]], str]
    neutralize_pending_action_claims: Callable[[str, list[dict[str, Any]]], str]
    retrieval_evidence: Callable[[str, bool, list[dict[str, Any]], dict[str, Any]], dict[str, Any]]
    answer_scope_for: Callable[..., str]
    synthesize_audio_b64: Callable[[str, bool], tuple[str, float | None]]
    elapsed_ms: Callable[[float], float]
    ai_log: Callable[[str, Any], None]


def planned_flow_response(
    *,
    site_id: str,
    transcript: str,
    safe_transcript: str,
    retrieved_products: list[dict[str, Any]],
    ecommerce_runtime: bool,
    price_constraints: dict[str, Any],
    conversation_history: list,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    deps: PlannedFlowRuntime,
) -> dict[str, Any] | None:
    started_at = time.perf_counter()
    planned = deps.planner(
        site_id=site_id,
        transcript=safe_transcript,
        retrieved_items=retrieved_products,
        ecommerce_runtime=ecommerce_runtime,
    )
    timings["planner_ms"] = deps.elapsed_ms(started_at)
    if not planned:
        return None

    final_actions = _planned_actions(
        site_id,
        safe_transcript,
        conversation_history,
        planned,
        deps,
    )
    filter_report = deps.apply_capability_filter_result(site_id, final_actions)
    final_actions = filter_report["actions"]
    if ecommerce_runtime:
        action_response = {"ui_actions": final_actions}
        deps.ensure_product_display_search_queries(action_response, safe_transcript, retrieved_products)
        final_actions = action_response["ui_actions"]
        filter_report["actions"] = final_actions

    response_text = _planned_response_text(str(planned.get("response_text") or ""), final_actions, filter_report, deps)
    retrieval_evidence = deps.retrieval_evidence(
        site_id,
        ecommerce_runtime,
        retrieved_products,
        price_constraints,
    )
    answer_scope = deps.answer_scope_for(
        safe_transcript,
        retrieved_products,
        final_actions,
        llm_scope="action_flow" if final_actions else "clarification",
    )
    audio_b64, tts_ms = deps.synthesize_audio_b64(response_text, skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms
    timings["total_ms"] = deps.elapsed_ms(start_time)
    deps.ai_log("assistant", response_text)
    deps.ai_log("actions", final_actions)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": str(planned.get("intent") or "action_flow"),
        "confidence": float(planned.get("confidence") or 0.0),
        "answer_scope": answer_scope,
        "ui_actions": final_actions,
        "action_filter": filter_report,
        "audio_b64": audio_b64,
        "latency_ms": timings,
        "retrieval": retrieval_evidence,
    }


def _planned_actions(
    site_id: str,
    safe_transcript: str,
    conversation_history: list,
    planned: dict[str, Any],
    deps: PlannedFlowRuntime,
) -> list[dict[str, Any]]:
    final_actions = deps.add_variant_ids_to_cart_actions(site_id, planned.get("ui_actions", []))
    return deps.enrich_action_params_from_context(
        site_id,
        safe_transcript,
        conversation_history,
        final_actions,
    )


def _planned_response_text(
    response_text: str,
    final_actions: list[dict[str, Any]],
    filter_report: dict[str, Any],
    deps: PlannedFlowRuntime,
) -> str:
    response_text = deps.align_response_with_action_filter(response_text, filter_report)
    response_text = deps.align_response_with_enriched_action_params(response_text, final_actions)
    return deps.neutralize_pending_action_claims(response_text, final_actions)
