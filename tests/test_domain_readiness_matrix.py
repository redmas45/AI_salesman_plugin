"""Universal readiness matrix for README-supported domains."""

from __future__ import annotations

import pytest

from agent import capabilities, client_initialization, orchestrator
from agent.actions.registry import get_action, normalize_action_name
from agent.verticals.discovery_profiles import get_discovery_profile
from agent.verticals.registry import list_verticals
from api.models import ACTION_SHOW_ENTITIES, ENTITY_IDS_PARAM


VERTICALS = list_verticals()
NON_ECOMMERCE_VERTICALS = [vertical for vertical in VERTICALS if vertical.key != "ecommerce"]


@pytest.mark.parametrize("vertical", VERTICALS, ids=lambda vertical: vertical.key)
def test_vertical_baseline_allows_its_discovery_profile_actions(monkeypatch: pytest.MonkeyPatch, vertical) -> None:
    """Every vertical's own discovery profile must survive capability filtering."""
    _patch_capability_client(monkeypatch, vertical.key)

    profile_actions = _profile_actions(get_discovery_profile(vertical.key))
    allowed_actions = capabilities.get_allowed_actions(f"{vertical.key}_demo")
    missing_actions = sorted(profile_actions - allowed_actions)

    assert not missing_actions


@pytest.mark.parametrize("vertical", VERTICALS, ids=lambda vertical: vertical.key)
def test_fallback_smoke_cases_have_allowed_actions_for_every_vertical(
    monkeypatch: pytest.MonkeyPatch,
    vertical,
) -> None:
    """Setup smoke tests must ask for actions the vertical can actually emit."""
    _patch_capability_client(monkeypatch, vertical.key)

    allowed_actions = capabilities.get_allowed_actions(f"{vertical.key}_demo")
    cases = client_initialization._fallback_assistant_smoke_cases(vertical.key)

    assert cases
    for case in cases:
        expected_actions = {normalize_action_name(action) for action in case.get("expected_actions", [])}
        invalid_actions = sorted(action for action in expected_actions if get_action(action) is None)
        actionable_matches = sorted(expected_actions & allowed_actions)

        assert not invalid_actions
        assert actionable_matches, case["name"]


@pytest.mark.parametrize("vertical", NON_ECOMMERCE_VERTICALS, ids=lambda vertical: vertical.key)
def test_non_commerce_fact_answer_fallback_shows_source_records_for_every_vertical(
    monkeypatch: pytest.MonkeyPatch,
    vertical,
) -> None:
    """If the LLM gives a weak answer, Maya still shows source-backed records."""
    site_id = f"{vertical.key}_demo"
    item_id = f"{vertical.key}:primary"
    item = {
        "id": item_id,
        "title": f"{vertical.default_plan_label} A",
        "entity_type": vertical.entity_types[0],
        "summary": f"Published source-backed details for {vertical.entity_label_singular}.",
    }

    _patch_capability_client(monkeypatch, vertical.key)
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda _site_id: vertical.key)
    monkeypatch.setattr(orchestrator, "get_user_profile", lambda _site_id: {})
    monkeypatch.setattr(
        "agent.retrieval.generic_rag.retrieve_knowledge",
        lambda _query, *, site_id: [item],
    )
    monkeypatch.setattr(
        "db.knowledge.knowledge_stats",
        lambda _site_id: {
            "total_items": 1,
            "active_items": 1,
            "missing_embeddings": 0,
            "entity_types": 1,
        },
    )
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "Let me check that for you.",
            "intent": "unknown",
            "confidence": 0.3,
            "ui_actions": [],
        },
    )

    result = orchestrator.run(
        site_id=site_id,
        text_input=f"Why should I choose this {vertical.entity_label_singular}?",
        audio_filename="matrix-smoke.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["ui_actions"] == [
        {"action": ACTION_SHOW_ENTITIES, "params": {ENTITY_IDS_PARAM: [item_id]}}
    ]
    assert item["title"] in result["response_text"]
    assert result["retrieval"]["issue"] == "ok"


def _profile_actions(profile) -> set[str]:
    actions = {
        normalize_action_name(profile.form_action),
        *(normalize_action_name(action) for action in profile.primary_actions),
        *(normalize_action_name(action) for action in profile.route_actions.values()),
        *(normalize_action_name(action) for action in profile.action_labels),
    }
    return {action for action in actions if action}


def _patch_capability_client(monkeypatch: pytest.MonkeyPatch, vertical_key: str) -> None:
    monkeypatch.setattr(
        capabilities.admin_db,
        "_client_row",
        lambda _site_id: {"vertical_key": vertical_key, "vertical_config_json": "{}"},
    )
    monkeypatch.setattr(capabilities.admin_db, "get_readiness_report", lambda _site_id: None)
