"""One display contract per turn, shared by speech, UI, browser and log.

Reported defect (local, 2026-08-07):

    User : "Can you show me the top 3 best phones from the Samsung?"
    Maya : "I found 4 matching products. I'm showing 3 here: ..."
    Page : /search?q=top%203%20phone%20from
    DOM  : 0 results for "top 3 phone from"

Two separate failures. The host query was built by truncating cleaned speech -
covered by ``test_nlu_semantic_frame.py``, which owns query construction. The
other is here: the count Maya claimed, the records she named, the ids the action
carried and what the page could show were each derived independently.

This module pins the contract that keeps them one thing: a requested count and a
matching total are different numbers, selected ids carry display order, and the
wording states both numbers rather than merging them.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.nlu.frame import parse_frame  # noqa: E402
from agent.nlu.schema import build_schema  # noqa: E402
from agent.products.display_request import (  # noqa: E402
    CanonicalDisplayRequest,
    build_display_request,
    canonical_host_query,
)


def _record(record_id, name, brand, family="Smartphones", price=50000):
    return {
        "id": record_id,
        "name": name,
        "brand": brand,
        "price": price,
        "stock": 4,
        "subcategory": family,
        "category": "electronics",
    }


ALPHA_PHONES = [
    _record("p1", "Alpha Flagship Smartphone 3", "Alpha", price=90000),
    _record("p2", "Alpha Ultra 26", "Alpha", price=80000),
    _record("p3", "Alpha Smartphone 2", "Alpha", price=30000),
    _record("p4", "Alpha Budget 1", "Alpha", price=12000),
]

TRAVEL = [
    {"id": "f1", "name": "Beta Morning Flight", "brand": "Beta", "subcategory": "Direct Flights"},
    {"id": "f2", "name": "Beta Evening Flight", "brand": "Beta", "subcategory": "Direct Flights"},
]


def _request(text, records=ALPHA_PHONES, requested_count=None):
    frame = parse_frame(text, build_schema(records))
    return build_display_request(frame, matching_records=records, requested_count=requested_count)


# --- The query carries no ranking, count, or filler -------------------------


def test_the_reported_transcript_never_produces_the_reported_query():
    request = _request("Can you show me the top 3 best phones from the Alpha?")
    assert request.host_query == "alpha smartphones"
    for banned in ("top", "best", "from", "3"):
        assert banned not in request.host_query.split()


def test_a_turn_that_named_nothing_carries_no_query_rather_than_a_guess():
    """An empty query makes the executor decline, instead of searching for noise."""
    assert _request("show me those").host_query == ""


# --- Counts stay distinct ---------------------------------------------------


def test_the_requested_count_is_taken_from_the_turn_itself():
    request = _request("show me the top 3 best phones from the Alpha")
    assert request.requested_count == 3
    assert request.matching_total == 4
    assert request.displayed_count == 3


def test_without_a_requested_count_every_matching_record_is_selected():
    request = _request("show me Alpha phones")
    assert request.requested_count is None
    assert request.matching_total == 4
    assert request.displayed_count == 4


def test_the_selected_ids_and_their_order_are_the_contract():
    assert _request("top 2 Alpha phones").selected_ids == ("p1", "p2")
    assert _request("show me Alpha phones").selected_ids == ("p1", "p2", "p3", "p4")


def test_an_explicit_count_overrides_the_one_in_the_turn():
    assert _request("top 3 Alpha phones", requested_count=2).selected_ids == ("p1", "p2")


def test_a_request_reports_whether_the_page_holds_more_than_it_names():
    assert _request("top 3 Alpha phones").page_shows_more_than_selected is True
    assert _request("Alpha phones").page_shows_more_than_selected is False


# --- Truthful wording -------------------------------------------------------


def test_a_shortlist_states_the_total_and_calls_itself_a_shortlist():
    """Reported: three records named while claiming the page held only three."""
    summary = _request("top 3 best phones from Alpha").count_summary()
    assert "4" in summary
    assert "top three" in summary.lower()
    assert "only" not in summary.lower()


def test_showing_everything_needs_no_shortlist_wording():
    summary = _request("Alpha phones").count_summary()
    assert "4" in summary
    assert "top" not in summary.lower()


def test_a_single_match_is_phrased_in_the_singular():
    summary = _request("Alpha phones", records=ALPHA_PHONES[:1]).count_summary()
    assert summary.startswith("I found one")


# --- Vertical independence and immutability ---------------------------------


def test_the_same_contract_holds_for_travel_records():
    request = _request("show me the top 2 best flights from Beta", records=TRAVEL)
    assert request.host_query == "beta flights"
    assert "top" not in request.host_query and "best" not in request.host_query
    assert request.requested_count == 2
    assert request.selected_ids == ("f1", "f2")


def test_the_query_carries_the_published_words_the_customer_named():
    """Someone who says "flights" searches for "flights", not "Direct Flights".

    The label they never used would be searched as a literal phrase and match
    less than the published word they did use.
    """
    assert canonical_host_query(parse_frame("Beta flights", build_schema(TRAVEL)), TRAVEL) == (
        "beta flights"
    )


def test_a_request_is_immutable():
    request = _request("Alpha phones")
    assert isinstance(request, CanonicalDisplayRequest)
    try:
        request.host_query = "changed"
    except AttributeError:
        return
    raise AssertionError("the display request must not be mutable after construction")
