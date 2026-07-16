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


def test_widget_action_executor_is_modular_and_shared() -> None:
    assert not Path("plugin/src/actions.js").exists()

    api_facade = Path("plugin/src/api.js").read_text(encoding="utf-8")
    api_source = Path("plugin/src/runtime/api.js").read_text(encoding="utf-8")
    widget_entry_facade = Path("plugin/src/index.js").read_text(encoding="utf-8")
    widget_entry = Path("plugin/src/widget/bootstrap.js").read_text(encoding="utf-8")
    conversation_facade = Path("plugin/src/conversationMemory.js").read_text(encoding="utf-8")
    recorder_facade = Path("plugin/src/recorder.js").read_text(encoding="utf-8")
    styles_facade = Path("plugin/src/styles.js").read_text(encoding="utf-8")
    widget_facade = Path("plugin/src/widget.js").read_text(encoding="utf-8")
    speech_facade = Path("plugin/src/speech.js").read_text(encoding="utf-8")
    speech_source = Path("plugin/src/audio/speech.js").read_text(encoding="utf-8")
    styles_source = Path("plugin/src/widget/styles.js").read_text(encoding="utf-8")
    availability_facade = Path("plugin/src/widgetAvailability.js").read_text(encoding="utf-8")
    conversation_source = Path("plugin/src/session/conversationMemory.js").read_text(encoding="utf-8")
    recorder_source = Path("plugin/src/audio/recorder.js").read_text(encoding="utf-8")
    bridge_facade = Path("plugin/src/adapterBridge.js").read_text(encoding="utf-8")
    bridge_source = Path("plugin/src/core/adapterBridge.js").read_text(encoding="utf-8")
    constants_facade = Path("plugin/src/constants.js").read_text(encoding="utf-8")
    runtime_source = Path("plugin/src/adapter/runtime/runtime.js").read_text(encoding="utf-8")
    executor_source = Path("plugin/src/actionExecutor/index.js").read_text(encoding="utf-8")
    runtime_executor = Path("plugin/src/actionExecutor/runtimeAction.js").read_text(encoding="utf-8")
    product_executor = Path("plugin/src/actionExecutor/productActions.js").read_text(encoding="utf-8")
    entity_executor = Path("plugin/src/actionExecutor/entityActions.js").read_text(encoding="utf-8")
    handoff_executor = Path("plugin/src/actionExecutor/handoffActions.js").read_text(encoding="utf-8")
    handoff_overlay_facade = Path("plugin/src/handoffOverlay.js").read_text(encoding="utf-8")
    entity_overlay_facade = Path("plugin/src/entityOverlay.js").read_text(encoding="utf-8")
    entity_resolver_facade = Path("plugin/src/entityResolver.js").read_text(encoding="utf-8")
    product_overlay_facade = Path("plugin/src/productOverlay.js").read_text(encoding="utf-8")
    product_resolver_facade = Path("plugin/src/productResolver.js").read_text(encoding="utf-8")
    handoff_overlay = Path("plugin/src/overlays/handoffOverlay.js").read_text(encoding="utf-8")
    entity_overlay = Path("plugin/src/overlays/entityOverlay.js").read_text(encoding="utf-8")
    entity_resolver = Path("plugin/src/catalog/entityResolver.js").read_text(encoding="utf-8")
    product_overlay = Path("plugin/src/overlays/productOverlay.js").read_text(encoding="utf-8")
    product_resolver = Path("plugin/src/catalog/productResolver.js").read_text(encoding="utf-8")
    dom_actions = Path("plugin/src/adapter/actions/domActions.js").read_text(encoding="utf-8")

    assert "export * from \"./runtime/api\"" in api_facade
    assert "import \"./widget/bootstrap\"" in widget_entry_facade
    assert "export * from \"./core/adapterBridge\"" in bridge_facade
    assert "export * from \"./core/constants\"" in constants_facade
    assert "from \"../actionExecutor\"" in api_source
    assert "export * from \"./session/conversationMemory\"" in conversation_facade
    assert "export * from \"./audio/recorder\"" in recorder_facade
    assert "export * from \"./widget/styles\"" in styles_facade
    assert "export * from \"./widget/ui\"" in widget_facade
    assert "export * from \"./audio/speech\"" in speech_facade
    assert "export * from \"./session/widgetAvailability\"" in availability_facade
    assert "export * from \"./overlays/handoffOverlay\"" in handoff_overlay_facade
    assert "export * from \"./overlays/entityOverlay\"" in entity_overlay_facade
    assert "export * from \"./catalog/entityResolver\"" in entity_resolver_facade
    assert "export * from \"./overlays/productOverlay\"" in product_overlay_facade
    assert "export * from \"./catalog/productResolver\"" in product_resolver_facade
    assert "let processingTurn = false" in widget_entry
    assert "if (processingTurn) return" in widget_entry
    assert "elements.btn.disabled = true" in widget_entry
    assert "elements.btn.disabled = false" in widget_entry
    assert "BROWSER_ACTION_RESULTS" in conversation_source
    assert "onActionResults: conversationMemory.rememberActionResults" in widget_entry
    assert "rendered_products=" in conversation_source
    assert "rendered_records=" in conversation_source
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
    assert "from \"../audio/speech\"" in api_source
    assert "new SpeechSynthesisUtterance" not in api_source
    assert "FEMALE_VOICE_HINTS.some" in speech_source
    assert ")) || null;" in speech_source
    assert "contain: layout style;" in styles_source
    assert "transition: all" not in styles_source
    assert "mayabotPulseRecord" not in styles_source
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
    plugin_source = Path("plugin/src/core/constants.js").read_text(encoding="utf-8")
    plugin_facade = Path("plugin/src/constants.js").read_text(encoding="utf-8")
    contract_source = Path("packages/contracts/index.js").read_text(encoding="utf-8")

    assert "export * from \"./core/constants\"" in plugin_facade
    assert '@ai-hub/contracts' in plugin_source
    for action_name in sorted(list_action_names()):
        assert f'{action_name}: "{action_name}"' in contract_source


