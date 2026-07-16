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


def test_public_runtime_config_exposes_adapter_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {
            "site_id": site,
            "adapter_name": "generated_adapter.js",
            "vertical_key": "ecommerce",
            "vertical_config": {
                "routes": {"shop": "/catalog"},
                "actions": {
                    "CHECKOUT": {"type": "navigate", "path": "/checkout"},
                    "FILTER_PRODUCTS": {
                        "type": "form",
                        "fields": ["need"],
                        "required_fields": ["need"],
                        "required_fields_known": True,
                    },
                },
                "validation": {
                    "summary": {"total": 1, "supported": 1},
                    "actions": {"CHECKOUT": {"supported": True, "status": "ok"}},
                },
                "initialization": {
                    "status": "ok",
                    "stages": [{"name": "flow_discovery", "status": "ok"}],
                },
                "flow": {
                    "summary": {"pages": 2, "actions": 3},
                    "prompt_suggestions": ["Show me products."],
                },
                "barriers": {
                    "summary": {"total": 1, "high": 1},
                    "findings": [
                        {
                            "key": "payment_handoff",
                            "severity": "high",
                            "evidence": "Payment provider(s): stripe",
                            "handling": "Never complete payment automatically.",
                        }
                    ],
                },
                "rehearsal": {
                    "summary": {"total": 2, "supported": 2},
                    "engine": "test",
                },
                "regression": {
                    "status": "stable",
                    "summary": {"changes": 0, "high": 0},
                },
                "runtime_capabilities": {
                    "script_loaded": True,
                    "secure_context": True,
                    "microphone_permission": "prompt",
                },
                "action_health": {
                    "summary": {"tracked": 1, "needs_repair": 1, "blocked": 0},
                    "needs_repair": [{"action": "CHECKOUT", "status": "needs_repair"}],
                    "blocked_actions": [],
                },
                "action_repairs": [
                    {"action": "CHECKOUT", "status": "applied", "repair": {"type": "click", "selector": "button.checkout"}},
                ],
                "flow_repair_proposals": [
                    {
                        "key": "route:shop",
                        "kind": "route_repair",
                        "scope": "route",
                        "item": "shop",
                        "patch": {"routes": {"shop": "/catalog"}},
                    }
                ],
                "flow_repair_reviews": [
                    {"proposal_key": "route:shop", "decision": "approve", "patch": {"routes": {"shop": "/catalog"}}},
                ],
                "policy_events": [
                    {"action": "CHECKOUT", "status": "blocked", "reason": "blocked_by_barrier_policy"},
                ],
                "interaction_events": [
                    {"event_type": "click", "label": "Checkout", "selector": "button.checkout"},
                ],
                "action_candidates": [
                    {"kind": "button", "action": "CHECKOUT", "type": "click", "label": "Checkout"},
                ],
                "prompt_suggestions": ["Help me checkout."],
                "intake_questions": [
                    {
                        "key": "need",
                        "label": "Need",
                        "question": "What are you looking for?",
                        "why": "Narrows product discovery.",
                        "actions": ["FILTER_PRODUCTS"],
                        "required": True,
                    }
                ],
            },
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_vertical_detail",
        lambda key: {
            "key": key,
            "label": "E-commerce",
            "risk_level": "low",
            "action_types": ["SHOW_PRODUCTS", "ADD_TO_CART", "CHECKOUT"],
            "entity_types": ["product"],
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_site_selectors",
        lambda site: {
            "selectors": {"add_to_cart": "button[data-add]"},
            "confidence": 0.82,
            "validated": True,
        },
    )
    monkeypatch.setattr(client_routes.admin_db, "is_client_widget_enabled", lambda site: True)
    monkeypatch.setattr(
        client_routes.admin_db,
        "list_client_action_events",
        lambda site_ids, limit=80: {
            site_id: [{"action": "CHECKOUT", "status": "failed", "stage": "dom_fallback"}]
            for site_id in site_ids
        },
    )

    payload = client_routes._public_runtime_config(
        site="ai_kart",
        api_base_url="https://hub.example.com/aihub",
    )

    assert payload["site_id"] == "ai_kart"
    assert payload["enabled"] is True
    assert payload["vertical"]["key"] == "ecommerce"
    assert payload["adapter"]["mode"] == "generated-runtime"
    assert payload["adapter"]["routes"]["shop"] == "/catalog"
    assert payload["adapter"]["actions"]["CHECKOUT"]["path"] == "/checkout"
    assert "CHECKOUT" in payload["adapter"]["action_policy"]["blocked_actions"]
    assert "CHECKOUT_HANDOFF" in payload["adapter"]["action_policy"]["handoff_actions"]
    assert payload["adapter"]["action_policy"]["handoff_flows"][0]["provider"] == "stripe"
    assert payload["adapter"]["action_policy"]["handoff_flows"][0]["action"] == "CHECKOUT_HANDOFF"
    assert payload["adapter"]["action_events"][0]["stage"] == "dom_fallback"
    assert payload["adapter"]["action_health"]["summary"]["needs_repair"] == 1
    assert "action_proposals" in payload["adapter"]
    assert "action_proposal_reviews" in payload["adapter"]
    assert payload["adapter"]["action_repairs"][0]["repair"]["selector"] == "button.checkout"
    assert payload["adapter"]["flow_repair_proposals"][0]["patch"]["routes"]["shop"] == "/catalog"
    assert payload["adapter"]["flow_repair_reviews"][0]["decision"] == "approve"
    assert payload["adapter"]["policy_events"][0]["action"] == "CHECKOUT"
    assert payload["adapter"]["interaction_events"][0]["selector"] == "button.checkout"
    assert payload["adapter"]["action_candidates"][0]["label"] == "Checkout"
    assert payload["adapter"]["prompt_suggestions"] == ["Help me checkout."]
    assert payload["adapter"]["intake_questions"][0]["key"] == "need"
    assert payload["adapter"]["intake_questions"][0]["required"] is True
    assert payload["adapter"]["action_readiness"][0]["action"] == "FILTER_PRODUCTS"
    assert payload["adapter"]["action_readiness"][0]["status"] == "requires_params"
    assert payload["adapter"]["validation"]["summary"]["supported"] == 1
    assert payload["adapter"]["initialization"]["status"] == "ok"
    assert payload["adapter"]["flow"]["summary"]["pages"] == 2
    assert payload["adapter"]["barriers"]["summary"]["high"] == 1
    assert payload["adapter"]["rehearsal"]["summary"]["supported"] == 2
    assert payload["adapter"]["regression"]["status"] == "stable"
    assert payload["adapter"]["runtime_capabilities"]["microphone_permission"] == "prompt"
    assert payload["adapter"]["selectors"]["add_to_cart"] == "button[data-add]"
    assert payload["install"]["adapter_script"].endswith("/mayabot-adapter.js?site=ai_kart")


def test_adapter_tab_surfaces_runtime_repair_candidates_and_history() -> None:
    source = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in [
                "crm/src/views/client-workspace/adapter/AdapterTab.tsx",
                "crm/src/views/client-workspace/adapter/AdapterDiagnostics.tsx",
                "crm/src/views/client-workspace/adapter/AdapterActionDiagnosticsPanels.tsx",
                "crm/src/views/client-workspace/adapter/AdapterFlowDiagnostics.tsx",
                "crm/src/views/client-workspace/adapter/AdapterOverviewPanels.tsx",
                "crm/src/views/client-workspace/adapter/adapterFormatters.ts",
        ]
    )

    assert "repair_candidate" in source
    assert "Runtime repairs" in source
    assert "action_repairs" in source
    assert "repairTargetLabel" in source
    assert "Handoff flows" in source
    assert "handoffFlowLabel" in source
    assert "reviewClientAdapterAction" in source
    assert "Action review history" in source
    assert "refreshClientAdapterActionProposals" in source
    assert "Action repair proposals" in source
    assert "flow_repair_proposals" in source
    assert "flow_repair_reviews" in source
    assert "Repair plans" in source
    assert "flowRepairProposalLabel" in source
    assert "reviewClientFlowRepairProposal" in source
    assert "flowRepairReviewLabel" in source
    assert "Vertical decision" in source
    assert "Action readiness" in source
    assert "readinessParamText" in source
    assert "verticalDecisionLabel" in source
    assert "Initialization" in source
    assert "initializationSummary" in source
    assert "Runtime permissions" in source
    assert "Live action candidates (pending review)" not in source
    assert "reviewActionCandidate" not in source
    assert "reviewClientAdapterActionProposal" in source
    assert "Approve" in source
    assert "Reject" in source


