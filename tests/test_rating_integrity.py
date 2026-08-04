"""Regressions for unrated products never being presented as "0/5".

Reported defect: curated flagship records ship with `rating: null` and
`review_count: null`, Hub ingestion coerced both to zero, and the comparison
formatter rendered that zero as a real score. A product nobody has reviewed was
therefore advertised as the worst possible rating.

"Not rated" and "rated zero" are different claims. The pipeline must keep them
different from source data through ingestion to the spoken answer and overlay.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ingestion_helpers.ingestion_product_rows import optional_rating, optional_review_count  # noqa: E402
from agent.prompts.ecommerce import _product_line  # noqa: E402
from agent.products.comparison_facts import build_comparison_facts, rating_text  # noqa: E402
from db.knowledge_base.knowledge_items import _product_attributes  # noqa: E402


def _product(**extra):
    base = {"id": "p1", "name": "Example", "brand": "Alpha", "price": 1000, "stock": 3}
    base.update(extra)
    return base


# --- Formatting: a zero or absent score is never a rating claim --------------


def test_zero_rating_is_not_presented_as_a_score():
    assert rating_text(_product(rating=0, review_count=0)) == ""


def test_zero_rating_with_reviews_is_still_not_a_score():
    """A zero score with a review count is unusable source data, not a rating."""
    assert rating_text(_product(rating=0.0, review_count=12)) == ""


def test_missing_rating_produces_no_rating_fact():
    facts = build_comparison_facts(_product(rating=None, review_count=None))
    assert "Rating" not in [fact["label"] for fact in facts]


def test_zero_rating_produces_no_rating_fact():
    facts = build_comparison_facts(_product(rating=0, review_count=0))
    assert "Rating" not in [fact["label"] for fact in facts]
    assert "0/5" not in " ".join(fact["value"] for fact in facts)


def test_real_rating_is_still_reported():
    assert rating_text(_product(rating=4.5, review_count=120)) == "4.5/5 (120 reviews)"


def test_rating_without_reviews_is_reported_without_a_count():
    assert rating_text(_product(rating=4.2, review_count=None)) == "4.2/5"


def test_unrated_product_is_not_described_as_zero_in_the_llm_context():
    line = _product_line(_product(rating=None, review_count=None, description="Demo"))
    assert "Rating:" not in line
    assert "0/5" not in line


def test_knowledge_attributes_preserve_unrated_values_as_null():
    attributes = _product_attributes(_product(rating=None, review_count=None), "Electronics", "Alpha")
    assert attributes["rating"] is None
    assert attributes["review_count"] is None


# --- Ingestion: missing source data must stay missing ------------------------


def test_ingestion_preserves_a_missing_rating_as_null():
    assert optional_rating({"name": "x"}) is None
    assert optional_rating({"rating": None}) is None
    assert optional_rating({"rating": ""}) is None


def test_ingestion_preserves_a_real_rating():
    assert optional_rating({"rating": 4.4}) == 4.4
    assert optional_rating({"rating": "4.4"}) == 4.4


def test_ingestion_rejects_an_out_of_range_rating():
    """A 0-5 scale cannot hold 9.9; keep it unrated rather than invent a score."""
    assert optional_rating({"rating": 9.9}) is None
    assert optional_rating({"rating": -1}) is None


def test_ingestion_treats_zero_rating_as_unrated():
    assert optional_rating({"rating": 0}) is None


def test_ingestion_preserves_a_missing_review_count_as_null():
    assert optional_review_count({"name": "x"}) is None
    assert optional_review_count({"review_count": None}) is None


def test_ingestion_preserves_a_real_review_count():
    assert optional_review_count({"review_count": 120}) == 120
    assert optional_review_count({"reviewCount": "120"}) == 120


def test_ingestion_treats_negative_review_counts_as_missing():
    assert optional_review_count({"review_count": -5}) is None
