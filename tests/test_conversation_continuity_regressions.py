"""Regressions for the reported conversational-continuity defects.

Every case here is taken from a real transcript recorded against the local
system. The failures they pin are:

  * A cart request became checkout navigation. Any mention of the word "cart"
    that was not "add ... to cart" was classified as a checkout intent, so
    "clear my cart", "remove all the items from the cart" and even "what is in
    my cart" all tried to open checkout.
  * A brand-only comparison paired unrelated items. "Compare Samsung versus
    Apple" returned a phone and a charger, because selection enforced brand
    diversity but never required the items to be the same kind of thing.
  * A result count was claimed that the customer could not see. The answer said
    "I found 5 matching products" and then listed three, while the storefront
    showed its own number.

Vendor names appear only in these fixtures, never in production logic; the
generalization cases below use neutral travel and policy records to prove the
same rules hold outside retail.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.action_helpers.action_response_filters import (  # noqa: E402
    neutralize_pending_action_claims,
)
from agent.flows.flow_planner import _flow_intent, _normalize_text  # noqa: E402
from agent.products.comparison_selection import (  # noqa: E402
    comparison_family_conflict,
    product_family,
    select_comparison_products,
)
from agent.products.product_response import ProductCatalogFormatter  # noqa: E402
from agent.products.product_turn_responses import (  # noqa: E402
    comparison_family_clarification,
    promote_comparison_action,
)
from agent.retrieval.referent_reference import (  # noqa: E402
    ordinal_position,
    refers_to_shown_records,
)


def _record(record_id, brand, price, family, name=None, **extra):
    base = {
        "id": record_id,
        "name": name or f"{brand} {family} {record_id}",
        "brand": brand,
        "price": price,
        "stock": 5,
        "subcategory": family,
        "category": "electronics",
        "rating": 4.4,
        "review_count": 8,
    }
    base.update(extra)
    return base


# --- Cart intent precedence: a cart request is never checkout ---------------


def _intent(text: str) -> str:
    return _flow_intent(_normalize_text(text), True)


def test_clearing_the_cart_is_never_checkout():
    """Reported: "clear my cart" answered "I'll try to open the checkout step"."""
    assert _intent("clear my cart") == "clear_cart"
    assert _intent("empty my cart") == "clear_cart"
    assert _intent("remove all the items from the cart") == "clear_cart"
    assert _intent("remove everything from my basket") == "clear_cart"


def test_the_full_reported_correction_still_clears_the_cart():
    """The exact transcript, including the "I want to buy it" negation."""
    reported = (
        "No, I'm asking you to clear my cart. This doesn't mean I want to buy it. "
        "I want you to clear the cart. Remove all the items from the cart."
    )
    assert _intent(reported) == "clear_cart"


def test_removing_one_named_item_is_not_clear_cart_and_not_checkout():
    assert _intent("remove the bomber jacket from my cart") == "remove_from_cart"
    assert _intent("take the charger out of my basket") == "remove_from_cart"


def test_asking_about_the_cart_is_not_a_transactional_flow():
    """"What is in my cart" is a question, not a request to check out."""
    assert _intent("what is in my cart") == ""
    assert _intent("is my cart empty") == ""
    assert _intent("how many items are in my bag") == ""


def test_explicit_checkout_language_still_reaches_checkout():
    assert _intent("checkout") == "checkout"
    assert _intent("proceed to checkout") == "checkout"
    assert _intent("take me to the checkout page") in {"checkout", ""}


def test_adding_to_cart_still_wins_over_every_other_cart_reading():
    assert _intent("add the bomber jacket to my cart") == "add_to_cart"
    assert _intent("put this in my basket") == "add_to_cart"


def test_cart_precedence_holds_for_a_non_retail_vertical():
    """Nothing in the cart rules depends on a retail catalog."""
    assert _intent("empty my booking cart") == "clear_cart"
    assert _intent("remove the baggage cover from my cart") == "remove_from_cart"


def test_ecommerce_discovery_maps_a_host_clear_cart_control():
    from agent.verticals.discovery_profile_catalog import ECOMMERCE_PROFILE

    labels = ECOMMERCE_PROFILE.action_labels
    assert "CLEAR_CART" in labels
    assert "clear cart" in labels["CLEAR_CART"]


# --- Comparison must contrast comparable records ---------------------------

PHONE = _record("p1", "Alpha", 65549, "Smartphones")
PHONE_OTHER_BRAND = _record("p2", "Beta", 54999, "Smartphones")
CHARGER = _record("c1", "Beta", 1399, "Chargers")


def test_brand_only_comparison_never_pairs_two_different_kinds_of_thing():
    """Reported: "compare Samsung versus Apple" returned a phone and a charger."""
    selected = select_comparison_products(
        [PHONE, CHARGER, PHONE_OTHER_BRAND],
        brands=("alpha", "beta"),
        requested_count=2,
    )
    families = {record["subcategory"] for record in selected}
    assert len(selected) == 2
    assert families == {"Smartphones"}, f"compared across families: {families}"


def test_a_brand_only_request_with_no_shared_family_is_reported_as_ambiguous():
    """Two brands that share no comparable family deserve one question."""
    assert comparison_family_conflict([PHONE, CHARGER], brands=("alpha", "beta")) == (
        "Chargers",
        "Smartphones",
    )


def test_a_single_family_request_reports_no_conflict():
    assert comparison_family_conflict([PHONE, PHONE_OTHER_BRAND], brands=("alpha", "beta")) is None


def test_comparison_order_and_ids_are_preserved():
    selected = select_comparison_products(
        [PHONE, PHONE_OTHER_BRAND],
        brands=("alpha", "beta"),
        requested_count=2,
    )
    assert [record["id"] for record in selected] == ["p1", "p2"]


def test_named_records_are_compared_even_across_families():
    """Naming both records explicitly is consent to compare them."""
    selected = select_comparison_products(
        [PHONE, CHARGER],
        brands=("alpha", "beta"),
        requested_count=2,
        records_named_explicitly=True,
    )
    assert [record["id"] for record in selected] == ["p1", "c1"]


def test_family_rule_holds_for_travel_records():
    flight = {"id": "f1", "name": "Coastal Flight", "brand": "AirOne", "price": 8200, "subcategory": "Flights"}
    hotel = {"id": "h1", "name": "Harbour Stay", "brand": "StayCo", "price": 4300, "subcategory": "Hotels"}
    assert comparison_family_conflict([flight, hotel], brands=("airone", "stayco")) == (
        "Flights",
        "Hotels",
    )


def test_family_rule_reads_ingested_category_path_when_subcategory_is_not_persisted():
    """Hub records retain the source family in the normalized description."""
    phone = {
        "id": "phone",
        "name": "Samsung Smartphone",
        "brand": "Samsung",
        "category": "electronics",
        "description": (
            "A Samsung phone. Category path: Electronics > Smartphones > Android Budget. "
            "Specifications: display: 6.5 inch"
        ),
    }
    charger = {
        "id": "charger",
        "name": "Apple Fast Charger",
        "brand": "Apple",
        "category": "electronics",
        "description": (
            "A fast charger. Category path: Electronics > Chargers, Cables & Adapters. "
            "Specifications: power: 20W"
        ),
    }

    assert product_family(phone) == "Android Budget"
    assert product_family(charger) == "Chargers, Cables & Adapters"
    assert comparison_family_conflict([phone, charger], brands=("samsung", "apple")) == (
        "Android Budget",
        "Chargers, Cables & Adapters",
    )


# --- One count, honestly stated --------------------------------------------


def _formatter() -> ProductCatalogFormatter:
    return ProductCatalogFormatter()


def test_the_claimed_count_is_the_number_of_records_on_screen():
    """Reported: a claimed count the customer could not reconcile with the page.

    Five displayed records are claimed as five, even though speech reads out a
    sample of three; the cards are what the customer counts.
    """
    records = [_record(f"r{index}", "Alpha", 1000 + index, "Smartphones") for index in range(5)]
    text = _formatter().search_text(records)
    assert "I found 5 matching products:" in text
    assert "showing" not in text.lower()


def test_showing_everything_that_matched_needs_no_explanation():
    records = [_record(f"r{index}", "Alpha", 1000 + index, "Smartphones") for index in range(3)]
    text = _formatter().search_text(records)
    assert "I found 3 matching products" in text
    assert "showing" not in text.lower()


def test_a_single_match_is_still_phrased_in_the_singular():
    text = _formatter().search_text([_record("r1", "Alpha", 1000, "Smartphones")])
    assert "I found this matching product" in text
    assert "showing" not in text.lower()


def test_a_total_larger_than_the_displayed_set_is_explained_not_hidden():
    """Twelve matched, five are shown: both numbers are said out loud."""
    records = [_record(f"r{index}", "Alpha", 1000 + index, "Smartphones") for index in range(5)]
    text = _formatter().search_text(records, matching_total=12)
    assert "I found 12 matching products. I'm showing 5 here:" in text


def test_a_total_can_never_be_reported_below_what_is_displayed():
    records = [_record(f"r{index}", "Alpha", 1000 + index, "Smartphones") for index in range(5)]
    text = _formatter().search_text(records, matching_total=2)
    assert "I found 5 matching products:" in text


# --- Referring back to records already shown --------------------------------


def test_a_bare_demonstrative_object_refers_to_the_shown_records():
    """Reported: "Okay, add this to the cart" reached an unrelated older set.

    The turn carries no searchable terms, so treating it as a fresh search means
    retrieving something arbitrary. It must resolve against what was just shown.
    """
    assert refers_to_shown_records("Okay, add this to the cart")
    assert refers_to_shown_records("put this in my cart")
    assert refers_to_shown_records("add these to cart")


def test_every_ordinal_form_refers_to_the_shown_records():
    """Reported: "The first one." had to resolve against the displayed list."""
    for phrasing in (
        "The first one.",
        "the first one",
        "I'll take the second",
        "add the first one to my cart",
        "option 2",
        "option two",
    ):
        assert refers_to_shown_records(phrasing), phrasing


def test_ordinal_positions_follow_display_order():
    assert ordinal_position("the first one") == 0
    assert ordinal_position("the second one") == 1
    assert ordinal_position("the third one") == 2
    assert ordinal_position("option 2") == 1
    assert ordinal_position("option two") == 1
    assert ordinal_position("the last one") == -1


def test_a_demonstrative_modifying_a_noun_is_not_a_back_reference():
    """"Show me this week's deals" starts a search; it does not point backwards."""
    assert not refers_to_shown_records("show me this week deals")
    assert not refers_to_shown_records("first i want to browse the store")
    assert ordinal_position("first i want to browse the store") is None


def test_an_explicit_new_scope_is_not_a_back_reference():
    """Reported: an electronics question was answered with a stale jacket.

    "The cheapest" was read as pointing at the records already under discussion
    even though the turn names a new section to search.
    """
    assert not refers_to_shown_records("what's the cheapest item in the electronics section")
    assert not refers_to_shown_records("show me the cheapest laptop")


def test_a_superlative_with_no_new_subject_still_refers_back():
    assert refers_to_shown_records("the cheaper one")
    assert refers_to_shown_records("which one is better value")
    assert refers_to_shown_records("add the cheapest to my cart")


def test_a_fresh_product_request_is_never_treated_as_a_reference():
    for phrasing in (
        "I'm looking for a jacket",
        "do you have samsung phones",
        "compare samsung galaxy s26 and iphone 17",
        "I want to buy a phone under 50000",
    ):
        assert not refers_to_shown_records(phrasing), phrasing


def test_reference_rules_hold_for_a_non_retail_vertical():
    assert refers_to_shown_records("book the second one")
    assert ordinal_position("book the second one") == 1
    assert not refers_to_shown_records("show me the cheapest flight to Delhi")


# --- The comparison turn as a whole -----------------------------------------


def test_a_brand_only_comparison_asks_instead_of_pairing_unrelated_records():
    """Reported: "Compare Samsung versus Apple" returned a phone and a charger."""
    response = {"response_text": "x", "intent": "product_search", "ui_actions": []}
    promote_comparison_action(
        response,
        "Compare Alpha versus Beta.",
        [PHONE, CHARGER, _record("p3", "Alpha", 9549, "Smartphones")],
    )
    assert response["intent"] == "clarify"
    assert response["response_text"] == "Which type should I compare: Chargers or Smartphones?"
    assert response["ui_actions"] == []


def test_a_same_family_comparison_still_compares_both_named_records():
    named_first = _record("p1", "Alpha", 65549, "Smartphones", _exact_name_match=True)
    named_second = _record("p2", "Beta", 54999, "Smartphones", _exact_name_match=True)
    response = {"response_text": "x", "intent": "product_search", "ui_actions": []}
    promote_comparison_action(
        response,
        "Compare the Alpha flagship versus the Beta flagship.",
        [named_first, named_second],
    )
    assert response["intent"] == "product_compare"
    assert response["ui_actions"][0]["params"]["product_ids"] == ["p1", "p2"]


def test_naming_both_records_skips_the_family_question():
    """Explicitly named records are compared even across families."""
    named_phone = dict(PHONE, _exact_name_match=True)
    named_charger = dict(CHARGER, _exact_name_match=True)
    assert comparison_family_clarification(
        "Compare the Alpha phone with the Beta charger.",
        [named_phone, named_charger],
    ) == ""


# --- Count wording survives the action-truth filter --------------------------

_DISPLAY_ACTION = [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["r1"]}}]


def test_stating_how_many_records_are_shown_is_not_an_action_claim():
    """The action-truth filter must not rewrite a count into a promise.

    "I'm showing 3 here" describes the answer, not the website. Neutralising it
    into "I'll try to show 3 here" both misreports the answer and restores the
    tentative wording action truth exists to remove.
    """
    text = "I found 7 matching products. I'm showing 3 here:\n- Alpha"
    assert neutralize_pending_action_claims(text, _DISPLAY_ACTION) == text


def test_a_real_action_claim_is_still_neutralised():
    assert neutralize_pending_action_claims(
        "I am opening the electronics section.", _DISPLAY_ACTION
    ) == "I'll try to open the electronics section."
    assert neutralize_pending_action_claims(
        "I am adding the jacket to your cart.", _DISPLAY_ACTION
    ) == "I'll try to add the jacket to your cart."


# --- Display order is what an ordinal counts --------------------------------


class _StubMatcher:
    """Exercises the history-tag lookup without a database."""

    def __init__(self, rows):
        self._rows = rows
        self._recoverable_errors = (RuntimeError,)

        class _Logger:
            def warning(self, *args, **kwargs):
                pass

        self._logger = _Logger()

    def _load_products_by_ids(self, site_id, tagged_ids):
        # A bulk lookup returns the database's own order, not the requested one.
        wanted = {str(value) for value in tagged_ids}
        return [row for row in self._rows if str(row["id"]) in wanted]


def test_an_ordinal_counts_the_order_the_customer_was_shown():
    """Reported live: "add the first one" added the second displayed record.

    The tag records display order; a bulk lookup returns database order. Losing
    the difference makes every ordinal point at the wrong record.
    """
    from agent.products.product_matching import ProductCatalogMatcher

    rows = [
        {"id": 11, "name": "Second Shown"},
        {"id": 22, "name": "First Shown"},
        {"id": 33, "name": "Third Shown"},
    ]
    stub = _StubMatcher(rows)
    resolved = ProductCatalogMatcher._products_from_ids(stub, "any_site", [22, 11, 33])
    assert [record["name"] for record in resolved] == ["First Shown", "Second Shown", "Third Shown"]


def test_an_unknown_tagged_id_is_skipped_rather_than_shifting_the_order():
    from agent.products.product_matching import ProductCatalogMatcher

    stub = _StubMatcher([{"id": 11, "name": "Kept"}])
    resolved = ProductCatalogMatcher._products_from_ids(stub, "any_site", [99, 11])
    assert [record["name"] for record in resolved] == ["Kept"]
