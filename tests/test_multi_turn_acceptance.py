"""The multi-turn acceptance suite: 60 conversations across three verticals.

Every reported conversational failure was a continuity failure - a budget that
evaporated on the next turn, a correction that was ignored, a superlative
answered from the previous topic, a page question answered with a fresh search.
Single-utterance assertions cannot catch any of those, so this suite replays
whole conversations and asserts what the assistant resolved on each turn.

Two layers are exercised:

* every conversation runs through the authoritative ``TurnPlan`` and the
  deterministic catalog operations, with each vertical supplying its own brand,
  type, and category vocabulary - which is what proves the shared code carries no
  e-commerce assumption;
* a subset also runs end to end through the real orchestrator, so the actioned
  record ids and the spoken wording are asserted, not just the resolved plan.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.catalog import catalog_operations as ops  # noqa: E402
from agent.orchestration.turn_plan import build_turn_plan  # noqa: E402
from tests.acceptance_corpus import CONVERSATIONS, ECOMMERCE_CATALOG, VERTICALS  # noqa: E402

MIN_REQUIRED_SCENARIOS = 50
ECOMMERCE_SITE = "ecommerce_site"


def test_the_corpus_meets_the_required_breadth():
    verticals = {vertical for _name, vertical, _turns in CONVERSATIONS}

    assert len(CONVERSATIONS) >= MIN_REQUIRED_SCENARIOS, (
        f"{len(CONVERSATIONS)} conversations; the acceptance bar is {MIN_REQUIRED_SCENARIOS}"
    )
    assert verticals == {"ecommerce", "travel", "policy"}
    assert sum(1 for _n, _v, turns in CONVERSATIONS if len(turns) > 1) >= 10, (
        "continuity is the point; enough conversations must span several turns"
    )


def _plan_for(vertical: str, utterance: str, history: list[dict], page_state):
    fixture = VERTICALS[vertical]
    return build_turn_plan(
        utterance,
        site_id=f"{vertical}_site",
        vertical=vertical,
        history=history,
        page_state=page_state,
        catalog_brands=fixture["brands"],
        catalog_types=_type_vocabulary(fixture),
    )


def _type_vocabulary(fixture) -> tuple[str, ...]:
    if fixture["types"]:
        return fixture["types"]
    from agent.products.product_matching_lexical import BUILTIN_TYPE_NOUNS

    return tuple(BUILTIN_TYPE_NOUNS)


def _selected_ids(plan, vertical: str) -> list[str]:
    """The records this turn resolves to, after every hard constraint."""
    catalog = [dict(record) for record in VERTICALS[vertical]["catalog"]]
    categories = ops.matching_category_names(plan.constraints.raw_query, catalog)
    selection = ops.select_records(catalog, plan.constraints, category_names=categories)
    if plan.aggregate:
        return [str(record["id"]) for record in ops.aggregate_records(selection, plan.aggregate, limit=1)]
    return list(selection.ids())


def _is_off_topic(plan) -> bool:
    """Small talk resolves off-topic rather than becoming a catalog search."""
    from agent.retrieval.resolved_context import resolve_turn_context

    return resolve_turn_context(plan.constraints.raw_query).is_off_topic


def _assert_turn(plan, expectations: dict, vertical: str, label: str) -> None:
    checks = {
        "operation": lambda: (plan.operation.value, expectations["operation"]),
        "aggregate": lambda: (plan.aggregate, expectations["aggregate"]),
        "max_price": lambda: (plan.constraints.max_price, expectations["max_price"]),
        "min_price": lambda: (plan.constraints.min_price, expectations["min_price"]),
        "brands": lambda: (set(plan.constraints.brands), expectations["brands"]),
        "types": lambda: (set(plan.constraints.product_types), expectations["types"]),
        "recipient": lambda: (plan.constraints.recipient, expectations["recipient"]),
        "cacheable": lambda: (plan.cache_eligible, expectations["cacheable"]),
        "navigation": lambda: (plan.navigation_requested, expectations["navigation"]),
        "referents": lambda: (plan.referent_ids, expectations["referents"]),
        "clarify": lambda: (plan.constraints.should_ask_clarification(), expectations["clarify"]),
        "off_topic": lambda: (_is_off_topic(plan), expectations["off_topic"]),
        "categories": lambda: (
            ops.matching_category_names(plan.constraints.raw_query, VERTICALS[vertical]["catalog"]),
            expectations["categories"],
        ),
        "ids": lambda: (_selected_ids(plan, vertical), expectations["ids"]),
    }
    for key, resolve in checks.items():
        if key not in expectations:
            continue
        actual, expected = resolve()
        assert actual == expected, f"{label}: {key} resolved to {actual!r}, expected {expected!r}"


@pytest.mark.parametrize("scenario", CONVERSATIONS, ids=[name for name, _v, _t in CONVERSATIONS])
def test_conversation_resolves_every_turn_as_specified(scenario):
    name, vertical, turns = scenario
    history: list[dict] = []
    for index, turn in enumerate(turns):
        utterance, expectations = turn[0], turn[1]
        page_state = turn[2] if len(turn) > 2 else None
        plan = _plan_for(vertical, utterance, history, page_state)
        _assert_turn(plan, expectations, vertical, f"{name} turn {index + 1} ({utterance!r})")
        history.append({"role": "user", "content": utterance})
        history.append({"role": "assistant", "content": "Here is what I found."})


# --- End to end: actioned record ids and spoken wording ---------------------


@pytest.fixture
def orchestrated(monkeypatch):
    """The real pipeline with fixture data and no database or model provider."""
    import psycopg

    from agent import orchestrator
    from agent.runtime_helpers.retrieval_runtime import RetrievalContext

    def no_database(*_args, **_kwargs):
        raise psycopg.OperationalError("database intentionally unavailable in this suite")

    catalog = [dict(record) for record in ECOMMERCE_CATALOG]
    monkeypatch.setattr(psycopg, "connect", no_database)
    monkeypatch.setattr("db.core.database._get_connection", no_database)
    monkeypatch.setattr(
        "agent.retrieval.catalog_vocabulary.catalog_brand_vocabulary",
        lambda site_id: ("aster", "borel", "corvi", "delta"),
    )
    monkeypatch.setattr(
        "agent.action_helpers.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "ecommerce", "vertical_config_json": "{}"},
    )
    monkeypatch.setattr(
        "agent.guardrail_helpers.guardrails.product_exists",
        lambda site_id, product_id: str(product_id) in {record["id"] for record in catalog},
    )
    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: [dict(r) for r in catalog])
    monkeypatch.setattr(orchestrator, "get_catalog_records", lambda site_id, **kw: [dict(r) for r in catalog])
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(orchestrator, "_add_variant_ids_to_cart_actions", lambda site_id, actions: actions)
    monkeypatch.setattr(orchestrator, "_persist_preference_actions", lambda site_id, actions: None)
    monkeypatch.setattr(orchestrator, "_cart_context_for_site", lambda site_id, ecommerce: "")
    monkeypatch.setattr(
        orchestrator,
        "_apply_capability_filter_result",
        lambda site_id, actions: {"actions": list(actions), "removed": [], "status": "applied"},
    )
    monkeypatch.setattr(
        orchestrator,
        "_retrieve_context",
        lambda site_id, transcript, history, price_constraints=None: RetrievalContext(
            profile={}, price_constraints={}, products=[dict(r) for r in catalog]
        ),
    )
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("this turn must be answered deterministically, without the model")
        ),
    )
    return orchestrator


def _run(orchestrator, text, **kwargs):
    return orchestrator.run(site_id=ECOMMERCE_SITE, text_input=text, skip_tts=True, **kwargs)


def _actioned_ids(result) -> list[str]:
    ids: list[str] = []
    for action in result.get("ui_actions") or []:
        params = action.get("params") or {}
        ids.extend(str(pid) for pid in params.get("product_ids") or [])
        if params.get("product_id"):
            ids.append(str(params["product_id"]))
    return ids


END_TO_END = [
    ("what is the cheapest item in Fashion Women?", ["e1"], "Aster Slim Kurta"),
    ("which is your cheapest product?", ["e3"], "Borel Steel Bottle"),
    ("what is the most expensive smartphone?", ["e5"], "Corvi Smartphone X9"),
    ("which item has the best rating?", ["e3"], "Borel Steel Bottle"),
    ("what is the cheapest laptop?", ["e7"], "Delta Laptop Air"),
]


@pytest.mark.parametrize("utterance,expected_ids,expected_name", END_TO_END)
def test_deterministic_turns_action_and_name_the_same_record(
    orchestrated, utterance, expected_ids, expected_name
):
    result = _run(orchestrated, utterance)

    assert _actioned_ids(result) == expected_ids, utterance
    assert expected_name in result["response_text"], utterance


def test_mixed_aggregate_and_navigation_produces_both_requirements(orchestrated):
    result = _run(orchestrated, "show the cheapest smartphone and take me there")

    action_names = {str(action.get("action")) for action in result["ui_actions"]}
    assert "e6" in _actioned_ids(result), "the cheapest smartphone must be named"
    assert action_names & {"NAVIGATE_TO", "SHOW_PRODUCT_DETAIL"}, "the customer asked to be taken there"


def test_a_sold_out_record_is_never_offered_end_to_end(orchestrated):
    result = _run(orchestrated, "what is the cheapest item in Fashion Women?")

    assert "e8" not in _actioned_ids(result)
    assert "Sold Out" not in result["response_text"]


def test_count_answers_the_whole_catalog_not_a_window(orchestrated, monkeypatch):
    monkeypatch.setattr(orchestrated, "get_all_products", lambda site_id, limit=1000: [dict(ECOMMERCE_CATALOG[0])])

    result = _run(orchestrated, "how many smartphones do you have?")

    assert "3" in result["response_text"], "three smartphone records match the request"
