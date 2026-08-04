"""One authoritative TurnPlan, resolved before any shortcut may run.

Root cause from the reported transcripts: the sort, navigation and inventory
shortcuts each re-parsed the raw utterance and answered on their own authority,
before `resolve_turn_context` had produced anything. A budgeted product search
("a phone under 50,000") and a gift recommendation ("something for my
girlfriend") were therefore stolen by the inventory-count shortcut, which
searched for a product literally named "something" and ignored the budget.

The plan is built once per turn and every shortcut consumes it. Shortcuts may
still optimise execution, but they may no longer decide what the customer meant.

Brand and catalog names appear only in these fixtures, never in production logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.orchestration.turn_plan import TurnOperation, build_turn_plan  # noqa: E402

BRANDS = ("apple", "samsung", "nova")
TYPES = ("phone", "smartphone", "laptop", "dress", "watch")


def _plan(utterance, history=(), page_state=None, **kwargs):
    return build_turn_plan(
        utterance,
        site_id="unit_site",
        session_id="session-1",
        turn_id="turn-1",
        history=list(history),
        session_summary="",
        page_state=page_state,
        catalog_brands=BRANDS,
        catalog_types=TYPES,
        **kwargs,
    )


def _user(text):
    return {"role": "user", "content": text}


def _maya(text):
    return {"role": "assistant", "content": text}


# --- Transcript 1: a budgeted search must stay a search ---------------------


def test_budgeted_phone_search_is_a_search_not_an_inventory_count():
    plan = _plan("I'm looking for a phone under 50,000")
    assert plan.operation == TurnOperation.SEARCH
    assert plan.constraints.max_price == 50000.0
    assert "phone" in plan.constraints.product_types


def test_budget_is_a_hard_constraint_on_the_plan():
    plan = _plan("I'm looking for a phone under 50,000")
    assert plan.hard_constraints()["max_price"] == 50000.0


# --- Transcript 2: correction inherits topic and replaces the budget --------


def test_correction_keeps_the_phone_topic_and_the_corrected_budget():
    history = [_user("I'm looking for a phone under 30000"), _maya("Here are phones.")]
    plan = _plan("But I said 50,000", history=history)
    assert "phone" in plan.constraints.product_types
    assert plan.constraints.max_price == 50000.0
    assert plan.operation == TurnOperation.SEARCH


# --- Transcript 3: "something for my girlfriend" is not a product named "something"


def test_gift_request_is_a_recommendation_not_a_literal_search():
    plan = _plan("I want to buy something for my girlfriend. I have a budget of 3000")
    assert plan.operation == TurnOperation.RECOMMEND
    assert plan.constraints.recipient == "girlfriend"
    assert plan.constraints.max_price == 3000.0
    assert "something" not in " ".join(plan.constraints.product_types)


def test_gift_request_never_becomes_an_inventory_count():
    plan = _plan("I want to buy something for my girlfriend. I have a budget of 3000")
    assert plan.operation != TurnOperation.INVENTORY_COUNT


# --- Transcript 4/5: aggregates and navigation are distinct operations ------


def test_cheapest_in_a_category_is_an_aggregate_operation():
    plan = _plan("What's the cheapest thing in Fashion Women?")
    assert plan.operation == TurnOperation.AGGREGATE
    assert plan.aggregate == "cheapest"


def test_best_rated_is_an_aggregate_operation():
    plan = _plan("Which is the best rated laptop?")
    assert plan.operation == TurnOperation.AGGREGATE
    assert plan.aggregate == "best_rated"


def test_take_me_to_a_category_is_navigation():
    plan = _plan("Take me to Fashion Women")
    assert plan.operation == TurnOperation.NAVIGATE
    assert plan.navigation_requested is True


def test_mixed_aggregate_and_navigation_preserves_both_requirements():
    plan = _plan("Show the cheapest item in Fashion Women and take me there")
    assert plan.operation == TurnOperation.AGGREGATE
    assert plan.aggregate == "cheapest"
    assert plan.navigation_requested is True
    assert plan.cache_eligible is False


# --- Transcript 6: page-relative questions must not search the catalog -----


def test_visible_products_question_is_page_relative():
    page_state = {"route": "/shop", "visible_entities": [{"id": "p1"}, {"id": "p2"}]}
    plan = _plan("What visible products?", page_state=page_state)
    assert plan.operation == TurnOperation.PAGE_QUESTION
    assert plan.referent_ids == ("p1", "p2")


def test_page_question_without_page_state_does_not_claim_referents():
    plan = _plan("What visible products?")
    assert plan.operation == TurnOperation.PAGE_QUESTION
    assert plan.referent_ids == ()


# --- Transcript 7: comparison keeps both requested brands ------------------


def test_comparison_names_both_brands():
    plan = _plan("Compare Apple versus Samsung in the premium segment")
    assert plan.operation == TurnOperation.COMPARE
    assert set(plan.constraints.brands) == {"apple", "samsung"}


# --- Genuine inventory questions still resolve to a count ------------------


def test_how_many_is_still_an_inventory_count():
    assert _plan("How many phones do you have?").operation == TurnOperation.INVENTORY_COUNT


def test_sort_request_is_a_sort_operation():
    assert _plan("Sort by price low to high").operation == TurnOperation.SORT


# --- Plan identity, immutability and cache policy --------------------------


def test_plan_is_immutable():
    import dataclasses

    plan = _plan("I'm looking for a phone under 50,000")
    try:
        plan.operation = TurnOperation.NAVIGATE
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("the turn plan must be immutable once resolved")


def test_plan_carries_turn_session_and_site_identity():
    plan = _plan("I'm looking for a phone under 50,000")
    assert plan.site_id == "unit_site"
    assert plan.session_id == "session-1"
    assert plan.turn_id == "turn-1"


def test_resolution_is_deterministic():
    first = _plan("I'm looking for a phone under 50,000")
    second = _plan("I'm looking for a phone under 50,000")
    assert first.operation == second.operation
    assert first.cache_key_component() == second.cache_key_component()


def test_state_dependent_operations_are_not_cacheable():
    for utterance in ("What visible products?", "Take me to Fashion Women", "Sort by price low to high"):
        assert _plan(utterance).cache_eligible is False, utterance


def test_corrections_and_referential_turns_are_not_cacheable():
    history = [_user("I'm looking for a phone under 30000"), _maya("Here are phones.")]
    assert _plan("But I said 50,000", history=history).cache_eligible is False
    assert _plan("compare these two", history=history).cache_eligible is False


def test_stable_informational_search_is_cacheable():
    assert _plan("I'm looking for a phone under 50,000").cache_eligible is True


def test_cache_key_component_separates_different_hard_constraints():
    cheap = _plan("I'm looking for a phone under 20000")
    dear = _plan("I'm looking for a phone under 50000")
    assert cheap.cache_key_component() != dear.cache_key_component()


def test_pipeline_skips_cache_io_for_ineligible_plans():
    source = (
        Path(__file__).parent.parent / "agent" / "orchestration" / "orchestrator_pipeline.py"
    ).read_text(encoding="utf-8")
    sync_source, stream_source = source.split("def run_stream_pipeline", 1)

    for pipeline_source in (sync_source, stream_source):
        assert "if plan.cache_eligible:" in pipeline_source
        assert 'retrieval_evidence["cache_write"] = "skipped_turn_plan"' in pipeline_source
