"""The generic page-state contract: what is visible, filtered and sorted.

A page-relative question ("how many of these are under 2000?", "which of these
is cheapest?") was answered with a fresh catalog search, because nothing in the
turn described the screen. These tests pin the contract that carries it: bounded,
vertical-independent, and free of anything a customer typed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.prompts.page_context import (
    MAX_VISIBLE_ENTITIES,
    format_page_context,
    sanitize_page_context,
)


def _context(**overrides):
    base = {
        "title": "Listing",
        "url": "https://store.example/list?color=blue",
        "path": "/list",
        "route": {"path": "/list", "search": "?color=blue"},
        "filters": {"color": "blue", "size": "m"},
        "sort": "price_asc",
        "visible_entities": [
            {
                "id": "p1",
                "entity_type": "product",
                "label": "Aster Kurta",
                "route": "/products/p1",
                "facts": {"price": "₹499", "rating": "4.2"},
            },
            {
                "id": "t9",
                "entity_type": "trip",
                "label": "Coastal Route",
                "route": "/trips/t9",
                "facts": {"price": "₹12,000"},
            },
        ],
    }
    base.update(overrides)
    return base


def test_visible_entities_survive_sanitization_with_stable_ids_and_types():
    context = sanitize_page_context(_context())

    assert [entity["id"] for entity in context["visible_entities"]] == ["p1", "t9"]
    assert [entity["entity_type"] for entity in context["visible_entities"]] == ["product", "trip"]
    assert context["visible_entities"][0]["facts"]["price"] == "₹499"
    assert context["route"] == {"path": "/list", "search": "?color=blue"}
    assert context["filters"] == {"color": "blue", "size": "m"}
    assert context["sort"] == "price_asc"


def test_entity_facts_are_restricted_to_a_safe_published_set():
    context = sanitize_page_context(
        _context(
            visible_entities=[
                {
                    "id": "p1",
                    "facts": {
                        "price": "₹499",
                        "customer_email": "someone@example.test",
                        "notes": "typed by the shopper",
                    },
                }
            ]
        )
    )

    facts = context["visible_entities"][0]["facts"]
    assert facts == {"price": "₹499"}, "only published display facts may cross the boundary"


def test_visible_entities_are_bounded():
    many = [{"id": f"p{index}"} for index in range(MAX_VISIBLE_ENTITIES + 20)]
    context = sanitize_page_context(_context(visible_entities=many))

    assert len(context["visible_entities"]) == MAX_VISIBLE_ENTITIES


def test_entities_without_a_stable_id_are_dropped():
    context = sanitize_page_context(_context(visible_entities=[{"label": "No id"}, {"id": "p2"}]))

    assert [entity["id"] for entity in context["visible_entities"]] == ["p2"]


def test_malformed_page_state_degrades_to_empty_rather_than_raising():
    context = sanitize_page_context(_context(visible_entities="not-a-list", filters=7, route=None))

    assert context["visible_entities"] == []
    assert context["filters"] == {}
    assert context["route"] == {"path": "", "search": ""}


def test_prompt_states_the_screen_so_page_questions_are_answered_from_it():
    text = format_page_context(_context())

    assert "Currently visible on screen (2):" in text
    assert "[product p1] Aster Kurta" in text
    assert "Active filters: color=blue, size=m" in text
    assert "Sorted by: price_asc" in text
    assert "Answer questions about what is on screen from this list only." in text


def test_turn_plan_reads_referents_from_the_screen_for_a_page_question():
    from agent.orchestration.turn_plan import TurnOperation, build_turn_plan

    plan = build_turn_plan(
        "which of these results is cheapest?",
        site_id="site_1",
        page_state=sanitize_page_context(_context()),
    )

    assert plan.operation in {TurnOperation.PAGE_QUESTION, TurnOperation.AGGREGATE}
    assert plan.referent_ids == ("p1", "t9")
    assert plan.cache_eligible is False, "an answer about this screen must never be replayed"
