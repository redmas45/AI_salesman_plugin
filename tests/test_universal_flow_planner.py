"""Universal transactional flow planner tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import capabilities
from agent.flow_planner import plan_universal_flow


def _client_with_actions(actions: dict):
    return {
        "site_id": "demo",
        "vertical_config": {
            "actions": actions,
        },
    }


def test_ecommerce_buy_specific_item_adds_to_cart(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "get_allowed_actions", lambda site_id: {"ADD_TO_CART"})
    monkeypatch.setattr(
        "agent.flow_planner.get_client_detail",
        lambda site_id: _client_with_actions({"ADD_TO_CART": {"type": "click", "label": "Add to cart"}}),
    )

    result = plan_universal_flow(
        site_id="shop_demo",
        transcript="buy the red iphone 15",
        retrieved_items=[
            {"id": "p1", "name": "Samsung S24"},
            {"id": "p2", "name": "Red iPhone 15"},
        ],
        ecommerce_runtime=True,
    )

    assert result is not None
    assert result["intent"] == "add_to_cart"
    assert result["ui_actions"] == [{"action": "ADD_TO_CART", "params": {"product_id": "p2"}}]
    assert "I'll try" in result["response_text"]


def test_ecommerce_buy_ambiguous_item_asks_one_clarification(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "get_allowed_actions", lambda site_id: {"ADD_TO_CART"})
    monkeypatch.setattr(
        "agent.flow_planner.get_client_detail",
        lambda site_id: _client_with_actions({"ADD_TO_CART": {"type": "click", "label": "Add to cart"}}),
    )

    result = plan_universal_flow(
        site_id="shop_demo",
        transcript="add one to cart",
        retrieved_items=[
            {"id": "p1", "name": "iPhone 15"},
            {"id": "p2", "name": "Samsung S24"},
        ],
        ecommerce_runtime=True,
    )

    assert result is not None
    assert result["flow_state"] == "collect_target"
    assert result["ui_actions"] == []
    assert "Which one" in result["response_text"]


def test_ecommerce_buy_recommendation_stays_in_product_discovery(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "get_allowed_actions", lambda site_id: {"ADD_TO_CART"})
    monkeypatch.setattr(
        "agent.flow_planner.get_client_detail",
        lambda site_id: _client_with_actions({"ADD_TO_CART": {"type": "click", "label": "Add to cart"}}),
    )

    result = plan_universal_flow(
        site_id="shop_demo",
        transcript="I want to buy a phone. Can you recommend me something?",
        retrieved_items=[
            {"id": "p1", "name": "OPPO Active Android Budget 9"},
            {"id": "p2", "name": "Realme Pro Android Budget 2"},
        ],
        ecommerce_runtime=True,
    )

    assert result is None


def test_quote_flow_uses_discovered_action_contract(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "get_allowed_actions", lambda site_id: {"START_QUOTE"})
    monkeypatch.setattr(
        "agent.flow_planner.get_client_detail",
        lambda site_id: _client_with_actions(
            {
                "START_QUOTE": {
                    "type": "sequence",
                    "label": "Check premium",
                    "field_schema": [{"param": "city", "label": "City"}],
                }
            }
        ),
    )

    result = plan_universal_flow(
        site_id="quote_demo",
        transcript="calculate premium for myself",
        retrieved_items=[],
        ecommerce_runtime=False,
    )

    assert result is not None
    assert result["intent"] == "quote"
    assert result["ui_actions"] == [{"action": "START_QUOTE", "params": {}}]


def test_generic_buy_opens_entity_when_no_purchase_flow_is_mapped(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "get_allowed_actions", lambda site_id: {"OPEN_ENTITY_DETAIL"})
    monkeypatch.setattr(
        "agent.flow_planner.get_client_detail",
        lambda site_id: _client_with_actions({"OPEN_ENTITY_DETAIL": {"type": "click", "label": "View details"}}),
    )

    result = plan_universal_flow(
        site_id="records_demo",
        transcript="buy the premium cabin option",
        retrieved_items=[
            {"id": "cabin-basic", "title": "Basic cabin"},
            {"id": "cabin-premium", "title": "Premium cabin option"},
        ],
        ecommerce_runtime=False,
    )

    assert result is not None
    assert result["ui_actions"] == [{"action": "OPEN_ENTITY_DETAIL", "params": {"entity_id": "cabin-premium"}}]


def test_ecommerce_page_request_does_not_become_purchase_flow(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "get_allowed_actions", lambda site_id: {"ADD_TO_CART", "OPEN_POLICY"})
    monkeypatch.setattr(
        "agent.flow_planner.get_client_detail",
        lambda site_id: _client_with_actions(
            {
                "ADD_TO_CART": {"type": "click", "label": "Add to cart"},
                "OPEN_POLICY": {"type": "navigate", "path": "/faq"},
            }
        ),
    )

    result = plan_universal_flow(
        site_id="shop_demo",
        transcript="I need to see the FAQ page.",
        retrieved_items=[{"id": "p1", "name": "NOVA Slip-On Shoes"}],
        ecommerce_runtime=True,
    )

    assert result is None


def test_ecommerce_buying_guidance_does_not_add_item_to_cart(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "get_allowed_actions", lambda site_id: {"ADD_TO_CART"})
    monkeypatch.setattr(
        "agent.flow_planner.get_client_detail",
        lambda site_id: _client_with_actions({"ADD_TO_CART": {"type": "click", "label": "Add to cart"}}),
    )

    result = plan_universal_flow(
        site_id="shop_demo",
        transcript="Why should I buy the NOVA Daily Phone?",
        retrieved_items=[{"id": "p1", "name": "NOVA Daily Phone"}],
        ecommerce_runtime=True,
    )

    assert result is None
