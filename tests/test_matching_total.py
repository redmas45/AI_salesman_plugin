"""Maya's spoken result total is a deterministic constrained catalog count.

Reported risk: ``matching_total`` was ``len(retrieved_products)`` - the RAG
candidate window (RAG_TOP_N), not the number of catalog records satisfying the
turn's hard constraints. So Maya could say "I found 3" when a dozen matched, or
overclaim a whole-catalog total from a sample (rules §14). These tests pin that
the count now measures the catalog through the same conjunctive validator a
filtered storefront page would apply, and that a no-constraint turn triggers no
catalog scan and keeps its old behaviour.

Fixture brand names ("Northwind"/"Contoso") are made up on purpose: the count
must ground against the records' own vocabulary, never a hardcoded taxonomy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.products.matching_total import (  # noqa: E402
    annotate_matching_total,
    constrained_catalog_total,
    response_matching_total,
)
from agent.products.product_response import ProductCatalogFormatter  # noqa: E402


def _cat(record_id, name, brand, price, stock=5):
    return {
        "id": record_id,
        "name": name,
        "brand": brand,
        "price": price,
        "stock": stock,
        "subcategory": "phones",
        "category": "electronics",
        "rating": 4.2,
        "review_count": 10,
    }


# Full tenant catalog: 5 Northwind phones, 3 Contoso phones.
CATALOG = [
    _cat("1", "Northwind Phone A", "Northwind", 12000),
    _cat("2", "Northwind Phone B", "Northwind", 18000),
    _cat("3", "Northwind Phone C", "Northwind", 25000),
    _cat("4", "Northwind Phone D", "Northwind", 9000),
    _cat("5", "Northwind Phone E", "Northwind", 30000),
    _cat("6", "Contoso Phone A", "Contoso", 11000),
    _cat("7", "Contoso Phone B", "Contoso", 21000),
    _cat("8", "Contoso Phone C", "Contoso", 15000),
]

# The RAG window the turn actually retrieved - deliberately smaller than the
# catalog so a window-sized count would be visibly wrong.
WINDOW = CATALOG[:2]


def _load_catalog():
    return list(CATALOG)


# --- The count measures the catalog, not the retrieval window ----------------


def test_brand_constrained_count_is_the_catalog_brand_count_not_the_window():
    total = constrained_catalog_total("show me Northwind phones", WINDOW, None, _load_catalog)
    assert total == (5, False)  # five Northwind phones in the catalog, not 2 in the window


def test_budget_count_counts_only_records_under_the_budget():
    total = constrained_catalog_total("show me phones under 15000", WINDOW, None, _load_catalog)
    # ids 1 (12000), 4 (9000), 6 (11000), 8 (15000) satisfy <= 15000.
    assert total == (4, False)


def test_authoritative_price_constraint_overrides_when_supplied():
    total = constrained_catalog_total(
        "show me phones", WINDOW, {"max_price": 12000.0}, _load_catalog
    )
    # ids 1 (12000), 4 (9000), 6 (11000) satisfy <= 12000.
    assert total == (3, False)


# --- No hard constraint: no catalog scan, behaviour unchanged ----------------


def test_no_constraint_turn_does_no_catalog_work_and_records_nothing():
    calls = {"n": 0}

    def counting_loader():
        calls["n"] += 1
        return list(CATALOG)

    response = {"ui_actions": []}
    annotate_matching_total(response, "show me what you have", WINDOW, None, counting_loader)
    assert "matching_total" not in response
    assert calls["n"] == 0  # the catalog was never scanned


def test_response_total_falls_back_to_displayed_when_unset():
    assert response_matching_total({}, WINDOW) == (2, False)


# --- annotate + composer wiring ---------------------------------------------


def test_annotate_records_the_constrained_total_on_the_response():
    response = {"ui_actions": []}
    annotate_matching_total(response, "show me Northwind phones", WINDOW, None, _load_catalog)
    assert response["matching_total"] == 5
    assert response["matching_total_is_lower_bound"] is False


def test_composer_states_matched_total_and_displayed_count():
    # Fewer displayed than matched -> "I found N ... showing M here".
    text = ProductCatalogFormatter().search_text(WINDOW, matching_total=5)
    assert "I found 5 matching products" in text
    assert "I'm showing 2 here" in text


def test_capped_scan_is_phrased_as_a_lower_bound_not_an_exact_total():
    # Cap honesty: a bounded count is rendered "N+", never asserted exact.
    text = ProductCatalogFormatter().search_text(
        WINDOW, matching_total=5000, matching_total_is_lower_bound=True
    )
    assert "I found 5000+ matching products" in text


def test_count_never_falls_below_the_displayed_count():
    # Even if a stale smaller total is passed, the claim cannot undercut the page.
    text = ProductCatalogFormatter().search_text(WINDOW, matching_total=1)
    assert "I found 2 matching products" in text
