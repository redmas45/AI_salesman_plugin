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


def test_all_vertical_actions_are_registered():
    missing = {
        action
        for vertical in list_verticals()
        for action in vertical.action_types
        if not is_supported_action(action)
    }

    assert missing == set()


def test_shop_response_accepts_generic_entity_action():
    response = ShopResponse(
        **_base_response(
            ui_actions=[
                {
                    "action": "show_entities",
                    "params": {"entity_ids": ["insurance_plan:term-life"]},
                }
            ]
        )
    )

    assert response.ui_actions[0].action == "SHOW_ENTITIES"


def test_ecommerce_no_scan_keeps_legacy_action_set(monkeypatch):
    monkeypatch.setattr("agent.capabilities.admin_db._client_row", lambda site_id: {"vertical_key": "ecommerce"})
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    assert get_allowed_actions("ai_kart") == set(config.VALID_UI_ACTIONS)


def test_non_ecommerce_no_scan_uses_vertical_actions(monkeypatch):
    monkeypatch.setattr("agent.capabilities.admin_db._client_row", lambda site_id: {"vertical_key": "insurance"})
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    allowed = get_allowed_actions("insurance_demo")

    assert "START_QUOTE" in allowed
    assert "HANDOFF_TO_AGENT" in allowed
    assert "CHECKOUT" not in allowed


def test_capability_lookup_failure_uses_generic_actions(monkeypatch):
    def fail_client(site_id: str):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr("agent.capabilities.admin_db._client_row", fail_client)
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    allowed = get_allowed_actions("unknown_site")

    assert "HANDOFF_TO_HUMAN" in allowed
    assert "CHECKOUT" not in allowed


def test_configured_adapter_actions_constrain_runtime_actions(monkeypatch):
    vertical_config = {
        "actions": {
            "REQUEST_ESTIMATE": {"type": "form", "input": "input[name='phone']"},
            "REQUEST_SITE_VISIT": {"type": "click", "selector": "button.site-visit"},
        },
        "validation": {
            "actions": {
                "REQUEST_ESTIMATE": {"supported": True, "status": "ok"},
                "REQUEST_SITE_VISIT": {"supported": False, "status": "missing"},
            }
        },
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "construction", "vertical_config_json": json.dumps(vertical_config)},
    )

    allowed = get_allowed_actions("builder_demo")

    assert "REQUEST_ESTIMATE" in allowed
    assert "REQUEST_SITE_VISIT" not in allowed
    assert "CHECKOUT" not in allowed


def test_barrier_policy_blocks_configured_final_actions_and_adds_handoff(monkeypatch):
    vertical_config = {
        "actions": {
            "REQUEST_ESTIMATE": {"type": "form", "input": "input[name='phone']"},
            "REQUEST_SITE_VISIT": {"type": "click", "selector": "button.site-visit"},
        },
        "barriers": {
            "findings": [
                {
                    "key": "captcha",
                    "severity": "high",
                    "handling": "Use human handoff for challenged forms.",
                }
            ]
        },
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "construction", "vertical_config_json": json.dumps(vertical_config)},
    )

    allowed = get_allowed_actions("builder_demo")

    assert "REQUEST_ESTIMATE" not in allowed
    assert "REQUEST_SITE_VISIT" not in allowed
    assert "HANDOFF_TO_HUMAN" in allowed
    assert "SHOW_ENTITIES" in allowed


