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


def test_generated_form_action_keeps_source_page_path() -> None:
    discovery = build_discovery(
        {
            "site_id": "policy_website",
            "origin": "https://policy.example.com",
            "url": "https://policy.example.com/",
            "title": "Compare insurance plans",
            "text_sample": "health insurance claim policy quote IRDAI",
            "forms": [
                {
                    "label": "Get insurance quote",
                    "selector": "form.quote",
                    "input_selector": "input[name='city']",
                    "submit_selector": "button.quote",
                    "fields": [{"selector": "input[name='city']", "name": "City", "type": "text"}],
                }
            ],
        }
    )

    action = discovery.vertical_config["actions"]["START_QUOTE"]

    assert action["type"] == "sequence"
    assert action["page_path"] == "/"


def test_insurance_discovery_adds_contact_fallback_lead_and_handoff_actions() -> None:
    discovery = build_discovery(
        {
            "site_id": "policy_website",
            "origin": "https://policy.example.com",
            "url": "https://policy.example.com/",
            "title": "InsureMax health insurance plans and claims",
            "text_sample": "health insurance premium quote claim coverage policy renewal",
            "links": [
                {"label": "Health Plans", "href": "https://policy.example.com/insurance/health"},
                {"label": "Get Quote", "href": "https://policy.example.com/quote"},
                {"label": "Contact advisor", "href": "https://policy.example.com/contact"},
            ],
        }
    )

    actions = discovery.vertical_config["actions"]

    assert actions["START_QUOTE"]["type"] == "navigate"
    assert actions["CAPTURE_LEAD"]["type"] == "navigate"
    assert actions["CAPTURE_LEAD"]["path"] == "/contact"
    assert actions["CAPTURE_LEAD"]["source"] == "contact_route_fallback"
    assert actions["HANDOFF_TO_AGENT"]["type"] == "handoff"
    assert actions["HANDOFF_TO_AGENT"]["path"] == "/contact"
    assert actions["HANDOFF_TO_AGENT"]["source"] == "contact_route_fallback"
    assert "human follow-up" in actions["HANDOFF_TO_AGENT"]["message"]


def test_adapter_action_validator_accepts_sequence_config() -> None:
    actions = client_db._validated_action_map(
        {
            "START_QUOTE": {
                "type": "sequence",
                "steps": [
                    {"op": "fill", "selector": "input[name='name']", "param": "full_name"},
                    {"op": "submit", "selector": "form.quote", "ms": 999999},
                ],
                "fields": ["full_name"],
                "confidence": 0.8,
            }
        }
    )

    assert actions["START_QUOTE"]["type"] == "sequence"
    assert actions["START_QUOTE"]["steps"][1]["ms"] == 5000
    assert actions["START_QUOTE"]["fields"] == ["full_name"]


def test_adapter_action_validator_accepts_handoff_config() -> None:
    actions = client_db._validated_action_map(
        {
            "HANDOFF_TO_AGENT": {
                "type": "handoff",
                "path": "/contact",
                "message": "Agent follow-up is needed.",
                "reason": "Coverage eligibility needs confirmation.",
                "confidence": 0.8,
            }
        }
    )

    assert actions["HANDOFF_TO_AGENT"]["type"] == "handoff"
    assert actions["HANDOFF_TO_AGENT"]["path"] == "/contact"
    assert actions["HANDOFF_TO_AGENT"]["message"] == "Agent follow-up is needed."
    assert actions["HANDOFF_TO_AGENT"]["reason"] == "Coverage eligibility needs confirmation."


def test_adapter_action_validator_preserves_safe_action_page_paths() -> None:
    actions = client_db._validated_action_map(
        {
            "START_QUOTE": {
                "type": "form",
                "form": "form.quote",
                "input": "input[name='city']",
                "submit": "button.quote",
                "pagePath": "/",
                "sourcePath": "/quote?step=1",
                "confidence": 0.8,
            },
            "OPEN_CLAIM_FLOW": {
                "type": "click",
                "selector": "a.claims",
                "page_path": "//evil.example.com/claims",
                "source_path": "https://evil.example.com/claims",
                "confidence": 0.8,
            },
        }
    )

    assert actions["START_QUOTE"]["page_path"] == "/"
    assert actions["START_QUOTE"]["source_path"] == "/quote?step=1"
    assert "page_path" not in actions["OPEN_CLAIM_FLOW"]
    assert "source_path" not in actions["OPEN_CLAIM_FLOW"]


