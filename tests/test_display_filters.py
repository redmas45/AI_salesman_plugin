"""Resolved hard constraints ride the SHOW_PRODUCTS action as a typed ``filters``.

The Hub half of "phones under 20000 must navigate to a filtered page": a turn's
grounded hard constraints are carried on the display action as a canonical
``filters`` object a host contract can map onto the storefront URL, while the
semantic search text stays in ``search_query``. These tests pin two invariants:

* filters appear ONLY when something grounded resolves (the no-filter path is
  byte-for-byte unchanged), and
* the price number and its operators never leak into ``search_query``.

Fixture brand names ("Northwind"/"Contoso") are made up on purpose - the
grounding must come from the records' own vocabulary, not a hardcoded taxonomy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.products import product_turn_responses as responses  # noqa: E402
from agent.products.display_filters import host_display_filters  # noqa: E402
from agent.products.product_response import (  # noqa: E402
    ProductCatalogFormatter,
    ProductSearchQueryCleaner,
)
from api.contracts.models import ACTION_SHOW_PRODUCTS, ShopResponse, UIAction  # noqa: E402


def _record(record_id, name, brand, family="Smartphones", price=15000):
    return {
        "id": record_id,
        "name": name,
        "brand": brand,
        "price": price,
        "stock": 4,
        "subcategory": family,
        "category": "electronics",
        "rating": 4.5,
        "review_count": 20,
    }


NORTHWIND_PHONES = [
    _record("1", "Northwind Ultra 5", "Northwind", price=18000),
    _record("2", "Northwind Lite 2", "Northwind", price=12000),
]

MIXED_BRANDS = [
    _record("1", "Northwind Ultra 5", "Northwind", price=18000),
    _record("3", "Contoso Prime 9", "Contoso", price=16000),
]


def _display_response(records):
    return {
        "intent": "product_search",
        "confidence": 0.9,
        "response_text": "Here you go.",
        "ui_actions": [
            {
                "action": ACTION_SHOW_PRODUCTS,
                "params": {"product_ids": [str(r["id"]) for r in records]},
            }
        ],
    }


def _run(transcript, records):
    """Drive the same recovery the pipeline runs after the output guardrail."""
    response = _display_response(records)
    responses.ensure_product_display_search_queries(
        response,
        transcript,
        records,
        ProductCatalogFormatter(),
        ProductSearchQueryCleaner(),
    )
    return response["ui_actions"][0]["params"]


# --- The no-filter path stays byte-for-byte unchanged -----------------------


def test_query_only_turn_adds_no_filters_key():
    params = _run("show me some phones", NORTHWIND_PHONES)
    assert "filters" not in params


# --- Price is grounded and lives in filters, not in the query ---------------


def test_budget_only_resolves_max_price_filter():
    params = _run("show me phones under 20000", NORTHWIND_PHONES)
    assert params["filters"] == {"max_price": 20000.0}


def test_price_number_and_operators_never_enter_search_query():
    params = _run("show me phones under 20000", NORTHWIND_PHONES)
    query = params["search_query"].lower()
    for banned in ("under", "20000", "less", "below"):
        assert banned not in query


def test_min_and_max_price_from_a_range():
    params = _run("show me phones between 10000 and 20000", NORTHWIND_PHONES)
    assert params["filters"] == {"min_price": 10000.0, "max_price": 20000.0}


# --- Brand and category are grounded against the records' own vocabulary -----


def test_brand_plus_budget_resolves_both():
    params = _run("show me Northwind phones under 20000", NORTHWIND_PHONES)
    assert params["filters"] == {"brand": "northwind", "max_price": 20000.0}


def test_category_resolves_from_the_records_family():
    params = _run("show me smartphones", NORTHWIND_PHONES)
    assert params["filters"] == {"category": "smartphones"}


def test_combined_constraints_all_present():
    params = _run("show me Northwind smartphones under 20000", NORTHWIND_PHONES)
    assert params["filters"] == {
        "brand": "northwind",
        "category": "smartphones",
        "max_price": 20000.0,
    }


def test_two_competing_brands_do_not_produce_a_single_brand_filter():
    # "Northwind or Contoso" is not one storefront brand filter, so brand is
    # withheld rather than guessed; only the grounded price survives.
    params = _run("show me Northwind or Contoso phones under 20000", MIXED_BRANDS)
    assert params["filters"] == {"max_price": 20000.0}


# --- The helper never invents an ungrounded value ---------------------------


def test_rating_is_omitted_until_a_grounded_parse_exists():
    # No grounded min-rating parse exists upstream, so a stated rating must not
    # silently become a filter (rule 14, "Ask, Never Assume").
    filters = host_display_filters("show me phones rated above 4 stars", NORTHWIND_PHONES)
    assert "min_rating" not in filters


def test_no_records_yields_no_filters():
    assert host_display_filters("phones under 20000", []) == {}


# --- The typed filters dict survives to the final ShopResponse --------------


def test_filters_dict_survives_pydantic_validation():
    params = _run("show me Northwind smartphones under 20000", NORTHWIND_PHONES)
    action = UIAction(action=ACTION_SHOW_PRODUCTS, params=params)
    assert action.params["filters"] == {
        "brand": "northwind",
        "category": "smartphones",
        "max_price": 20000.0,
    }

    shop_response = ShopResponse(
        transcript="show me Northwind smartphones under 20000",
        response_text="Here you go.",
        intent="product_search",
        confidence=0.9,
        ui_actions=[action],
    )
    assert shop_response.ui_actions[0].params["filters"]["max_price"] == 20000.0