def test_auth_barrier_allows_reversible_ecommerce_cart_prep(monkeypatch):
    vertical_config = {
        "barriers": {
            "findings": [
                {
                    "key": "auth_required",
                    "severity": "high",
                    "handling": "Require login before checkout.",
                }
            ]
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "ecommerce", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: {})

    allowed = get_allowed_actions("shop_demo")

    assert "ADD_TO_CART" in allowed
    assert "CHECKOUT" not in allowed
    assert "CHECKOUT_HANDOFF" in allowed


def test_barrier_policy_blocks_insurance_quote_in_prompt_context(monkeypatch):
    vertical_config = {
        "barriers": {
            "findings": [
                {
                    "key": "auth_required",
                    "severity": "high",
                    "handling": "Require logged-in user before quote flow.",
                }
            ]
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")

    allowed = get_allowed_actions("insurance_demo")
    prompt = generic_prompt.build_generic_system_prompt(
        site_id="insurance_demo",
        vertical_key="insurance",
        knowledge_context='[ID:"plan:1"] Term Life | Type: insurance_plan',
    )

    assert "START_QUOTE" not in allowed
    assert "HANDOFF_TO_AGENT" in allowed or "HANDOFF_TO_LICENSED_AGENT" in allowed
    assert "Blocked UI actions" in prompt
    assert "START_QUOTE" in prompt


def test_prompt_context_includes_configured_action_required_params(monkeypatch):
    vertical_config = {
        "actions": {
            "START_QUOTE": {
                "type": "form",
                "form": "form.quote",
                "fields": ["coverage_type", "full_name", "phone"],
                "required_fields": ["phone"],
                "field_schema": [
                    {
                        "param": "coverage_type",
                        "label": "Coverage Type",
                        "type": "select",
                        "required": False,
                        "options": [
                            {"label": "Individual", "value": "individual"},
                            {"label": "Family", "value": "family"},
                        ],
                    },
                    {"param": "phone", "label": "Phone", "type": "tel", "required": True},
                ],
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")

    prompt = generic_prompt.build_generic_system_prompt(
        site_id="insurance_demo",
        vertical_key="insurance",
        knowledge_context='[ID:"plan:1"] Term Life | Type: insurance_plan',
    )

    assert "Action START_QUOTE requires params: phone." in prompt
    assert "Action START_QUOTE accepts params:" in prompt
    assert "coverage_type (Coverage Type, select, optional, choices: Individual | Family)" in prompt
    assert "requires params: coverage_type" not in prompt
    assert "ask follow-up questions before emitting the action" in prompt


def test_prompt_context_respects_known_empty_required_params(monkeypatch):
    vertical_config = {
        "actions": {
            "START_QUOTE": {
                "type": "form",
                "form": "form.quote",
                "fields": ["full_name", "phone"],
                "required_fields": [],
                "required_fields_known": True,
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")

    prompt = generic_prompt.build_generic_system_prompt(
        site_id="insurance_demo",
        vertical_key="insurance",
        knowledge_context='[ID:"plan:1"] Term Life | Type: insurance_plan',
    )

    assert "Action START_QUOTE requires params" not in prompt
    assert "Allowed UI actions" in prompt


def test_filter_actions_removes_configured_action_missing_required_params(monkeypatch):
    vertical_config = {
        "actions": {
            "START_QUOTE": {
                "type": "form",
                "form": "form.quote",
                "fields": ["full_name", "phone"],
                "required_fields": ["phone"],
                "required_fields_known": True,
                "field_schema": [
                    {"param": "phone", "label": "Phone", "type": "tel", "required": True},
                ],
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    actions = [{"action": "START_QUOTE", "params": {"full_name": "Ana"}}]

    assert filter_actions("insurance_demo", actions) == []


def test_filter_actions_reports_missing_required_params(monkeypatch):
    vertical_config = {
        "actions": {
            "START_QUOTE": {
                "type": "form",
                "form": "form.quote",
                "fields": ["coverage_type", "phone"],
                "required_fields": ["phone"],
                "required_fields_known": True,
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    report = filter_actions_with_diagnostics("insurance_demo", [{"action": "START_QUOTE", "params": {}}])
    notice = report["removed_actions"][0]

    assert report["actions"] == []
    assert notice["reason"] == "missing_required_params"
    assert notice["missing_params"] == ("phone",)
    assert "phone" in notice["question"].lower()
    assert "one more detail" in action_filter_response_note(report)


def test_filter_actions_keeps_configured_action_with_required_param_alias(monkeypatch):
    vertical_config = {
        "actions": {
            "START_QUOTE": {
                "type": "form",
                "form": "form.quote",
                "fields": ["full_name", "phone"],
                "required_fields": ["phone"],
                "required_fields_known": True,
                "field_schema": [
                    {"param": "phone", "label": "Phone", "type": "tel", "required": True},
                ],
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    actions = [{"action": "START_QUOTE", "params": {"Phone": "555-0100"}}]

    assert filter_actions("insurance_demo", actions) == actions


def test_filter_actions_respects_known_empty_required_params(monkeypatch):
    vertical_config = {
        "actions": {
            "START_QUOTE": {
                "type": "form",
                "form": "form.quote",
                "fields": ["full_name", "phone"],
                "required_fields": [],
                "required_fields_known": True,
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    actions = [{"action": "START_QUOTE", "params": {}}]

    assert filter_actions("insurance_demo", actions) == actions


def test_filter_actions_requires_sequence_params_when_value_is_not_configured(monkeypatch):
    vertical_config = {
        "actions": {
            "REQUEST_ESTIMATE": {
                "type": "sequence",
                "steps": [
                    {"op": "fill", "selector": "input[name='phone']", "param": "phone"},
                    {"op": "click", "selector": "button[type='submit']"},
                ],
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "construction", "vertical_config_json": json.dumps(vertical_config)},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    missing = [{"action": "REQUEST_ESTIMATE", "params": {}}]
    complete = [{"action": "REQUEST_ESTIMATE", "params": {"phone": "555-0100"}}]

    assert filter_actions("builder_demo", missing) == []
    assert filter_actions("builder_demo", complete) == complete