def test_configured_click_resolver_prefers_matching_child_control() -> None:
    source = Path("plugin/src/adapter/dom/targetResolver.js").read_text(encoding="utf-8")

    assert "clickableChildren(configured)" in source
    assert "return childTarget || configured" in source


def test_runtime_tries_client_hooks_before_generated_dom_actions() -> None:
    source = Path("plugin/src/adapter/runtime/runtime.js").read_text(encoding="utf-8")

    client_hook_index = source.index('["client_hook", () => executeClientHookAction(normalizedAction)]')
    configured_index = source.index('["configured_action", () => executeConfiguredAction(normalizedAction, this.config)]')

    assert 'import { executeClientHookAction } from "./clientHooks"' in source
    assert client_hook_index < configured_index


def test_universal_adapter_supports_configured_handoff_actions() -> None:
    dom_actions = Path("plugin/src/adapter/actions/domActions.js").read_text(encoding="utf-8")
    validation = Path("plugin/src/adapter/dom/validation.js").read_text(encoding="utf-8")

    assert 'import { showHandoffOverlay } from "../../handoffOverlay"' in dom_actions
    assert 'actionConfig.type === "handoff"' in dom_actions
    assert "showHandoffOverlay(normalizedAction.action" in dom_actions
    assert "function validateHandoff(actionConfig)" in validation
    assert 'if (type === "handoff") return validateHandoff(actionConfig)' in validation


def test_runtime_resumes_product_specific_actions_after_product_navigation() -> None:
    source = Path("plugin/src/adapter/runtime/runtime.js").read_text(encoding="utf-8")

    resume_index = source.index('["product_page_resume", () => this.prepareProductPageAction(normalizedAction)]')
    configured_index = source.index('["configured_action", () => executeConfiguredAction(normalizedAction, this.config)]')

    assert 'import { storePendingAction, takePendingAction } from "../actions/pendingAction"' in source
    assert 'import { resolveProductActionPath } from "../actions/productNavigation"' in source
    assert "this.executePendingAction()" in source
    assert "storePendingAction(this.siteId, action)" in source
    assert "PRODUCT_NAVIGATION_TELEMETRY_GRACE_MS = 300" in source
    assert resume_index < configured_index


def test_configured_dom_product_actions_do_not_ignore_product_id() -> None:
    source = Path("plugin/src/adapter/actions/domActions.js").read_text(encoding="utf-8")

    assert "PRODUCT_SPECIFIC_DOM_ACTIONS" in source
    assert "isProductSpecificActionOnDifferentPage(normalizedAction)" in source
    assert "productIdFromPath()" in source
    assert 'import { resolveProductActionPath } from "./productNavigation"' in source
    assert "samePath(targetPath, currentPagePath())" in source


def test_configured_dom_product_actions_ignore_stale_listing_page_path_on_product_page() -> None:
    source = Path("plugin/src/adapter/actions/domActions.js").read_text(encoding="utf-8")

    assert "shouldNavigateToActionPage(normalizedAction, actionConfig)" in source
    assert "if (await isCurrentProductSpecificAction(action)) return false" in source
    assert "async function isCurrentProductSpecificAction(action)" in source


def test_adapter_product_navigation_uses_adapter_config_not_widget_config() -> None:
    source = Path("plugin/src/adapter/actions/productNavigation.js").read_text(encoding="utf-8")

    assert 'import { adapterConfig } from "../runtime/config"' in source
    assert 'import { detectPlatform } from "../discovery/platforms"' in source
    assert 'from "../../core/config"' not in source
    assert "API_PATHS.PRODUCTS_BY_IDS" in source
    assert "CUSTOM_CATALOG_ENDPOINTS" in source
    assert "SHOPIFY_CATALOG_ENDPOINTS" in source
    assert "WOOCOMMERCE_CATALOG_ENDPOINTS" in source
    assert "fetchFirstAvailableHostCatalog(catalogEndpointsForPlatform(detectPlatform()))" in source
    assert "/api/products?per_page=96" in source
    assert "/products.json" in source
    assert "/wp-json/wc/store/products?per_page=96" in source
    assert "imageCandidateFrom" in source
    assert "featuredImage" in source


