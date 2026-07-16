"""Public widget installer and adapter runtime contract tests."""

import sys
from pathlib import Path

import pytest
from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import clients as client_routes
from api.routes.client_widgets import client_scripts
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


def test_install_script_loads_adapter_before_widget() -> None:
    script = client_routes._render_install_script(
        site="ai_kart",
        api_base_url="https://hub.example.com/aihub",
    )

    adapter_index = script.index("mayabot-adapter.js?site=ai_kart")
    widget_index = script.index("mayabot.js?site=ai_kart")

    assert "__aihubInstallLoadedSites" in script
    assert adapter_index < widget_index
    assert "data-site-id" in script
    assert "data-api-url" in script


def test_widget_bundles_resolve_from_repository_plugin_directory() -> None:
    repository_root = Path(__file__).resolve().parent.parent

    assert client_scripts.PLUGIN_DIR == repository_root / "plugin"
    assert (client_scripts.PLUGIN_DIR / client_scripts.ADAPTER_SCRIPT_NAME).is_file()
    assert (client_scripts.PLUGIN_DIR / client_scripts.WIDGET_SCRIPT_NAME).is_file()


def test_universal_install_script_does_not_require_manual_site_id() -> None:
    script = client_routes._render_install_script(
        api_base_url="https://hub.example.com/aihub",
    )

    adapter_index = script.index("mayabot-adapter.js")
    widget_index = script.index("mayabot.js")

    assert "mayabot-adapter.js?site=" not in script
    assert "mayabot.js?site=" not in script
    assert "data-aihub-universal" in script
    assert 'script.setAttribute("data-site-id", siteId)' in script
    assert '"auto:" + window.location.origin' in script
    assert adapter_index < widget_index


def test_public_widget_base_url_upgrades_public_http_hosts() -> None:
    assert client_routes._public_script_base_url("http://demo1.ergobite.com") == "https://demo1.ergobite.com"
    assert client_routes._public_script_base_url("http://127.0.0.1:5176") == "http://127.0.0.1:5176"


def test_available_installs_still_load_scripts_for_discovery(monkeypatch) -> None:
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {"site_id": site, "status": client_db.CLIENT_STATUS_AVAILABLE},
    )

    assert client_routes._client_scripts_can_load("policy_website") is True


def test_disabled_clients_do_not_load_public_scripts(monkeypatch) -> None:
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {"site_id": site, "status": client_db.CLIENT_STATUS_DISABLED},
    )

    assert client_routes._client_scripts_can_load("policy_website") is False


def test_ecommerce_discovery_prefers_add_to_cart_button_over_parent_card_link() -> None:
    discovery = build_discovery(
        {
            "site_id": "ai_kart",
            "origin": "https://shop.example.com",
            "url": "https://shop.example.com/",
            "title": "AI-KART shop",
            "text_sample": "Product catalog, price, sale, add to cart, cart, checkout.",
            "buttons": [
                {
                    "label": "50% off Add to cart Portronics Signature Chargers Rs 5,299",
                    "selector": "a.group.block",
                    "href": "https://shop.example.com/product/1",
                },
                {
                    "label": "Add to cart",
                    "selector": "button[aria-label=\"Add Portronics Signature Chargers to cart\"]",
                },
            ],
            "links": [
                {"label": "Cart", "href": "https://shop.example.com/cart", "selector": "a[href=\"/cart\"]"},
                {"label": "Checkout", "href": "https://shop.example.com/checkout", "selector": "a[href=\"/checkout\"]"},
            ],
        }
    )

    action = discovery.vertical_config["actions"]["ADD_TO_CART"]

    assert action["selector"].startswith("button[aria-label=")
    assert action["label"] == "Add to cart"


def test_generated_insurance_prompt_is_deep_and_client_specific() -> None:
    discovery = build_discovery(
        {
            "site_id": "policy_site",
            "origin": "https://policy.example.com",
            "url": "https://policy.example.com/plans",
            "title": "InsureMax - Compare & Buy Insurance Online",
            "text_sample": (
                "Health insurance, term insurance, premium, claim support, renew policy, "
                "cashless network, waiting period, exclusions, and request quote."
            ),
            "buttons": [
                {"label": "Get Quote", "selector": "button.quote"},
                {"label": "Renew Policy", "selector": "button.renew"},
            ],
            "links": [
                {"label": "Plans", "href": "https://policy.example.com/plans"},
                {"label": "Claims", "href": "https://policy.example.com/claims"},
                {"label": "Contact", "href": "https://policy.example.com/contact"},
            ],
            "forms": [
                {
                    "label": "Get insurance quote",
                    "selector": "form.quote",
                    "fields": [
                        {"label": "Coverage type", "selector": "select.coverage", "type": "select"},
                        {"label": "Phone", "selector": "input.phone", "type": "tel", "required": True},
                    ],
                }
            ],
        }
    )

    assert discovery.vertical_key == "insurance"
    assert len(discovery.prompt) > 1800
    assert "## Insurance Sales Playbook" in discovery.prompt
    assert "## Conversation Intelligence And Slot Filling" in discovery.prompt
    assert "discovered action fields" in discovery.prompt
    assert "not to hardcoded site or industry assumptions" in discovery.prompt
    assert "InsureMax" in discovery.prompt
    assert "waiting periods" in discovery.prompt
    assert "Claims" in discovery.prompt
    assert "Get insurance quote" in discovery.prompt
    assert "SORT_ENTITIES" in discovery.developer_rules
    assert "extract matching values from the latest user message" in discovery.developer_rules


