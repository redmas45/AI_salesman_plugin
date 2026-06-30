"""Tests for vertical-aware sales intake planning."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.prompts.generic import build_generic_system_prompt
from agent.sales_intake import intake_questions_for, sales_intake_prompt_context, sanitize_intake_questions
from agent.verticals.registry import list_verticals


def test_every_registered_vertical_has_sales_intake_questions() -> None:
    missing = [vertical.key for vertical in list_verticals() if not intake_questions_for(vertical.key)]

    assert missing == []


def test_high_risk_intake_context_requires_professional_handoff() -> None:
    context = sales_intake_prompt_context("insurance")

    assert "## Sales Intake Plan" in context
    assert "Coverage need" in context
    assert "licensed advisor" in context or "professional handoff" in context
    assert "passwords" in context
    assert "card numbers" in context


def test_generic_prompt_includes_vertical_intake_plan(monkeypatch) -> None:
    monkeypatch.setattr("agent.prompts.generic.get_allowed_actions", lambda site_id: {"SHOW_ENTITIES", "REQUEST_ESTIMATE"})
    monkeypatch.setattr("agent.prompts.generic.prompt_profile_context", lambda site_id: "")
    monkeypatch.setattr("agent.prompts.generic.capability_prompt_context", lambda site_id: "")

    prompt = build_generic_system_prompt(
        site_id="builder_demo",
        vertical_key="construction",
        knowledge_context='[ID:"service:1"] Renovation | Type: construction_service',
        profile_context="No profile.",
    )

    assert "Vertical: Construction" in prompt
    assert "## Sales Intake Plan" in prompt
    assert "Project scope" in prompt
    assert "REQUEST_ESTIMATE" in prompt
    assert "card numbers" in prompt


def test_intake_question_sanitizer_drops_bad_rows() -> None:
    rows = sanitize_intake_questions(
        [
            {"key": "goal", "label": "Goal", "question": "What do you need?", "why": "Routes flow.", "actions": ["CAPTURE_LEAD"], "required": True},
            {"key": "", "question": "bad"},
            "bad",
        ]
    )

    assert rows == [
        {
            "key": "goal",
            "label": "Goal",
            "question": "What do you need?",
            "why": "Routes flow.",
            "actions": ["CAPTURE_LEAD"],
            "required": True,
        }
    ]