def test_discovery_config_audit_does_not_reference_quota_locals() -> None:
    source = Path("db/client_domain/runtime/client_runtime_workflows.py").read_text(encoding="utf-8")
    section = source[
        source.index("def update_client_discovery_config("):source.index("def update_client_adapter_actions(")
    ]

    assert "clean_limit" not in section
    assert 'event_type="discovery_config_updated"' in section
    assert 'event_scope="discovery"' in section


def test_widget_voice_runtime_uses_stable_http_path_by_default() -> None:
    config_source = Path("plugin/src/core/config.js").read_text(encoding="utf-8")
    api_source = Path("plugin/src/runtime/api.js").read_text(encoding="utf-8")
    recorder_source = Path("plugin/src/audio/recorder.js").read_text(encoding="utf-8")

    assert 'data-use-websocket")).toLowerCase() === "true"' in config_source
    assert "audioFilenameForBlob(blob)" in api_source
    assert "supportedAudioMimeType()" in recorder_source
    assert "MIN_AUDIO_BYTES" in recorder_source
    assert "mediaRecorder.start(RECORDING_TIMESLICE_MS)" in recorder_source


def test_public_widget_cors_covers_overlay_data_endpoints() -> None:
    source = Path("api/runtime/cors_policy.py").read_text(encoding="utf-8")
    cors_block = source[source.index("PUBLIC_WIDGET_CORS_PATHS"):source.index("def origin_from_url")]

    assert '"/v1/products"' in cors_block
    assert '"/v1/products/by-ids"' in cors_block
    assert '"/v1/knowledge/by-ids"' in cors_block


def test_pending_action_store_is_short_lived_and_site_scoped() -> None:
    source = Path("plugin/src/adapter/actions/pendingAction.js").read_text(encoding="utf-8")

    assert "MAX_PENDING_ACTION_AGE_MS = 15000" in source
    assert "aihub:pending-action:" in source
    assert "window.sessionStorage.setItem" in source
    assert "window.sessionStorage.removeItem" in source


def test_client_hook_executor_supports_product_specific_cart_actions() -> None:
    source = Path("plugin/src/adapter/runtime/clientHooks.js").read_text(encoding="utf-8")

    assert "ACTIONS.ADD_TO_CART" in source
    assert "window.AIHubClient" in source
    assert "window.__AIHUB_CLIENT__" in source
    assert "client.addToCart({ productId, quantity, params })" in source


def test_adapter_action_validator_preserves_form_fields() -> None:
    actions = client_db._validated_action_map(
        {
            "REQUEST_ESTIMATE": {
                "type": "form",
                "form": "form.estimate",
                "input": "input[name='phone']",
                "submit": "button.submit",
                "submit_mode": "fill_only",
                "fields": ["full_name", "phone"],
                "required_fields": ["phone"],
                "required_fields_known": True,
                "field_schema": [
                    {"param": "full_name", "label": "Full name", "type": "text", "required": False},
                    {"param": "phone", "label": "Phone", "type": "tel", "required": True},
                ],
                "confidence": 0.8,
            }
        }
    )

    assert actions["REQUEST_ESTIMATE"]["type"] == "form"
    assert actions["REQUEST_ESTIMATE"]["fields"] == ["full_name", "phone"]
    assert actions["REQUEST_ESTIMATE"]["required_fields"] == ["phone"]
    assert actions["REQUEST_ESTIMATE"]["required_fields_known"] is True
    assert actions["REQUEST_ESTIMATE"]["field_schema"][1]["label"] == "Phone"


def test_adapter_action_validator_preserves_known_empty_required_fields() -> None:
    actions = client_db._validated_action_map(
        {
            "REQUEST_ESTIMATE": {
                "type": "form",
                "form": "form.estimate",
                "input": "input[name='phone']",
                "submit_mode": "fill_only",
                "fields": ["full_name", "phone"],
                "required_fields": [],
                "required_fields_known": True,
                "confidence": 0.8,
            }
        }
    )

    assert actions["REQUEST_ESTIMATE"]["fields"] == ["full_name", "phone"]
    assert actions["REQUEST_ESTIMATE"]["required_fields"] == []
    assert actions["REQUEST_ESTIMATE"]["required_fields_known"] is True



