"""Grounded response text and actions for deterministic catalog aggregates.

Every sentence produced here names a record that survived the hard-constraint
filter, and every action id comes from that same validated set. There is no
model call in this path, so the wording cannot drift away from the data and a
superlative cannot be attributed to a record that was never a candidate.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from agent.catalog import catalog_operations as ops
from agent.products.comparison_facts import format_price
from api.contracts.models import (
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_SHOW_PRODUCTS,
    PRODUCT_ID_PARAM,
    PRODUCT_IDS_PARAM,
)

AGGREGATE_LABELS = {
    ops.AGGREGATE_CHEAPEST: "cheapest",
    ops.AGGREGATE_MOST_EXPENSIVE: "most expensive",
    ops.AGGREGATE_BEST_RATED: "best rated",
}
DEFAULT_ENTITY_NOUN = "product"
AGGREGATE_INTENT = "product_search"


def answer_noun(plan: Any, selection: ops.CatalogSelection, fallback: str = DEFAULT_ENTITY_NOUN) -> str:
    """The noun the answer should use, taken from what the customer said."""
    types = getattr(plan.constraints, "product_types", ()) or ()
    if types:
        return str(types[0])
    if selection.applied_categories:
        return f"{selection.applied_categories[0]} item"
    return fallback


def aggregate_answer_text(aggregate: str, records: list[dict], noun: str) -> str:
    """One grounded sentence about the single record that won the superlative."""
    label = AGGREGATE_LABELS.get(aggregate, aggregate)
    if not records:
        return (
            f"I couldn't find a {noun} that matches those requirements right now. "
            "Want to widen the budget or try another category?"
        )
    winner = records[0]
    name = str(winner.get("name") or winner.get("title") or "").strip()
    if aggregate == ops.AGGREGATE_BEST_RATED:
        return f"The {label} {noun} is {name}, rated {ops.record_rating(winner):.1f} from {ops.record_review_count(winner)} reviews."
    price = format_price(winner)
    priced = f" at {price}" if price else ""
    return f"The {label} {noun} I have is {name}{priced}."


def aggregate_actions(records: list[dict], *, navigation_requested: bool) -> list[dict[str, Any]]:
    """Show the winning record, and open it when the customer asked to go there."""
    if not records:
        return []
    winner_id = str(records[0].get("id") or "")
    if not winner_id:
        return []
    actions: list[dict[str, Any]] = [
        {"action": ACTION_SHOW_PRODUCTS, "params": {PRODUCT_IDS_PARAM: [winner_id]}}
    ]
    if navigation_requested:
        # "…and take me there" is a second, independent requirement. Opening the
        # winning record satisfies it without guessing at a listing route.
        actions.append({"action": ACTION_SHOW_PRODUCT_DETAIL, "params": {PRODUCT_ID_PARAM: winner_id}})
    return actions


def catalog_aggregate_response(
    site_id: str,
    transcript: str,
    plan: Any,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    load_records: Callable[[str], list[dict]],
    synthesize_b64: Callable[[str], str],
    ai_log: Callable[[str, Any], None],
    elapsed_ms: Callable[[float], float],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: Any,
) -> dict[str, Any] | None:
    """Answer a superlative question from the catalog, without the model."""
    if plan.aggregate not in ops.SUPPORTED_AGGREGATES:
        return None

    started_at = time.perf_counter()
    try:
        records = load_records(site_id)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | catalog aggregate lookup failed: %s", exc)
        return None
    timings["catalog_scan_ms"] = elapsed_ms(started_at)
    if not records:
        return None

    categories = ops.matching_category_names(plan.constraints.raw_query, records)
    selection = ops.select_records(records, plan.constraints, category_names=categories)
    winners = ops.aggregate_records(selection, plan.aggregate, limit=1)
    noun = answer_noun(plan, selection)
    response_text = aggregate_answer_text(plan.aggregate, winners, noun)
    actions = aggregate_actions(winners, navigation_requested=plan.navigation_requested)

    ai_log("assistant", response_text)
    ai_log("actions", actions)
    audio_b64 = _synthesize(response_text, skip_tts, timings, synthesize_b64, elapsed_ms, logger)
    timings["total_ms"] = elapsed_ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": AGGREGATE_INTENT,
        "confidence": 1.0,
        "answer_scope": "product_search",
        "ui_actions": actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
        "retrieval": {
            "operation": plan.operation.value,
            "aggregate": plan.aggregate,
            "matching_records": selection.facts.matching_records,
            "variant_count": selection.facts.variant_count,
            "stock_units": selection.facts.stock_units,
            "exact_count": selection.facts.exact(),
            "applied_categories": list(selection.applied_categories),
            "product_ids": [str(record.get("id")) for record in winners],
        },
    }


def _synthesize(
    response_text: str,
    skip_tts: bool,
    timings: dict[str, float],
    synthesize_b64: Callable[[str], str],
    elapsed_ms: Callable[[float], float],
    logger: Any,
) -> str:
    if skip_tts:
        return ""
    started_at = time.perf_counter()
    try:
        audio_b64 = synthesize_b64(response_text)
    except RuntimeError as exc:
        logger.error("PIPELINE | TTS failed for catalog aggregate: %s", exc)
        audio_b64 = ""
    timings["tts_ms"] = elapsed_ms(started_at)
    return audio_b64
