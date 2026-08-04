"""Retrieval must consume the resolved plan, not re-parse the customer.

`retrieve_context` used to call `extract_price_constraints(safe_transcript)` on
the raw utterance. That is a second, independent interpretation of the same turn,
and the two disagree exactly where it matters most: on a correction.

"smartphones under 20000" then "but I said 50,000" resolves to a ceiling of
50,000 in the plan, because the plan folds in recent context. The raw text of the
second turn carries a bare number with no cue word, so the independent re-parse
found no ceiling at all - and a search with no ceiling can return anything.
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.acceptance_corpus import ECOMMERCE_CATALOG  # noqa: E402

SITE = "ecommerce_site"
OVER_BUDGET_NAME = "Corvi Smartphone X9"  # 72,999


@pytest.fixture
def pipeline(monkeypatch):
    """The real pipeline with a real retrieval seam, recording what it received."""
    from agent import orchestrator

    received: list[dict] = []

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
    # The retrieval seam itself is real enough to record the constraints it is
    # handed; only the database-backed search is replaced.
    monkeypatch.setattr(
        orchestrator.rag,
        "retrieve",
        lambda query, site_id="", price_constraints=None, **kw: _filtered(catalog, price_constraints, received),
    )
    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda site_id: {})
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda site_id, transcript, products, **kwargs: {
            "response_text": "Here is what I found: " + ", ".join(p["name"] for p in products),
            "intent": "product_search",
            "confidence": 0.9,
            "answer_scope": "product_search",
            "ui_actions": [
                {"action": "SHOW_PRODUCTS", "params": {"product_ids": [p["id"] for p in products]}}
            ],
        },
    )
    return orchestrator, received


def _filtered(catalog, price_constraints, received):
    constraints = dict(price_constraints or {})
    received.append(constraints)
    ceiling = constraints.get("max_price")
    floor = constraints.get("min_price")
    return [
        dict(record)
        for record in catalog
        if record["stock"] > 0
        and (ceiling is None or record["price"] <= ceiling)
        and (floor is None or record["price"] >= floor)
    ]


CORRECTION_HISTORY = [
    {"role": "user", "content": "show me smartphones under 20000"},
    {"role": "assistant", "content": "I found 1 option within your budget: Delta Smartphone Lite."},
]


def test_retrieval_receives_the_corrected_ceiling_not_a_reparse(pipeline):
    orchestrator, received = pipeline

    orchestrator.run(
        site_id=SITE,
        text_input="but I said 50,000",
        skip_tts=True,
        conversation_history=list(CORRECTION_HISTORY),
    )

    assert received, "retrieval was never reached"
    assert received[0].get("max_price") == 50000.0, (
        f"retrieval re-parsed the raw turn and saw {received[0]!r} instead of the resolved ceiling"
    )


def test_a_correction_turn_never_leaks_an_over_budget_record(pipeline):
    orchestrator, _received = pipeline

    result = orchestrator.run(
        site_id=SITE,
        text_input="but I said 50,000",
        skip_tts=True,
        conversation_history=list(CORRECTION_HISTORY),
    )

    assert OVER_BUDGET_NAME not in result["response_text"]
    actioned = [
        pid
        for action in result["ui_actions"]
        for pid in (action.get("params") or {}).get("product_ids") or []
    ]
    assert "e5" not in actioned, "72,999 is above the corrected 50,000 ceiling"


def test_an_explicit_ceiling_still_reaches_retrieval_unchanged(pipeline):
    orchestrator, received = pipeline

    orchestrator.run(site_id=SITE, text_input="show me smartphones under 20000", skip_tts=True)

    assert received[0].get("max_price") == 20000.0


def test_a_turn_with_no_budget_sends_no_ceiling(pipeline):
    orchestrator, received = pipeline

    orchestrator.run(site_id=SITE, text_input="show me some smartphones", skip_tts=True)

    assert received[0].get("max_price") is None
