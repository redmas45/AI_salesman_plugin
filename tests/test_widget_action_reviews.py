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


def test_client_interaction_event_promotes_click_action(monkeypatch) -> None:
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
            "url": "https://builder.example.com/services",
            "event_type": "click",
            "label": "Book site visit",
            "selector": "button.site-visit",
        },
    )

    assert stored["interaction_events"][0]["inferred_action"] == "REQUEST_SITE_VISIT"
    assert stored["action_candidates"][0]["action"] == "REQUEST_SITE_VISIT"
    assert stored["actions"]["REQUEST_SITE_VISIT"]["type"] == "click"
    assert stored["actions"]["REQUEST_SITE_VISIT"]["selector"] == "button.site-visit"


def test_action_candidate_review_approves_click_and_records_history(monkeypatch) -> None:
    stored = {
        "actions": {},
        "action_reviews": [],
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.review_client_action_candidate(
        "builder_demo",
        {
            "kind": "button",
            "action": "REQUEST_SITE_VISIT",
            "type": "click",
            "label": "Book site visit",
            "selector": "button.visit",
            "confidence": 0.82,
        },
        decision="approve",
    )

    assert stored["actions"]["REQUEST_SITE_VISIT"]["selector"] == "button.visit"
    assert stored["actions"]["REQUEST_SITE_VISIT"]["source"] == "crm_approved_candidate"
    assert stored["action_reviews"][0]["decision"] == "approve"
    assert stored["overrides"]["actions"]["source"] == "crm"


def test_action_candidate_review_rejects_without_changing_actions(monkeypatch) -> None:
    stored = {
        "actions": {"REQUEST_SITE_VISIT": {"type": "navigate", "path": "/visit"}},
        "action_reviews": [],
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.review_client_action_candidate(
        "builder_demo",
        {
            "kind": "button",
            "action": "REQUEST_SITE_VISIT",
            "type": "click",
            "label": "Bad visit",
            "selector": "button.bad",
            "confidence": 0.7,
        },
        decision="reject",
        note="Wrong button",
    )

    assert stored["actions"]["REQUEST_SITE_VISIT"]["path"] == "/visit"
    assert stored["action_reviews"][0]["decision"] == "reject"
    assert stored["action_reviews"][0]["note"] == "Wrong button"


def test_action_candidate_review_blocks_external_navigation(monkeypatch) -> None:
    stored = {
        "actions": {},
        "action_reviews": [],
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))

    with pytest.raises(ValueError):
        client_db.review_client_action_candidate(
            "builder_demo",
            {
                "kind": "route",
                "action": "NAVIGATE_TO",
                "type": "navigate",
                "label": "External",
                "path": "https://evil.example.com",
                "confidence": 0.9,
            },
            decision="approve",
        )


def test_action_proposal_refresh_and_approval(monkeypatch) -> None:
    stored = {
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.old"}},
        "action_health": {
            "needs_repair": [
                {
                    "action": "REQUEST_ESTIMATE",
                    "last_reason": "missing selector",
                    "repair_candidate": {
                        "type": "click",
                        "selector": "button.estimate-new",
                        "confidence": 0.91,
                    },
                }
            ]
        },
        "action_proposal_reviews": [],
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})
    monkeypatch.setattr(client_db, "get_client_vertical_key", lambda site: "construction")

    client_db.refresh_client_action_proposals("builder_demo")
    proposal = stored["action_proposals"][0]
    client_db.review_client_action_proposal("builder_demo", proposal, decision="approve")

    assert proposal["action"] == "REQUEST_ESTIMATE"
    assert stored["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.estimate-new"
    assert stored["actions"]["REQUEST_ESTIMATE"]["source"] == "crm_approved_proposal"
    assert stored["action_proposal_reviews"][0]["decision"] == "approve"


def test_action_proposal_reject_does_not_change_action(monkeypatch) -> None:
    stored = {
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.old"}},
        "action_proposal_reviews": [],
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.review_client_action_proposal(
        "builder_demo",
        {
            "action": "REQUEST_ESTIMATE",
            "kind": "runtime_repair",
            "source": "action_health",
            "confidence": 0.88,
            "config": {"type": "click", "selector": "button.new", "confidence": 0.88},
        },
        decision="reject",
    )

    assert stored["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.old"
    assert stored["action_proposal_reviews"][0]["decision"] == "reject"


def test_action_proposal_refresh_persists_flow_repair_plans(monkeypatch) -> None:
    stored = {
        "routes": {"projects": "/our-work"},
        "actions": {
            "REQUEST_ESTIMATE": {
                "type": "click",
                "selector": "button.estimate",
                "confidence": 0.88,
            }
        },
        "regression": {
            "status": "changed",
            "changes": [
                {
                    "kind": "route_changed",
                    "item": "projects",
                    "severity": "medium",
                    "previous": "/projects",
                    "current": "/our-work",
                    "evidence": "Route target changed.",
                },
                {
                    "kind": "action_changed",
                    "item": "REQUEST_ESTIMATE",
                    "severity": "medium",
                    "previous": "click|button.old",
                    "current": "click|button.estimate",
                    "evidence": "Adapter target changed.",
                },
            ],
        },
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})
    monkeypatch.setattr(client_db, "get_client_vertical_key", lambda site: "construction")

    client_db.refresh_client_action_proposals("builder_demo")
    by_key = {proposal["key"]: proposal for proposal in stored["flow_repair_proposals"]}

    assert by_key["route:projects"]["patch"]["routes"]["projects"] == "/our-work"
    assert by_key["action:REQUEST_ESTIMATE"]["patch"]["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.estimate"


def test_flow_repair_proposal_approval_applies_patch(monkeypatch) -> None:
    stored = {
        "routes": {"projects": "/projects"},
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.old"}},
        "flow_repair_reviews": [],
    }
    proposal = {
        "key": "action:REQUEST_ESTIMATE",
        "kind": "action_repair",
        "scope": "action",
        "item": "REQUEST_ESTIMATE",
        "confidence": 0.88,
        "patch": {
            "routes": {"projects": "/our-work"},
            "actions": {
                "REQUEST_ESTIMATE": {
                    "type": "click",
                    "selector": "button.estimate",
                    "confidence": 0.88,
                }
            },
        },
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.review_client_flow_repair_proposal("builder_demo", proposal, decision="approve")

    assert stored["routes"]["projects"] == "/our-work"
    assert stored["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.estimate"
    assert stored["actions"]["REQUEST_ESTIMATE"]["confidence"] == 0.88
    assert stored["flow_repair_reviews"][0]["decision"] == "approve"
    assert stored["flow_repair_reviews"][0]["proposal_key"] == "action:REQUEST_ESTIMATE"


def test_flow_repair_proposal_reject_does_not_apply_patch(monkeypatch) -> None:
    stored = {
        "routes": {"projects": "/projects"},
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.old"}},
        "flow_repair_reviews": [],
    }
    proposal = {
        "key": "route:projects",
        "kind": "route_repair",
        "scope": "route",
        "item": "projects",
        "patch": {"routes": {"projects": "/our-work"}},
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})

    client_db.review_client_flow_repair_proposal("builder_demo", proposal, decision="reject")

    assert stored["routes"]["projects"] == "/projects"
    assert stored["actions"]["REQUEST_ESTIMATE"]["selector"] == "button.old"
    assert stored["flow_repair_reviews"][0]["decision"] == "reject"


def test_client_interaction_event_does_not_replace_manual_action(monkeypatch) -> None:
    stored = {
        "interaction_events": [],
        "action_candidates": [],
        "actions": {
            "REQUEST_SITE_VISIT": {
                "type": "navigate",
                "path": "/site-visit",
                "confidence": 0.9,
                "source": "crm",
            }
        },
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})
    monkeypatch.setattr(client_db, "get_client_vertical_key", lambda site: "construction")

    client_db.save_client_interaction_event(
        "builder_demo",
        {
            "origin": "https://builder.example.com",
            "url": "https://builder.example.com/services",
            "event_type": "click",
            "label": "Book site visit",
            "selector": "button.site-visit",
        },
    )

    assert stored["actions"]["REQUEST_SITE_VISIT"]["source"] == "crm"
    assert stored["actions"]["REQUEST_SITE_VISIT"]["path"] == "/site-visit"


def test_submit_interaction_prefers_lead_action_over_navigation(monkeypatch) -> None:
    stored = {
        "interaction_events": [],
        "action_candidates": [],
        "actions": {},
    }

    monkeypatch.setattr(client_db, "_client_vertical_config", lambda site: dict(stored))
    monkeypatch.setattr(client_db, "_write_client_vertical_config", lambda site, config: stored.update(config))
    monkeypatch.setattr(client_db, "get_client_detail", lambda site: {"site_id": site, "vertical_config": stored})
    monkeypatch.setattr(client_db, "get_client_vertical_key", lambda site: "generic")

    client_db.save_client_interaction_event(
        "generic_demo",
        {
            "origin": "https://generic.example.com",
            "url": "https://generic.example.com/contact",
            "event_type": "submit",
            "label": "Contact",
            "selector": "form.contact",
            "form": {
                "selector": "form.contact",
                "fields": [{"selector": "input[name='email']", "name": "Email"}],
            },
        },
    )

    assert stored["interaction_events"][0]["inferred_action"] == "CAPTURE_LEAD"
    assert stored["actions"]["CAPTURE_LEAD"]["type"] == "sequence"


def test_browser_rediscovery_preserves_learned_runtime_state() -> None:
    existing = {
        "routes": {"contact": "/contact"},
        "actions": {"REQUEST_SITE_VISIT": {"type": "click", "selector": "button.visit", "source": "browser_interaction"}},
        "validation": {"summary": {"supported": 1}},
        "flow": {"summary": {"pages": 4}},
        "rehearsal": {"summary": {"supported": 2}},
        "regression": {"status": "stable"},
        "action_health": {"summary": {"needs_repair": 1}, "blocked_actions": []},
        "policy_events": [{"action": "CHECKOUT", "status": "blocked"}],
        "interaction_events": [{"event_type": "click", "label": "Book site visit"}],
        "action_candidates": [{"kind": "observed_click", "action": "REQUEST_SITE_VISIT", "selector": "button.visit"}],
        "prompt_suggestions": ["Help me book a site visit."],
        "barriers": {
            "site_id": "builder_demo",
            "site_url": "https://builder.example.com",
            "findings": [{"key": "captcha", "severity": "high", "page_url": "/contact", "evidence": "captcha"}],
        },
    }
    fresh = {
        "routes": {"services": "/services"},
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
        "action_candidates": [{"kind": "button", "action": "REQUEST_ESTIMATE", "selector": "button.estimate"}],
        "prompt_suggestions": ["Help me request an estimate."],
        "barriers": {
            "site_id": "builder_demo",
            "site_url": "https://builder.example.com",
            "findings": [{"key": "payment_handoff", "severity": "high", "page_url": "/checkout", "evidence": "stripe"}],
        },
        "platform": "auto",
    }

    merged = client_db._merge_discovery_vertical_config(existing, fresh, vertical_changed=False)

    assert merged["routes"] == {"contact": "/contact", "services": "/services"}
    assert set(merged["actions"]) == {"REQUEST_SITE_VISIT", "REQUEST_ESTIMATE"}
    assert merged["validation"] == existing["validation"]
    assert merged["flow"] == existing["flow"]
    assert merged["rehearsal"] == existing["rehearsal"]
    assert merged["regression"] == existing["regression"]
    assert "action_events" not in merged
    assert merged["action_health"] == existing["action_health"]
    assert merged["policy_events"] == existing["policy_events"]
    assert merged["interaction_events"] == existing["interaction_events"]
    assert merged["prompt_suggestions"] == ["Help me request an estimate.", "Help me book a site visit."]
    assert set(merged["barriers"]["summary"]["keys"]) == {"captcha", "payment_handoff"}


def test_browser_rediscovery_does_not_replace_crm_action_override() -> None:
    existing = {
        "actions": {"REQUEST_ESTIMATE": {"type": "navigate", "path": "/estimate", "source": "crm"}},
        "overrides": {"actions": {"source": "crm", "updated": True}},
    }
    fresh = {
        "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
    }

    merged = client_db._merge_discovery_vertical_config(existing, fresh, vertical_changed=False)

    assert merged["actions"] == existing["actions"]


def test_action_auto_approve_threshold_is_configurable(monkeypatch) -> None:
    monkeypatch.setattr(client_db.config, "ACTION_AUTO_APPROVE_CONFIDENCE", 0.6)
    fresh = {
        "action_candidates": [
            {
                "kind": "button",
                "action": "REQUEST_SITE_VISIT",
                "type": "click",
                "label": "Book visit",
                "selector": "button.visit",
                "confidence": 0.66,
            }
        ],
    }

    merged = client_db._merge_discovery_vertical_config({}, fresh, vertical_changed=False)

    assert merged["action_candidates"][0]["review"] == "approve"
    assert merged["actions"]["REQUEST_SITE_VISIT"]["selector"] == "button.visit"
    assert merged["action_reviews"][0]["decision"] == "approve"



