"""Regression tests for slice 10: constraint-aware answer cache keys.

Same wording with different budgets must not share a cached answer, and a
budget-scoped answer must not serve an unbudgeted query (or vice versa).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.cache.answer_cache import (  # noqa: E402
    _price_constraint_matches,
    _semantic_constraints_match,
    normalize_question,
)


def test_different_budgets_produce_different_keys():
    assert normalize_question("show phones under 20000") != normalize_question("show phones under 50000")


def test_budget_key_carries_price_signature():
    assert "price max20000" in normalize_question("show phones under 20000")


def test_unbudgeted_query_has_no_price_signature():
    assert "price" not in normalize_question("show me some phones")


def test_same_wording_same_budget_is_stable():
    assert normalize_question("phones under 20000") == normalize_question("phones under 20000")


def test_semantic_guard_rejects_mismatched_budget():
    cached = normalize_question("phones under 50000")
    assert not _price_constraint_matches("phones under 20000", cached)


def test_semantic_guard_accepts_matching_budget():
    cached = normalize_question("phones under 20000")
    assert _price_constraint_matches("phones under 20000", cached)


def test_semantic_guard_rejects_budget_scoped_answer_for_unbudgeted_query():
    cached = normalize_question("phones under 20000")
    assert not _price_constraint_matches("show me phones", cached)


def test_semantic_guard_rejects_different_brand_or_product_type():
    apple_row = {
        "question": "Show me Apple smartwatches under 20000",
        "normalized_question": normalize_question("Show me Apple smartwatches under 20000"),
    }
    assert not _semantic_constraints_match("Recommend Samsung smartwatches under 20000", apple_row)
    assert not _semantic_constraints_match("Recommend Apple laptops under 20000", apple_row)


def test_semantic_guard_accepts_safe_paraphrase_with_same_anchors():
    cached_row = {
        "question": "Show me Apple smartwatches under 20000",
        "normalized_question": normalize_question("Show me Apple smartwatches under 20000"),
    }
    assert _semantic_constraints_match("Can you recommend Apple smartwatches below 20k?", cached_row)


def test_price_signature_survives_a_long_normalized_question():
    key = normalize_question(f"{'detail ' * 120} phones under 20000")
    assert key.startswith("price max20000 ")
    assert len(key) <= 500


def test_price_guard_reads_legacy_suffix_keys():
    assert _price_constraint_matches("phones under 20000", "phones under 20000 price max20000")
