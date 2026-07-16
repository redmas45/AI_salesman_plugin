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


def test_travel_site_registration_generates_booking_adapter_config() -> None:
    discovery = build_discovery(
        {
            "site_id": "tickets_to_do",
            "origin": "https://www.ticketstodo.com",
            "url": "https://www.ticketstodo.com/",
            "title": "TicketsToDo - Tours, Attractions and Activities",
            "text_sample": "Book tours, attractions, activity tickets, destinations, theme parks, and travel experiences.",
            "buttons": [
                {"label": "Book Now", "selector": "button.book-now"},
                {"label": "Search", "selector": "button.search"},
            ],
            "links": [
                {"label": "Things to do", "href": "https://www.ticketstodo.com/things-to-do/"},
                {"label": "Help", "href": "https://www.ticketstodo.com/contact/"},
            ],
            "forms": [
                {
                    "label": "Search destination or activity",
                    "selector": "form.search",
                    "input_selector": "input[name='q']",
                    "submit_selector": "button.search",
                }
            ],
            "platform_hints": {},
        }
    )

    actions = discovery.vertical_config["actions"]

    assert discovery.vertical_key == "travel"
    assert "START_BOOKING" in actions
    assert actions["START_BOOKING"]["selector"] == "button.book-now"
    assert "SEARCH_AVAILABILITY" in actions
    assert discovery.vertical_config["routes"]["shop"] == "/things-to-do/"


def test_browser_barrier_hints_generate_runtime_policy_inputs() -> None:
    discovery = build_discovery(
        {
            "site_id": "tickets_to_do",
            "origin": "https://www.ticketstodo.com",
            "url": "https://www.ticketstodo.com/booking",
            "title": "TicketsToDo - Book Activities",
            "text_sample": "Book tickets, select a date, choose a time, and continue to secure payment.",
            "buttons": [{"label": "Book Now", "selector": "button.book-now"}],
            "links": [{"label": "Checkout", "href": "https://checkout.stripe.com/session"}],
            "forms": [],
            "platform_hints": {},
            "barrier_hints": {
                "iframe_count": 2,
                "iframe_sources": ["https://calendly.com/demo", "https://checkout.stripe.com/embed"],
                "password_inputs": 0,
                "file_uploads": 0,
                "date_inputs": 1,
                "captcha": True,
                "payment_providers": ["stripe"],
                "calendar_providers": ["calendly"],
                "map_providers": [],
                "external_action_hosts": ["checkout.stripe.com"],
            },
        }
    )

    barrier_keys = set(discovery.vertical_config["barriers"]["summary"]["keys"])
    policy = build_barrier_action_policy(discovery.vertical_config, discovery.vertical_key)

    assert "captcha" in barrier_keys
    assert "payment_handoff" in barrier_keys
    assert "calendar_widget" in barrier_keys
    assert "external_handoff" in barrier_keys
    assert "START_BOOKING" in policy["blocked_actions"]
    assert "HANDOFF_TO_HUMAN" in policy["handoff_actions"]
    assert any(flow["key"] == "calendar_widget" for flow in policy["handoff_flows"])


def test_insurance_site_registration_generates_quote_and_policy_actions() -> None:
    discovery = build_discovery(
        {
            "site_id": "Policy_website",
            "origin": "https://policy.example.com",
            "url": "https://policy.example.com/",
            "title": "Policy Website - Insurance Plans and Claims",
            "text_sample": "Compare insurance policy coverage, premiums, renewal options, claims support, and request a quote.",
            "buttons": [
                {"label": "Get Quote", "selector": "button.get-quote"},
                {"label": "Request Callback", "selector": "button.callback"},
            ],
            "links": [
                {"label": "Claims", "href": "https://policy.example.com/claims"},
                {"label": "Renew Policy", "href": "https://policy.example.com/renewal"},
                {"label": "Policy Coverage", "href": "https://policy.example.com/policy-coverage"},
                {"label": "Contact", "href": "https://policy.example.com/contact"},
            ],
            "forms": [
                {
                    "label": "Get insurance quote",
                    "selector": "form.quote",
                    "input_selector": "input[name='phone']",
                    "submit_selector": "button.get-quote",
                }
            ],
            "platform_hints": {},
        }
    )

    actions = discovery.vertical_config["actions"]

    assert discovery.vertical_key == "insurance"
    assert "START_QUOTE" in actions
    assert actions["START_QUOTE"]["type"] == "form"
    assert actions["START_QUOTE"]["submit_mode"] == "fill_only"
    assert "SEARCH_AVAILABILITY" not in actions
    assert actions["OPEN_CLAIM_FLOW"]["path"] == "/claims"
    assert actions["OPEN_RENEWAL_FLOW"]["path"] == "/renewal"
    assert actions["OPEN_POLICY"]["path"] == "/policy-coverage"


