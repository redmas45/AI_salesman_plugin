"""Regression tests for the deterministic resolved-turn context (dialogue slice).

Root cause reproduced here: the e-commerce clarification gate ran on the raw
transcript alone, so it ignored conversation history, the session summary, and
previously displayed/compared products. Follow-ups such as "What should I buy?
No budget issue" after an explicit phone comparison were treated as a fresh,
under-determined request and re-asked for a product category.

Brand and catalog names appear ONLY in these fixtures, never in production logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.retrieval.resolved_context import resolve_turn_context  # noqa: E402

BRANDS = ("apple", "samsung", "nova", "acer")
TYPES = ("phone", "smartphone", "laptop", "smartwatch", "shirt", "jacket", "raincoat", "umbrella")


def _resolve(query, history=(), summary="", product_ids=()):
    return resolve_turn_context(
        query,
        history=list(history),
        session_summary=summary,
        recent_product_ids=tuple(product_ids),
        catalog_brands=BRANDS,
        catalog_types=TYPES,
    )


def _user(text):
    return {"role": "user", "content": text}


def _maya(text):
    return {"role": "assistant", "content": text}


# --- Regression 1: flagship comparison then "What should I buy? No budget issue" ---


FLAGSHIP_HISTORY = [
    _user("Compare Apple and Samsung flagship phones"),
    _maya("I found 2 matching products: Apple Flagship Smartphone, Samsung Flagship Smartphone."),
]


def test_no_budget_issue_followup_keeps_phone_topic_and_does_not_clarify():
    resolved = _resolve("What should I buy? No budget issue", history=FLAGSHIP_HISTORY)
    assert not resolved.should_ask_clarification(), resolved.constraints.ambiguity_reason
    assert "phone" in resolved.constraints.product_types
    assert set(resolved.constraints.brands) == {"apple", "samsung"}


def test_no_budget_issue_means_no_maximum_not_zero():
    resolved = _resolve("What should I buy? No budget issue", history=FLAGSHIP_HISTORY)
    assert resolved.constraints.max_price is None
    assert resolved.budget_waived is True


def test_no_budget_issue_clears_an_inherited_maximum():
    history = [*FLAGSHIP_HISTORY, _user("under 20000")]
    resolved = _resolve("What should I buy? No budget issue", history=history)
    assert resolved.constraints.max_price is None


# --- Regression 2: frustrated correction must not re-ask ---


def test_i_told_you_already_is_treated_as_continuity():
    resolved = _resolve("I told you already", history=FLAGSHIP_HISTORY)
    assert not resolved.should_ask_clarification()
    assert resolved.constraints.is_followup


# --- Regression 3: "something to wear" after "for himself" ---


WEAR_HISTORY = [
    _user("I am shopping for myself"),
    _maya("Happy to help you find something."),
]


def test_something_to_wear_keeps_self_recipient_and_asks_focused_question():
    resolved = _resolve("Something to wear", history=WEAR_HISTORY)
    # Recipient is already known: never re-ask for it.
    assert resolved.constraints.recipient == "self"
    # No concrete apparel type yet -> exactly one focused apparel question.
    assert resolved.should_ask_clarification()
    assert resolved.clarification_topic == "apparel"


def test_apparel_clarification_does_not_reask_recipient():
    resolved = _resolve("Something to wear", history=WEAR_HISTORY)
    question = resolved.clarification_question()
    assert question.count("?") == 1
    assert "who" not in question.lower()


# --- Regression 4: rainy + budget after the wear context ---


RAINY_HISTORY = [
    *WEAR_HISTORY,
    _user("Something to wear"),
    _maya("What kind of clothing are you after?"),
]


def test_rainy_budget_preserves_need_and_budget_and_does_not_reask():
    resolved = _resolve("It is rainy and my budget is INR 2,000", history=RAINY_HISTORY)
    assert resolved.constraints.max_price == 2000.0
    assert resolved.constraints.recipient == "self"
    assert not resolved.should_ask_clarification()


# --- Regression 5: explicit count + budget ---


def test_two_phones_with_budget_extracts_count_and_price():
    resolved = _resolve("Budget INR 50,000, suggest two phones and compare them")
    assert resolved.constraints.max_price == 50000.0
    assert resolved.requested_count == 2
    assert "phone" in resolved.constraints.product_types
    assert not resolved.should_ask_clarification()


# --- Regression 6: brand-scoped inventory request stays brand-scoped ---


def test_single_brand_inventory_request_is_not_widened_by_history():
    resolved = _resolve("Do you have Samsung phones?", history=FLAGSHIP_HISTORY)
    # The current turn names exactly one brand; history must not re-add the other.
    assert set(resolved.constraints.brands) == {"samsung"}


# --- Regression 7: greetings stay clean ---


def test_greeting_does_not_inherit_product_context():
    resolved = _resolve("Hello", history=FLAGSHIP_HISTORY)
    assert resolved.constraints.product_types == ()
    assert resolved.constraints.brands == ()


# --- Regression 8: off-topic is bounded without erasing shopping context ---


def test_off_topic_question_preserves_active_context():
    resolved = _resolve("Who is the prime minister?", history=FLAGSHIP_HISTORY)
    assert resolved.is_off_topic
    # Context is preserved for the next real shopping turn.
    assert "phone" in resolved.constraints.product_types


# --- Precedence rules ---


def test_current_explicit_type_overrides_history_topic():
    resolved = _resolve("Show me laptops", history=FLAGSHIP_HISTORY)
    assert "laptop" in resolved.constraints.product_types
    assert "phone" not in resolved.constraints.product_types
    assert resolved.is_topic_change


def test_topic_change_discards_stale_brands():
    resolved = _resolve("Show me laptops", history=FLAGSHIP_HISTORY)
    assert resolved.constraints.brands == ()


def test_current_recipient_overrides_an_inherited_recipient():
    history = [_user("a gift for my mom"), _maya("What kind of gift?")]
    resolved = _resolve("Actually it is for myself", history=history)
    assert resolved.constraints.recipient == "self"


def test_correction_replaces_only_the_corrected_constraint():
    history = [_user("Show me phones under 20000"), _maya("Here are phones.")]
    resolved = _resolve("Actually, under 50000", history=history)
    assert resolved.constraints.max_price == 50000.0
    assert "phone" in resolved.constraints.product_types


def test_history_is_not_concatenated_into_the_query():
    resolved = _resolve("What should I buy? No budget issue", history=FLAGSHIP_HISTORY)
    assert resolved.constraints.raw_query == "What should I buy? No budget issue"


def test_referenced_product_ids_are_carried_for_followups():
    resolved = _resolve("Compare them", history=FLAGSHIP_HISTORY, product_ids=("p1", "p2"))
    assert resolved.referenced_product_ids == ("p1", "p2")


def test_session_summary_supplies_context_when_history_is_empty():
    summary = "User: Compare Apple and Samsung flagship phones\nMaya: Here are two phones."
    resolved = _resolve("What should I buy? No budget issue", summary=summary)
    assert "phone" in resolved.constraints.product_types


def test_resolution_is_deterministic():
    first = _resolve("What should I buy? No budget issue", history=FLAGSHIP_HISTORY)
    second = _resolve("What should I buy? No budget issue", history=FLAGSHIP_HISTORY)
    assert first.constraints == second.constraints
    assert first.cache_identity() == second.cache_identity()


def test_cache_identity_separates_different_resolved_constraints():
    waived = _resolve("What should I buy? No budget issue", history=FLAGSHIP_HISTORY)
    capped = _resolve("What should I buy under 20000?", history=FLAGSHIP_HISTORY)
    assert waived.cache_identity() != capped.cache_identity()
