"""A comparison must keep BOTH sides through the retrieval facet filter.

Reproduced defect (local voice probe, 2026-08-05):

    "Compare Samsung Galaxy S26 and iPhone 17."
    -> retrieved_count: 1 (iPhone 17 only), intent product_search,
       response "I found this matching product: iPhone 17"

`requested_product_type_aliases` returned only the first family it recognized, so
a query naming two families resolved to the iPhone alias set alone. The brand+type
conjunction in `products_matching_query_facets` then rejected every Samsung record,
and one of the two products the customer asked about vanished before grounding -
which is also why the turn was never promoted to a comparison (that needs two
exact matches) and instead drove a nonsense host search.

The facets are vertical-neutral, so the same rule is asserted for a neutral
two-family query as well as the reported transcript.
"""

from __future__ import annotations

import pytest

from agent.products.product_matching_lexical import (
    brand_alias_index,
    products_matching_query_facets,
    requested_catalog_brands,
    requested_type_tokens,
)

IPHONE = {"id": "1", "name": "iPhone 17", "brand": "Apple", "category": "electronics", "tags": "phone smartphone"}
GALAXY = {"id": "2", "name": "Samsung Galaxy S26", "brand": "Samsung", "category": "electronics", "tags": "phone smartphone"}
LAPTOP = {"id": "3", "name": "ASUS Gaming Laptop", "brand": "ASUS", "category": "electronics", "tags": "laptop"}
CATALOG = [IPHONE, GALAXY, LAPTOP]

REPORTED_QUERY = "compare samsung galaxy s26 and iphone 17"


def test_both_named_families_are_requested() -> None:
    """Product lines are learned from the catalog, not hardcoded in Hub code."""
    tokens = requested_type_tokens(REPORTED_QUERY, CATALOG)
    assert "iphone" in tokens, "the Apple side was named"
    assert "galaxy" in tokens, "the Samsung side was named and must not be dropped"


def test_product_lines_are_learned_from_the_connected_catalog() -> None:
    aliases = brand_alias_index(CATALOG)
    assert aliases["iphone"] == "apple"
    assert aliases["galaxy"] == "samsung"
    assert aliases["asus"] == "asus"


def test_a_line_token_shared_by_two_brands_is_not_claimed_by_either() -> None:
    shared = CATALOG + [{"id": "4", "name": "Apple Galaxy Watch", "brand": "Apple", "category": "electronics"}]
    assert "galaxy" not in brand_alias_index(shared), "an ambiguous line token must stay unmapped"


def test_both_named_brands_survive_the_facet_filter() -> None:
    assert requested_catalog_brands(REPORTED_QUERY, CATALOG) == ["samsung", "apple"]
    kept = [product["name"] for product in products_matching_query_facets(CATALOG, REPORTED_QUERY)]
    assert kept == ["iPhone 17", "Samsung Galaxy S26"], (
        "a comparison keeps both sides; dropping one is what produced a single-product answer"
    )


def test_an_unrelated_category_is_still_excluded() -> None:
    """Widening to both families must not widen to everything."""
    kept = [product["name"] for product in products_matching_query_facets(CATALOG, REPORTED_QUERY)]
    assert "ASUS Gaming Laptop" not in kept


@pytest.mark.parametrize(
    "query",
    [
        "compare the galaxy and the iphone",
        "which is better, iphone or galaxy",
        "difference between galaxy and iphone",
    ],
)
def test_neutral_two_family_phrasings_keep_both_sides(query: str) -> None:
    kept = {product["name"] for product in products_matching_query_facets(CATALOG, query)}
    assert kept == {"iPhone 17", "Samsung Galaxy S26"}


def test_a_single_family_query_is_unchanged() -> None:
    kept = [product["name"] for product in products_matching_query_facets(CATALOG, "show me iphone 17")]
    assert kept == ["iPhone 17"], "naming one family must still narrow to that family"


def test_navigation_verbs_never_reach_the_storefront_search_box() -> None:
    """Reproduced live: "Take me to an iPod" searched the store for "take ipod".

    The storefront matched that phrase literally and rendered
    `0 results for "take ipod"`. Verbs describe how to act, never what to look
    for, so they must be stripped before a query is handed to a host site.
    """
    from agent.products.product_response import ProductSearchQueryCleaner

    cleaner = ProductSearchQueryCleaner()
    assert cleaner.display_search_query("Take me to an iPod.") == "ipod"
    assert cleaner.display_search_query("Open the electronics section") == "electronics"
    assert cleaner.display_search_query("go to women fashion") == "women fashion"
    # The subject itself is never lost.
    assert cleaner.display_search_query("I want a smartwatch") == "smartwatch"
