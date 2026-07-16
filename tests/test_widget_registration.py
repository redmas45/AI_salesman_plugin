"""Public widget installer and adapter runtime contract tests."""

import sys
from pathlib import Path

import pytest
from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import clients as client_routes
from agent import client_initialization
from agent.actions.registry import list_action_names
from agent.adapter_discovery import build_discovery
from agent.barrier_policy import build_barrier_action_policy
from agent.ingestion import _build_candidates_from_html
from agent.verticals.discovery_profiles import knowledge_entity_type_for, list_discovery_profiles
from agent.verticals.registry import list_verticals
from db import clients as client_db


def _mock_durable_action_events(monkeypatch, initial: list[dict] | None = None) -> list[dict]:
    events = list(initial or [])

    def insert_event(site_id: str, event: dict) -> None:
        events.insert(0, {**event, "site_id": site_id})

    def list_events(site_ids, *, limit: int = 500):
        return {site_id: events[:limit] for site_id in site_ids}

    monkeypatch.setattr(client_db, "_insert_client_action_event", insert_event)
    monkeypatch.setattr(client_db, "record_audit_event", lambda **kwargs: None)
    monkeypatch.setattr(client_db, "list_client_action_events", list_events)
    return events


def test_runtime_capabilities_refresh_and_are_whitelisted() -> None:
    existing = {
        "runtime_capabilities": {"script_loaded": True, "microphone_permission": "denied"},
    }
    fresh = {
        "runtime_capabilities": {
            "script_loaded": True,
            "microphone_permission": "prompt",
            "secure_context": True,
            "iframe_count": 99999,
            "field_value": "secret",
        },
    }

    cleaned = client_routes._validated_runtime_capabilities(fresh["runtime_capabilities"])
    merged = client_db._merge_discovery_vertical_config(existing, {"runtime_capabilities": cleaned}, vertical_changed=False)

    assert merged["runtime_capabilities"]["microphone_permission"] == "prompt"
    assert merged["runtime_capabilities"]["iframe_count"] == 10000
    assert "field_value" not in merged["runtime_capabilities"]


