import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import config
from agent.actions.registry import is_supported_action
from agent.capabilities import get_allowed_actions
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