def test_registration_with_form_fields_generates_sequence_action() -> None:
    discovery = build_discovery(
        {
            "site_id": "Policy_website",
            "origin": "https://policy.example.com",
            "url": "https://policy.example.com/",
            "title": "Policy Website - Insurance Plans",
            "text_sample": "Insurance quote, policy coverage, claims, premium support, and request callback.",
            "buttons": [{"label": "Get Quote", "selector": "button.get-quote"}],
            "links": [{"label": "Contact", "href": "https://policy.example.com/contact"}],
            "forms": [
                {
                    "label": "Get insurance quote",
                    "selector": "form.quote",
                    "input_selector": "input[name='phone']",
                    "submit_selector": "button.get-quote",
                    "fields": [
                        {"selector": "input[name='name']", "name": "Full name", "type": "text"},
                        {"selector": "input[name='phone']", "name": "Phone", "type": "tel", "required": True},
                        {
                            "selector": "select[name='coverage']",
                            "name": "Coverage Type",
                            "type": "select",
                            "options": [
                                {"label": "Individual", "value": "individual"},
                                {"label": "Family", "value": "family"},
                            ],
                        },
                        {
                            "selector": "input[name='billing'][value='monthly']",
                            "name": "Billing cycle",
                            "type": "radio",
                            "required": True,
                            "options": [
                                {"label": "Monthly", "value": "monthly"},
                                {"label": "Annual", "value": "annual"},
                            ],
                        },
                    ],
                }
            ],
            "platform_hints": {},
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]

    assert action["type"] == "sequence"
    assert action["submit_mode"] == "fill_only"
    assert action["fields"] == ["billing_cycle", "coverage_type", "full_name", "phone"]
    assert action["required_fields"] == ["billing_cycle", "phone"]
    assert action["required_fields_known"] is True
    coverage_schema = next(field for field in action["field_schema"] if field["param"] == "coverage_type")
    assert coverage_schema["label"] == "Coverage Type"
    assert coverage_schema["options"] == [
        {"label": "Individual", "value": "individual"},
        {"label": "Family", "value": "family"},
    ]
    billing_schema = next(field for field in action["field_schema"] if field["param"] == "billing_cycle")
    assert billing_schema["type"] == "radio"
    assert billing_schema["required"] is True
    assert discovery.vertical_config["action_candidates"]
    generated_candidate = next(
        candidate
        for candidate in discovery.vertical_config["action_candidates"]
        if candidate["kind"] == "generated_action" and candidate["action"] == "START_QUOTE"
    )
    assert generated_candidate["required_fields"] == ["billing_cycle", "phone"]
    assert generated_candidate["required_fields_known"] is True
    assert any(field["param"] == "coverage_type" for field in generated_candidate["field_schema"])
    assert "Help me get a quote." in discovery.vertical_config["prompt_suggestions"]
    assert action["steps"][0] == {
        "op": "fill",
        "selector": "input[name='name']",
        "param": "full_name",
        "optional": True,
    }
    assert action["steps"][1]["param"] == "phone"
    assert action["steps"][1]["optional"] is False
    assert action["steps"][3]["op"] == "check"
    assert action["steps"][3]["param"] == "billing_cycle"
    assert action["steps"][3]["optional"] is False
    assert "START_QUOTE(sequence fields: billing_cycle, coverage_type, full_name, phone)" in discovery.developer_rules


def test_registration_prefers_visible_labels_for_anonymous_form_params() -> None:
    discovery = build_discovery(
        {
            "site_id": "Policy_website",
            "origin": "https://policy.example.com",
            "url": "https://policy.example.com/",
            "title": "Policy Website - Insurance Plans",
            "text_sample": "Insurance quote, policy coverage, claims, premium support, and request callback.",
            "buttons": [{"label": "Get Quote", "selector": "button.get-quote"}],
            "links": [{"label": "Contact", "href": "https://policy.example.com/contact"}],
            "forms": [
                {
                    "label": "Get insurance quote",
                    "selector": "form.quote",
                    "input_selector": "select.w-full.px-3",
                    "submit_selector": "button.get-quote",
                    "fields": [
                        {
                            "selector": "select.w-full.px-3",
                            "name": "",
                            "label": "Age of eldest member",
                            "type": "select",
                            "options": [{"label": "34 years", "value": "34"}],
                        },
                        {
                            "selector": "input.w-full.px-3",
                            "name": "",
                            "label": "City",
                            "placeholder": "e.g. Mumbai",
                            "type": "text",
                        },
                    ],
                }
            ],
            "platform_hints": {},
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]

    assert action["fields"] == ["age_of_eldest_member", "city"]
    assert action["steps"][0]["param"] == "age_of_eldest_member"
    assert action["steps"][1]["param"] == "city"
    assert [field["param"] for field in action["field_schema"]] == ["age_of_eldest_member", "city"]
    assert action["required_fields"] == ["age_of_eldest_member", "city"]
    assert all(field["required"] is True for field in action["field_schema"])
    assert action["steps"][0]["optional"] is False
    assert action["steps"][1]["optional"] is False
    assert "e_g_mumbai" not in action["fields"]
    assert "value" not in action["fields"]
    assert action["submit_mode"] == "submit"
    assert action["steps"][-1] == {"op": "submit", "selector": "button.get-quote"}


def test_low_sensitivity_result_quote_form_is_allowed_to_submit() -> None:
    discovery = build_discovery(
        {
            "site_id": "quote_demo",
            "origin": "https://coverage.example.com",
            "url": "https://coverage.example.com/",
            "title": "Compare insurance quotes",
            "text_sample": "Compare health insurance plans and show quotes from top insurers.",
            "buttons": [{"label": "Get Quotes", "selector": "button.get-quotes"}],
            "links": [{"label": "Plans", "href": "https://coverage.example.com/plans"}],
            "forms": [
                {
                    "label": "Compare plans Age City Get Quotes",
                    "selector": "form.quote",
                    "input_selector": "input[name='city']",
                    "submit_selector": "button.get-quotes",
                    "fields": [
                        {
                            "selector": "select[name='age']",
                            "name": "",
                            "label": "Age of eldest member",
                            "type": "select",
                            "options": [{"label": "27 years", "value": "27"}],
                        },
                        {
                            "selector": "input[name='city']",
                            "name": "",
                            "label": "City",
                            "placeholder": "e.g. Mumbai",
                            "type": "text",
                        },
                    ],
                }
            ],
            "platform_hints": {},
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]

    assert action["type"] == "sequence"
    assert action["submit_mode"] == "submit"
    assert action["fields"] == ["age_of_eldest_member", "city"]
    assert action["required_fields"] == ["age_of_eldest_member", "city"]
    assert action["steps"][0]["optional"] is False
    assert action["steps"][1]["optional"] is False
    assert action["steps"][-1] == {"op": "submit", "selector": "button.get-quotes"}


def test_submit_text_label_allows_anonymous_quote_form_to_submit() -> None:
    discovery = build_discovery(
        {
            "site_id": "anonymous_quote_demo",
            "origin": "https://coverage.example.com",
            "url": "https://coverage.example.com/",
            "title": "Compare insurance quotes",
            "text_sample": "Compare health insurance plans and show quotes from top insurers.",
            "buttons": [{"label": "Get Health Quotes", "selector": "button.w-full.inline-flex"}],
            "links": [{"label": "Plans", "href": "https://coverage.example.com/plans"}],
            "forms": [
                {
                    "label": "Get Health Quotes Who do you want to insure? Self Self + Family Age of eldest member City",
                    "selector": "form",
                    "input_selector": "select.w-full.px-3",
                    "submit_selector": "button.w-full.inline-flex",
                    "fields": [
                        {
                            "selector": "select.w-full.px-3",
                            "name": "",
                            "label": "Age of eldest member",
                            "type": "select",
                            "options": [{"label": "27 years", "value": "27"}],
                        },
                        {
                            "selector": "input.w-full.px-3",
                            "name": "",
                            "label": "City",
                            "placeholder": "e.g. Mumbai",
                            "type": "text",
                        },
                    ],
                }
            ],
            "platform_hints": {},
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]

    assert action["submit_mode"] == "submit"
    assert action["fields"] == ["age_of_eldest_member", "city"]
    assert action["required_fields"] == ["age_of_eldest_member", "city"]
    assert action["steps"][0]["optional"] is False
    assert action["steps"][1]["optional"] is False
    assert action["steps"][-1] == {"op": "submit", "selector": "button.w-full.inline-flex"}



