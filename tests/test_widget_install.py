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
    widget_config = Path("plugin/src/config.js").read_text(encoding="utf-8")
    adapter_config = Path("plugin/src/adapter/config.js").read_text(encoding="utf-8")
    site_identity = Path("plugin/src/siteIdentity.js").read_text(encoding="utf-8")

    assert "from \"./siteIdentity\"" in widget_config
    assert "from \"../siteIdentity\"" in adapter_config
    assert "export function resolveSiteId" in site_identity
    assert "aihub:auto-site-id:" in site_identity
    assert "canonicalAutoSiteId" in site_identity
    assert ".replace(/[^a-z0-9]+/g, \"_\")" in site_identity
    assert "hostNeedsPathScope" not in site_identity
    assert "basePathScope" not in site_identity
    assert "data-aihub-site-id" in site_identity
    assert "data-aihub-scope" in site_identity


def test_adapter_runtime_refreshes_config_after_registration() -> None:
    source = Path("plugin/src/adapter/runtime.js").read_text(encoding="utf-8")
    telemetry = Path("plugin/src/adapter/actionTelemetry.js").read_text(encoding="utf-8")
    action_params = Path("plugin/src/adapter/actionParams.js").read_text(encoding="utf-8")
    discovery = Path("plugin/src/adapter/discovery.js").read_text(encoding="utf-8")
    policy = Path("plugin/src/adapter/policy.js").read_text(encoding="utf-8")
    page_context = Path("plugin/src/adapter/pageContext.js").read_text(encoding="utf-8")
    widget_api = Path("plugin/src/api.js").read_text(encoding="utf-8")

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


def test_widget_action_executor_is_modular_and_shared() -> None:
    assert not Path("plugin/src/actions.js").exists()

    api_source = Path("plugin/src/api.js").read_text(encoding="utf-8")
    widget_entry = Path("plugin/src/index.js").read_text(encoding="utf-8")
    recorder_source = Path("plugin/src/recorder.js").read_text(encoding="utf-8")
    bridge_source = Path("plugin/src/adapterBridge.js").read_text(encoding="utf-8")
    runtime_source = Path("plugin/src/adapter/runtime.js").read_text(encoding="utf-8")
    executor_source = Path("plugin/src/actionExecutor/index.js").read_text(encoding="utf-8")
    runtime_executor = Path("plugin/src/actionExecutor/runtimeAction.js").read_text(encoding="utf-8")
    product_executor = Path("plugin/src/actionExecutor/productActions.js").read_text(encoding="utf-8")
    entity_executor = Path("plugin/src/actionExecutor/entityActions.js").read_text(encoding="utf-8")
    handoff_executor = Path("plugin/src/actionExecutor/handoffActions.js").read_text(encoding="utf-8")
    handoff_overlay = Path("plugin/src/handoffOverlay.js").read_text(encoding="utf-8")
    entity_overlay = Path("plugin/src/entityOverlay.js").read_text(encoding="utf-8")
    entity_resolver = Path("plugin/src/entityResolver.js").read_text(encoding="utf-8")
    product_overlay = Path("plugin/src/productOverlay.js").read_text(encoding="utf-8")
    product_resolver = Path("plugin/src/productResolver.js").read_text(encoding="utf-8")
    dom_actions = Path("plugin/src/adapter/domActions.js").read_text(encoding="utf-8")

    assert "from \"./actionExecutor\"" in api_source
    assert "let processingTurn = false" in widget_entry
    assert "if (processingTurn) return" in widget_entry
    assert "elements.btn.disabled = true" in widget_entry
    assert "elements.btn.disabled = false" in widget_entry
    assert "BROWSER_ACTION_RESULTS" in widget_entry
    assert "onActionResults: rememberActionResults" in widget_entry
    assert "rendered_products=" in widget_entry
    assert "rendered_records=" in widget_entry
    assert "let isStarting = false" in recorder_source
    assert "if (isStarting || isRecording) return" in recorder_source
    assert "mediaRecorder.onerror" in recorder_source
    assert "executePlatformAction" in executor_source
    assert "executeProviderAction" in executor_source
    assert "executeRuntimeAction" in executor_source
    assert "STOP_ACTION_FALLBACK" in executor_source
    assert "executeWithAIHubAdapterResult" in bridge_source
    assert "lastActionResult" in runtime_source
    assert "status: \"blocked\"" in runtime_source
    assert "status: \"disabled\"" in runtime_source
    assert "result.blocked || result.disabled" in runtime_executor
    assert "PRODUCT_OVERLAY_ACTIONS" in runtime_executor
    assert "!PRODUCT_OVERLAY_ACTIONS.has(action.action)" in runtime_executor
    assert "executeProductAction" in executor_source
    assert "normalizeExecutorResult" in executor_source
    assert "result.evidence" in executor_source
    assert "return results" in executor_source
    assert "final_url: finalUrl" in executor_source
    assert "callbacks.onActionResults" in api_source
    assert "const sharedAudioQueue = new AudioQueue()" in api_source
    assert "speakTextFallback(data.response_text)" in api_source
    assert "retryBlocked()" in api_source
    assert "SHOW_COMPARISON" in product_executor
    assert "Product comparison" in product_executor
    assert "syncListing: false" in product_executor
    assert "executeWithAIHubAdapterResult" in product_executor
    assert "ACTIONS.FILTER_PRODUCTS" in product_executor
    assert "listing_sync_status" in product_executor
    assert "rendered_product_count" in product_overlay
    assert "no_matching_products_rendered" in product_overlay
    assert "fetchProductsForDisplay" in product_overlay
    assert "lookup_source" in product_overlay
    assert "/api/products?per_page=96" in product_resolver
    assert "hub_search" in product_resolver
    assert "host_search" in product_resolver
    assert "imageCandidateFrom" in product_resolver
    assert "featuredImage" in product_resolver
    assert "removeNegativeCorrections" in product_resolver
    assert "canonicalQueryTerm" in product_resolver
    assert "url.searchParams.set(\"q\", searchQuery)" in dom_actions
    assert "navigateToSearchPage(searchQuery, runtimeConfig)" in dom_actions
    assert "executeEntityAction" in executor_source
    assert "executeHandoffAction" in executor_source
    assert "HANDOFF_ACTIONS" in handoff_executor
    assert "CHECKOUT_HANDOFF" in handoff_overlay
    assert "HANDOFF_TO_HUMAN" in handoff_overlay
    assert "handoffActionForPolicy" in handoff_overlay
    assert "flowMetaMarkup" in handoff_overlay
    assert "handoff_flow" in runtime_source
    assert "automation_boundary" in handoff_overlay
    assert "Recovery" in handoff_overlay
    assert "showHandoffOverlay" in runtime_source
    assert "provider_adapter" in runtime_source
    assert "SHOW_ENTITIES" in entity_executor
    assert "COMPARE_ENTITIES" in entity_executor
    assert "OPEN_ENTITY_DETAIL" in entity_executor
    assert "showEntityOverlay" in entity_overlay
    assert "rendered_entity_count" in entity_overlay
    assert "no_matching_entities_rendered" in entity_overlay
    assert "fetchHubEntitiesByIds" in entity_resolver
    assert "KNOWLEDGE_BY_IDS" in entity_resolver
    assert "demo.vercel.store" not in entity_overlay
    assert "demo.vercel.store" not in product_overlay
    assert "ShopifyNativeAdapter" not in executor_source
    assert "WooCommerceNativeAdapter" not in executor_source


