"""Provider-heavy layout fixtures for universal website onboarding."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from agent.barrier_policy import build_barrier_action_policy, barrier_policy_prompt_context
from agent.flow_discovery import build_flow_report_from_snapshots
from agent.page_context import format_page_context, parse_page_context


COMPLEX_LAYOUT_CASES: list[dict[str, Any]] = [
    {
        "name": "travel_ticketing_provider_checkout",
        "vertical": "travel",
        "text": "Dubai tours, attraction tickets, destination booking, choose a date, secure checkout, pay now, and recaptcha verification.",
        "buttons": [("Book tickets", "button.book"), ("Pay now", "button.pay")],
        "links": [("Things to do", "/things-to-do"), ("Tickets", "/tickets"), ("Checkout", "/checkout")],
        "form_label": "Book tickets",
        "fields": [
            {"selector": "input[name='destination']", "name": "Destination", "type": "text", "required": True},
            {"selector": "input[name='date']", "name": "Date", "type": "date", "required": True},
        ],
        "barrier_hints": {
            "iframe_count": 1,
            "iframe_sources": ["https://checkout.stripe.com/pay/session_123"],
            "date_inputs": 1,
            "captcha": True,
            "captcha_providers": ["recaptcha"],
            "payment_providers": ["stripe"],
            "calendar_providers": ["calendly"],
            "external_action_hosts": ["checkout.stripe.com"],
        },
        "expected_barriers": {"captcha", "payment_handoff", "calendar_widget", "embedded_iframe", "external_handoff"},
        "expected_handoff": ("payment_handoff", "stripe", "CHECKOUT_HANDOFF"),
        "expected_action": "START_BOOKING",
    },
    {
        "name": "healthcare_scheduler_provider",
        "vertical": "healthcare",
        "text": "Doctor clinic specialists, treatment departments, appointment slot, choose a time, hcaptcha, and Zocdoc scheduling.",
        "buttons": [("Book appointment", "button.appointment"), ("Talk to clinic", "a.clinic")],
        "links": [("Doctors", "/doctors"), ("Treatments", "/treatments"), ("Appointments", "/appointments")],
        "form_label": "Book appointment",
        "fields": [
            {"selector": "input[name='patient']", "name": "Patient name", "type": "text", "required": True},
            {"selector": "select[name='department']", "name": "Department", "type": "select", "required": True},
        ],
        "barrier_hints": {
            "iframe_count": 1,
            "iframe_sources": ["https://www.zocdoc.com/widget/booking"],
            "date_inputs": 1,
            "captcha": True,
            "captcha_providers": ["hcaptcha"],
            "calendar_providers": ["zocdoc"],
            "external_action_hosts": ["www.zocdoc.com"],
        },
        "expected_barriers": {"captcha", "calendar_widget", "embedded_iframe", "external_handoff"},
        "expected_handoff": ("calendar_widget", "zocdoc", "HANDOFF_TO_CLINIC"),
        "expected_action": "REQUEST_APPOINTMENT",
    },
    {
        "name": "insurance_quote_document_gate",
        "vertical": "insurance",
        "text": "Health insurance policy coverage, premium quote, claim support, upload document, login required, and renewal.",
        "buttons": [("Get insurance quote", "button.quote"), ("Open claim", "button.claim")],
        "links": [("Plans", "/plans"), ("Claims", "/claims"), ("Renewal", "/renewal")],
        "form_label": "Get insurance quote",
        "fields": [
            {"selector": "input[name='age']", "name": "Age", "type": "number", "required": True},
            {"selector": "input[name='sum_insured']", "name": "Sum insured", "type": "number", "required": True},
        ],
        "barrier_hints": {
            "password_inputs": 1,
            "file_uploads": 1,
            "captcha": True,
            "captcha_providers": ["turnstile"],
            "external_action_hosts": ["secure.insurer.example"],
        },
        "expected_barriers": {"auth_required", "captcha", "file_upload", "external_handoff"},
        "expected_handoff": ("captcha", "turnstile", "HANDOFF_TO_LICENSED_AGENT"),
        "expected_action": "START_QUOTE",
    },
    {
        "name": "ecommerce_paypal_checkout",
        "vertical": "ecommerce",
        "text": "Fashion store product catalog, sale, add to cart, checkout, payment, PayPal secure checkout, and delivery.",
        "buttons": [("Add to cart", "button.add-cart"), ("Checkout", "button.checkout")],
        "links": [("Shop", "/collections/all"), ("Cart", "/cart"), ("Checkout", "/checkout")],
        "form_label": "Search products",
        "fields": [
            {"selector": "input[name='q']", "name": "Search", "type": "search", "required": True},
        ],
        "barrier_hints": {
            "iframe_count": 1,
            "iframe_sources": ["https://www.paypal.com/buttons"],
            "payment_providers": ["paypal"],
            "external_action_hosts": ["www.paypal.com"],
        },
        "expected_barriers": {"payment_handoff", "embedded_iframe", "external_handoff"},
        "expected_handoff": ("payment_handoff", "paypal", "CHECKOUT_HANDOFF"),
        "expected_action": "ADD_TO_CART",
    },
    {
        "name": "construction_estimate_upload_map",
        "vertical": "construction",
        "text": "Construction contractor renovation, remodeling, roofing, concrete, request estimate, upload blueprint, site visit, and service area map.",
        "buttons": [("Request estimate", "button.estimate"), ("Schedule site visit", "button.site-visit")],
        "links": [("Services", "/services"), ("Projects", "/projects"), ("Estimate", "/estimate")],
        "form_label": "Request estimate",
        "fields": [
            {"selector": "input[name='postcode']", "name": "Postcode", "type": "text", "required": True},
            {"selector": "textarea[name='scope']", "name": "Project scope", "type": "textarea", "required": True},
        ],
        "barrier_hints": {
            "iframe_count": 1,
            "iframe_sources": ["https://forms.hubspot.com/embed/project-estimate"],
            "file_uploads": 1,
            "map_providers": ["google_maps"],
            "external_action_hosts": ["forms.hubspot.com"],
        },
        "expected_barriers": {"file_upload", "map_widget", "embedded_iframe", "external_handoff"},
        "expected_handoff": ("file_upload", "", "HANDOFF_TO_HUMAN"),
        "expected_action": "REQUEST_ESTIMATE",
    },
    {
        "name": "education_enrollment_scheduler",
        "vertical": "education",
        "text": "Online courses, syllabus, admissions, enroll now, upload transcript, counselor appointment, and Microsoft Bookings calendar.",
        "buttons": [("Enroll now", "button.enroll"), ("Book counselor callback", "button.counselor")],
        "links": [("Courses", "/courses"), ("Admissions", "/admissions"), ("Syllabus", "/syllabus")],
        "form_label": "Enroll now",
        "fields": [
            {"selector": "input[name='program']", "name": "Program", "type": "text", "required": True},
            {"selector": "select[name='level']", "name": "Level", "type": "select", "required": True},
        ],
        "barrier_hints": {
            "password_inputs": 1,
            "file_uploads": 1,
            "date_inputs": 1,
            "calendar_providers": ["microsoft_bookings"],
            "external_action_hosts": ["outlook.office365.com"],
        },
        "expected_barriers": {"auth_required", "calendar_widget", "file_upload", "external_handoff"},
        "expected_handoff": ("calendar_widget", "microsoft_bookings", "HANDOFF_TO_HUMAN"),
        "expected_action": "START_ENROLLMENT",
    },
    {
        "name": "recruiting_resume_challenge",
        "vertical": "jobs_recruiting",
        "text": "Careers, recruiting, job vacancy, resume upload, apply now, salary skills, and recaptcha challenge.",
        "buttons": [("Apply now", "button.apply-job"), ("Match jobs", "button.match")],
        "links": [("Jobs", "/jobs"), ("Careers", "/careers"), ("Apply", "/apply")],
        "form_label": "Apply now",
        "fields": [
            {"selector": "input[name='role']", "name": "Role", "type": "text", "required": True},
            {"selector": "input[name='resume']", "name": "Resume", "type": "file", "required": True},
        ],
        "barrier_hints": {
            "iframe_count": 1,
            "iframe_sources": ["https://boards.greenhouse.io/embed/job_board"],
            "file_uploads": 1,
            "captcha": True,
            "captcha_providers": ["recaptcha"],
            "external_action_hosts": ["boards.greenhouse.io"],
        },
        "expected_barriers": {"captcha", "file_upload", "embedded_iframe", "external_handoff"},
        "expected_handoff": ("captcha", "recaptcha", "HANDOFF_TO_RECRUITER"),
        "expected_action": "START_APPLICATION",
    },
]


@pytest.mark.parametrize("case", COMPLEX_LAYOUT_CASES, ids=lambda item: item["name"])
def test_complex_provider_layouts_generate_safe_handoff_playbooks(case: dict[str, Any]) -> None:
    report = _flow_report(case)
    barrier_keys = set(report["barriers"]["summary"]["keys"])
    vertical_config = _vertical_config_from_report(report)
    policy = build_barrier_action_policy(vertical_config, case["vertical"])
    handoff_key, provider, action = case["expected_handoff"]
    handoff_flow = _handoff_flow(policy, handoff_key)

    assert report["vertical_key"] == case["vertical"]
    assert case["expected_barriers"] <= barrier_keys
    assert case["expected_action"] in report["adapter_actions"]
    assert handoff_flow["provider"] == provider
    assert handoff_flow["action"] == action
    assert handoff_flow["automation_boundary"]
    assert handoff_flow["admin_action"]
    assert handoff_flow["recovery"]
    assert handoff_flow["playbook_steps"]
    assert action in policy["handoff_actions"]
    assert _has_field_schema(report["adapter_actions"])


@pytest.mark.parametrize("case", COMPLEX_LAYOUT_CASES[:4], ids=lambda item: item["name"])
def test_complex_provider_context_is_prompt_safe(case: dict[str, Any]) -> None:
    report = _flow_report(case)
    vertical_config = _vertical_config_from_report(report)
    policy = build_barrier_action_policy(vertical_config, case["vertical"])
    raw_context = json.dumps({"adapter": {"handoff_flows": policy["handoff_flows"]}})
    context = parse_page_context(raw_context)
    prompt_context = barrier_policy_prompt_context(case["name"], vertical_config, case["vertical"])
    browser_context = format_page_context(context)

    assert context["handoff_flows"]
    assert "evidence" not in context["handoff_flows"][0]
    assert "Boundary for" in prompt_context
    assert "evidence" not in json.dumps(context).lower()
    assert context["handoff_flows"][0]["automation_boundary"]
    assert "use" in browser_context.lower()


def _flow_report(case: dict[str, Any]) -> dict[str, Any]:
    return build_flow_report_from_snapshots(
        [_snapshot(case)],
        site_id=case["name"],
        site_url=_origin(case),
        requested_vertical_key=case["vertical"],
        engine="fixture",
    ).to_dict()


def _snapshot(case: dict[str, Any]) -> dict[str, Any]:
    origin = _origin(case)
    return {
        "url": f"{origin}/",
        "title": case["name"].replace("_", " ").title(),
        "text_sample": case["text"],
        "links": [{"label": label, "href": f"{origin}{path}", "selector": f"a[href='{path}']"} for label, path in case["links"]],
        "buttons": [{"label": label, "selector": selector} for label, selector in case["buttons"]],
        "forms": [_form(case)],
        "platform_hints": {},
        "barrier_hints": case["barrier_hints"],
    }


def _form(case: dict[str, Any]) -> dict[str, Any]:
    primary_button = case["buttons"][0][1]
    return {
        "label": case["form_label"],
        "selector": "form.primary-flow",
        "input_selector": case["fields"][0]["selector"],
        "submit_selector": primary_button,
        "fields": case["fields"],
    }


def _origin(case: dict[str, Any]) -> str:
    return f"https://{case['name']}.example.com"


def _vertical_config_from_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "barriers": report["barriers"],
        "routes": report["routes"],
        "actions": report["adapter_actions"],
    }


def _handoff_flow(policy: dict[str, Any], key: str) -> dict[str, Any]:
    for flow in policy["handoff_flows"]:
        if flow["key"] == key:
            return flow
    raise AssertionError(f"Missing handoff flow: {key}")


def _has_field_schema(actions: dict[str, dict[str, Any]]) -> bool:
    return any(action.get("field_schema") for action in actions.values())