def test_adapter_observes_spa_navigation_and_async_dom_changes() -> None:
    source = Path("plugin/src/adapter/runtime/pageLifecycle.js").read_text(encoding="utf-8")

    assert "from \"../dom/controlSelectors\"" in source
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
    source = Path("plugin/src/adapter/runtime/interactionTracker.js").read_text(encoding="utf-8")

    assert "/v1/widget/interaction-event" in source
    assert "document.addEventListener(\"click\"" in source
    assert "document.addEventListener(\"submit\"" in source
    assert "field.value" not in source
    assert "value:" not in source


def test_adapter_uses_shared_target_resolver_for_stale_selectors() -> None:
    selectors = Path("plugin/src/adapter/dom/controlSelectors.js").read_text(encoding="utf-8")
    event_driver = Path("plugin/src/adapter/dom/eventDriver.js").read_text(encoding="utf-8")
    deep_dom = Path("plugin/src/adapter/dom/deepDom.js").read_text(encoding="utf-8")
    resolver = Path("plugin/src/adapter/dom/targetResolver.js").read_text(encoding="utf-8")
    actions = Path("plugin/src/adapter/actions/domActions.js").read_text(encoding="utf-8")
    sequence = Path("plugin/src/adapter/dom/domSequence.js").read_text(encoding="utf-8")
    form_filler = Path("plugin/src/adapter/dom/formFiller.js").read_text(encoding="utf-8")
    action_params = Path("plugin/src/adapter/actions/actionParams.js").read_text(encoding="utf-8")
    field_schema = Path("plugin/src/adapter/dom/fieldSchema.js").read_text(encoding="utf-8")
    discovery = Path("plugin/src/adapter/discovery/discovery.js").read_text(encoding="utf-8")
    validation = Path("plugin/src/adapter/dom/validation.js").read_text(encoding="utf-8")
    tracker = Path("plugin/src/adapter/runtime/interactionTracker.js").read_text(encoding="utf-8")
    submit_resolver = Path("plugin/src/adapter/dom/submitResolver.js").read_text(encoding="utf-8")

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
    assert "from \"../dom/targetResolver\"" in actions
    assert "from \"../dom/eventDriver\"" in actions
    assert "enterText(input" in actions
    assert "from \"../dom/formFiller\"" in actions
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
    assert "from \"../dom/submitResolver\"" in discovery
    assert "field.getAttribute(\"placeholder\")" not in discovery.split("name: clean", 1)[1].split("label: fieldLabel", 1)[0]
    assert "queryElementDeep" in validation
    assert "queryElementsDeep(CLICKABLE_SELECTOR)" in validation
    assert "from \"./submitResolver\"" in validation
    assert "waitForValidationTargets(actions)" in validation
    assert "VALIDATION_WAIT_MS" in validation
    assert "from \"../dom/controlSelectors\"" in tracker
    assert "composedPath" in tracker


def test_adapter_collects_browser_barrier_hints() -> None:
    hints = Path("plugin/src/adapter/discovery/barrierHints.js").read_text(encoding="utf-8")
    discovery = Path("plugin/src/adapter/discovery/discovery.js").read_text(encoding="utf-8")
    signatures = Path("plugin/src/adapter/discovery/providerSignatures.js").read_text(encoding="utf-8")

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
    source = Path("plugin/src/adapter/actions/providerActions.js").read_text(encoding="utf-8")
    signatures = Path("plugin/src/adapter/discovery/providerSignatures.js").read_text(encoding="utf-8")

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
