"""Confirmed-outcome wording and leak-free capability notes.

`confirmed_action_success_text` is what the widget speaks once it has verified an
action, replacing the tentative "I'll try to ..." promise the server emits. The
capability note is what the shopper hears when an action was removed; it must never
expose an internal action token such as ADD_TO_CART.
"""

from __future__ import annotations

from agent.action_helpers.capabilities import action_filter_response_note
from agent.responses.action_confirmation import confirmed_action_success_text

PRODUCTS = {
    "p1": {"id": "p1", "name": "Samsung Galaxy S26"},
    "p2": {"id": "p2", "name": "iPhone 17"},
}


def test_verified_cart_add_names_the_product() -> None:
    actions = [{"action": "ADD_TO_CART", "params": {"product_id": "p1"}}]
    text = confirmed_action_success_text("I'll try to add Samsung Galaxy S26 to your cart now.", actions, PRODUCTS)
    assert text == "Samsung Galaxy S26 is now in your cart."


def test_verified_cart_add_respects_quantity() -> None:
    actions = [{"action": "ADD_TO_CART", "params": {"product_id": "p1", "quantity": 2}}]
    assert confirmed_action_success_text("", actions, PRODUCTS) == "2 x Samsung Galaxy S26 are now in your cart."


def test_verified_cart_add_without_a_known_record_stays_generic() -> None:
    actions = [{"action": "ADD_TO_CART", "params": {"product_id": "unknown"}}]
    assert confirmed_action_success_text("", actions, PRODUCTS) == "That item is now in your cart."


def test_verified_product_navigation_names_the_record() -> None:
    actions = [{"action": "NAVIGATE_TO", "params": {"page": "/p/2", "product_id": "p2"}}]
    assert confirmed_action_success_text("I'll try to open iPhone 17.", actions, PRODUCTS) == "I opened iPhone 17."


def test_verified_section_navigation_humanizes_the_route() -> None:
    actions = [{"action": "NAVIGATE_TO", "params": {"page": "/fashion-women"}}]
    assert confirmed_action_success_text("I'll try to open fashion women.", actions, {}) == "I opened fashion women."


def test_navigation_to_an_opaque_url_stays_generic() -> None:
    actions = [{"action": "NAVIGATE_TO", "params": {"page": "https://example.test/x"}}]
    assert confirmed_action_success_text("", actions, {}) == "I opened that page for you."


def test_sort_and_filter_confirm_the_updated_results() -> None:
    assert (
        confirmed_action_success_text("", [{"action": "SORT_PRODUCTS", "params": {"sort_by": "price_asc"}}], {})
        == "I updated the results on the page."
    )


def test_display_actions_have_no_confirmation_override() -> None:
    # A search/compare answer already lists the records; its wording is independently
    # true and must not be replaced by a generic confirmation.
    for name in ("SHOW_PRODUCTS", "SHOW_COMPARISON", "SHOW_ENTITIES"):
        actions = [{"action": name, "params": {"product_ids": ["p1", "p2"]}}]
        assert confirmed_action_success_text("I found 2 products.", actions, PRODUCTS) == ""


def test_no_outcome_action_returns_empty() -> None:
    assert confirmed_action_success_text("Hi, how can I help?", [], PRODUCTS) == ""


def test_removed_cart_action_note_does_not_leak_the_action_token() -> None:
    report = {
        "status": "changed",
        "actions": [],
        "removed_actions": [
            {"action": "ADD_TO_CART", "reason": "unsupported_action", "message": "ADD_TO_CART is not currently available for this client website."}
        ],
    }
    note = action_filter_response_note(report)
    assert "ADD_TO_CART" not in note
    assert "cart" in note.lower()
    assert "guide you instead" in note