def test_widget_action_constants_cover_backend_registry() -> None:
    plugin_source = Path("plugin/src/constants.js").read_text(encoding="utf-8")
    contract_source = Path("packages/contracts/index.js").read_text(encoding="utf-8")

    assert '@ai-hub/contracts' in plugin_source
    for action_name in sorted(list_action_names()):
        assert f'{action_name}: "{action_name}"' in contract_source


def test_adapter_observes_spa_navigation_and_async_dom_changes() -> None:
    source = Path("plugin/src/adapter/pageLifecycle.js").read_text(encoding="utf-8")

    assert "from \"./controlSelectors\"" in source
    assert "pushState" in source
    assert "replaceState" in source
    assert "popstate" in source
    assert "hashchange" in source
    assert "MutationObserver" in source
    assert "pageStructureSignature" in source
    assert "MIN_DOM_DISCOVERY_INTERVAL_MS" in source
    assert "#mayabot-widget" in source
    assert "CONTROL_SELECTOR" in source
    assert "searchRoots()" in source
    assert "queryElementsDeep" in source


def test_adapter_tracks_privacy_safe_interactions() -> None:
    source = Path("plugin/src/adapter/interactionTracker.js").read_text(encoding="utf-8")

    assert "/v1/widget/interaction-event" in source
    assert "document.addEventListener(\"click\"" in source
    assert "document.addEventListener(\"submit\"" in source
    assert "field.value" not in source
    assert "value:" not in source


