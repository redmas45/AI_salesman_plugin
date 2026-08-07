"""Schema-guided understanding of one turn: constraints, operators, and asking.

These pin the behaviour the reported defects needed:

  * "Can you show me the top 3 best phones from the Samsung?" must resolve to a
    brand and a family, with "top", "best", "3" and "from" held as ranking and
    counting operators that are structurally incapable of reaching a search box.
    The storefront rendered `0 results for "top 3 phone from"` because they were
    not held apart.
  * A spoken word must align with a published one through morphology and
    head-final compounding ("phones" names "Smartphones") without the substring
    accident that matched "ipod" against "Tripods".
  * When two readings are equally good, or none is plausible, the turn asks -
    offering the options - rather than picking one.

Vendor names appear only in fixtures. The travel and policy cases prove the same
code serves any vertical, because every vocabulary comes from the records.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.nlu.frame import (  # noqa: E402
    RANK_MAX,
    RANK_MIN,
    SCALE_PRICE,
    SCALE_RATING,
    SCALE_TIER,
    SCALE_UNSPECIFIED,
    parse_frame,
)
from agent.nlu.lexical import build_vocabulary, word_alignment  # noqa: E402
from agent.nlu.resolution import (  # noqa: E402
    DECISION_ACT,
    DECISION_ASK,
    DECISION_CHOOSE,
    clarification_question,
    decide_slot,
)
from agent.nlu.schema import SLOT_BRAND, SLOT_FAMILY, build_schema  # noqa: E402


def _record(record_id, name, brand, family):
    return {"id": record_id, "name": name, "brand": brand, "subcategory": family}


STORE = [
    _record("p1", "Alpha Flagship Smartphone 3", "Alpha", "Smartphones"),
    _record("p2", "Alpha Ultra 26", "Alpha", "Smartphones"),
    _record("p3", "Beta Smartphone 2", "Beta", "Smartphones"),
    _record("c1", "Beta Fast Charger", "Beta", "Chargers, Cables & Adapters"),
    _record("t1", "Gamma Camera Tripod", "Gamma", "Lenses & Tripods"),
    _record("w1", "Alpha Fitness Band", "Alpha", "Smartwatches & Fitness Bands"),
]
SCHEMA = build_schema(STORE)


# --- Operators never become constraints ------------------------------------


def test_the_reported_turn_separates_constraints_from_ranking():
    frame = parse_frame("Can you show me the top 3 best phones from the Alpha?", SCHEMA)
    assert frame.brand == "Alpha"
    assert frame.family == "Smartphones"
    assert frame.limit == 3
    assert frame.rank is not None and frame.rank.direction == RANK_MAX
    # The searchable part contains only published values.
    assert frame.constraint_terms() == ("alpha", "smartphones")


def test_no_operator_word_can_reach_the_searchable_terms():
    banned = {"top", "best", "from", "3", "show", "me", "the", "can", "you"}
    for phrasing in (
        "Can you show me the top 3 best phones from the Alpha?",
        "show top three Alpha phones",
        "best 3 phones by Alpha",
        "give me the top 5 Alpha phones please",
    ):
        frame = parse_frame(phrasing, SCHEMA)
        words = {word.lower() for term in frame.constraint_terms() for word in term.split()}
        assert not words & banned, f"{phrasing!r} leaked {words & banned}"


def test_every_neutral_variant_resolves_to_the_same_constraints():
    for phrasing in ("show top three Alpha phones", "best 3 phones by Alpha", "Alpha phones"):
        frame = parse_frame(phrasing, SCHEMA)
        assert frame.constraint_terms() == ("alpha", "smartphones"), phrasing


def test_a_limit_is_read_only_where_a_count_was_requested():
    assert parse_frame("show me the top 3 Alpha phones", SCHEMA).limit == 3
    assert parse_frame("compare two Alpha phones", SCHEMA).limit == 2
    # A price bound is not a count of records.
    assert parse_frame("Alpha phones under 50000", SCHEMA).limit is None


def test_superlatives_carry_the_scale_they_quantify_over():
    def rank_of(text):
        operator = parse_frame(text, SCHEMA).rank
        return (operator.direction, operator.scale)

    assert rank_of("cheapest Alpha phone") == (RANK_MIN, SCALE_PRICE)
    assert rank_of("best rated Alpha phone") == (RANK_MAX, SCALE_RATING)
    assert rank_of("premium Alpha phone") == (RANK_MAX, SCALE_TIER)
    assert rank_of("budget Alpha phone") == (RANK_MIN, SCALE_TIER)
    assert rank_of("best Alpha phone") == (RANK_MAX, SCALE_UNSPECIFIED)


# --- Alignment: morphology and compounds, without the substring accident -----


def test_a_spoken_plural_names_the_published_family():
    assert word_alignment("phones", "Smartphones", SCHEMA.vocabulary) >= 0.9
    assert word_alignment("watches", "Smartwatches", SCHEMA.vocabulary) >= 0.9


def test_a_substring_that_is_not_a_compound_never_matches():
    """The camera-lens defect: "ipod" is not the head of "Tripods"."""
    assert word_alignment("ipod", "Tripods", SCHEMA.vocabulary) == 0.0
    assert word_alignment("pod", "Tripods", SCHEMA.vocabulary) == 0.0


def test_unrelated_families_never_align():
    assert word_alignment("phone", "Chargers", SCHEMA.vocabulary) == 0.0


def test_speech_recognition_damage_still_aligns_but_with_less_confidence():
    vocabulary = build_vocabulary(["Samsung"])
    confidence = word_alignment("samsang", "Samsung", vocabulary)
    assert 0.0 < confidence < 1.0


def test_a_word_the_catalogue_does_not_publish_is_reported_not_matched():
    frame = parse_frame("take me to an ipod", SCHEMA)
    assert frame.family == ""
    assert "ipod" in frame.content_words


# --- Ask, never assume ------------------------------------------------------


def test_a_clear_single_reading_is_acted_on():
    frame = parse_frame("show me Alpha phones", SCHEMA)
    decision = decide_slot(SLOT_FAMILY, frame.family_candidates)
    assert decision.decision == DECISION_ACT
    assert decision.value == "Smartphones"


def test_nothing_plausible_asks_rather_than_inventing():
    frame = parse_frame("take me to an ipod", SCHEMA)
    decision = decide_slot(SLOT_FAMILY, frame.family_candidates)
    assert decision.decision == DECISION_ASK
    question = clarification_question(frame, (decision,))
    assert "ipod" in question.lower()
    assert "?" in question


def test_two_equally_good_readings_offer_the_customer_the_choice():
    store = [
        _record("a1", "Delta Wall Adapter", "Delta", "Adapters"),
        _record("a2", "Delta Mains Adapter", "Delta", "Power Adapters"),
    ]
    schema = build_schema(store)
    frame = parse_frame("show me Delta power adapters", schema)
    decision = decide_slot(SLOT_FAMILY, frame.family_candidates)
    assert decision.decision == DECISION_CHOOSE
    assert set(decision.options) == {"Adapters", "Power Adapters"}
    assert "Adapters" in clarification_question(frame, (decision,))


def test_a_brand_with_no_stated_family_is_never_narrowed_silently():
    """The rule the owner set: do not assume the family from today's results."""
    frame = parse_frame("do you have Alpha", SCHEMA)
    assert frame.brand == "Alpha"
    assert frame.family == "", "a family the customer never said must not be assumed"
    assert frame.constraint_terms() == ("alpha",)


