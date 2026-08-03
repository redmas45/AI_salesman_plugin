"""Regression tests for slice 7: one useful clarification for ambiguous asks.

Malformed/undecided requests ("It's raining air. What should I buy?") and
recipient-only gifts ("a gift for my mom") must ask exactly one clarifying
question instead of returning random products whose descriptions merely mention
gifting. Concrete product nouns and mood/need queries must NOT be clarified.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ECOMMERCE_TEST_SITE_ID = "ecommerce_site"

PRODUCTS = [
    {"id": "p1", "name": "NOVA Dog Sweater", "brand": "NOVA", "category_name": "Pets",
     "description": "A cozy gift for pets.", "stock": 5},
    {"id": "p2", "name": "NOVA Air Fryer", "brand": "NOVA", "category_name": "Home",
     "description": "Great for gifting.", "stock": 8},
]


def _run(monkeypatch, text):
    from agent import orchestrator

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: PRODUCTS)
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )
    events = list(orchestrator.run_stream(site_id=ECOMMERCE_TEST_SITE_ID, text_input=text, skip_tts=True))
    response = next(event for event in events if event["event"] == "response")
    actions = next(event for event in events if event["event"] == "actions")
    return response["data"], actions["data"]["ui_actions"]


def test_raining_air_asks_a_single_clarification(monkeypatch):
    data, actions = _run(monkeypatch, "It's raining air. What should I buy? I'm not decided.")
    assert actions == []
    text = data["response_text"]
    assert "?" in text
    assert text.count("?") == 1  # exactly one question
    assert "dog sweater" not in text.lower() and "air fryer" not in text.lower()


def test_what_should_i_buy_is_clarified(monkeypatch):
    data, actions = _run(monkeypatch, "What should I buy?")
    assert actions == []
    assert "?" in data["response_text"]


def test_recipient_only_gift_is_clarified_and_mentions_recipient(monkeypatch):
    data, actions = _run(monkeypatch, "I want a gift for my mom")
    assert actions == []
    assert "mom" in data["response_text"].lower()


def test_concrete_product_noun_is_not_clarified(monkeypatch):
    # "laptop" is a concrete type; must fall through to normal retrieval, not clarify.
    from agent.retrieval.query_constraints import extract_ecommerce_constraints
    from agent.products.product_matching_lexical import BUILTIN_TYPE_NOUNS

    constraints = extract_ecommerce_constraints("I'm looking for a laptop", catalog_types=tuple(BUILTIN_TYPE_NOUNS))
    assert not constraints.should_ask_clarification()


def test_mood_query_is_not_clarified():
    # Mood/need queries stay on the retrieval path (reason 'underspecified').
    from agent.retrieval.query_constraints import extract_ecommerce_constraints
    from agent.products.product_matching_lexical import BUILTIN_TYPE_NOUNS

    constraints = extract_ecommerce_constraints("something to keep me warm", catalog_types=tuple(BUILTIN_TYPE_NOUNS))
    assert not constraints.should_ask_clarification()
