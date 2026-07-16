"""Public widget installer and adapter runtime contract tests."""

import sys
from pathlib import Path

import pytest
from fastapi import BackgroundTasks
from starlette.requests import Request

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


def test_widget_browser_origin_must_match_claimed_payload_origin() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/widget/action-event",
            "headers": [(b"origin", b"https://attacker.example")],
        }
    )

    with pytest.raises(client_routes.HTTPException) as exc_info:
        client_routes.client_security.require_claimed_browser_origin(
            request,
            "https://client.example",
            client_routes._safe_script_base_url,
        )

    assert exc_info.value.status_code == 403


def test_widget_action_report_checks_origin_and_saves_validation(monkeypatch) -> None:
    saved = {}

    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {
            "site_id": site,
            "allowed_origin": "https://builder.example.com",
            "vertical_config": {
                "validation": {"summary": {"total": 1, "supported": 1}},
            },
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "save_adapter_validation_report",
        lambda site, report: saved.update({"site": site, "report": report}),
    )

    req = client_routes.WidgetActionValidationRequest(
        site_id="Builder Co",
        origin="https://builder.example.com",
        url="https://builder.example.com/services",
        actions={"REQUEST_ESTIMATE": {"supported": True, "status": "ok"}},
    )

    result = client_routes._process_action_validation_report(req)

    assert saved["site"] == "builder_co"
    assert saved["report"]["origin"] == "https://builder.example.com"
    assert saved["report"]["url"] == "https://builder.example.com/services"
    assert result["summary"]["supported"] == 1


def test_widget_policy_event_checks_origin_and_saves_event(monkeypatch) -> None:
    saved = {}

    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {
            "site_id": site,
            "allowed_origin": "https://builder.example.com",
            "vertical_config": {},
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "save_client_policy_event",
        lambda site_id, event: saved.update({"site_id": site_id, "event": event}),
    )

    req = client_routes.WidgetPolicyEventRequest(
        site_id="Builder Demo",
        origin="https://builder.example.com",
        url="https://builder.example.com/checkout",
        occurred_at="2026-01-01T00:00:00Z",
        action="CHECKOUT",
        reason="blocked_by_barrier_policy",
        policy={
            "blocked_actions": ["CHECKOUT"],
            "handoff_actions": ["CHECKOUT_HANDOFF"],
            "handoff_flow": {"key": "payment_handoff", "provider": "stripe"},
        },
    )

    result = client_routes._process_policy_event(req)

    assert result["status"] == "ok"
    assert saved["site_id"] == "builder_demo"
    assert saved["event"]["action"] == "CHECKOUT"
    assert saved["event"]["origin"] == "https://builder.example.com"
    assert saved["event"]["policy"]["handoff_flow"]["provider"] == "stripe"


def test_widget_action_event_checks_origin_and_saves_event(monkeypatch) -> None:
    saved = {}

    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {
            "site_id": site,
            "allowed_origin": "https://builder.example.com",
            "vertical_config": {},
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "save_client_action_event",
        lambda site_id, event: saved.update({"site_id": site_id, "event": event}),
    )

    req = client_routes.WidgetActionExecutionEventRequest(
        site_id="Builder Demo",
        origin="https://builder.example.com",
        url="https://builder.example.com/services",
        occurred_at="2026-01-01T00:00:00Z",
        request_id="turn_demo_1",
        turn_id="turn_demo",
        sequence=1,
        action="REQUEST_ESTIMATE",
        status="succeeded",
        stage="configured_action",
        reason="",
        duration_ms=25.5,
        param_keys=["phone", "budget"],
        requested_url="https://builder.example.com/services",
        final_url="https://builder.example.com/contact",
        evidence={"url_changed": True, "target_page": "contact", "secret": {"nested": "kept_safe"}},
    )

    result = client_routes._process_action_execution_event(req)

    assert result["status"] == "ok"
    assert saved["site_id"] == "builder_demo"
    assert saved["event"]["action"] == "REQUEST_ESTIMATE"
    assert saved["event"]["request_id"] == "turn_demo_1"
    assert saved["event"]["turn_id"] == "turn_demo"
    assert saved["event"]["sequence"] == 1
    assert saved["event"]["status"] == "succeeded"
    assert saved["event"]["requested_url"] == "https://builder.example.com/services"
    assert saved["event"]["final_url"] == "https://builder.example.com/contact"
    assert saved["event"]["evidence"]["url_changed"] is True
    assert saved["event"]["param_keys"] == ["phone", "budget"]