def test_plugin_runtime_uses_shared_automatic_site_identity() -> None:
    widget_config_facade = Path("plugin/src/config.js").read_text(encoding="utf-8")
    widget_config = Path("plugin/src/core/config.js").read_text(encoding="utf-8")
    adapter_config = Path("plugin/src/adapter/runtime/config.js").read_text(encoding="utf-8")
    site_identity_facade = Path("plugin/src/siteIdentity.js").read_text(encoding="utf-8")
    site_identity = Path("plugin/src/core/siteIdentity.js").read_text(encoding="utf-8")

    assert "export * from \"./core/config\"" in widget_config_facade
    assert "export * from \"./core/siteIdentity\"" in site_identity_facade
    assert "from \"./siteIdentity\"" in widget_config
    assert "from \"../../core/siteIdentity\"" in adapter_config
    assert "export function resolveSiteId" in site_identity
    assert "aihub:auto-site-id:" in site_identity
    assert "canonicalAutoSiteId" in site_identity
    assert ".replace(/[^a-z0-9]+/g, \"_\")" in site_identity
    assert "hostNeedsPathScope" not in site_identity
    assert "basePathScope" not in site_identity
    assert "data-aihub-site-id" in site_identity
    assert "data-aihub-scope" in site_identity


def test_adapter_runtime_refreshes_config_after_registration() -> None:
    source = Path("plugin/src/adapter/runtime/runtime.js").read_text(encoding="utf-8")
    telemetry = Path("plugin/src/adapter/runtime/actionTelemetry.js").read_text(encoding="utf-8")
    action_params = Path("plugin/src/adapter/actions/actionParams.js").read_text(encoding="utf-8")
    discovery = Path("plugin/src/adapter/discovery/discovery.js").read_text(encoding="utf-8")
    policy = Path("plugin/src/adapter/runtime/policy.js").read_text(encoding="utf-8")
    page_context = Path("plugin/src/adapter/runtime/pageContext.js").read_text(encoding="utf-8")
    widget_api = Path("plugin/src/runtime/api.js").read_text(encoding="utf-8")

    assert "await this.registerDiscovery()" in source
    assert "await this.discoverAndRefresh(\"initial\")" in source
    assert "await this.refreshRuntimeConfig(reason)" in source
    assert "discoverPage" in source
    assert "discoveryInFlight" in source
    assert "dom_mutation" in source
    assert "reportActionExecution" in source
    assert "configured_action" in source
    assert "dom_fallback" in source
    assert "isActionFallbackStop" in source
    assert "missing_params" in action_params
    assert "required_fields" in action_params
    assert "required_fields_known" in action_params
    assert "stopForMissingParams" in action_params
    assert "fieldRequired" in discovery
    assert "fieldLabel" in discovery
    assert "fieldOptions" in discovery
    assert "formLabel(form, input, submit)" in discovery
    assert "submitElementFor(form)" in discovery
    assert "autocomplete" in discovery
    assert "from \"./pageContext\"" in source
    assert "readPageContext(this.config)" in source
    assert "/v1/widget/action-event" in telemetry
    assert "param_keys" in telemetry
    assert "navigator.sendBeacon" in telemetry
    assert "new Blob([payload], { type: \"application/json\" })" in telemetry
    assert "runtime_blocked_actions" in policy
    assert "blocked_by_action_health" in policy
    assert "handoff_flows" in policy
    assert "handoff_flow" in policy
    assert "export function readPageContext" in page_context
    assert "controls:" in page_context
    assert "handoff_flows" in page_context
    assert "handoffFlowContext" in page_context
    assert "automation_boundary" in page_context
    assert "admin_action" in page_context
    assert "recovery" in page_context
    assert "field.value" not in page_context
    assert "page_context" in widget_api
    assert "currentPageContext()" in widget_api


