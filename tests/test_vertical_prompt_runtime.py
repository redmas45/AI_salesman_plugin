import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import config
from agent import llm, orchestrator
from agent.actions.registry import is_supported_action
from agent.capabilities import action_filter_response_note, filter_actions, filter_actions_with_diagnostics, get_allowed_actions
from agent.verticals.registry import DEFAULT_VERTICAL_KEY
from db import prompts as prompt_db
from db.prompts import _allowed_prompt_actions
from agent.prompts import generic as generic_prompt
from agent.verticals.registry import list_verticals
from api import crm
from api.main import app
from api.models import ShopResponse


def _base_response(**overrides):
    data = {
        "transcript": "show plans",
        "response_text": "Here are the matching plans.",
        "intent": "discovery",
        "confidence": 0.9,
        "ui_actions": [],
        "audio_b64": "",
        "latency_ms": {},
    }
    data.update(overrides)
    return data


def test_insurance_prompt_actions_do_not_include_commerce():
    allowed = set(_allowed_prompt_actions("insurance"))

    assert "START_QUOTE" in allowed
    assert "HANDOFF_TO_AGENT" in allowed
    assert "ADD_TO_CART" not in allowed
    assert "CHECKOUT" not in allowed


def test_construction_prompt_actions_include_estimate_not_checkout():
    allowed = set(_allowed_prompt_actions("construction"))

    assert "REQUEST_ESTIMATE" in allowed
    assert "REQUEST_SITE_VISIT" in allowed
    assert "OPEN_PROJECTS" in allowed
    assert "ADD_TO_CART" not in allowed
    assert "CHECKOUT" not in allowed


def test_generic_prompt_has_no_cart_or_product_instructions(monkeypatch):
    monkeypatch.setattr(generic_prompt, "get_allowed_actions", lambda site_id: {"SHOW_ENTITIES", "START_QUOTE"})
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")
    monkeypatch.setattr(generic_prompt, "capability_prompt_context", lambda site_id: "")

    prompt = generic_prompt.build_generic_system_prompt(
        site_id="insurance_demo",
        vertical_key="insurance",
        knowledge_context='[ID:"plan:1"] Term Life | Type: insurance_plan',
        profile_context="No profile.",
    )

    assert "Vertical: Insurance" in prompt
    assert "SHOW_ENTITIES" in prompt
    assert "## Conversation Intelligence" in prompt
    assert "action field schema as the source of truth" in prompt
    assert "Never ask again for a required field already supplied" in prompt
    assert "ADD_TO_CART" not in prompt
    assert "shopping cart" not in prompt.lower()


def test_llm_uses_generic_prompt_for_insurance_without_mayabot(monkeypatch):
    captured = {}

    monkeypatch.setattr(llm, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(generic_prompt, "get_allowed_actions", lambda site_id: {"SHOW_ENTITIES", "START_QUOTE"})
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")
    monkeypatch.setattr(generic_prompt, "capability_prompt_context", lambda site_id: "")

    def fake_call(system_prompt: str, messages: list[dict]):
        captured["system_prompt"] = system_prompt
        captured["messages"] = messages
        return json.dumps(
            {
                "response_text": "I can compare the matching policy options.",
                "intent": "compare",
                "confidence": 0.9,
                "ui_actions": [],
            }
        )

    monkeypatch.setattr(llm, "_call_llm", fake_call)

    response = llm.generate_response(
        "insurance_demo",
        "compare term plans",
        [{"id": "plan:term", "title": "Term Cover", "entity_type": "insurance_plan"}],
        profile_context="No profile.",
    )

    prompt = captured["system_prompt"]
    assert response["intent"] == "compare"
    assert "Vertical: Insurance" in prompt
    assert "MayaBot" not in prompt
    assert "ADD_TO_CART" not in prompt
    assert "shopping cart" not in prompt.lower()


def test_llm_vertical_lookup_failure_defaults_to_generic(monkeypatch):
    def fail_lookup(site_id: str) -> str:
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(llm, "get_client_vertical_key", fail_lookup)

    assert llm._runtime_vertical_key("unknown_site") == DEFAULT_VERTICAL_KEY


def test_prompt_profile_missing_client_defaults_to_generic(monkeypatch):
    monkeypatch.setattr(prompt_db, "_client_row", lambda site_id: None)

    assert prompt_db._client_vertical_key("missing_site") == DEFAULT_VERTICAL_KEY


def test_non_ecommerce_cart_context_does_not_touch_cart_table(monkeypatch):
    def fail_cart(site_id: str):
        raise AssertionError("cart lookup should not run")

    monkeypatch.setattr(orchestrator, "get_cart_items", fail_cart)

    assert orchestrator._cart_context_for_site("insurance_demo", ecommerce_runtime=False).startswith("No ecommerce cart")


def test_vertical_lookup_failure_is_not_treated_as_ecommerce(monkeypatch):
    def fail_lookup(site_id: str) -> str:
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(orchestrator, "get_client_vertical_key", fail_lookup)

    assert orchestrator._is_ecommerce_site("unknown_site") is False


def test_generic_prompt_includes_current_page_context(monkeypatch):
    monkeypatch.setattr(generic_prompt, "get_allowed_actions", lambda site_id: {"START_QUOTE"})
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")
    monkeypatch.setattr(generic_prompt, "capability_prompt_context", lambda site_id: "")

    prompt = generic_prompt.build_generic_system_prompt(
        site_id="insurance_demo",
        vertical_key="insurance",
        knowledge_context='[ID:"plan:1"] Term Life | Type: insurance_plan',
        profile_context="No profile.",
        page_context=(
            "## Current Browser Page\n"
            "Path: /quote\n"
            "Forms:\n"
            "- Get Quote: Phone (tel), Coverage Type (select) options=Term, Health"
        ),
    )

    assert "## Current Browser Page" in prompt
    assert "Path: /quote" in prompt
    assert "Coverage Type (select)" in prompt


