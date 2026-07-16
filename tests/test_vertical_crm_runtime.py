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
                "adapter_script": f"https://hub.example.com/mayabot-adapter.js?site={site}",
                "widget_script": f"https://hub.example.com/mayabot.js?site={site}",
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