def test_adapter_uses_shared_target_resolver_for_stale_selectors() -> None:
    selectors = Path("plugin/src/adapter/controlSelectors.js").read_text(encoding="utf-8")
    event_driver = Path("plugin/src/adapter/eventDriver.js").read_text(encoding="utf-8")
    deep_dom = Path("plugin/src/adapter/deepDom.js").read_text(encoding="utf-8")
    resolver = Path("plugin/src/adapter/targetResolver.js").read_text(encoding="utf-8")
    actions = Path("plugin/src/adapter/domActions.js").read_text(encoding="utf-8")
    sequence = Path("plugin/src/adapter/domSequence.js").read_text(encoding="utf-8")
    form_filler = Path("plugin/src/adapter/formFiller.js").read_text(encoding="utf-8")
    action_params = Path("plugin/src/adapter/actionParams.js").read_text(encoding="utf-8")
    field_schema = Path("plugin/src/adapter/fieldSchema.js").read_text(encoding="utf-8")
    discovery = Path("plugin/src/adapter/discovery.js").read_text(encoding="utf-8")
    validation = Path("plugin/src/adapter/validation.js").read_text(encoding="utf-8")
    tracker = Path("plugin/src/adapter/interactionTracker.js").read_text(encoding="utf-8")
    submit_resolver = Path("plugin/src/adapter/submitResolver.js").read_text(encoding="utf-8")

    assert "[role='menuitem']" in selectors
    assert "[role='tab']" in selectors
    assert "[role='combobox']" in selectors
    assert "[role='radio']" in selectors
    assert "[role='checkbox']" in selectors
    assert "[role='searchbox']" in selectors
    assert "[contenteditable='true']" in selectors
    assert "export function activateElement" in event_driver
    assert "export function enterText" in event_driver
    assert "export function selectNativeOption" in event_driver
    assert "export function setControlChecked" in event_driver
    assert "PointerEvent" in event_driver
    assert "KeyboardEvent" in event_driver
    assert "requestSubmit" in event_driver
    assert "export function queryElementsDeep" in deep_dom
    assert "shadowRoot" in deep_dom
    assert "sameOriginFrameDocument" in deep_dom
    assert "export function findClickableTarget" in resolver
    assert "export function findFieldTarget" in resolver
    assert "export function findFormTarget" in resolver
    assert "from \"./controlSelectors\"" in resolver
    assert "from \"./submitResolver\"" in resolver
    assert "submitElementFor(form)" in resolver
    assert "export function submitElementFor" in submit_resolver
    assert "SUBMIT_INTENT_PATTERN" in submit_resolver
    assert "queryElementDeep" in resolver
    assert "queryElementsDeep(CLICKABLE_SELECTOR)" in resolver
    assert "bestTextMatch" in resolver
    assert "bestFieldMatch" in resolver
    assert "from \"./targetResolver\"" in actions
    assert "from \"./eventDriver\"" in actions
    assert "enterText(input" in actions
    assert "from \"./formFiller\"" in actions
    assert "fillFormFields(form, params" in actions
    assert "fieldSchema: actionConfig.field_schema" in actions
    assert "fallbackQuery" in actions
    assert "activateElement(element)" in actions
    assert "findClickableTarget" in actions
    assert "findFormTarget" in actions
    assert "export function fillFormFields" in form_filler
    assert "FIELD_ALIAS_GROUPS" in form_filler
    assert "label[for=" in form_filler
    assert "aria-labelledby" in form_filler
    assert "nearbyLabelText" in form_filler
    assert "autocomplete" in form_filler
    assert "selectNativeOption" in form_filler
    assert "setControlChecked" in form_filler
    assert "[role=\"radio\"][name=" in form_filler
    assert "schemaValueForItem" in form_filler
    assert "schemaParamKey" in form_filler
    assert "\"checkbox\"" in form_filler
    assert "\"radio\"" in form_filler
    assert "from \"./targetResolver\"" in sequence
    assert "from \"./eventDriver\"" in sequence
    assert "from \"./fieldSchema\"" in sequence
    assert "normalizeSchemaValue" in sequence
    assert "selectNativeOption" in sequence
    assert "setControlChecked" in sequence
    assert "submitFormElement" in sequence
    assert "findFieldTarget(step)" in sequence
    assert "findClickableTarget(step)" in sequence
    assert "matchingRadio" in sequence
    assert "checkboxState" in sequence
    assert "fieldType(input) === \"radio\"" in sequence
    assert "[role=\"radio\"][name=" in sequence
    assert "schemaItemForParam" in action_params
    assert "schemaParamKey" in action_params
    assert "hasRequiredParamValue" in action_params
    assert "export function schemaItems" in field_schema
    assert "export function schemaValueForItem" in field_schema
    assert "export function normalizeSchemaValue" in field_schema
    assert "textMatchesOption" in field_schema
    assert "queryElementsDeep(CLICKABLE_SELECTOR)" in discovery
    assert "queryElementsDeep(FORM_SELECTOR)" in discovery
    assert "FORM_INPUT_SELECTOR" in discovery
    assert "OPTION_SELECTOR" in discovery
    assert "aria-controls" in discovery
    assert "controlledFieldOptions" in discovery
    assert "nearbyFieldLabel" in discovery
    assert "from \"./submitResolver\"" in discovery
    assert "field.getAttribute(\"placeholder\")" not in discovery.split("name: clean", 1)[1].split("label: fieldLabel", 1)[0]
    assert "queryElementDeep" in validation
    assert "queryElementsDeep(CLICKABLE_SELECTOR)" in validation
    assert "from \"./submitResolver\"" in validation
    assert "waitForValidationTargets(actions)" in validation
    assert "VALIDATION_WAIT_MS" in validation
    assert "from \"./controlSelectors\"" in tracker
    assert "composedPath" in tracker