def test_an_empty_turn_says_nothing_searchable():
    assert parse_frame("show me those", SCHEMA).says_nothing_searchable()
    assert not parse_frame("Alpha phones", SCHEMA).says_nothing_searchable()


# --- Vertical independence --------------------------------------------------


TRAVEL = [
    {"id": "f1", "name": "AirOne Morning Flight", "brand": "AirOne", "subcategory": "Direct Flights"},
    {"id": "f2", "name": "AirOne Night Flight", "brand": "AirOne", "subcategory": "Direct Flights"},
    {"id": "h1", "name": "StayCo Harbour Room", "brand": "StayCo", "subcategory": "Hotels"},
]


def test_travel_records_produce_the_same_frame_shape():
    schema = build_schema(TRAVEL)
    frame = parse_frame("show me the top 2 best flights from AirOne", schema)
    assert frame.brand == "AirOne"
    assert frame.family == "Direct Flights"
    assert frame.limit == 2
    assert frame.rank.direction == RANK_MAX
    assert "top" not in " ".join(frame.constraint_terms()).lower()


POLICY = [
    {"id": "y1", "name": "Nova Family Cover", "brand": "Nova", "subcategory": "Health Policies"},
    {"id": "y2", "name": "Nova Motor Cover", "brand": "Nova", "subcategory": "Motor Policies"},
]


def test_policy_records_resolve_a_family_and_offer_a_choice_when_ambiguous():
    schema = build_schema(POLICY)
    frame = parse_frame("show me the cheapest Nova policies", schema)
    assert frame.brand == "Nova"
    assert (frame.rank.direction, frame.rank.scale) == (RANK_MIN, SCALE_PRICE)
    decision = decide_slot(SLOT_FAMILY, frame.family_candidates)
    assert decision.decision == DECISION_CHOOSE
    assert set(decision.options) == {"Health Policies", "Motor Policies"}


def test_a_brand_is_resolved_from_tenant_data_not_a_builtin_list():
    schema = build_schema([{"id": "x", "name": "Zeta Widget", "brand": "Zeta", "subcategory": "Widgets"}])
    frame = parse_frame("do you have Zeta widgets", schema)
    assert frame.brand == "Zeta"
    assert frame.family == "Widgets"
