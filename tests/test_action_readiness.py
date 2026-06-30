"""Tests for generated action readiness summaries."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.action_readiness import action_readiness_for, action_readiness_prompt_context, sanitize_action_readiness
from agent import capabilities


def test_action_readiness_maps_required_params_to_vertical_question() -> None:
    vertical_config = {
        "actions": {
            "REQUEST_ESTIMATE": {
                "type": "sequence",
                "fields": ["project_scope", "phone"],
                "required_fields": ["project_scope", "phone"],
                "required_fields_known": True,
            }
        }
    }

    rows = action_readiness_for(vertical_config, "construction")

    assert rows[0]["action"] == "REQUEST_ESTIMATE"
    assert rows[0]["status"] == "requires_params"
    assert rows[0]["required_params"] == ("project_scope", "phone")
    assert "construction" in rows[0]["question"].lower()
    assert rows[0]["reason"]


def test_action_readiness_uses_sequence_params_when_field_list_missing() -> None:
    vertical_config = {
        "actions": {
            "START_BOOKING": {
                "type": "sequence",
                "steps": [
                    {"op": "fill", "selector": "input[name='destination']", "param": "destination"},
                    {"op": "select", "selector": "select[name='date']", "param": "date"},
                    {"op": "click", "selector": "button.book"},
                ],
            }
        }
    }

    context = action_readiness_prompt_context(vertical_config, "travel")

    assert "START_BOOKING requires destination, date" in context
    assert "What dates or date flexibility should I use?" in context


def test_action_readiness_sanitizer_drops_unknown_actions() -> None:
    rows = sanitize_action_readiness(
        [
            {"action": "REQUEST_ESTIMATE", "status": "requires_params", "required_params": ["phone"]},
            {"action": "HACK", "status": "requires_params", "required_params": ["secret"]},
        ]
    )

    assert rows == [
        {
            "action": "REQUEST_ESTIMATE",
            "status": "requires_params",
            "required_params": ["phone"],
            "optional_params": [],
            "question": "",
            "reason": "",
        }
    ]


def test_capability_prompt_context_includes_action_readiness(monkeypatch) -> None:
    vertical_config = {
        "actions": {
            "REQUEST_ESTIMATE": {
                "type": "form",
                "fields": ["phone"],
                "required_fields": ["phone"],
                "required_fields_known": True,
            }
        }
    }
    monkeypatch.setattr(
        capabilities.admin_db,
        "_client_row",
        lambda site_id: {"vertical_key": "construction", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr(capabilities.admin_db, "get_readiness_report", lambda site_id: None)

    context = capabilities.capability_prompt_context("builder_demo")

    assert "Action REQUEST_ESTIMATE requires params: phone." in context
    assert "Action readiness before execution:" in context
    assert "REQUEST_ESTIMATE requires phone before emitting the action." in context