def test_widget_interaction_event_checks_origin_and_saves_event(monkeypatch) -> None:
    saved = {}

    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {
            "site_id": site,
            "allowed_origin": "https://builder.example.com",
            "vertical_config": {},
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "save_client_interaction_event",
        lambda site_id, event: saved.update({"site_id": site_id, "event": event}),
    )

    req = client_routes.WidgetInteractionEventRequest(
        site_id="Builder Demo",
        origin="https://builder.example.com",
        url="https://builder.example.com/contact",
        occurred_at="2026-01-01T00:00:00Z",
        event_type="submit",
        label="Request estimate",
        selector="form.estimate",
        tag="form",
        form={
            "selector": "form.estimate",
            "fields": [
                {"selector": "input[name='phone']", "name": "Phone", "type": "tel"},
            ],
        },
    )

    result = client_routes._process_interaction_event(req)

    assert result["status"] == "ok"
    assert saved["site_id"] == "builder_demo"
    assert saved["event"]["event_type"] == "submit"
    assert saved["event"]["form"]["fields"][0]["name"] == "Phone"


def test_client_interaction_event_updates_candidates(monkeypatch) -> None:
    stored = {
        "interaction_events": [],
        "action_candidates": [],
        "actions": {},
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})
    monkeypatch.setattr(client_db, "get_client_vertical_key", lambda site: "construction")

    client_db.save_client_interaction_event(
        "builder_demo",
        {
            "origin": "https://builder.example.com",
            "url": "https://builder.example.com/contact",
            "event_type": "submit",
            "label": "Request estimate",
            "selector": "form.estimate",
            "form": {
                "selector": "form.estimate",
                "fields": [{"selector": "input[name='phone']", "name": "Phone"}],
            },
        },
    )

    assert stored["interaction_events"][0]["event_type"] == "submit"
    assert stored["interaction_events"][0]["inferred_action"] == "REQUEST_ESTIMATE"
    assert stored["action_candidates"][0]["kind"] == "observed_form"
    assert stored["action_candidates"][0]["action"] == "REQUEST_ESTIMATE"
    assert stored["action_candidates"][0]["fields"] == ["Phone"]
    assert stored["actions"]["REQUEST_ESTIMATE"]["type"] == "sequence"
    assert stored["actions"]["REQUEST_ESTIMATE"]["submit_mode"] == "fill_only"
    assert stored["actions"]["REQUEST_ESTIMATE"]["fields"] == ["phone"]


def test_client_action_event_updates_recent_execution_events(monkeypatch) -> None:
    stored = {}
    durable_events = _mock_durable_action_events(monkeypatch)

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.save_client_action_event(
        "builder_demo",
        {
            "origin": "https://builder.example.com",
            "url": "https://builder.example.com/services",
            "request_id": "turn_demo_1",
            "turn_id": "turn_demo",
            "sequence": 1,
            "action": "request_estimate",
            "status": "succeeded",
            "stage": "configured-action",
            "reason": "",
            "duration_ms": "12.345",
            "param_keys": ["phone", "budget"],
            "requested_url": "https://builder.example.com/services",
            "final_url": "https://builder.example.com/contact",
            "evidence": {"url_changed": True, "title": "Contact"},
            "params": {"phone": "secret"},
        },
    )

    event = durable_events[0]

    assert event["action"] == "REQUEST_ESTIMATE"
    assert event["request_id"] == "turn_demo_1"
    assert event["turn_id"] == "turn_demo"
    assert event["sequence"] == 1
    assert event["status"] == "succeeded"
    assert event["stage"] == "configured_action"
    assert event["duration_ms"] == 12.35
    assert event["param_keys"] == ["phone", "budget"]
    assert event["requested_url"] == "https://builder.example.com/services"
    assert event["final_url"] == "https://builder.example.com/contact"
    assert event["evidence"]["url_changed"] is True
    assert "params" not in event
    assert "action_events" not in stored
    assert stored["action_health"]["summary"]["needs_repair"] == 0
    assert stored["action_health"]["actions"]["REQUEST_ESTIMATE"]["status"] == "healthy"
    assert stored["action_health"]["actions"]["REQUEST_ESTIMATE"]["last_request_id"] == "turn_demo_1"
    assert stored["action_health"]["blocked_actions"] == []