def test_prompt_tab_promotes_discovered_prompt_suggestions() -> None:
    source = Path("crm/src/views/client-workspace/tabs/PromptTab.tsx").read_text(encoding="utf-8")

    assert "applyPromptSuggestion" in source
    assert "Prompt suggestion added to developer rules" in source
    assert "Customer prompt coverage" in source
    assert "Sales intake" in source
    assert "salesIntakeQuestions" in source


def test_generated_client_script_tag_uses_installer(monkeypatch) -> None:
    monkeypatch.setattr(client_db, "_public_hub_origin", lambda: "https://hub.example.com/aihub")

    script_tag = client_db.script_tag_for_site("AI KART")

    assert "install.js?site=ai_kart" in script_tag
    assert "mayabot.js" not in script_tag


def test_auto_client_rows_collapse_by_origin() -> None:
    rows = client_db._visible_client_rows(
        [
            {
                "site_id": "auto_127_0_0_1_5183_root",
                "allowed_origin": "http://127.0.0.1:5183",
                "store_url": "http://127.0.0.1:5183",
                "status": "live",
                "created_at": "2026-06-27T10:00:00",
            },
            {
                "site_id": "auto_127_0_0_1_5183_claims",
                "allowed_origin": "http://127.0.0.1:5183",
                "store_url": "http://127.0.0.1:5183",
                "status": "live",
                "created_at": "2026-06-27T10:01:00",
            },
            {
                "site_id": "manual_policy",
                "allowed_origin": "http://127.0.0.1:5183",
                "store_url": "http://127.0.0.1:5183",
                "status": "live",
                "created_at": "2026-06-27T10:02:00",
            },
        ]
    )

    assert [row["site_id"] for row in rows] == ["manual_policy"]


def test_auto_client_rows_collapse_localhost_aliases_for_explicit_client() -> None:
    rows = client_db._visible_client_rows(
        [
            {
                "site_id": "ai_kart",
                "allowed_origin": "http://host.docker.internal:5175",
                "store_url": "http://host.docker.internal:5175",
                "status": "available",
                "created_at": "2026-06-27T10:00:00",
            },
            {
                "site_id": "auto_127_0_0_1_5175_root",
                "allowed_origin": "http://127.0.0.1:5175",
                "store_url": "http://127.0.0.1:5175",
                "status": "available",
                "created_at": "2026-06-27T10:01:00",
            },
            {
                "site_id": "policy_website",
                "allowed_origin": "http://127.0.0.1:5183",
                "store_url": "http://127.0.0.1:5183",
                "status": "available",
                "created_at": "2026-06-27T10:02:00",
            },
        ]
    )

    assert [row["site_id"] for row in rows] == ["ai_kart", "policy_website"]