def test_adapter_collects_browser_barrier_hints() -> None:
    hints = Path("plugin/src/adapter/barrierHints.js").read_text(encoding="utf-8")
    discovery = Path("plugin/src/adapter/discovery.js").read_text(encoding="utf-8")
    signatures = Path("plugin/src/adapter/providerSignatures.js").read_text(encoding="utf-8")

    assert "export function collectBarrierHints" in hints
    assert "password_inputs" in hints
    assert "file_uploads" in hints
    assert "CAPTCHA_PROVIDER_SIGNATURES" in hints
    assert "captcha_providers" in hints
    assert "payment_providers" in hints
    assert "calendar_providers" in hints
    assert "map_providers" in hints
    assert "microsoft_bookings" in signatures
    assert "authorize.net" in signatures
    assert "external_action_hosts" in hints
    assert "queryElementsDeep" in hints
    assert "field.value" not in hints
    assert "barrier_hints: collectBarrierHints()" in discovery


def test_adapter_provider_actions_open_only_safe_provider_handoffs() -> None:
    source = Path("plugin/src/adapter/providerActions.js").read_text(encoding="utf-8")
    signatures = Path("plugin/src/adapter/providerSignatures.js").read_text(encoding="utf-8")

    assert "export async function executeProviderAction" in source
    assert "export function canExecuteProviderAction" in source
    assert "MAP_ACTIONS" in source
    assert "CALENDAR_ACTIONS" in source
    assert "CONTACT_ACTIONS" in source
    assert "ACTIONS.OPEN_MAP" in source
    assert "ACTIONS.OPEN_LOCATION" in source
    assert "ACTIONS.CHECK_APPOINTMENT_AVAILABILITY" in source
    assert "ACTIONS.REQUEST_APPOINTMENT" in source
    assert "ACTIONS.OPEN_CONTACT" in source
    assert "ACTIONS.CONTACT_AGENT" in source
    assert "HTTP_PROTOCOLS" in source
    assert "CONTACT_PROTOCOLS" in source
    assert "window.open(url.href" in source
    assert "PAYMENT_PROVIDER_SIGNATURES" not in source
    assert "CAPTCHA_PROVIDER_SIGNATURES" not in source
    assert "checkout.stripe.com" not in source
    assert "google_maps" in signatures
    assert "microsoft_bookings" in signatures
    assert "whatsapp" in signatures


def test_navigation_fallback_uses_runtime_routes_without_trailing_slash_guess() -> None:
    source = Path("plugin/src/actionExecutor/navigationActions.js").read_text(encoding="utf-8")

    assert "AIHubAdapterRuntime?.config?.adapter?.routes" in source
    assert "AIHubAdapter?.config?.adapter?.routes" in source
    assert "`/${path}`" in source
    assert "`/${path}/`" not in source


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
    source = Path("crm/src/views/client-workspace/AdapterTab.tsx").read_text(encoding="utf-8")

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
    source = Path("crm/src/views/client-workspace/PromptTab.tsx").read_text(encoding="utf-8")

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


def test_runtime_capabilities_refresh_and_are_whitelisted() -> None:
    existing = {
        "runtime_capabilities": {"script_loaded": True, "microphone_permission": "denied"},
    }
    fresh = {
        "runtime_capabilities": {
            "script_loaded": True,
            "microphone_permission": "prompt",
            "secure_context": True,
            "iframe_count": 99999,
            "field_value": "secret",
        },
    }

    cleaned = client_routes._validated_runtime_capabilities(fresh["runtime_capabilities"])
    merged = client_db._merge_discovery_vertical_config(existing, {"runtime_capabilities": cleaned}, vertical_changed=False)

    assert merged["runtime_capabilities"]["microphone_permission"] == "prompt"
    assert merged["runtime_capabilities"]["iframe_count"] == 10000
    assert "field_value" not in merged["runtime_capabilities"]