def test_repeated_action_failures_block_runtime_policy(monkeypatch) -> None:
    stored = {}
    _mock_durable_action_events(monkeypatch)

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    for index in range(3):
        client_db.save_client_action_event(
            "builder_demo",
            {
                "origin": "https://builder.example.com",
                "url": "https://builder.example.com/services",
                "occurred_at": f"2026-01-01T00:0{index}:00Z",
                "action": "REQUEST_ESTIMATE",
                "status": "failed",
                "stage": "all",
                "reason": "no_executor_succeeded",
            },
        )

    health = stored["action_health"]
    policy = build_barrier_action_policy(stored, "construction")

    assert health["summary"]["blocked"] == 1
    assert health["actions"]["REQUEST_ESTIMATE"]["status"] == "blocked"
    assert health["blocked_actions"] == ["REQUEST_ESTIMATE"]
    assert "REQUEST_ESTIMATE" in policy["runtime_blocked_actions"]
    assert "REQUEST_ESTIMATE" in policy["blocked_actions"]
    assert any(note["key"] == "action_health:REQUEST_ESTIMATE" for note in policy["notes"])


def test_action_failure_applies_runtime_repair_from_recent_interaction(monkeypatch) -> None:
    stored = {
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.old", "confidence": 0.7}},
        "interaction_events": [
            {
                "event_type": "click",
                "label": "Request Estimate",
                "selector": "button.estimate-new",
                "inferred_action": "REQUEST_ESTIMATE",
                "inference_confidence": 0.92,
            }
        ],
    }
    _mock_durable_action_events(monkeypatch)

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.save_client_action_event(
        "builder_demo",
        {
            "origin": "https://builder.example.com",
            "url": "https://builder.example.com/services",
            "occurred_at": "2026-01-01T00:00:00Z",
            "action": "REQUEST_ESTIMATE",
            "status": "failed",
            "stage": "all",
            "reason": "no_executor_succeeded",
        },
    )

    repair = stored["action_repairs"][0]

    assert stored["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.estimate-new"
    assert stored["actions"]["REQUEST_ESTIMATE"]["source"] == "runtime_repair"
    assert repair["action"] == "REQUEST_ESTIMATE"
    assert repair["repair"]["selector"] == "button.estimate-new"
    assert stored["action_health"]["summary"]["needs_repair"] == 0
    assert stored["action_health"]["actions"]["REQUEST_ESTIMATE"]["status"] == "repair_applied"
    assert stored["action_health"]["blocked_actions"] == []


def test_action_failure_does_not_replace_crm_override(monkeypatch) -> None:
    stored = {
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.crm", "source": "crm"}},
        "overrides": {"actions": {"source": "crm", "updated": True}},
        "interaction_events": [
            {
                "event_type": "click",
                "label": "Request Estimate",
                "selector": "button.estimate-new",
                "inferred_action": "REQUEST_ESTIMATE",
                "inference_confidence": 0.92,
            }
        ],
    }
    _mock_durable_action_events(monkeypatch)

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.save_client_action_event(
        "builder_demo",
        {
            "origin": "https://builder.example.com",
            "url": "https://builder.example.com/services",
            "occurred_at": "2026-01-01T00:00:00Z",
            "action": "REQUEST_ESTIMATE",
            "status": "failed",
            "stage": "all",
            "reason": "no_executor_succeeded",
        },
    )

    health_row = stored["action_health"]["needs_repair"][0]

    assert stored["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.crm"
    assert "action_repairs" not in stored
    assert health_row["repair_candidate"]["selector"] == "button.estimate-new"


def test_newer_validation_clears_action_health_block(monkeypatch) -> None:
    durable_events = [
        {
            "action": "REQUEST_ESTIMATE",
            "status": "failed",
            "stage": "all",
            "occurred_at": "2026-01-01T00:02:00Z",
        },
        {
            "action": "REQUEST_ESTIMATE",
            "status": "failed",
            "stage": "all",
            "occurred_at": "2026-01-01T00:01:00Z",
        },
        {
            "action": "REQUEST_ESTIMATE",
            "status": "failed",
            "stage": "all",
            "occurred_at": "2026-01-01T00:00:00Z",
        },
    ]
    stored = {
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.old"}},
    }
    _mock_durable_action_events(monkeypatch, durable_events)

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.save_adapter_validation_report(
        "builder_demo",
        {
            "validated_at": "2026-01-01T00:03:00Z",
            "actions": {
                "REQUEST_ESTIMATE": {
                    "type": "click",
                    "status": "ok",
                    "supported": True,
                    "confidence": 0.9,
                }
            },
        },
    )

    health = stored["action_health"]

    assert health["summary"]["blocked"] == 0
    assert health["actions"]["REQUEST_ESTIMATE"]["status"] == "validated"
    assert health["blocked_actions"] == []

