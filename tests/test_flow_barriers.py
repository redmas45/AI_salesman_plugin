import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.barrier_policy import build_barrier_action_policy, barrier_policy_prompt_context
from agent.flow_discovery import build_flow_report_from_snapshots
from agent.scanner import _barrier_capabilities


def test_flow_report_detects_hard_automation_barriers() -> None:
    report = build_flow_report_from_snapshots(
        [
            {
                "url": "https://clinic.example.com/book",
                "title": "Clinic appointment",
                "text_sample": "Choose a time and upload document. CAPTCHA required before payment.",
                "links": [],
                "buttons": [{"label": "Pay now", "selector": "button.pay"}],
                "forms": [],
                "platform_hints": {},
                "barrier_hints": {
                    "iframe_count": 1,
                    "iframe_sources": ["https://calendly.com/demo"],
                    "password_inputs": 1,
                    "file_uploads": 1,
                    "date_inputs": 1,
                    "captcha": True,
                    "captcha_providers": ["turnstile"],
                    "payment_providers": ["stripe"],
                    "calendar_providers": ["calendly"],
                    "external_action_hosts": ["checkout.stripe.com"],
                },
            }
        ],
        site_id="clinic_demo",
        site_url="https://clinic.example.com",
        requested_vertical_key="healthcare",
    ).to_dict()

    barrier_keys = set(report["barriers"]["summary"]["keys"])
    captcha_findings = [finding for finding in report["barriers"]["findings"] if finding["key"] == "captcha"]

    assert report["summary"]["high_barriers"] >= 2
    assert "auth_required" in barrier_keys
    assert "captcha" in barrier_keys
    assert any("turnstile" in finding["evidence"] for finding in captcha_findings)
    assert "payment_handoff" in barrier_keys
    assert "calendar_widget" in barrier_keys
    assert "file_upload" in barrier_keys
    assert "external_handoff" in barrier_keys


def test_scanner_barrier_capability_flags_high_severity_blockers() -> None:
    caps = {
        cap.name: cap
        for cap in _barrier_capabilities(
            {
                "barriers": {
                    "summary": {
                        "total": 3,
                        "high": 1,
                        "medium": 1,
                        "keys": ["captcha", "embedded_iframe", "map_widget"],
                    }
                }
            },
            "generic",
        )
    }

    assert not caps["flow_barriers"].supported
    assert "1 high" in caps["flow_barriers"].evidence


def test_barrier_policy_builds_provider_aware_handoff_flows() -> None:
    vertical_config = {
        "barriers": {
            "findings": [
                {
                    "key": "captcha",
                    "severity": "high",
                    "page_url": "https://clinic.example.com/book",
                    "evidence": "CAPTCHA provider(s): turnstile",
                    "handling": "Use human handoff.",
                },
                {
                    "key": "payment_handoff",
                    "severity": "high",
                    "page_url": "https://clinic.example.com/pay",
                    "evidence": "Payment provider(s): stripe",
                    "handling": "Never complete payment automatically.",
                },
                {
                    "key": "calendar_widget",
                    "severity": "medium",
                    "page_url": "https://clinic.example.com/book",
                    "evidence": "Calendar provider(s): calendly",
                    "handling": "Use provider-specific slot integration before booking.",
                },
                {
                    "key": "map_widget",
                    "severity": "low",
                    "page_url": "https://clinic.example.com/location",
                    "evidence": "Map provider(s): google",
                    "handling": "Informational only.",
                },
            ]
        }
    }

    policy = build_barrier_action_policy(vertical_config, "healthcare")
    flows = {flow["key"]: flow for flow in policy["handoff_flows"]}
    prompt_context = barrier_policy_prompt_context("clinic_demo", vertical_config, "healthcare")

    assert flows["payment_handoff"]["action"] == "CHECKOUT_HANDOFF"
    assert flows["payment_handoff"]["provider"] == "stripe"
    assert flows["payment_handoff"]["provider_label"] == "Stripe"
    assert "must not enter payment credentials" in flows["payment_handoff"]["automation_boundary"]
    assert "webhooks" in flows["payment_handoff"]["admin_action"]
    assert flows["payment_handoff"]["playbook_steps"]
    assert flows["captcha"]["provider"] == "turnstile"
    assert "must not collect credentials" in flows["captcha"]["automation_boundary"]
    assert flows["calendar_widget"]["action"] == "HANDOFF_TO_CLINIC"
    assert flows["calendar_widget"]["provider"] == "calendly"
    assert "calendar API" in flows["calendar_widget"]["admin_action"]
    assert "map_widget" not in flows
    assert "Handoff flow payment_handoff uses CHECKOUT_HANDOFF" in prompt_context
    assert "Boundary for payment_handoff" in prompt_context
    assert "Admin action for calendar_widget" in prompt_context