def test_registration_keeps_existing_vertical_on_weak_generic_rediscovery(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "generic"
        confidence = 0.45
        vertical_config = {
            "actions": {"CAPTURE_LEAD": {"type": "form", "selector": "form.contact"}},
            "prompt_suggestions": ["Help me send an enquiry."],
            "intake_questions": [{"key": "goal", "question": "What do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {}
        prompt = "generic prompt"
        developer_rules = "generic rules"

    captured: dict[str, object] = {}
    existing_client = {
        "site_id": "policy_site",
        "vertical_key": "insurance",
        "last_crawl_status": client_db.CRAWL_STATUS_RUNNING,
        "catalog": {"active_products": 5},
    }

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: existing_client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: captured.setdefault("update", kwargs) or {**existing_client, "vertical_key": kwargs["vertical_key"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)

    response = client_routes._process_widget_registration(
        client_routes.WidgetRegisterRequest(
            site_id="policy_site",
            origin="https://policy.example.com",
            url="https://policy.example.com/contact",
            title="Contact us",
        ),
        BackgroundTasks(),
    )

    update = captured["update"]
    vertical_config = update["vertical_config"]
    assert update["vertical_key"] == "insurance"
    assert "actions" not in vertical_config
    assert "prompt_suggestions" not in vertical_config
    assert "intake_questions" not in vertical_config
    assert vertical_config["discovery"]["detected_vertical_key"] == "generic"
    assert vertical_config["discovery"]["applied_vertical_key"] == "insurance"
    assert response["vertical_key"] == "insurance"
    assert response["detected_vertical_key"] == "generic"
    assert response["actions"] == []


def test_registration_upgrades_generic_client_on_confident_vertical() -> None:
    decision = client_routes._registration_vertical_decision(
        {"vertical_key": "generic"},
        "construction",
        0.72,
    )
    vertical_config = client_routes._registration_vertical_config(
        {
            "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
            "prompt_suggestions": ["Help me request an estimate."],
            "intake_questions": [{"key": "project", "question": "What project do you need?"}],
            "discovery": {"source": "widget_register"},
        },
        {"script_loaded": True},
        decision,
    )

    assert decision["applied_vertical_key"] == "construction"
    assert decision["apply_generated_actions"] is True
    assert "REQUEST_ESTIMATE" in vertical_config["actions"]
    assert vertical_config["intake_questions"][0]["key"] == "project"
    assert vertical_config["runtime_capabilities"]["script_loaded"] is True
    assert vertical_config["discovery"]["vertical_decision"] == "generic_upgraded_from_confident_discovery"


def test_widget_registration_creates_available_client_without_integration(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "insurance"
        confidence = 0.82
        vertical_config = {
            "actions": {"SHOW_ENTITIES": {"type": "navigate", "path": "/plans"}},
            "prompt_suggestions": ["Help me compare insurance plans."],
            "intake_questions": [{"key": "coverage", "question": "What coverage do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {"buttons": []}
        prompt = "insurance prompt"
        developer_rules = "insurance rules"

    scheduled: list[object] = []
    discovered: dict[str, object] = {}
    available_client = {
        "site_id": "policy_site",
        "name": "Policy Site",
        "store_url": "https://policy.example.com",
        "vertical_key": "insurance",
        "status": client_db.CLIENT_STATUS_AVAILABLE,
        "last_crawl_status": client_db.CRAWL_STATUS_NOT_STARTED,
        "catalog": {"active_products": 0},
        "vertical_config": {},
    }

    class FakeBackgroundTasks:
        def add_task(self, *args, **kwargs):
            scheduled.append((args, kwargs))

    def fake_discover_available_client(**kwargs):
        discovered.update(kwargs)
        return available_client

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: (_ for _ in ()).throw(LookupError()))
    monkeypatch.setattr(client_routes.admin_db, "discover_available_client", fake_discover_available_client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: {**available_client, "vertical_key": kwargs["vertical_key"], "vertical_config": kwargs["vertical_config"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)
    monkeypatch.setattr(client_routes, "_seed_generated_prompt_once", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available clients must not auto-crawl")),
    )

    response = client_routes._process_widget_registration(
        client_routes.WidgetRegisterRequest(
            site_id="policy_site",
            origin="https://policy.example.com",
            url="https://policy.example.com/plans",
            title="Policy Site",
        ),
        FakeBackgroundTasks(),
    )

    assert discovered["site_id"] == "policy_site"
    assert discovered["store_url"] == "https://policy.example.com"
    assert response["vertical_key"] == "insurance"
    assert response["crawl_scheduled"] is False
    assert response["flow_scheduled"] is False
    assert response["rehearsal_scheduled"] is False
    assert scheduled == []


def test_widget_registration_refreshes_existing_client_origin(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "insurance"
        confidence = 0.82
        vertical_config = {
            "actions": {"START_QUOTE": {"type": "navigate", "path": "/insurance/health"}},
            "prompt_suggestions": ["Help me compare insurance plans."],
            "intake_questions": [{"key": "coverage", "question": "What coverage do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {"buttons": []}
        prompt = "insurance prompt"
        developer_rules = "insurance rules"

    existing_client = {
        "site_id": "policy_website",
        "name": "Policy Website",
        "store_url": "http://127.0.0.1:5183",
        "allowed_origin": "http://127.0.0.1:5183",
        "deploy_mode": client_db.DEFAULT_DEPLOY_MODE,
        "plan": client_db.DEFAULT_PLAN,
        "vertical_key": "insurance",
        "status": client_db.CLIENT_STATUS_AVAILABLE,
        "last_crawl_status": client_db.CRAWL_STATUS_NOT_STARTED,
        "catalog": {"active_products": 0},
        "vertical_config": {},
    }
    refreshed: dict[str, object] = {}

    def fake_discover_available_client(**kwargs):
        refreshed.update(kwargs)
        return {**existing_client, "store_url": kwargs["store_url"], "allowed_origin": kwargs["store_url"]}

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: existing_client)
    monkeypatch.setattr(client_routes.admin_db, "discover_available_client", fake_discover_available_client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: {**existing_client, "vertical_key": kwargs["vertical_key"], "vertical_config": kwargs["vertical_config"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)
    monkeypatch.setattr(client_routes, "_seed_generated_prompt_once", lambda *args, **kwargs: None)

    client_routes._process_widget_registration(
        client_routes.WidgetRegisterRequest(
            site_id="policy_website",
            origin="http://localhost:5173",
            url="http://localhost:5173/insurance/health",
            title="Policy Website",
        ),
        BackgroundTasks(),
    )

    assert refreshed["site_id"] == "policy_website"
    assert refreshed["store_url"] == "http://localhost:5173"


def test_widget_registration_initialization_plan_is_manual() -> None:
    plan = client_routes._manual_registration_initialization_plan()

    assert plan == {"crawl": False, "flow": False, "rehearsal": False}


def test_current_clients_do_not_schedule_auto_initialization_from_widget_registration(monkeypatch) -> None:
    class FakeDiscovery:
        vertical_key = "construction"
        confidence = 0.88
        vertical_config = {
            "actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
            "prompt_suggestions": ["Help me request an estimate."],
            "intake_questions": [{"key": "project_type", "question": "What project do you need?"}],
            "discovery": {"source": "widget_register"},
        }
        selectors = {"buttons": ["button.estimate"]}
        prompt = "construction prompt"
        developer_rules = "construction rules"

    scheduled: list[object] = []
    client = {
        "site_id": "builder_demo",
        "vertical_key": "construction",
        "status": client_db.CLIENT_STATUS_LIVE,
        "last_crawl_status": client_db.CRAWL_STATUS_NOT_STARTED,
        "catalog": {"active_products": 0},
        "vertical_config": {},
    }

    class FakeBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            scheduled.append((func, args, kwargs))

    monkeypatch.setattr(client_routes, "build_discovery", lambda payload: FakeDiscovery())
    monkeypatch.setattr(client_routes.admin_db, "get_client_detail", lambda site_id: client)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_discovery_config",
        lambda site_id, **kwargs: {**client, "vertical_key": kwargs["vertical_key"], "vertical_config": kwargs["vertical_config"]},
    )
    monkeypatch.setattr(client_routes.admin_db, "save_site_selectors", lambda *args, **kwargs: None)
    monkeypatch.setattr(client_routes, "_seed_generated_prompt_once", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        client_routes.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("widget registration must not auto-crawl")),
    )

    response = client_routes._process_widget_registration(
        client_routes.WidgetRegisterRequest(
            site_id="builder_demo",
            origin="https://builder.example.com",
            url="https://builder.example.com/estimate",
            title="Builder Demo",
        ),
        FakeBackgroundTasks(),
    )

    assert response["vertical_key"] == "construction"
    assert response["crawl_scheduled"] is False
    assert response["flow_scheduled"] is False
    assert response["rehearsal_scheduled"] is False
    assert scheduled == []


def test_widget_initialization_job_persists_flow_rehearsal_and_report(monkeypatch) -> None:
    saved_reports: list[dict[str, object]] = []
    saved_flow: dict[str, object] = {}
    saved_rehearsal: dict[str, object] = {}
    saved_regression: dict[str, object] = {}

    class FakeFlow:
        def to_dict(self):
            return {
                "site_id": "builder_demo",
                "site_url": "https://builder.example.com",
                "vertical_key": "construction",
                "detected_vertical_key": "construction",
                "confidence": 0.9,
                "engine": "test",
                "summary": {"pages": 2, "actions": 1},
                "adapter_actions": {"REQUEST_ESTIMATE": {"type": "click", "selector": "button.estimate"}},
            }

    class FakeRehearsal:
        def to_dict(self):
            return {
                "site_id": "builder_demo",
                "site_url": "https://builder.example.com",
                "engine": "test",
                "summary": {"total": 1, "supported": 1, "blocked": 0},
                "steps": [],
            }

    async def fake_discover_site_flows(*args, **kwargs):
        return FakeFlow()

    async def fake_rehearse_site_flows(*args, **kwargs):
        return FakeRehearsal()

    monkeypatch.setattr(client_initialization.admin_db, "get_client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(client_initialization, "discover_site_flows", fake_discover_site_flows)
    monkeypatch.setattr(client_initialization, "rehearse_site_flows", fake_rehearse_site_flows)
    monkeypatch.setattr(client_initialization.admin_db, "save_client_flow_report", lambda site_id, report: saved_flow.update(report))
    monkeypatch.setattr(
        client_initialization.admin_db,
        "save_client_rehearsal_report",
        lambda site_id, report: saved_rehearsal.update(report),
    )
    monkeypatch.setattr(
        client_initialization.admin_db,
        "save_client_regression_report",
        lambda site_id, report: saved_regression.update(report),
    )
    monkeypatch.setattr(
        client_initialization.admin_db,
        "save_client_initialization_report",
        lambda site_id, report: saved_reports.append(report),
    )

    report = client_initialization.run_widget_initialization(
        "builder_demo",
        "https://builder.example.com",
        vertical_key="construction",
        run_crawl=False,
        run_flow=True,
        run_rehearsal=True,
        crawl_max_pages=1,
        crawl_max_depth=1,
    )

    assert report["status"] == "ok"
    assert saved_flow["vertical_key"] == "construction"
    assert saved_rehearsal["summary"]["supported"] == 1
    assert saved_regression["site_id"] == "builder_demo"
    assert saved_reports[0]["status"] == "running"
    assert saved_reports[-1]["status"] == "ok"


def test_widget_register_model_preserves_form_fields() -> None:
    req = client_routes.WidgetRegisterRequest(
        site_id="Policy Website",
        origin="https://policy.example.com",
        url="https://policy.example.com/",
        forms=[
            {
                "label": "Get insurance quote",
                "selector": "form.quote",
                "input_selector": "input[name='phone']",
                "submit_selector": "button.get-quote",
                "fields": [
                    {"selector": "input[name='name']", "name": "Full name", "type": "text"},
                    {
                        "selector": "input[name='phone']",
                        "name": "Phone",
                        "label": "Mobile number",
                        "type": "tel",
                        "autocomplete": "tel",
                        "required": True,
                        "options": [{"label": "Mobile", "value": "mobile"}],
                    },
                ],
            }
        ],
        runtime_capabilities={"script_loaded": True, "microphone_permission": "prompt"},
    )

    payload = req.model_dump()

    assert payload["forms"][0]["fields"][0]["name"] == "Full name"
    assert payload["forms"][0]["fields"][1]["label"] == "Mobile number"
    assert payload["forms"][0]["fields"][1]["required"] is True
    assert payload["forms"][0]["fields"][1]["options"][0]["label"] == "Mobile"
    assert payload["runtime_capabilities"]["microphone_permission"] == "prompt"


def test_widget_register_model_trims_verbose_discovery_element_text() -> None:
    verbose_label = "Who do you want to insure? " + " ".join(f"{age} years" for age in range(18, 81))

    req = client_routes.WidgetRegisterRequest(
        site_id="policy_website",
        origin="https://policy.example.com",
        url="https://policy.example.com/",
        forms=[
            {
                "label": verbose_label,
                "selector": "form.quote",
                "input_selector": "input[name='city']",
                "submit_selector": "button.get-quote",
            }
        ],
    )

    payload = req.model_dump()

    assert len(payload["forms"][0]["label"]) == client_routes.MAX_DISCOVERY_LABEL_LENGTH
    assert payload["forms"][0]["label"] == verbose_label[: client_routes.MAX_DISCOVERY_LABEL_LENGTH]


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
    source = Path("plugin/src/adapter/targetResolver.js").read_text(encoding="utf-8")

    assert "clickableChildren(configured)" in source
    assert "return childTarget || configured" in source


def test_runtime_tries_client_hooks_before_generated_dom_actions() -> None:
    source = Path("plugin/src/adapter/runtime.js").read_text(encoding="utf-8")

    client_hook_index = source.index('["client_hook", () => executeClientHookAction(normalizedAction)]')
    configured_index = source.index('["configured_action", () => executeConfiguredAction(normalizedAction, this.config)]')

    assert 'import { executeClientHookAction } from "./clientHooks"' in source
    assert client_hook_index < configured_index


def test_universal_adapter_supports_configured_handoff_actions() -> None:
    dom_actions = Path("plugin/src/adapter/domActions.js").read_text(encoding="utf-8")
    validation = Path("plugin/src/adapter/validation.js").read_text(encoding="utf-8")

    assert 'import { showHandoffOverlay } from "../handoffOverlay"' in dom_actions
    assert 'actionConfig.type === "handoff"' in dom_actions
    assert "showHandoffOverlay(normalizedAction.action" in dom_actions
    assert "function validateHandoff(actionConfig)" in validation
    assert 'if (type === "handoff") return validateHandoff(actionConfig)' in validation


def test_runtime_resumes_product_specific_actions_after_product_navigation() -> None:
    source = Path("plugin/src/adapter/runtime.js").read_text(encoding="utf-8")

    resume_index = source.index('["product_page_resume", () => this.prepareProductPageAction(normalizedAction)]')
    configured_index = source.index('["configured_action", () => executeConfiguredAction(normalizedAction, this.config)]')

    assert 'import { storePendingAction, takePendingAction } from "./pendingAction"' in source
    assert 'import { resolveProductActionPath } from "./productNavigation"' in source
    assert "this.executePendingAction()" in source
    assert "storePendingAction(this.siteId, action)" in source
    assert "PRODUCT_NAVIGATION_TELEMETRY_GRACE_MS = 300" in source
    assert resume_index < configured_index


def test_configured_dom_product_actions_do_not_ignore_product_id() -> None:
    source = Path("plugin/src/adapter/domActions.js").read_text(encoding="utf-8")

    assert "PRODUCT_SPECIFIC_DOM_ACTIONS" in source
    assert "isProductSpecificActionOnDifferentPage(normalizedAction)" in source
    assert "productIdFromPath()" in source
    assert 'import { resolveProductActionPath } from "./productNavigation"' in source
    assert "samePath(targetPath, currentPagePath())" in source


def test_configured_dom_product_actions_ignore_stale_listing_page_path_on_product_page() -> None:
    source = Path("plugin/src/adapter/domActions.js").read_text(encoding="utf-8")

    assert "shouldNavigateToActionPage(normalizedAction, actionConfig)" in source
    assert "if (await isCurrentProductSpecificAction(action)) return false" in source
    assert "async function isCurrentProductSpecificAction(action)" in source


def test_adapter_product_navigation_uses_adapter_config_not_widget_config() -> None:
    source = Path("plugin/src/adapter/productNavigation.js").read_text(encoding="utf-8")

    assert 'import { adapterConfig } from "./config"' in source
    assert 'import { detectPlatform } from "./platforms"' in source
    assert 'from "../config"' not in source
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
    source = Path("db/clients.py").read_text(encoding="utf-8")
    section = source[
        source.index("def update_client_discovery_config("):source.index("def update_client_adapter_actions(")
    ]

    assert "clean_limit" not in section
    assert 'event_type="discovery_config_updated"' in section
    assert 'event_scope="discovery"' in section


def test_widget_voice_runtime_uses_stable_http_path_by_default() -> None:
    config_source = Path("plugin/src/config.js").read_text(encoding="utf-8")
    api_source = Path("plugin/src/api.js").read_text(encoding="utf-8")
    recorder_source = Path("plugin/src/recorder.js").read_text(encoding="utf-8")

    assert 'data-use-websocket")).toLowerCase() === "true"' in config_source
    assert "audioFilenameForBlob(blob)" in api_source
    assert "supportedAudioMimeType()" in recorder_source
    assert "MIN_AUDIO_BYTES" in recorder_source
    assert "mediaRecorder.start(RECORDING_TIMESLICE_MS)" in recorder_source


def test_public_widget_cors_covers_overlay_data_endpoints() -> None:
    source = Path("api/main.py").read_text(encoding="utf-8")
    cors_block = source[source.index("PUBLIC_WIDGET_CORS_PATHS"):source.index("def _is_public_widget_cors_path")]

    assert '"/v1/products"' in cors_block
    assert '"/v1/products/by-ids"' in cors_block
    assert '"/v1/knowledge/by-ids"' in cors_block


def test_pending_action_store_is_short_lived_and_site_scoped() -> None:
    source = Path("plugin/src/adapter/pendingAction.js").read_text(encoding="utf-8")

    assert "MAX_PENDING_ACTION_AGE_MS = 15000" in source
    assert "aihub:pending-action:" in source
    assert "window.sessionStorage.setItem" in source
    assert "window.sessionStorage.removeItem" in source


def test_client_hook_executor_supports_product_specific_cart_actions() -> None:
    source = Path("plugin/src/adapter/clientHooks.js").read_text(encoding="utf-8")

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
    assert knowledge_entity_type_for("ecommerce") == "product"
