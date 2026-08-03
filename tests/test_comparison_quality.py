"""Regression tests for comparison selection and grounded comparison facts.

Reproduced defects:
  * The overlay showed only image, name and "Brand - price", so a comparison
    carried almost no decision-useful information.
  * Selection ignored the requested item count, did not prefer distinct brands,
    and applied price/stock only loosely, so two variants of one model (or an
    over-budget item) could be compared.

Brand names appear only in these fixtures, never in production logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.products.comparison_facts import (  # noqa: E402
    MAX_TOTAL_FACTS,
    build_comparison_facts,
    comparison_facts_payload,
    comparison_fact_sentence,
)
from agent.products.comparison_selection import select_comparison_products  # noqa: E402


def _product(pid, brand, price, **extra):
    base = {
        "id": pid,
        "name": f"{brand} Model {pid}",
        "brand": brand,
        "price": price,
        "stock": 5,
        "category_name": "Phones",
        "rating": 4.4,
        "review_count": 120,
    }
    base.update(extra)
    return base


MIXED = [
    _product("a1", "Alpha", 30000),
    _product("a2", "Alpha", 28000),
    _product("b1", "Beta", 26000),
    _product("c1", "Gamma", 52000),
]


# --- Selection: count, diversity, hard constraints -------------------------


def test_requested_count_is_honoured_when_enough_valid_items_exist():
    assert len(select_comparison_products(MIXED, requested_count=2)) == 2
    assert len(select_comparison_products(MIXED, requested_count=3)) == 3


def test_distinct_brands_are_preferred_when_no_brand_was_requested():
    selected = select_comparison_products(MIXED, requested_count=2)
    brands = {item["brand"] for item in selected}
    assert len(brands) == 2, brands


def test_explicit_single_brand_allows_same_brand_comparison():
    selected = select_comparison_products(MIXED, requested_count=2, brands=("alpha",))
    assert [item["id"] for item in selected] == ["a1", "a2"]


def test_multiple_requested_brands_are_each_represented_when_available():
    selected = select_comparison_products(MIXED, requested_count=2, brands=("alpha", "beta"))
    assert [item["brand"] for item in selected] == ["Alpha", "Beta"]


def test_single_brand_catalog_falls_back_without_inventing_diversity():
    only_alpha = [_product("a1", "Alpha", 30000), _product("a2", "Alpha", 28000)]
    selected = select_comparison_products(only_alpha, requested_count=2)
    assert len(selected) == 2
    assert {item["brand"] for item in selected} == {"Alpha"}


def test_budget_is_a_hard_constraint():
    selected = select_comparison_products(MIXED, requested_count=4, price_constraints={"max_price": 30000})
    assert all(item["price"] <= 30000 for item in selected)
    assert "c1" not in [item["id"] for item in selected]


def test_unknown_price_is_excluded_when_a_budget_is_active():
    candidates = [_product("p1", "Alpha", None), _product("p2", "Beta", 1000)]
    selected = select_comparison_products(candidates, requested_count=2, price_constraints={"max_price": 5000})
    assert [item["id"] for item in selected] == ["p2"]


def test_unknown_price_is_allowed_when_no_budget_is_active():
    candidates = [_product("p1", "Alpha", None), _product("p2", "Beta", 1000)]
    assert len(select_comparison_products(candidates, requested_count=2)) == 2


def test_out_of_stock_items_are_not_compared():
    candidates = [_product("p1", "Alpha", 1000, stock=0), _product("p2", "Beta", 1200)]
    assert [item["id"] for item in select_comparison_products(candidates, requested_count=2)] == ["p2"]


def test_exclusions_are_applied():
    selected = select_comparison_products(MIXED, requested_count=4, exclusions=("gamma",))
    assert "c1" not in [item["id"] for item in selected]


def test_selection_is_deterministic():
    first = select_comparison_products(MIXED, requested_count=2)
    second = select_comparison_products(MIXED, requested_count=2)
    assert [item["id"] for item in first] == [item["id"] for item in second]


def test_cached_and_uncached_selection_agree_for_equal_inputs():
    """The selector is pure, so a cached replay of the same inputs cannot diverge."""
    live = select_comparison_products(MIXED, requested_count=2, price_constraints={"max_price": 30000})
    replayed = select_comparison_products(list(MIXED), requested_count=2, price_constraints={"max_price": 30000})
    assert [item["id"] for item in live] == [item["id"] for item in replayed]


# --- Grounded facts --------------------------------------------------------


def test_facts_include_published_fields_only():
    facts = build_comparison_facts(_product("a1", "Alpha", 30000))
    labels = [fact["label"] for fact in facts]
    assert "Brand" in labels and "Price" in labels and "Availability" in labels
    assert len(facts) <= MAX_TOTAL_FACTS


def test_missing_price_is_reported_without_inventing_a_value():
    facts = build_comparison_facts({"id": "x", "name": "X", "brand": "Alpha", "stock": 1})
    price = next(fact["value"] for fact in facts if fact["label"] == "Price")
    assert price == "Not published"
    assert "Rating" not in [fact["label"] for fact in facts]


def test_price_is_formatted_and_never_zero_filled():
    facts = build_comparison_facts(_product("a1", "Alpha", 30000, currency="INR"))
    price = next(fact["value"] for fact in facts if fact["label"] == "Price")
    assert price == "₹30,000"


def test_price_without_currency_does_not_invent_inr_for_other_verticals():
    facts = build_comparison_facts(_product("a1", "Alpha", 30000))
    price = next(fact["value"] for fact in facts if fact["label"] == "Price")
    assert price == "30,000"


def test_dangling_sentence_fragments_are_removed():
    facts = build_comparison_facts(
        _product("a1", "Alpha", 1000, description="Lightweight, durable and")
    )
    summary = next((fact["value"] for fact in facts if fact["label"] == "Summary"), "")
    assert not summary.rstrip(".").endswith(" and")


def test_fact_values_are_length_bounded():
    facts = build_comparison_facts(_product("a1", "Alpha", 1000, description="word " * 200))
    assert all(len(fact["value"]) <= 120 for fact in facts)


def test_payload_shape_is_per_product_and_id_keyed():
    payload = comparison_facts_payload(MIXED[:2])
    assert [entry["product_id"] for entry in payload] == ["a1", "a2"]
    assert all(entry["facts"] for entry in payload)


def test_products_without_an_id_are_dropped_from_the_payload():
    assert comparison_facts_payload([{"name": "no id", "brand": "Alpha"}]) == []


def test_response_text_uses_the_same_grounded_facts():
    product = _product("a1", "Alpha", 30000)
    sentence = comparison_fact_sentence(product)
    for fact in build_comparison_facts(product):
        assert fact["value"] in sentence
