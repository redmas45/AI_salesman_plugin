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
    assert "coverage" in notice["question"].lower()
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

    prompt = generic_prompt.build_generic_system_prompt(
        site_id="insurance_demo",
        vertical_key="insurance",
        knowledge_context='[ID:"plan:1"] Term Life | Type: insurance_plan',
        profile_context="No profile.",
    )

    assert "Vertical: Insurance" in prompt
    assert "SHOW_ENTITIES" in prompt
    assert "ADD_TO_CART" not in prompt
    assert "shopping cart" not in prompt.lower()


def test_llm_uses_generic_prompt_for_insurance_without_shopbot(monkeypatch):
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
    assert "ShopBot" not in prompt
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


def test_crm_prompt_profile_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    def fake_get(site_id: str):
        return {
            "profile": {"id": "profile_1", "site_id": site_id, "name": "Demo prompt"},
            "versions": [],
            "draft_version": None,
            "published_version": None,
            "active_version": None,
        }

    monkeypatch.setattr(crm.admin_db, "get_client_prompt_profile", fake_get)

    res = TestClient(app).get(
        "/v1/admin/clients/demo/prompt-profile",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["profile"]["site_id"] == "demo"


def test_crm_prompt_profile_save_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_save(site_id: str, **kwargs):
        captured.update({"site_id": site_id, **kwargs})
        return {
            "profile": {"id": "profile_1", "site_id": site_id, "name": kwargs["name"]},
            "versions": [{"id": "version_1", "version": 1, "status": "published"}],
            "draft_version": None,
            "published_version": {"id": "version_1", "version": 1, "status": "published"},
            "active_version": {"id": "version_1", "version": 1, "status": "published"},
        }

    monkeypatch.setattr(crm.admin_db, "save_client_prompt_profile", fake_save)

    res = TestClient(app).post(
        "/v1/admin/clients/demo/prompt-profile",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={
            "name": "Demo prompt",
            "system_prompt": "Use source data only.",
            "developer_rules": "Do not invent rates.",
            "publish": True,
        },
    )

    assert res.status_code == 200
    assert captured["publish"] is True
    assert captured["system_prompt"] == "Use source data only."


def test_crm_adapter_actions_save_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_update(site_id: str, actions: dict):
        captured.update({"site_id": site_id, "actions": actions})
        return {"site_id": site_id}

    monkeypatch.setattr(crm.admin_db, "update_client_adapter_actions", fake_update)
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {
            "site_id": site,
            "enabled": True,
            "vertical": {"key": "construction"},
            "adapter": {"actions": captured["actions"]},
        },
    )
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")
    monkeypatch.setattr(crm, "render_adapter_code", lambda runtime_config: "// adapter")

    res = TestClient(app).patch(
        "/v1/admin/clients/builder_demo/adapter/actions",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.quote"}}},
    )

    assert res.status_code == 200
    assert captured["site_id"] == "builder_demo"
    assert captured["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.quote"


def test_crm_adapter_action_review_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_review(site_id: str, candidate: dict, **kwargs):
        captured.update({"site_id": site_id, "candidate": candidate, **kwargs})
        return {"site_id": site_id}

    monkeypatch.setattr(crm.admin_db, "review_client_action_candidate", fake_review)
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {
            "site_id": site,
            "enabled": True,
            "vertical": {"key": "construction"},
            "adapter": {"action_reviews": [{"action": "REQUEST_ESTIMATE", "decision": "approve"}]},
        },
    )
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")
    monkeypatch.setattr(crm, "render_adapter_code", lambda runtime_config: "// adapter")

    res = TestClient(app).post(
        "/v1/admin/clients/builder_demo/adapter/action-candidates/review",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={
            "decision": "approve",
            "candidate": {
                "action": "REQUEST_ESTIMATE",
                "type": "click",
                "selector": "button.quote",
            },
        },
    )

    assert res.status_code == 200
    assert captured["site_id"] == "builder_demo"
    assert captured["decision"] == "approve"
    assert captured["candidate"]["selector"] == "button.quote"