def test_registration_keeps_existing_vertical_on_weak_generic_rediscovery(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "generic"
        confidence = 0.45
        vertical_config = {
            "actions": {"CAPTURE_LEAD": {"type": "form", "selector": "form.contact"}},
            "prompt_suggestions": ["Help me send an enquiry."],
            "intake_questions": [{"key": "goal", "question": "What do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {}
        prompt = "generic prompt"
        developer_rules = "generic rules"

    captured: dict[str, object] = {}
    existing_client = {
        "site_id": "policy_site",
        "vertical_key": "insurance",
        "last_crawl_status": client_db.CRAWL_STATUS_RUNNING,
        "catalog": {"active_products": 5},
    }

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: existing_client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: captured.setdefault("update", kwargs) or {**existing_client, "vertical_key": kwargs["vertical_key"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)

    response = client_routes._process_widget_registration(
        client_routes.WidgetRegisterRequest(
            site_id="policy_site",
            origin="https://policy.example.com",
            url="https://policy.example.com/contact",
            title="Contact us",
        ),
        BackgroundTasks(),
    )

    update = captured["update"]
    vertical_config = update["vertical_config"]
    assert update["vertical_key"] == "insurance"
    assert "actions" not in vertical_config
    assert "prompt_suggestions" not in vertical_config
    assert "intake_questions" not in vertical_config
    assert vertical_config["discovery"]["detected_vertical_key"] == "generic"
    assert vertical_config["discovery"]["applied_vertical_key"] == "insurance"
    assert response["vertical_key"] == "insurance"
    assert response["detected_vertical_key"] == "generic"
    assert response["actions"] == []


def test_registration_upgrades_generic_client_on_confident_vertical() -> None:
    decision = client_routes._registration_vertical_decision(
        {"vertical_key": "generic"},
        "construction",
        0.72,
    )
    vertical_config = client_routes._registration_vertical_config(
        {
            "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
            "prompt_suggestions": ["Help me request an estimate."],
            "intake_questions": [{"key": "project", "question": "What project do you need?"}],
            "discovery": {"source": "widget_register"},
        },
        {"script_loaded": True},
        decision,
    )

    assert decision["applied_vertical_key"] == "construction"
    assert decision["apply_generated_actions"] is True
    assert "REQUEST_ESTIMATE" in vertical_config["actions"]
    assert vertical_config["intake_questions"][0]["key"] == "project"
    assert vertical_config["runtime_capabilities"]["script_loaded"] is True
    assert vertical_config["discovery"]["vertical_decision"] == "generic_upgraded_from_confident_discovery"


def test_widget_registration_creates_available_client_without_integration(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "insurance"
        confidence = 0.82
        vertical_config = {
            "actions": {"SHOW_ENTITIES": {"type": "navigate", "path": "/plans"}},
            "prompt_suggestions": ["Help me compare insurance plans."],
            "intake_questions": [{"key": "coverage", "question": "What coverage do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {"buttons": []}
        prompt = "insurance prompt"
        developer_rules = "insurance rules"

    scheduled: list[object] = []
    discovered: dict[str, object] = {}
    available_client = {
        "site_id": "policy_site",
        "name": "Policy Site",
        "store_url": "https://policy.example.com",
        "vertical_key": "insurance",
        "status": client_db.CLIENT_STATUS_AVAILABLE,
        "last_crawl_status": client_db.CRAWL_STATUS_NOT_STARTED,
        "catalog": {"active_products": 0},
        "vertical_config": {},
    }

    class FakeBackgroundTasks:
        def add_task(self, *args, **kwargs):
            scheduled.append((args, kwargs))

    def fake_discover_available_client(**kwargs):
        discovered.update(kwargs)
        return available_client

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: (_ for _ in ()).throw(LookupError()))
    monkeypatch.setattr(client_routes.admin_db, "discover_available_client", fake_discover_available_client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: {**available_client, "vertical_key": kwargs["vertical_key"], "vertical_config": kwargs["vertical_config"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)
    monkeypatch.setattr(client_routes, "_seed_generated_prompt_once", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available clients must not auto-crawl")),
    )

    response = client_routes._process_widget_registration(
        client_routes.WidgetRegisterRequest(
            site_id="policy_site",
            origin="https://policy.example.com",
            url="https://policy.example.com/plans",
            title="Policy Site",
        ),
        FakeBackgroundTasks(),
    )

    assert discovered["site_id"] == "policy_site"
    assert discovered["store_url"] == "https://policy.example.com"
    assert response["vertical_key"] == "insurance"
    assert response["crawl_scheduled"] is False
    assert response["flow_scheduled"] is False
    assert response["rehearsal_scheduled"] is False
    assert scheduled == []


def test_widget_registration_rejects_existing_client_origin_change(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "insurance"
        confidence = 0.82
        vertical_config = {
            "actions": {"START_QUOTE": {"type": "navigate", "path": "/insurance/health"}},
            "prompt_suggestions": ["Help me compare insurance plans."],
            "intake_questions": [{"key": "coverage", "question": "What coverage do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {"buttons": []}
        prompt = "insurance prompt"
        developer_rules = "insurance rules"

    existing_client = {
        "site_id": "policy_website",
        "name": "Policy Website",
        "store_url": "http://127.0.0.1:5183",
        "allowed_origin": "http://127.0.0.1:5183",
        "deploy_mode": client_db.DEFAULT_DEPLOY_MODE,
        "plan": client_db.DEFAULT_PLAN,
        "vertical_key": "insurance",
        "status": client_db.CLIENT_STATUS_AVAILABLE,
        "last_crawl_status": client_db.CRAWL_STATUS_NOT_STARTED,
        "catalog": {"active_products": 0},
        "vertical_config": {},
    }
    refreshed: dict[str, object] = {}

    def fake_discover_available_client(**kwargs):
        refreshed.update(kwargs)
        return {**existing_client, "store_url": kwargs["store_url"], "allowed_origin": kwargs["store_url"]}

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: existing_client)
    monkeypatch.setattr(client_routes.admin_db, "discover_available_client", fake_discover_available_client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: {**existing_client, "vertical_key": kwargs["vertical_key"], "vertical_config": kwargs["vertical_config"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)
    monkeypatch.setattr(client_routes, "_seed_generated_prompt_once", lambda *args, **kwargs: None)

    with pytest.raises(client_routes.HTTPException) as exc_info:
        client_routes._process_widget_registration(
            client_routes.WidgetRegisterRequest(
                site_id="policy_website",
                origin="http://localhost:5173",
                url="http://localhost:5173/insurance/health",
                title="Policy Website",
            ),
            BackgroundTasks(),
        )

    assert exc_info.value.status_code == 403
    assert refreshed == {}


def test_widget_registration_initialization_plan_is_manual() -> None:
    plan = client_routes._manual_registration_initialization_plan()

    assert plan == {"crawl": False, "flow": False, "rehearsal": False}


def test_current_clients_do_not_schedule_auto_initialization_from_widget_registration(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "construction"
        confidence = 0.88
        vertical_config = {
            "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
            "prompt_suggestions": ["Help me request an estimate."],
            "intake_questions": [{"key": "project_type", "question": "What project do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {"buttons": ["button.estimate"]}
        prompt = "construction prompt"
        developer_rules = "construction rules"

    scheduled: list[object] = []
    client = {
        "site_id": "builder_demo",
        "vertical_key": "construction",
        "status": client_db.CLIENT_STATUS_LIVE,
        "last_crawl_status": client_db.CRAWL_STATUS_NOT_STARTED,
        "catalog": {"active_products": 0},
        "vertical_config": {},
    }

    class FakeBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            scheduled.append((func, args, kwargs))

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: {**client, "vertical_key": kwargs["vertical_key"], "vertical_config": kwargs["vertical_config"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)
    monkeypatch.setattr(client_routes, "_seed_generated_prompt_once", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("widget registration must not auto-crawl")),
    )

    response = client_routes._process_widget_registration(
        client_routes.WidgetRegisterRequest(
            site_id="builder_demo",
            origin="https://builder.example.com",
            url="https://builder.example.com/estimate",
            title="Builder Demo",
        ),
        FakeBackgroundTasks(),
    )

    assert response["vertical_key"] == "construction"
    assert response["crawl_scheduled"] is False
    assert response["flow_scheduled"] is False
    assert response["rehearsal_scheduled"] is False
    assert scheduled == []


def test_widget_initialization_job_persists_flow_rehearsal_and_report(monkeypatch) -> None:
    saved_reports: list[dict[str, object]] = []
    saved_flow: dict[str, object] = {}
    saved_rehearsal: dict[str, object] = {}
    saved_regression: dict[str, object] = {}

    class FakeFlow:
        def to_dict(self):
            return {
                "site_id": "builder_demo",
                "site_url": "https://builder.example.com",
                "vertical_key": "construction",
                "detected_vertical_key": "construction",
                "confidence": 0.9,
                "engine": "test",
                "summary": {"pages": 2, "actions": 1},
                "adapter_actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
            }

    class FakeRehearsal:
        def to_dict(self):
            return {
                "site_id": "builder_demo",
                "site_url": "https://builder.example.com",
                "engine": "test",
                "summary": {"total": 1, "supported": 1, "blocked": 0},
                "steps": [],
            }

    async def fake_discover_site_flows(*args, **kwargs):
        return FakeFlow()

    async def fake_rehearse_site_flows(*args, **kwargs):
        return FakeRehearsal()

    monkeypatch.setattr(client_initialization.admin_db, "get_client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(client_initialization.admin_db, "setup_cancel_requested", lambda site_id, run_id: False)
    monkeypatch.setattr(client_initialization, "discover_site_flows", fake_discover_site_flows)
    monkeypatch.setattr(client_initialization, "rehearse_site_flows", fake_rehearse_site_flows)
    monkeypatch.setattr(client_initialization.admin_db, "save_client_flow_report", lambda site_id, report: saved_flow.update(report))
    monkeypatch.setattr(
        client_initialization.admin_db,
        "save_client_rehearsal_report",
        lambda site_id, report: saved_rehearsal.update(report),
    )
    monkeypatch.setattr(
        client_initialization.admin_db,
        "save_client_regression_report",
        lambda site_id, report: saved_regression.update(report),
    )
    monkeypatch.setattr(
        client_initialization.admin_db,
        "save_client_initialization_report",
        lambda site_id, report: saved_reports.append(report),
    )

    report = client_initialization.run_widget_initialization(
        "builder_demo",
        "https://builder.example.com",
        vertical_key="construction",
        run_crawl=False,
        run_flow=True,
        run_rehearsal=True,
        crawl_max_pages=1,
        crawl_max_depth=1,
        run_readiness=False,
    )

    assert report["status"] == "ok"
    assert saved_flow["vertical_key"] == "construction"
    assert saved_rehearsal["summary"]["supported"] == 1
    assert saved_regression["site_id"] == "builder_demo"
    assert saved_reports[0]["status"] == "running"
    assert saved_reports[-1]["status"] == "ok"


def test_widget_register_model_preserves_form_fields() -> None:
    req = client_routes.WidgetRegisterRequest(
        site_id="Policy Website",
        origin="https://policy.example.com",
        url="https://policy.example.com/",
        forms=[
            {
                "label": "Get insurance quote",
                "selector": "form.quote",
                "input_selector": "input[name='phone']",
                "submit_selector": "button.get-quote",
                "fields": [
                    {"selector": "input[name='name']", "name": "Full name", "type": "text"},
                    {
                        "selector": "input[name='phone']",
                        "name": "Phone",
                        "label": "Mobile number",
                        "type": "tel",
                        "autocomplete": "tel",
                        "required": True,
                        "options": [{"label": "Mobile", "value": "mobile"}],
                    },
                ],
            }
        ],
        runtime_capabilities={"script_loaded": True, "microphone_permission": "prompt"},
    )

    payload = req.model_dump()

    assert payload["forms"][0]["fields"][0]["name"] == "Full name"
    assert payload["forms"][0]["fields"][1]["label"] == "Mobile number"
    assert payload["forms"][0]["fields"][1]["required"] is True
    assert payload["forms"][0]["fields"][1]["options"][0]["label"] == "Mobile"
    assert payload["runtime_capabilities"]["microphone_permission"] == "prompt"


def test_widget_register_model_trims_verbose_discovery_element_text() -> None:
    verbose_label = "Who do you want to insure? " + " ".join(f"{age} years" for age in range(18, 81))

    req = client_routes.WidgetRegisterRequest(
        site_id="policy_website",
        origin="https://policy.example.com",
        url="https://policy.example.com/",
        forms=[
            {
                "label": verbose_label,
                "selector": "form.quote",
                "input_selector": "input[name='city']",
                "submit_selector": "button.get-quote",
            }
        ],
    )

    payload = req.model_dump()

    assert len(payload["forms"][0]["label"]) == client_routes.MAX_DISCOVERY_LABEL_LENGTH
    assert payload["forms"][0]["label"] == verbose_label[: client_routes.MAX_DISCOVERY_LABEL_LENGTH]


