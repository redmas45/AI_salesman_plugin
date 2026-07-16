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


def test_contact_quote_form_remains_prepare_only() -> None:
    discovery = build_discovery(
        {
            "site_id": "quote_demo",
            "origin": "https://coverage.example.com",
            "url": "https://coverage.example.com/",
            "title": "Request insurance quote",
            "text_sample": "Request a policy quote and advisor callback.",
            "buttons": [{"label": "Get Quote", "selector": "button.get-quote"}],
            "links": [{"label": "Contact", "href": "https://coverage.example.com/contact"}],
            "forms": [
                {
                    "label": "Request quote Full name Phone Get Quote",
                    "selector": "form.quote",
                    "input_selector": "input[name='phone']",
                    "submit_selector": "button.get-quote",
                    "fields": [
                        {"selector": "input[name='name']", "label": "Full name", "type": "text"},
                        {"selector": "input[name='phone']", "label": "Phone", "type": "tel"},
                    ],
                }
            ],
            "platform_hints": {},
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]

    assert action["type"] == "sequence"
    assert action["submit_mode"] == "fill_only"
    assert all(step.get("op") != "submit" for step in action["steps"])


def test_registration_with_optional_form_fields_marks_required_fields_known_empty() -> None:
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
                        {"selector": "input[name='phone']", "name": "Phone", "type": "tel"},
                    ],
                }
            ],
            "platform_hints": {},
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]

    assert action["fields"] == ["full_name", "phone"]
    assert action["required_fields"] == []
    assert action["required_fields_known"] is True
    assert all(step["optional"] is True for step in action["steps"])


def test_registration_merges_radio_group_into_one_required_action_param() -> None:
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
                        {"selector": "input[name='phone']", "name": "Phone", "type": "tel", "required": True},
                        {
                            "selector": "input[name='billing_cycle'][value='monthly']",
                            "name": "billing_cycle",
                            "label": "Monthly",
                            "type": "radio",
                            "required": True,
                            "options": [{"label": "Monthly", "value": "monthly"}],
                        },
                        {
                            "selector": "input[name='billing_cycle'][value='annual']",
                            "name": "billing_cycle",
                            "label": "Annual",
                            "type": "radio",
                            "required": True,
                            "options": [{"label": "Annual", "value": "annual"}],
                        },
                    ],
                }
            ],
            "platform_hints": {},
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]
    billing_steps = [step for step in action["steps"] if step.get("param") == "billing_cycle"]
    billing_schema = next(field for field in action["field_schema"] if field["param"] == "billing_cycle")

    assert action["required_fields"] == ["billing_cycle", "phone"]
    assert len(billing_steps) == 1
    assert billing_steps[0]["op"] == "check"
    assert billing_schema["options"] == [
        {"label": "Monthly", "value": "monthly"},
        {"label": "Annual", "value": "annual"},
    ]


def test_construction_site_registration_generates_estimate_adapter_config() -> None:
    discovery = build_discovery(
        {
            "site_id": "BuilderCo",
            "origin": "https://builder.example.com",
            "url": "https://builder.example.com/",
            "title": "BuilderCo Construction, Renovation and Civil Contractors",
            "text_sample": (
                "Residential construction, renovation, remodeling, concrete, roofing, "
                "project portfolio, site visit, and free estimate services."
            ),
            "buttons": [
                {"label": "Request Estimate", "selector": "button.estimate"},
                {"label": "Book Site Visit", "selector": "button.site-visit"},
            ],
            "links": [
                {"label": "Services", "href": "https://builder.example.com/services"},
                {"label": "Projects", "href": "https://builder.example.com/projects"},
                {"label": "Contact", "href": "https://builder.example.com/contact"},
            ],
            "forms": [
                {
                    "label": "Request construction estimate",
                    "selector": "form.estimate",
                    "input_selector": "input[name='phone']",
                    "submit_selector": "button.estimate",
                }
            ],
            "platform_hints": {},
        }
    )

    actions = discovery.vertical_config["actions"]

    assert discovery.vertical_key == "construction"
    assert actions["REQUEST_ESTIMATE"]["type"] == "form"
    assert actions["REQUEST_ESTIMATE"]["submit_mode"] == "fill_only"
    assert actions["REQUEST_SITE_VISIT"]["selector"] == "button.site-visit"
    assert actions["OPEN_PROJECTS"]["path"] == "/projects"
    assert discovery.vertical_config["routes"]["services"] == "/services"


def test_insurance_crawler_extracts_plan_like_blocks_without_prices() -> None:
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@type": "Service",
          "name": "Family Health Insurance Plan",
          "serviceType": "Health Insurance",
          "description": "Coverage for hospitalization, claims support, renewal reminders, and optional riders.",
          "provider": {"name": "Policy Co"}
        }
        </script>
      </head>
      <body>
        <section>
          Term Life Policy: life insurance coverage with premium options, claim support,
          renewal reminders, riders, and family protection.
        </section>
      </body>
    </html>
    """

    rows = _build_candidates_from_html("https://policy.example.com/insurance", html, vertical_key="insurance")
    names = {row["name"] for row in rows}

    assert "Family Health Insurance Plan" in names
    assert any("Term Life Policy" in name for name in names)
    assert all(row["category"] == "Insurance Plans" or "Insurance" in row["category"] for row in rows)


def test_construction_crawler_extracts_service_like_blocks_without_prices() -> None:
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@type": "Service",
          "name": "Turnkey Home Renovation",
          "serviceType": "Construction",
          "description": "Renovation contractor services with site visit, estimate, project planning, concrete, and roofing support.",
          "provider": {"name": "BuilderCo"}
        }
        </script>
      </head>
      <body>
        <section>
          Commercial Construction: contractor-led project planning, site visit,
          estimate, concrete work, roofing coordination, and full renovation delivery.
        </section>
      </body>
    </html>
    """

    rows = _build_candidates_from_html("https://builder.example.com/services", html, vertical_key="construction")
    names = {row["name"] for row in rows}

    assert "Turnkey Home Renovation" in names
    assert any("Commercial Construction" in name for name in names)
    assert all(row["category"] == "Construction Services" for row in rows)


def test_every_backend_vertical_has_discovery_profile() -> None:
    profile_keys = {profile.key for profile in list_discovery_profiles()}
    vertical_keys = {vertical.key for vertical in list_verticals()}

    assert vertical_keys <= profile_keys


def test_non_commerce_knowledge_entity_type_is_vertical_specific() -> None:
    assert knowledge_entity_type_for("construction") == "construction_service"
    assert knowledge_entity_type_for("insurance") == "insurance_plan"

