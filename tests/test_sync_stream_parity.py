"""The synchronous and streaming pipelines must interpret a turn identically.

Two transports answering the same customer differently is invisible in testing
and obvious in production: the widget prefers the WebSocket and silently falls
back to HTTP, so the same question could be resolved as a browse on one path and
an inventory count on the other.

Both pipelines resolve exactly one `TurnPlan` before any shortcut may answer.
These tests drive the real `run` and `run_stream` over the same fixtures and
compare what each produced.
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.acceptance_corpus import ECOMMERCE_CATALOG  # noqa: E402

SITE = "ecommerce_site"

# One utterance per shape that a shortcut could have hijacked on only one path.
PARITY_TURNS = [
    "what is the cheapest item in Fashion Women?",
    "which item has the best rating?",
    "what is the most expensive smartphone?",
    "how many smartphones do you have?",
    "show me a smartphone under 50000",
    "take me to the offers page",
    "sort them by price low to high",
    "show the cheapest smartphone and take me there",
    "do you have Aster?",
]


@pytest.fixture
def both_pipelines(monkeypatch):
    from agent import orchestrator
    from agent.runtime_helpers.retrieval_runtime import RetrievalContext

    def no_database(*_args, **_kwargs):
        raise psycopg.OperationalError("database intentionally unavailable in this suite")

    catalog = [dict(record) for record in ECOMMERCE_CATALOG]
    monkeypatch.setattr(psycopg, "connect", no_database)
    monkeypatch.setattr("db.core.database._get_connection", no_database)
    monkeypatch.setattr(
        "agent.retrieval.catalog_vocabulary.catalog_brand_vocabulary",
        lambda site_id: ("aster", "borel", "corvi", "delta"),
    )
    monkeypatch.setattr(
        "agent.action_helpers.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "ecommerce", "vertical_config_json": "{}"},
    )
    monkeypatch.setattr(
        "agent.guardrail_helpers.guardrails.product_exists",
        lambda site_id, product_id: str(product_id) in {record["id"] for record in catalog},
    )
    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: [dict(r) for r in catalog])
    monkeypatch.setattr(orchestrator, "get_catalog_records", lambda site_id, **kw: [dict(r) for r in catalog])
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(orchestrator, "_add_variant_ids_to_cart_actions", lambda site_id, actions: actions)
    monkeypatch.setattr(orchestrator, "_persist_preference_actions", lambda site_id, actions: None)
    monkeypatch.setattr(orchestrator, "_cart_context_for_site", lambda site_id, ecommerce: "")
    monkeypatch.setattr(
        orchestrator,
        "_apply_capability_filter_result",
        lambda site_id, actions: {"actions": list(actions), "removed": [], "status": "applied"},
    )
    monkeypatch.setattr(
        orchestrator,
        "_retrieve_context",
        lambda site_id, transcript, history, price_constraints=None: RetrievalContext(
            profile={}, price_constraints={}, products=[dict(r) for r in catalog]
        ),
    )
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "Here is what I found.",
            "intent": "product_search",
            "confidence": 0.9,
            "answer_scope": "product_search",
            "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["e4"]}}],
        },
    )
    return orchestrator


def _sync(orchestrator, text: str) -> dict:
    return orchestrator.run(site_id=SITE, text_input=text, skip_tts=True)


def _streamed(orchestrator, text: str) -> dict:
    events = list(orchestrator.run_stream(site_id=SITE, text_input=text, skip_tts=True))
    response = next((e for e in events if e["event"] == "response"), {"data": {}})
    actions = next((e for e in events if e["event"] == "actions"), {"data": {}})
    return {
        "response_text": response["data"].get("response_text", ""),
        "ui_actions": actions["data"].get("ui_actions", []),
        "answer_scope": response["data"].get("answer_scope", ""),
    }


def _comparable(result: dict) -> dict:
    return {
        "response_text": result.get("response_text", ""),
        "ui_actions": result.get("ui_actions", []),
    }


@pytest.mark.parametrize("utterance", PARITY_TURNS)
def test_both_transports_answer_the_same_turn_identically(both_pipelines, utterance):
    sync_result = _sync(both_pipelines, utterance)
    stream_result = _streamed(both_pipelines, utterance)

    assert _comparable(stream_result) == _comparable(sync_result), (
        f"{utterance!r} was answered differently by the two transports"
    )


@pytest.mark.parametrize("utterance", PARITY_TURNS)
def test_both_transports_resolve_the_same_plan(both_pipelines, utterance):
    """Parity comes from one shared plan, not from two agreeing re-parses."""
    plans = []
    original = both_pipelines._build_turn_plan

    def recording_plan(*args, **kwargs):
        plan = original(*args, **kwargs)
        plans.append(plan)
        return plan

    both_pipelines._build_turn_plan = recording_plan
    try:
        _sync(both_pipelines, utterance)
        _streamed(both_pipelines, utterance)
    finally:
        both_pipelines._build_turn_plan = original

    assert len(plans) == 2, "each transport must resolve exactly one plan for the turn"
    sync_plan, stream_plan = plans
    assert sync_plan.operation == stream_plan.operation
    assert sync_plan.aggregate == stream_plan.aggregate
    assert sync_plan.constraints == stream_plan.constraints
    assert sync_plan.cache_eligible == stream_plan.cache_eligible
    assert sync_plan.navigation_requested == stream_plan.navigation_requested


def test_a_budgeted_search_is_never_stolen_by_a_shortcut_on_either_transport(both_pipelines):
    utterance = "I want to buy a smartphone under 20000"

    sync_result = _sync(both_pipelines, utterance)
    stream_result = _streamed(both_pipelines, utterance)

    for label, result in (("sync", sync_result), ("stream", stream_result)):
        text = result["response_text"]
        assert "72,999" not in text and "64,999" not in text, f"{label} leaked an over-budget record"
