"""Deterministic catalog operations: aggregates, exact counts, hard filters.

Reproduces the reported failures before the fix:

* "cheapest item in Fashion Women" answered with the globally cheapest product
  because the minimum-price selection ran before the category filter.
* "the cheapest phone and take me there" answered one of the two requirements.
* best-rated picked a record whose rating had no review evidence behind it, and
  ties resolved differently between runs.
* counts were computed from a randomly sampled retrieval window and presented as
  whole-catalog truth.

The catalog fixture uses neutral, invented names so the assertions prove generic
behaviour rather than one demo store's taxonomy.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

ECOMMERCE_TEST_SITE_ID = "ecommerce_site"

# Deliberately arranged so that the globally cheapest record ("Borel Steel
# Bottle", 199) is NOT in the Fashion Women category, and the globally
# best-rated record by raw rating ("Corvi Trial Unit", 5.0) has no reviews.
CATALOG = [
    {
        "id": "1", "name": "Aster Slim Kurta", "brand": "Aster",
        "category_name": "Fashion Women", "price": 499.0,
        "rating": 4.2, "review_count": 18, "stock": 5, "variant_id": 101,
    },
    {
        "id": "2", "name": "Aster Cotton Top", "brand": "Aster",
        "category_name": "Fashion Women", "price": 1299.0,
        "rating": 4.8, "review_count": 9, "stock": 3, "variant_id": 102,
    },
    {
        "id": "3", "name": "Borel Steel Bottle", "brand": "Borel",
        "category_name": "Home Kitchen", "price": 199.0,
        "rating": 4.9, "review_count": 40, "stock": 12, "variant_id": 103,
    },
    {
        "id": "4", "name": "Corvi Smartphone X1", "brand": "Corvi",
        "category_name": "Electronics", "price": 42999.0,
        "rating": 4.4, "review_count": 120, "stock": 2, "variant_id": 104,
    },
    {
        "id": "5", "name": "Corvi Smartphone X9", "brand": "Corvi",
        "category_name": "Electronics", "price": 72999.0,
        "rating": 4.7, "review_count": 80, "stock": 4, "variant_id": 105,
    },
    {
        "id": "6", "name": "Corvi Trial Unit", "brand": "Corvi",
        "category_name": "Electronics", "price": 91000.0,
        "rating": 5.0, "review_count": 0, "stock": 1, "variant_id": 106,
    },
    {
        "id": "7", "name": "Delta Smartphone Lite", "brand": "Delta",
        "category_name": "Electronics", "price": 42999.0,
        "rating": 4.4, "review_count": 120, "stock": 6, "variant_id": 107,
    },
    {
        "id": "8", "name": "Aster Sold Out Dress", "brand": "Aster",
        "category_name": "Fashion Women", "price": 149.0,
        "rating": 4.9, "review_count": 30, "stock": 0, "variant_id": 108,
    },
]


def _records(**_filters):
    return [dict(record) for record in CATALOG]


# --- Pure operation layer ---------------------------------------------------


def test_hard_filters_are_conjunctive_and_run_before_ranking():
    from agent.catalog import catalog_operations as ops
    from agent.retrieval.query_constraints import QueryConstraints

    constraints = QueryConstraints(
        raw_query="cheapest corvi smartphone under 50000",
        brands=("corvi",),
        product_types=("smartphone",),
        max_price=50000.0,
    )
    selection = ops.select_records(_records(), constraints)

    assert [record["id"] for record in selection.records] == ["4"], (
        "brand AND type AND price must all hold; a record satisfying only one is not a match"
    )


def test_out_of_stock_records_never_reach_an_aggregate():
    from agent.catalog import catalog_operations as ops
    from agent.retrieval.query_constraints import QueryConstraints

    selection = ops.select_records(
        _records(),
        QueryConstraints(raw_query="cheapest fashion women item"),
        category_names=("Fashion Women",),
    )
    cheapest = ops.aggregate_records(selection, ops.AGGREGATE_CHEAPEST)

    assert "8" not in [record["id"] for record in selection.records]
    assert cheapest[0]["id"] == "1"


def test_best_rated_requires_review_evidence():
    from agent.catalog import catalog_operations as ops
    from agent.retrieval.query_constraints import QueryConstraints

    selection = ops.select_records(_records(), QueryConstraints(raw_query="best rated"))
    best = ops.aggregate_records(selection, ops.AGGREGATE_BEST_RATED)

    assert best, "a catalog with reviewed records must produce a best-rated answer"
    assert best[0]["id"] != "6", "a 5.0 rating with zero reviews is not review evidence"
    assert best[0]["id"] == "3"


def test_aggregate_tie_breaking_is_stable_under_input_order():
    from agent.catalog import catalog_operations as ops
    from agent.retrieval.query_constraints import QueryConstraints

    constraints = QueryConstraints(raw_query="best rated smartphone", product_types=("smartphone",))
    forward = ops.aggregate_records(
        ops.select_records(_records(), constraints), ops.AGGREGATE_BEST_RATED
    )
    reversed_input = ops.aggregate_records(
        ops.select_records(list(reversed(_records())), constraints), ops.AGGREGATE_BEST_RATED
    )

    # Records 4 and 7 share rating 4.4 and review_count 120 and price 42999.
    assert [record["id"] for record in forward] == [record["id"] for record in reversed_input]


def test_catalog_facts_distinguish_records_variants_and_stock_units():
    from agent.catalog import catalog_operations as ops
    from agent.retrieval.query_constraints import QueryConstraints

    selection = ops.select_records(
        _records(),
        QueryConstraints(raw_query="smartphones", product_types=("smartphone",)),
    )

    assert selection.facts.matching_records == 3
    assert selection.facts.variant_count == 3
    assert selection.facts.stock_units == 12
    assert selection.facts.truncated is False


def test_truncated_scan_is_reported_and_never_claimed_as_exact():
    from agent.catalog import catalog_operations as ops
    from agent.retrieval.query_constraints import QueryConstraints

    many = [dict(CATALOG[3], id=str(1000 + index)) for index in range(ops.CATALOG_SCAN_CAP + 5)]
    selection = ops.select_records(many, QueryConstraints(raw_query="smartphones"))

    assert selection.facts.truncated is True
    assert ops.count_phrase(selection.facts, "smartphone").startswith("at least")


def test_inventory_type_count_never_reports_a_bounded_scan_as_exact():
    import logging
    import time

    from agent.responses.inventory_responses import inventory_type_count_response

    products = [
        {
            "id": str(index),
            "name": f"Example Smartphone {index}",
            "category_name": "Electronics",
            "stock": 1,
        }
        for index in range(5001)
    ]
    requested_limits: list[int] = []

    def load_products(_site_id: str, limit: int) -> list[dict]:
        requested_limits.append(limit)
        return products

    result = inventory_type_count_response(
        "site",
        "How many smartphones do you have?",
        "smartphone",
        True,
        {},
        time.perf_counter(),
        load_products=load_products,
        matching_products=lambda rows, _term: rows,
        available_categories=lambda _rows: ["Electronics"],
        synthesize_b64=lambda _text: "",
        ai_log=lambda _role, _value: None,
        elapsed_ms=lambda _started: 0.0,
        recoverable_errors=(RuntimeError,),
        logger=logging.getLogger(__name__),
    )

    assert requested_limits == [5001]
    assert result["response_text"].startswith("I found at least 5000 smartphones in stock")


def test_category_detection_is_data_driven_not_hardcoded():
    from agent.catalog import catalog_operations as ops

    assert ops.matching_category_names("cheapest item in fashion women", _records()) == (
        "Fashion Women",
    )
    assert ops.matching_category_names("cheapest item", _records()) == ()


# --- Orchestrated turn behaviour -------------------------------------------


@pytest.fixture
def deterministic_catalog(monkeypatch):
    from agent import orchestrator

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: _records())
    monkeypatch.setattr(orchestrator, "get_catalog_records", lambda site_id, **kwargs: _records())
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("a deterministic catalog operation must not call the LLM")
        ),
    )
    return orchestrator


def _run(orchestrator, text, **kwargs):
    return orchestrator.run(
        site_id=ECOMMERCE_TEST_SITE_ID,
        text_input=text,
        skip_tts=True,
        **kwargs,
    )


def _actioned_ids(result):
    ids = []
    for action in result.get("ui_actions") or []:
        params = action.get("params") or {}
        ids.extend(str(pid) for pid in params.get("product_ids") or [])
        if params.get("product_id"):
            ids.append(str(params["product_id"]))
    return ids


def test_cheapest_in_a_category_filters_category_before_selecting_minimum_price(
    deterministic_catalog,
):
    result = _run(deterministic_catalog, "What is the cheapest item in Fashion Women?")

    assert _actioned_ids(result) == ["1"], (
        "the cheapest Fashion Women record is 1 (499); 3 (199) is Home Kitchen"
    )
    assert "Aster Slim Kurta" in result["response_text"]
    assert "Borel Steel Bottle" not in result["response_text"]


def test_cheapest_phone_under_budget_never_exceeds_the_ceiling(deterministic_catalog):
    result = _run(deterministic_catalog, "cheapest smartphone under 50000")

    assert _actioned_ids(result) == ["4"]
    assert "72,999" not in result["response_text"] and "72999" not in result["response_text"]


def test_cheapest_plus_take_me_there_satisfies_both_requirements(deterministic_catalog):
    result = _run(deterministic_catalog, "Show me the cheapest smartphone and take me there")

    action_names = {str(action.get("action")) for action in result["ui_actions"]}
    # Either action moves the customer; opening the winning record is the grounded
    # form because it cannot navigate to a page the aggregate did not identify.
    assert action_names & {"NAVIGATE_TO", "SHOW_PRODUCT_DETAIL"}, (
        "the customer explicitly asked to be taken there"
    )
    assert "4" in _actioned_ids(result), "the aggregate requirement must also be answered"


def test_most_expensive_uses_the_maximum_of_the_validated_set(deterministic_catalog):
    result = _run(deterministic_catalog, "What is the most expensive smartphone you have?")

    assert _actioned_ids(result) == ["5"], "6 is not a smartphone; 5 is the dearest smartphone"


def test_best_rated_answer_is_grounded_in_review_backed_records(deterministic_catalog):
    result = _run(deterministic_catalog, "Which is your best rated item?")

    # 6 carries a raw 5.0 with zero reviews; 3 is the best rating backed by reviews.
    assert _actioned_ids(result) == ["3"]
    assert "Corvi Trial Unit" not in result["response_text"]


def test_best_rated_within_a_type_uses_that_types_review_evidence(deterministic_catalog):
    result = _run(deterministic_catalog, "Which is your best rated smartphone?")

    assert _actioned_ids(result) == ["5"], "4.7 from 80 reviews beats 4.4 from 120"
    assert "80 reviews" in result["response_text"]


def test_count_reports_exact_matching_records_not_a_retrieval_window(
    deterministic_catalog, monkeypatch
):
    """The window loader must not be the source of a whole-catalog claim."""
    seen_limits = []

    def sampled_window(site_id, limit=1000):
        seen_limits.append(limit)
        return _records()[:2]

    monkeypatch.setattr(deterministic_catalog, "get_all_products", sampled_window)

    result = _run(deterministic_catalog, "How many smartphones do you have?")

    assert "3" in result["response_text"], (
        "3 smartphone records match; the 2-row sampled window must not decide the count"
    )


def test_aggregate_turn_is_not_cached(deterministic_catalog, monkeypatch):
    stored = []
    monkeypatch.setattr(
        deterministic_catalog,
        "_maybe_store_answer_cache",
        lambda *args, **kwargs: stored.append(kwargs),
    )

    _run(deterministic_catalog, "What is the cheapest item in Fashion Women?")

    assert stored == [], "a deterministic aggregate is recomputed, never replayed from cache"