def test_crm_adapter_action_proposal_refresh_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_refresh(site_id: str):
        captured["site_id"] = site_id
        return {"site_id": site_id}

    monkeypatch.setattr(crm.admin_db, "refresh_client_action_proposals", fake_refresh)
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {
            "site_id": site,
            "enabled": True,
            "vertical": {"key": "construction"},
            "adapter": {"action_proposals": [{"action": "REQUEST_ESTIMATE"}]},
        },
    )
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")
    monkeypatch.setattr(crm, "render_adapter_code", lambda runtime_config: "// adapter")

    res = TestClient(app).post(
        "/v1/admin/clients/builder_demo/adapter/action-proposals/refresh",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert captured["site_id"] == "builder_demo"


def test_crm_adapter_action_proposal_review_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_review(site_id: str, proposal: dict, **kwargs):
        captured.update({"site_id": site_id, "proposal": proposal, **kwargs})
        return {"site_id": site_id}

    monkeypatch.setattr(crm.admin_db, "review_client_action_proposal", fake_review)
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {
            "site_id": site,
            "enabled": True,
            "vertical": {"key": "construction"},
            "adapter": {"action_proposal_reviews": [{"action": "REQUEST_ESTIMATE", "decision": "approve"}]},
        },
    )
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")
    monkeypatch.setattr(crm, "render_adapter_code", lambda runtime_config: "// adapter")

    res = TestClient(app).post(
        "/v1/admin/clients/builder_demo/adapter/action-proposals/review",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={
            "decision": "approve",
            "proposal": {
                "action": "REQUEST_ESTIMATE",
                "config": {"type": "click", "selector": "button.quote", "confidence": 0.9},
            },
        },
    )

    assert res.status_code == 200
    assert captured["site_id"] == "builder_demo"
    assert captured["decision"] == "approve"
    assert captured["proposal"]["config"]["selector"] == "button.quote"


def test_crm_flow_repair_proposal_review_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_review(site_id: str, proposal: dict, **kwargs):
        captured.update({"site_id": site_id, "proposal": proposal, **kwargs})
        return {"site_id": site_id}

    monkeypatch.setattr(crm.admin_db, "review_client_flow_repair_proposal", fake_review)
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {
            "site_id": site,
            "enabled": True,
            "vertical": {"key": "construction"},
            "adapter": {"flow_repair_reviews": [{"proposal_key": "route:projects", "decision": "approve"}]},
        },
    )
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")
    monkeypatch.setattr(crm, "render_adapter_code", lambda runtime_config: "// adapter")

    res = TestClient(app).post(
        "/v1/admin/clients/builder_demo/adapter/flow-repair-proposals/review",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={
            "decision": "approve",
            "proposal": {
                "key": "route:projects",
                "kind": "route_repair",
                "scope": "route",
                "item": "projects",
                "patch": {"routes": {"projects": "/our-work"}},
            },
        },
    )

    assert res.status_code == 200
    assert captured["site_id"] == "builder_demo"
    assert captured["decision"] == "approve"
    assert captured["proposal"]["patch"]["routes"]["projects"] == "/our-work"


def test_crm_client_isolation_audit_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    monkeypatch.setattr(crm.admin_db, "get_client_detail", lambda site_id: {"site_id": site_id})
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {
            "site_id": site,
            "install": {
                "adapter_script": f"https://hub.example.com/shopbot-adapter.js?site={site}",
                "widget_script": f"https://hub.example.com/shopbot.js?site={site}",
            },
            "adapter": {},
        },
    )
    monkeypatch.setattr(
        crm.admin_db,
        "get_client_prompt_profile",
        lambda site_id: {
            "profile": {"id": "profile_1", "site_id": site_id},
            "versions": [{"id": "version_1", "profile_id": "profile_1"}],
        },
    )
    monkeypatch.setattr("db.knowledge.knowledge_stats", lambda site_id: {"active_items": 1})
    monkeypatch.setattr("db.knowledge.knowledge_preview", lambda site_id, limit: [{"id": "item_1"}])
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")

    res = TestClient(app).get(
        "/v1/admin/clients/builder_demo/isolation-audit",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["audit"]["status"] == "passed"
