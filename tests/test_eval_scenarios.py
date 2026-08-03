"""Slice 14: deterministic 50-case evaluation set + vertical-independence fixtures.

Each scenario exercises the deterministic decision layer (constraint model, budget
parser, browse/count intent, ambiguity gate) that was hardened in slices 3-10, so
regressions in buyer understanding surface as plain assertions with no DB, LLM, or
network dependency. A separate live-provider smoke set is provided but skipped
unless RUN_LIVE_SMOKE is set. Travel and policy fixtures prove the shared changes
are vertical-independent (no e-commerce assumptions leak into other verticals).
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.products.product_matching_lexical import BUILTIN_TYPE_NOUNS  # noqa: E402
from agent.responses.inventory_responses import is_browse_search_phrase  # noqa: E402
from agent.retrieval.query_constraints import (  # noqa: E402
    extract_ecommerce_constraints,
    parse_budget,
)

CATALOG_BRANDS = ("apple", "samsung", "nike", "adidas", "nova", "acer", "asus", "sony", "hp", "dell")
CATALOG_TYPES = tuple(BUILTIN_TYPE_NOUNS)


def _constraints(query: str):
    return extract_ecommerce_constraints(query, catalog_brands=CATALOG_BRANDS, catalog_types=CATALOG_TYPES)


# archetype, query, expectations. Only asserted keys are checked.
SCENARIOS: list[tuple[str, str, dict]] = [
    # --- eager (clear buying intent) ---
    ("eager", "I'm looking for Nike sneakers", {"browse": True, "brands": {"nike"}, "types": {"sneaker"}, "clarify": False}),
    ("eager", "I want to buy a Samsung tablet", {"browse": True, "brands": {"samsung"}, "types": {"tablet"}}),
    ("eager", "I need a laptop", {"browse": True, "types": {"laptop"}, "clarify": False}),
    ("eager", "I'm interested in Apple Flex smartwatches", {"brands": {"apple"}, "types": {"smartwatch"}, "both": True}),
    ("eager", "I'm looking for a Sony camera", {"browse": True, "brands": {"sony"}, "types": {"camera"}}),
    # --- time-wasting / undecided ---
    ("time_waster", "I'm just browsing", {"clarify": True, "explicit": False}),
    ("time_waster", "not sure what I want", {"clarify": True}),
    ("time_waster", "show me something", {"clarify": True}),
    ("time_waster", "surprise me", {"clarify": True}),
    ("time_waster", "help me choose", {"clarify": True}),
    # --- checking (availability/count, not browse) ---
    ("checking", "Do you have any Apple?", {"browse": False, "brands": {"apple"}}),
    ("checking", "How many smartwatches do you have?", {"browse": False}),
    ("checking", "Is the iPhone available?", {"browse": False}),
    ("checking", "Do you sell headphones?", {"browse": False, "types": {"headphone"}}),
    # --- curious (category exploration) ---
    ("curious", "I'm looking for headphones", {"browse": True, "types": {"headphone"}, "clarify": False}),
    ("curious", "I'm interested in cameras", {"browse": True, "types": {"camera"}}),
    ("curious", "I'm looking for a dress", {"browse": True, "types": {"dress"}}),
    # --- confused / malformed ---
    ("confused", "It's raining air. What should I buy? I'm not decided.", {"clarify": True, "explicit": False}),
    ("confused", "I have no idea", {"clarify": True}),
    ("confused", "What should I buy?", {"clarify": True}),
    # --- correction / follow-up ---
    ("correction", "No, I meant the laptop", {"followup": True}),
    ("correction", "Actually, under 1000", {"followup": True, "max": 1000.0}),
    ("correction", "the second one", {"followup": True}),
    ("correction", "the cheaper one", {"followup": True}),
    # --- gift ---
    ("gift", "I want a gift for my mom", {"recipient": "mom", "occasion": "gift", "clarify": True}),
    ("gift", "a birthday present for my sister", {"recipient": "sister", "occasion": "birthday", "clarify": True}),
    ("gift", "gift for my girlfriend under 2000", {"recipient": "girlfriend", "max": 2000.0, "clarify": True}),
    ("gift", "a gift for my husband", {"recipient": "husband", "clarify": True}),
    ("gift", "something for my kids", {"recipient": "kids", "clarify": True}),
    # --- budget forms ---
    ("budget", "phones under 20000", {"max": 20000.0}),
    ("budget", "I have a budget of 1500", {"max": 1500.0}),
    ("budget", "between 1000 and 3000", {"min": 1000.0, "max": 3000.0}),
    ("budget", "at most 5000", {"max": 5000.0}),
    ("budget", "around 2500", {"max": 2500.0}),
    ("budget", "1.5k budget", {"max": 1500.0}),
    ("budget", "over 10000", {"min": 10000.0}),
    ("budget", "I can spend up to 800", {"max": 800.0}),
    ("budget", "within 3000", {"max": 3000.0}),
    ("budget", "not more than 750", {"max": 750.0}),
    ("budget", "starting from 200", {"min": 200.0}),
    # --- comparison ---
    ("comparison", "compare Apple and Samsung phones", {"brands": {"apple", "samsung"}, "types": {"phone"}, "clarify": False}),
    ("comparison", "Nike vs Adidas shoes", {"brands": {"nike", "adidas"}, "types": {"shoe"}}),
    # --- off-topic ---
    ("off_topic", "what's the weather today", {"explicit": False, "clarify": False}),
    ("off_topic", "who is the prime minister", {"explicit": False, "clarify": False}),
    # --- brand-only / type-only ---
    ("brand_only", "I'm looking for Apple products", {"brands": {"apple"}, "types": set(), "browse": True}),
    ("type_only", "I'm looking for a smartwatch", {"types": {"smartwatch"}, "brands": set(), "browse": True}),
    # --- multi-turn budget refinement ---
    ("multi_turn", "actually make it under 1000", {"followup": True, "max": 1000.0}),
    ("multi_turn", "Samsung laptop", {"brands": {"samsung"}, "types": {"laptop"}, "both": True}),
    # --- price-only (no product) ---
    ("budget", "just under 500", {"max": 500.0}),
    ("curious", "I'm interested in Adidas shoes", {"browse": True, "brands": {"adidas"}, "types": {"shoe"}}),
]


def test_scenario_count_is_at_least_fifty():
    assert len(SCENARIOS) >= 50, f"only {len(SCENARIOS)} scenarios"


@pytest.mark.parametrize("archetype,query,expect", SCENARIOS, ids=[f"{a}:{q[:24]}" for a, q, _ in SCENARIOS])
def test_scenario(archetype: str, query: str, expect: dict):
    constraints = _constraints(query)
    if "max" in expect:
        assert constraints.max_price == expect["max"], f"{query!r} max_price"
    if "min" in expect:
        assert constraints.min_price == expect["min"], f"{query!r} min_price"
    if "brands" in expect:
        assert set(constraints.brands) == expect["brands"], f"{query!r} brands={constraints.brands}"
    if "types" in expect:
        assert set(constraints.product_types) == expect["types"], f"{query!r} types={constraints.product_types}"
    if "browse" in expect:
        assert is_browse_search_phrase(query) is expect["browse"], f"{query!r} browse"
    if "clarify" in expect:
        assert constraints.should_ask_clarification() is expect["clarify"], f"{query!r} clarify"
    if "followup" in expect:
        assert constraints.is_followup is expect["followup"], f"{query!r} followup"
    if "explicit" in expect:
        assert constraints.has_explicit_product_request() is expect["explicit"], f"{query!r} explicit"
    if "recipient" in expect:
        assert constraints.recipient == expect["recipient"], f"{query!r} recipient"
    if "occasion" in expect:
        assert constraints.occasion == expect["occasion"], f"{query!r} occasion"
    if "both" in expect:
        assert constraints.requires_both_brand_and_type() is expect["both"], f"{query!r} both"


# --- Vertical independence: travel + policy must not inherit e-commerce assumptions ---


def test_travel_query_extracts_only_generic_price_no_ecommerce_signal():
    # A travel vertical would not pass e-commerce brands/types.
    constraints = extract_ecommerce_constraints("flights to Goa under 5000", catalog_brands=(), catalog_types=())
    assert constraints.max_price == 5000.0  # shared price parsing is vertical-independent
    assert constraints.brands == () and constraints.product_types == ()
    assert not constraints.should_ask_clarification()  # a priced travel query is not "ambiguous"


def test_policy_question_is_not_clarified_or_mispriced():
    constraints = extract_ecommerce_constraints("what is your return policy", catalog_brands=(), catalog_types=())
    assert parse_budget("what is your return policy") == {}
    assert not constraints.should_ask_clarification()
    assert not constraints.has_explicit_product_request()


# --- Live-provider smoke set (opt-in; skipped by default) ---

LIVE_SMOKE_QUERIES = [
    "I'm looking for an Apple smartwatch under 30000",
    "What should I buy for my mom's birthday?",
    "Show me the cheapest laptop you have",
]


@pytest.mark.skipif(not os.environ.get("RUN_LIVE_SMOKE"), reason="live provider smoke is opt-in (set RUN_LIVE_SMOKE=1)")
@pytest.mark.parametrize("query", LIVE_SMOKE_QUERIES)
def test_live_provider_smoke(query: str):  # pragma: no cover - requires a live provider + DB
    from agent import orchestrator

    events = list(orchestrator.run_stream(site_id=os.environ.get("SMOKE_SITE_ID", "demo"), text_input=query, skip_tts=True))
    response = next(event for event in events if event["event"] == "response")
    assert response["data"]["response_text"].strip()
