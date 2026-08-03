"""Regression tests for slice 8: deterministic final grounding + price invariant.

Even if an upstream filter is bypassed, no actioned product may exceed the hard
price ceiling. Over-budget products are removed, the text is re-grounded from the
survivors, and an explicit request that survives nothing yields a grounded
no-match instead of leaking the ungrounded answer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.contracts.models import PRODUCT_IDS_PARAM  # noqa: E402
from agent.runtime_helpers.grounding_validator import (  # noqa: E402
    enforce_grounded_constraints,
    product_within_price,
)

RETRIEVED = [
    {"id": "cheap", "name": "Budget Watch", "price": 1200},
    {"id": "mid", "name": "Mid Watch", "price": 1499},
    {"id": "over", "name": "Premium Watch", "price": 38000},
]


def _show_action(*ids):
    return {"action": "SHOW_PRODUCTS", "params": {PRODUCT_IDS_PARAM: list(ids)}}


def test_within_price_floor_and_ceiling():
    assert product_within_price({"price": 1499}, {"max_price": 1500})
    assert not product_within_price({"price": 1501}, {"max_price": 1500})
    assert not product_within_price({"price": 100}, {"min_price": 500})
    assert not product_within_price({"price": None}, {"max_price": 1500})


def test_over_budget_product_is_removed_and_text_regrounded():
    response = {
        "response_text": "Here are laptops: Premium Watch for 38000.",
        "ui_actions": [_show_action("cheap", "over")],
        "intent": "product_search",
    }
    result = enforce_grounded_constraints(response, RETRIEVED, {"max_price": 1500})
    ids = result["ui_actions"][0]["params"][PRODUCT_IDS_PARAM]
    assert ids == ["cheap"]
    assert "38000" not in result["response_text"]
    assert "within your budget" in result["response_text"].lower()


def test_all_over_budget_yields_grounded_no_match():
    response = {
        "response_text": "Here is the Premium Watch for 38000.",
        "ui_actions": [_show_action("over")],
        "intent": "product_search",
    }
    result = enforce_grounded_constraints(response, RETRIEVED, {"max_price": 1500})
    assert result["ui_actions"] == []
    assert "couldn't find" in result["response_text"].lower()
    assert "1500" in result["response_text"]


def test_no_constraint_is_a_noop():
    response = {"response_text": "x", "ui_actions": [_show_action("over")], "intent": "product_search"}
    assert enforce_grounded_constraints(response, RETRIEVED, {}) is response


def test_all_within_budget_is_unchanged():
    response = {"response_text": "ok", "ui_actions": [_show_action("cheap", "mid")], "intent": "product_search"}
    result = enforce_grounded_constraints(response, RETRIEVED, {"max_price": 1500})
    assert result["ui_actions"][0]["params"][PRODUCT_IDS_PARAM] == ["cheap", "mid"]
    assert result["response_text"] == "ok"
