""""Premium" and "budget" resolved from tenant data, never from model names.

Reported (2026-08-07): "Compare Apple Premium versus Samsung Premium" returned
`Apple Fast Charger` against `Samsung Smartphone 2`. "Premium" is a ranking
operator over a tier scale, not a slot value, so it must select the top of each
brand's range among records that already satisfy brand and family.

The tier signal comes from whatever the tenant publishes; price is the last
resort and the answer says so, because price alone is a weak proxy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.nlu.frame import RANK_MIN, parse_frame  # noqa: E402
from agent.nlu.schema import build_schema  # noqa: E402
from agent.products.tier_ranking import (  # noqa: E402
    BASIS_PRICE,
    BASIS_PUBLISHED_TIER,
    BASIS_RATING,
    frame_requests_tier,
    published_tier_score,
    rank_by_tier,
    tier_basis_note,
    top_record_per_brand,
)


def _record(record_id, name, brand, price, family="Electronics > Smartphones", **extra):
    base = {"id": record_id, "name": name, "brand": brand, "price": price, "subcategory": family}
    base.update(extra)
    return base


def test_a_tier_word_is_read_as_a_ranking_operator_not_a_product():
    schema = build_schema([_record("p", "Alpha Phone", "Alpha", 1)])
    frame = parse_frame("Compare Alpha premium versus Beta premium", schema)
    assert frame_requests_tier(frame)
    assert "premium" not in " ".join(frame.constraint_terms()).lower()


def test_a_published_flagship_marker_outranks_a_dearer_record():
    records = [
        _record("a", "Alpha Everyday Phone", "Alpha", 90000),
        _record("b", "Alpha Flagship Phone", "Alpha", 60000),
    ]
    ranking = rank_by_tier(records)
    assert ranking.basis == BASIS_PUBLISHED_TIER
    assert ranking.records[0]["id"] == "b"


def test_a_published_tag_counts_as_a_tier_marker():
    records = [
        _record("a", "Alpha One", "Alpha", 10, tags=["entry-level"]),
        _record("b", "Alpha Two", "Alpha", 20, tags=["premium"]),
    ]
    assert published_tier_score(records[1]) == 1
    assert published_tier_score(records[0]) == -1
    assert rank_by_tier(records).records[0]["id"] == "b"


def test_ratings_decide_when_no_tier_is_published():
    records = [
        _record("a", "Alpha One", "Alpha", 90000, rating=3.9, review_count=10),
        _record("b", "Alpha Two", "Alpha", 30000, rating=4.8, review_count=200),
    ]
    ranking = rank_by_tier(records)
    assert ranking.basis == BASIS_RATING
    assert ranking.records[0]["id"] == "b"


def test_price_is_the_last_resort_and_is_declared():
    records = [_record("a", "Alpha One", "Alpha", 100), _record("b", "Alpha Two", "Alpha", 900)]
    ranking = rank_by_tier(records)
    assert ranking.basis == BASIS_PRICE
    assert ranking.records[0]["id"] == "b"
    assert ranking.price_only
    assert "price" in tier_basis_note(ranking).lower()


def test_a_justified_ranking_adds_no_caveat():
    records = [_record("a", "Alpha Flagship", "Alpha", 1), _record("b", "Alpha Basic", "Alpha", 2)]
    assert tier_basis_note(rank_by_tier(records)) == ""


def test_budget_ranks_from_the_other_end():
    records = [_record("a", "Alpha Flagship", "Alpha", 90000), _record("b", "Alpha Basic", "Alpha", 9000)]
    assert rank_by_tier(records, direction=RANK_MIN).records[0]["id"] == "b"


def test_the_reported_comparison_picks_one_flagship_per_brand():
    """The exact defect: a charger was compared against a phone."""
    records = [
        _record("c1", "Beta Fast Charger", "Beta", 1399, family="Electronics > Chargers"),
        _record("p1", "Alpha Elite Flagship Phone", "Alpha", 97199),
        _record("p2", "Beta Active Flagship Phone", "Beta", 88999),
        _record("p3", "Alpha Everyday Phone", "Alpha", 30000),
    ]
    selected, basis = top_record_per_brand(records, ("alpha", "beta"))
    assert basis == BASIS_PUBLISHED_TIER
    assert {record["id"] for record in selected} == {"p1", "p2"}
    assert all("Charger" not in record["name"] for record in selected)


def test_one_record_per_brand_and_no_more():
    records = [
        _record("a1", "Alpha Flagship One", "Alpha", 90000),
        _record("a2", "Alpha Flagship Two", "Alpha", 80000),
        _record("b1", "Beta Flagship One", "Beta", 70000),
    ]
    selected, _ = top_record_per_brand(records, ("alpha", "beta"))
    assert [record["id"] for record in selected] == ["a1", "b1"]


def test_tier_ranking_holds_for_a_travel_catalogue():
    records = [
        {"id": "f1", "name": "AirOne Economy Seat", "brand": "AirOne", "price": 4000,
         "subcategory": "Travel > Flights", "tags": ["basic"]},
        {"id": "f2", "name": "AirOne Business Seat", "brand": "AirOne", "price": 18000,
         "subcategory": "Travel > Flights", "tags": ["premium"]},
    ]
    ranking = rank_by_tier(records)
    assert ranking.basis == BASIS_PUBLISHED_TIER
    assert ranking.records[0]["id"] == "f2"


def test_an_empty_set_ranks_without_failing():
    assert rank_by_tier([]).records == ()
