import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from agent.flow_discovery import (
    FlowAction,
    _adapter_actions_from_flow,
    _parse_robots_disallow,
    _parse_sitemap_urls,
    _prioritized_candidate_urls,
    _snapshot_from_html,
    build_flow_report_from_snapshots,
)
from agent.scanner import _flow_capabilities
from api import crm
from api.main import app


def test_flow_report_maps_construction_pages_actions_and_prompts() -> None:
    report = build_flow_report_from_snapshots(
        [
            {
                "url": "https://builder.example.com/",
                "title": "BuilderCo Construction",
                "text_sample": "Construction contractor renovation roofing concrete site visit estimate services.",
                "links": [
                    {"label": "Services", "href": "https://builder.example.com/services", "selector": "a.services"},
                    {"label": "Projects", "href": "https://builder.example.com/projects", "selector": "a.projects"},
                ],
                "buttons": [
                    {"label": "Book Site Visit", "selector": "button.visit"},
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
        ],
        site_id="builder_demo",
        site_url="https://builder.example.com",
        requested_vertical_key="",
    )

    data = report.to_dict()

    assert data["vertical_key"] == "construction"
    assert data["summary"]["pages"] == 1
    assert data["adapter_actions"]["REQUEST_ESTIMATE"]["type"] == "form"
    assert data["adapter_actions"]["REQUEST_ESTIMATE"]["submit_mode"] == "fill_only"
    assert data["adapter_actions"]["REQUEST_SITE_VISIT"]["selector"] == "button.visit"
    assert data["routes"]["services"] == "/services"
    assert any("request estimate" in prompt.lower() for prompt in data["prompt_suggestions"])


def test_flow_merge_preserves_rich_browser_form_contract() -> None:
    browser_actions = {
        "START_QUOTE": {
            "type": "sequence",
            "steps": [
                {"op": "select", "selector": "select[name='age']", "param": "age"},
                {"op": "fill", "selector": "input[name='city']", "param": "city"},
                {"op": "submit", "selector": "button.quote"},
            ],
            "fields": ["age", "city"],
            "field_schema": [
                {"param": "age", "label": "Age", "type": "select"},
                {"param": "city", "label": "City", "type": "text"},
            ],
            "submit_mode": "submit",
            "confidence": 0.66,
        }
    }
    flow_actions = [
        FlowAction(
            action_name="START_QUOTE",
            action_type="form",
            page_url="https://coverage.example.com/",
            form="form.quote",
            input="input[name='city']",
            submit="button.quote",
            confidence=0.95,
        )
    ]

    merged = _adapter_actions_from_flow(browser_actions, flow_actions)

    assert merged["START_QUOTE"] == browser_actions["START_QUOTE"]
    assert merged["START_QUOTE"]["submit_mode"] == "submit"


def test_flow_merge_replaces_submit_only_sequence_with_form_contract() -> None:
    weak_actions = {
        "START_QUOTE": {
            "type": "sequence",
            "steps": [{"op": "submit", "selector": "button.quote"}],
            "submit_mode": "submit",
            "confidence": 0.9,
        }
    }
    flow_actions = [
        FlowAction(
            action_name="START_QUOTE",
            action_type="form",
            page_url="https://coverage.example.com/",
            form="form.quote",
            input="input[name='city']",
            submit="button.quote",
            confidence=0.66,
        )
    ]

    merged = _adapter_actions_from_flow(weak_actions, flow_actions)

    assert merged["START_QUOTE"]["type"] == "form"
    assert merged["START_QUOTE"]["input"] == "input[name='city']"
    assert merged["START_QUOTE"]["submit_mode"] == "fill_only"


def test_flow_report_builds_field_sequence_from_server_snapshot() -> None:
    report = build_flow_report_from_snapshots(
        [
            {
                "url": "https://coverage.example.com/",
                "title": "Compare health insurance quotes",
                "text_sample": "Compare health insurance plans and show quotes from top insurers.",
                "links": [],
                "buttons": [{"label": "Get Quotes", "selector": "button.get-quotes"}],
                "forms": [
                    {
                        "label": "Age of eldest member City Show quotes",
                        "selector": "form.quote",
                        "input_selector": "select[name='age']",
                        "submit_selector": "button.get-quotes",
                        "fields": [
                            {
                                "selector": "select[name='age']",
                                "name": "age",
                                "label": "Age of eldest member",
                                "type": "select",
                                "required": True,
                                "options": [{"label": "27 years", "value": "27"}],
                            },
                            {
                                "selector": "input[name='city']",
                                "name": "city",
                                "label": "City",
                                "type": "text",
                                "required": True,
                            },
                        ],
                    }
                ],
                "platform_hints": {},
            }
        ],
        site_id="coverage_demo",
        site_url="https://coverage.example.com",
        requested_vertical_key="insurance",
    )

    action = report.adapter_actions["START_QUOTE"]

    assert action["type"] == "sequence"
    assert action["submit_mode"] == "submit"
    assert action["fields"] == ["age_of_eldest_member", "city"]
    assert action["required_fields"] == ["age_of_eldest_member", "city"]
    assert action["steps"] == [
        {"op": "select", "selector": "select[name='age']", "param": "age_of_eldest_member", "optional": False},
        {"op": "fill", "selector": "input[name='city']", "param": "city", "optional": False},
        {"op": "submit", "selector": "button.get-quotes"},
    ]


def test_static_flow_snapshot_extracts_form_fields_for_http_fallback() -> None:
    html = """
    <html>
      <head><title>Compare health insurance quotes</title></head>
      <body>
        <form class="quote">
          <label for="age">Age of eldest member</label>
          <select id="age" name="age" required>
            <option value="27">27 years</option>
          </select>
          <label for="city">City</label>
          <input id="city" name="city" type="text" placeholder="e.g. Mumbai" required>
          <button class="get-quotes" type="submit">Show quotes</button>
        </form>
      </body>
    </html>
    """

    snapshot = _snapshot_from_html("https://coverage.example.com/", html, "https://coverage.example.com")
    form = snapshot["forms"][0]
    report = build_flow_report_from_snapshots(
        [snapshot],
        site_id="coverage_demo",
        site_url="https://coverage.example.com",
        requested_vertical_key="insurance",
    )

    assert form["fields"][0]["label"] == "Age of eldest member"
    assert form["fields"][0]["options"] == [{"label": "27 years", "value": "27"}]
    assert form["fields"][1]["label"] == "City"
    assert report.adapter_actions["START_QUOTE"]["type"] == "sequence"
    assert report.adapter_actions["START_QUOTE"]["steps"][-1] == {
        "op": "submit",
        "selector": "button.get-quotes",
    }


def test_scanner_flow_capabilities_reflect_saved_flow_graph() -> None:
    caps = {cap.name: cap for cap in _flow_capabilities({
        "flow": {
            "engine": "playwright",
            "summary": {"pages": 3, "actions": 8},
            "prompt_suggestions": ["Show me services."],
        }
    })}

    assert caps["flow_graph"].supported
    assert caps["flow_prompt_suggestions"].supported
    assert "3 page" in caps["flow_graph"].evidence


def test_static_flow_snapshot_extracts_provider_barrier_signatures() -> None:
    html = """
    <html>
      <head>
        <script src="https://js.stripe.com/v3/"></script>
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>
      </head>
      <body>
        <a href="https://checkout.razorpay.com/session">Pay now</a>
        <iframe src="https://outlook.office365.com/book/demo"></iframe>
        <iframe src="https://maps.googleapis.com/maps/api/js"></iframe>
      </body>
    </html>
    """

    hints = _snapshot_from_html(
        "https://demo.example.com/pay",
        html,
        "https://demo.example.com",
    )["barrier_hints"]

    assert hints["captcha"] is True
    assert "turnstile" in hints["captcha_providers"]
    assert "stripe" in hints["payment_providers"]
    assert "razorpay" in hints["payment_providers"]
    assert "microsoft_bookings" in hints["calendar_providers"]
    assert "google_maps" in hints["map_providers"]


def test_http_flow_discovery_prioritizes_sitemap_and_respects_robots() -> None:
    base_url = "https://builder.example.com"
    robots = """
    User-agent: *
    Disallow: /private
    Disallow: /admin
    """
    sitemap = """
    <urlset>
      <url><loc>https://builder.example.com/projects</loc></url>
      <url><loc>https://builder.example.com/private/estimate</loc></url>
      <url><loc>https://other.example.com/projects</loc></url>
      <url><loc>https://builder.example.com/blog</loc></url>
    </urlset>
    """

    disallowed = _parse_robots_disallow(robots)
    sitemap_urls = _parse_sitemap_urls(sitemap, base_url, ("project", "estimate", "services"))
    urls = _prioritized_candidate_urls(base_url, "construction", sitemap_urls, disallowed)

    assert disallowed == ["/private", "/admin"]
    assert "https://builder.example.com/projects" in urls[:3]
    assert all("/private" not in url for url in urls)
    assert all("other.example.com" not in url for url in urls)


def test_crm_flow_discovery_endpoint_persists_and_returns_runtime(monkeypatch) -> None:
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    saved = {}

    class FakeFlow:
        def to_dict(self):
            return {
                "site_id": "builder_demo",
                "site_url": "https://builder.example.com",
                "vertical_key": "construction",
                "detected_vertical_key": "construction",
                "confidence": 0.9,
                "engine": "test",
                "pages": [],
                "actions": [],
                "routes": {},
                "adapter_actions": {},
                "prompt_suggestions": ["Show me construction services."],
                "summary": {"pages": 1, "actions": 1},
                "discovered_at": "now",
                "duration_ms": 1,
            }

    async def fake_discover_site_flows(*args, **kwargs):
        return FakeFlow()

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://builder.example.com",
            "vertical_key": "construction",
            "vertical_config": {},
        },
    )
    monkeypatch.setattr(crm.admin_db, "save_client_flow_report", lambda site_id, report: saved.update({site_id: report}))
    monkeypatch.setattr(crm.admin_db, "save_client_regression_report", lambda site_id, report: None)
    monkeypatch.setattr("agent.flow_discovery.discover_site_flows", fake_discover_site_flows)
    monkeypatch.setattr(
        crm,
        "_public_runtime_config",
        lambda site, api_base_url: {"site_id": site, "enabled": True, "vertical": {}, "adapter": {"flow": saved[site]}},
    )
    monkeypatch.setattr(crm, "_public_widget_base_url", lambda: "https://hub.example.com")
    monkeypatch.setattr(crm, "render_adapter_code", lambda runtime_config: "// adapter")

    res = TestClient(app).post(
        "/v1/admin/clients/builder_demo/flows/discover",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"max_pages": 3},
    )

    assert res.status_code == 200
    assert saved["builder_demo"]["vertical_key"] == "construction"
    assert res.json()["flow"]["prompt_suggestions"] == ["Show me construction services."]
