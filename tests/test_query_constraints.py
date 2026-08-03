"""Regression tests for the vertical-independent query-constraint model.

These encode the exact failure cases reported from the AI-KART demo:
a "budget of 1500" that was ignored, a recipient ("girlfriend") that was
never parsed, a brand+type request ("Apple Flex smartwatches") that must be
captured as *both* a brand and a product type, and malformed / undecided
inputs ("It's raining air", "What should I buy?") that must be flagged
ambiguous instead of driving a random product match.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.retrieval.query_constraints import (  # noqa: E402
    extract_ecommerce_constraints,
    parse_budget,
)

CATALOG_BRANDS = ("apple", "nova", "acer", "asus", "samsung", "havells")
CATALOG_TYPES = ("smartwatch", "laptop", "phone", "smartphone", "dry fruits", "air fryer")


# --- Budget parsing (slice 4): price is a hard invariant --------------------


def test_budget_of_1500_is_parsed_as_ceiling():
    assert parse_budget("I have a budget of 1500 for my girlfriend") == {"max_price": 1500.0}


def test_budget_variants_all_parse_to_1500():
    for phrase in (
        "my budget is 1500",
        "budget: 1500",
        "budget of ₹1,500",
        "budget of Rs. 1500",
        "budget of INR 1500",
        "around 1500 rupees",
        "I can spend up to 1500",
        "within 1500",
        "at most 1500",
        "1.5k budget",
    ):
        assert parse_budget(phrase) == {"max_price": 1500.0}, phrase


def test_budget_range_and_minimum():
    assert parse_budget("between 1000 and 2000") == {"min_price": 1000.0, "max_price": 2000.0}
    assert parse_budget("over 5000") == {"min_price": 5000.0}


def test_budget_backward_compatible_with_existing_below_form():
    # Locked in by tests/test_sales_relevance_cache.py — must not regress.
    assert parse_budget("Show phones below INR 20,000") == {"max_price": 20000.0}


def test_plain_number_without_budget_context_is_not_a_price():
    # A bare number with no budget/price cue must not become a hard price filter.
    assert parse_budget("I want the iPhone 15") == {}


def test_inventory_counts_and_product_specs_are_not_prices():
    for phrase in (
        "I have 2 phones",
        "I got 3 chargers",
        "at least 8 GB RAM laptop",
        "phone under 2 kg",
        "between 4 and 5 stars",
        "around 3 cameras",
    ):
        assert parse_budget(phrase) == {}, phrase


def test_explicit_wallet_amount_with_currency_remains_a_budget():
    assert parse_budget("I have ₹1500") == {"max_price": 1500.0}
    assert parse_budget("I only have 1.5k") == {"max_price": 1500.0}


# --- Brand + type + recipient (slice 3) -------------------------------------


def test_apple_flex_smartwatch_captures_brand_and_type():
    constraints = extract_ecommerce_constraints(
        "I'm interested in Apple Flex smartwatches",
        catalog_brands=CATALOG_BRANDS,
        catalog_types=CATALOG_TYPES,
    )
    assert constraints.brands == ("apple",)
    assert "smartwatch" in constraints.product_types
    assert constraints.has_explicit_product_request()
    assert not constraints.is_ambiguous


def test_budget_gift_extracts_recipient_and_price():
    constraints = extract_ecommerce_constraints(
        "I have a budget of 1500. Suggest something for my girlfriend",
        catalog_brands=CATALOG_BRANDS,
        catalog_types=CATALOG_TYPES,
    )
    assert constraints.max_price == 1500.0
    assert constraints.recipient == "girlfriend"


def test_brand_only_query_is_not_a_product_type():
    # "Apple products" is a brand request, not a product type named "apple".
    constraints = extract_ecommerce_constraints(
        "I'm looking for Apple products",
        catalog_brands=CATALOG_BRANDS,
        catalog_types=CATALOG_TYPES,
    )
    assert constraints.brands == ("apple",)
    assert constraints.product_types == ()


# --- Ambiguity (slice 7 relies on this signal) ------------------------------


def test_raining_air_is_flagged_ambiguous():
    constraints = extract_ecommerce_constraints(
        "It's raining air. What should I buy? I'm not decided.",
        catalog_brands=CATALOG_BRANDS,
        catalog_types=CATALOG_TYPES,
    )
    assert constraints.is_ambiguous
    assert not constraints.has_explicit_product_request()


def test_what_should_i_buy_is_flagged_ambiguous():
    constraints = extract_ecommerce_constraints(
        "What should I buy?",
        catalog_brands=CATALOG_BRANDS,
        catalog_types=CATALOG_TYPES,
    )
    assert constraints.is_ambiguous
    assert constraints.ambiguity_reason


def test_recipient_only_gift_is_ambiguous_but_keeps_recipient():
    constraints = extract_ecommerce_constraints(
        "I want a gift for my mom",
        catalog_brands=CATALOG_BRANDS,
        catalog_types=CATALOG_TYPES,
    )
    assert constraints.recipient == "mom"
    assert constraints.occasion == "gift"
    assert constraints.is_ambiguous  # no brand/type/budget -> ask one clarifying question


# --- Follow-up references (slice 9 relies on this signal) --------------------


def test_correction_followup_is_detected():
    constraints = extract_ecommerce_constraints(
        "No, I was just looking for the flex watch",
        catalog_brands=CATALOG_BRANDS,
        catalog_types=CATALOG_TYPES,
    )
    assert constraints.is_followup
