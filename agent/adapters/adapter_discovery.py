"""Generate client adapter configuration from one-line script observations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from agent.adapters import adapter_action_candidates, adapter_browser_barriers, adapter_form_compat, adapter_routes
from agent.adapters.adapter_prompt_generation import (
    adapter_action_summary as build_adapter_action_summary,
    generated_developer_rules as build_generated_developer_rules,
    generated_prompt_suggestions as build_generated_prompt_suggestions,
    generated_system_prompt as build_generated_system_prompt,
    prompt_for_action as build_prompt_for_action,
)
from agent.adapters.adapter_repair import repair_actions_from_html
from agent.adapters.adapter_observations import (
    ObservedElement,
    clean_html_sample,
    clean_selector,
    clean_text,
    first_matching_element,
    first_matching_form,
    first_search_form,
    form_fields_text,
    host_label,
    labels_text,
    matching_element_rank,
    parse_elements,
    parse_form_fields,
    path_from_href,
    safe_origin,
    same_origin_url,
)
from agent.action_helpers.sales_intake import intake_questions_for
from agent.verticals.discovery_profiles import (
    get_discovery_profile,
    list_discovery_profiles,
    merged_action_labels,
    merged_route_actions,
)

MAX_TEXT_SAMPLE_CHARS = 3000
MAX_HTML_SAMPLE_CHARS = 6000
MAX_ACTION_CANDIDATES = 80
MAX_FIELD_SCHEMA_OPTIONS = 20
DEFAULT_CONFIDENCE = 0.45
HIGH_CONFIDENCE = 0.82
MEDIUM_CONFIDENCE = 0.66
LOW_CONFIDENCE = 0.35

@dataclass(frozen=True)
class DiscoveryInput:
    site_id: str
    origin: str
    url: str
    title: str = ""
    text_sample: str = ""
    html_sample: str = ""
    buttons: tuple[ObservedElement, ...] = ()
    links: tuple[ObservedElement, ...] = ()
    forms: tuple[ObservedElement, ...] = ()
    platform_hints: dict[str, Any] = field(default_factory=dict)
    barrier_hints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveryResult:
    vertical_key: str
    confidence: float
    vertical_config: dict[str, Any]
    selectors: dict[str, Any]
    prompt: str
    developer_rules: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_discovery(raw: dict[str, Any]) -> DiscoveryResult:
    """Build generated adapter config from a browser registration payload."""
    data = parse_discovery_input(raw)
    vertical_key, confidence = classify_vertical(data)
    routes = discover_routes(data, vertical_key)
    actions = discover_actions(data, vertical_key, routes)
    actions = repair_actions_from_html(
        html_sample=data.html_sample,
        vertical_key=vertical_key,
        actions=actions,
        site_id=data.site_id,
    )
    selectors = discover_selectors(actions)
    vertical_config = {
        "platform": detect_platform(data),
        "routes": routes,
        "actions": actions,
        "action_candidates": discover_action_candidates(data, vertical_key, actions, routes),
        "prompt_suggestions": generated_prompt_suggestions(vertical_key, actions, routes),
        "intake_questions": intake_questions_for(vertical_key),
        "barriers": browser_barrier_report(data),
        "discovery": {
            "source": "widget_register",
            "confidence": confidence,
            "url": data.url,
            "title": data.title,
        },
    }
    return DiscoveryResult(
        vertical_key=vertical_key,
        confidence=confidence,
        vertical_config=vertical_config,
        selectors=selectors,
        prompt=generated_system_prompt(data, vertical_key),
        developer_rules=generated_developer_rules(vertical_key, actions),
    )


def parse_discovery_input(raw: dict[str, Any]) -> DiscoveryInput:
    """Validate and normalize public browser observations."""
    return DiscoveryInput(
        site_id=clean_text(raw.get("site_id"))[:80],
        origin=safe_origin(raw.get("origin")),
        url=same_origin_url(raw.get("url"), raw.get("origin")),
        title=clean_text(raw.get("title"))[:180],
        text_sample=clean_text(raw.get("text_sample"))[:MAX_TEXT_SAMPLE_CHARS],
        html_sample=clean_html_sample(raw.get("html_sample"))[:MAX_HTML_SAMPLE_CHARS],
        buttons=parse_elements(raw.get("buttons")),
        links=parse_elements(raw.get("links")),
        forms=parse_elements(raw.get("forms")),
        platform_hints=dict(raw.get("platform_hints") or {}),
        barrier_hints=safe_barrier_hints(raw.get("barrier_hints")),
    )


def classify_vertical(data: DiscoveryInput) -> tuple[str, float]:
    """Classify the website vertical using registry discovery profiles."""
    if data.platform_hints.get("shopify") or data.platform_hints.get("woocommerce"):
        return "ecommerce", 0.92

    text = " ".join([data.title, data.text_sample, labels_text(data.buttons), labels_text(data.links)]).lower()
    scores = {}
    for profile in list_discovery_profiles():
        if profile.key == "generic":
            continue
        keyword_hits = sum(1 for keyword in profile.classification_keywords if keyword in text)
        route_hits = sum(
            1
            for keywords in profile.route_keywords.values()
            for keyword in keywords
            if keyword in text
        )
        action_hits = sum(
            1
            for labels in profile.action_labels.values()
            for keyword in labels
            if keyword in text
        )
        profile_bonus = 1 if profile.key.replace("_", " ") in text or profile.key in text else 0
        scores[profile.key] = keyword_hits * 3 + route_hits + action_hits + profile_bonus

    best_key, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        return "generic", DEFAULT_CONFIDENCE
    second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
    confidence = min(0.95, 0.55 + (best_score * 0.025) + max(0, best_score - second_score) * 0.04)
    return best_key, round(confidence, 2)


def discover_routes(data: DiscoveryInput, vertical_key: str) -> dict[str, str]:
    return adapter_routes.discover_routes(data, vertical_key)


def discover_actions(data: DiscoveryInput, vertical_key: str, routes: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Build runtime action map from observed forms, buttons, and routes."""
    profile = get_discovery_profile(vertical_key)
    labels_by_action = merged_action_labels(profile)
    actions: dict[str, dict[str, Any]] = {}
    add_search_action(actions, data, profile.form_action)
    for action_name in profile.primary_actions:
        add_form_action(actions, data, action_name, labels_by_action)
        add_button_action(actions, data, action_name, labels_by_action)
    add_route_actions(actions, routes, merged_route_actions(profile))
    add_contact_route_fallback_actions(actions, routes, vertical_key)
    return actions


def discover_selectors(actions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Extract selector-focused view of action config for readiness display."""
    selectors: dict[str, Any] = {}
    for action_name, action in actions.items():
        if "selector" in action:
            selectors[action_name.lower()] = action["selector"]
        if "input" in action:
            selectors[f"{action_name.lower()}_input"] = action["input"]
    return selectors


def discover_action_candidates(
    data: DiscoveryInput,
    vertical_key: str,
    actions: dict[str, dict[str, Any]],
    routes: dict[str, str],
) -> list[dict[str, Any]]:
    """Return admin-visible controls and likely action mappings from one-page browser discovery."""
    profile = get_discovery_profile(vertical_key)
    labels_by_action = merged_action_labels(profile)
    route_actions = merged_route_actions(profile)
    candidates = [
        *generated_action_candidates(actions),
        *button_action_candidates(data, labels_by_action),
        *form_action_candidates(data, labels_by_action),
        *route_action_candidates(routes, route_actions),
    ]
    return dedupe_candidates(candidates)[:MAX_ACTION_CANDIDATES]


def generated_system_prompt(data: DiscoveryInput, vertical_key: str) -> str:
    return build_generated_system_prompt(
        data,
        vertical_key,
        discover_routes=discover_routes,
        discover_actions=discover_actions,
        detect_platform=detect_platform,
        browser_barrier_report=browser_barrier_report,
    )


def generated_developer_rules(vertical_key: str, actions: dict[str, dict[str, Any]]) -> str:
    return build_generated_developer_rules(vertical_key, actions)


def generated_prompt_suggestions(vertical_key: str, actions: dict[str, dict[str, Any]], routes: dict[str, str]) -> list[str]:
    return build_generated_prompt_suggestions(vertical_key, actions, routes)


def prompt_for_action(action_name: str, entity_plural: str) -> str:
    return build_prompt_for_action(action_name, entity_plural)


def adapter_action_summary(action_name: str, action_config: dict[str, Any]) -> str:
    return build_adapter_action_summary(action_name, action_config)


def generated_action_candidates(actions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return adapter_action_candidates.generated_action_candidates(actions, _candidate_dependencies())


def button_action_candidates(
    data: DiscoveryInput,
    labels_by_action: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    return adapter_action_candidates.button_action_candidates(data, labels_by_action, _candidate_dependencies())


def form_action_candidates(
    data: DiscoveryInput,
    labels_by_action: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    return adapter_action_candidates.form_action_candidates(data, labels_by_action, _candidate_dependencies())


def route_action_candidates(routes: dict[str, str], route_actions: dict[str, str]) -> list[dict[str, Any]]:
    return adapter_action_candidates.route_action_candidates(routes, route_actions)


def likely_action_for_label(
    label: str,
    labels_by_action: dict[str, tuple[str, ...]],
) -> tuple[str, float]:
    return adapter_action_candidates.likely_action_for_label(label, labels_by_action, clean_text)


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return adapter_action_candidates.dedupe_candidates(candidates, clean_text)


def unique_texts(values: list[str], limit: int) -> list[str]:
    return adapter_action_candidates.unique_texts(values, limit, clean_text)


def safe_field_list(value: Any) -> list[str]:
    return adapter_action_candidates.safe_field_list(value, clean_text)


def safe_field_schema(value: Any) -> list[dict[str, Any]]:
    return adapter_action_candidates.safe_field_schema(value, clean_text)


def safe_field_schema_item(item: dict[str, Any]) -> dict[str, Any]:
    return adapter_action_candidates.safe_field_schema_item(item, clean_text)


def safe_field_options(value: Any) -> list[dict[str, str]]:
    return adapter_action_candidates.safe_field_options(value, clean_text)


def safe_field_option(item: Any) -> dict[str, str]:
    return adapter_action_candidates.safe_field_option(item, clean_text)


def safe_confidence(value: Any, default: float) -> float:
    return adapter_action_candidates.safe_confidence(value, default)


def _candidate_dependencies() -> adapter_action_candidates.CandidateDependencies:
    return adapter_action_candidates.CandidateDependencies(
        clean_text=clean_text,
        path_from_href=path_from_href,
        form_fields_text=form_fields_text,
        form_is_rejected_for_action=form_is_rejected_for_action,
        field_param_names=field_param_names,
        action_required_field_params=action_required_field_params,
        form_field_schema=form_field_schema,
    )


def render_adapter_code(runtime_config: dict[str, Any]) -> str:
    """Render readable adapter code/config for CRM inspection."""
    site_id = str(runtime_config.get("site_id") or "")
    adapter = runtime_config.get("adapter") if isinstance(runtime_config.get("adapter"), dict) else {}
    vertical = runtime_config.get("vertical") if isinstance(runtime_config.get("vertical"), dict) else {}
    payload = {
        "site_id": site_id,
        "vertical": vertical.get("key"),
        "platform": adapter.get("platform", "auto"),
        "routes": adapter.get("routes", {}),
        "actions": adapter.get("actions", {}),
        "selectors": adapter.get("selectors", {}),
    }
    return (
        "// Generated by AI Hub. The client still pastes only /install.js.\n"
        "// This is the per-client adapter config that AIHubAdapterRuntime uses.\n"
        f"window.__AIHUB_GENERATED_ADAPTER__ = {json.dumps(payload, indent=2, ensure_ascii=False)};\n"
    )


def add_search_action(actions: dict[str, dict[str, Any]], data: DiscoveryInput, action_name: str) -> None:
    form = first_search_form(data.forms, action_name)
    if not form:
        return
    page_path = path_from_href(data.url, data.origin)
    sequence_steps = form_sequence_steps(form, action_name) if should_generate_sequence_action(action_name) else []
    if sequence_steps:
        field_config = form_action_field_config(form, action_name)
        actions[action_name] = {
            "type": "sequence",
            "steps": sequence_steps,
            "label": form.label,
            "page_path": page_path,
            "confidence": MEDIUM_CONFIDENCE,
            "submit_mode": form_submit_mode(action_name, form),
            **field_config,
        }
        return
    field_config = form_action_field_config(form, action_name)
    actions[action_name] = {
        "type": "form",
        "form": form.selector,
        "input": form.input_selector,
        "submit": form.submit_selector,
        "page_path": page_path,
        "submit_mode": form_submit_mode(action_name, form),
        "confidence": MEDIUM_CONFIDENCE,
        **field_config,
    }


def add_button_action(
    actions: dict[str, dict[str, Any]],
    data: DiscoveryInput,
    action_name: str,
    labels_by_action: dict[str, tuple[str, ...]],
) -> None:
    if action_name in actions:
        return
    labels = labels_by_action.get(action_name, ())
    button = first_matching_element(data.buttons, labels)
    if not button:
        return
    actions[action_name] = {
        "type": "click",
        "selector": button.selector,
        "label": button.label,
        "page_path": path_from_href(data.url, data.origin),
        "confidence": HIGH_CONFIDENCE,
    }


def add_form_action(
    actions: dict[str, dict[str, Any]],
    data: DiscoveryInput,
    action_name: str,
    labels_by_action: dict[str, tuple[str, ...]],
) -> None:
    if action_name in actions:
        return
    if not should_generate_sequence_action(action_name):
        return
    form = first_matching_form(data.forms, labels_by_action.get(action_name, ()), action_name)
    if not form:
        return
    steps = form_sequence_steps(form, action_name)
    if not steps:
        return
    field_config = form_action_field_config(form, action_name)
    actions[action_name] = {
        "type": "sequence",
        "steps": steps,
        "label": form.label,
        "page_path": path_from_href(data.url, data.origin),
        "confidence": MEDIUM_CONFIDENCE,
        "submit_mode": form_submit_mode(action_name, form),
        **field_config,
    }


def add_route_actions(
    actions: dict[str, dict[str, Any]],
    routes: dict[str, str],
    route_actions: dict[str, str],
) -> None:
    adapter_routes.add_route_actions(actions, routes, route_actions)


def add_contact_route_fallback_actions(
    actions: dict[str, dict[str, Any]],
    routes: dict[str, str],
    vertical_key: str,
) -> None:
    adapter_routes.add_contact_route_fallback_actions(actions, routes, vertical_key)


def contact_route_path(routes: dict[str, str]) -> str:
    return adapter_routes.contact_route_path(routes)


def is_handoff_action(action_name: str) -> bool:
    return adapter_routes.is_handoff_action(action_name)


def detect_platform(data: DiscoveryInput) -> str:
    return adapter_browser_barriers.detect_platform(data.platform_hints)


def browser_barrier_report(data: DiscoveryInput) -> dict[str, Any]:
    """Convert first-page browser barrier hints into the standard barrier report."""
    return adapter_browser_barriers.browser_barrier_report(data)


def safe_barrier_hints(value: Any) -> dict[str, Any]:
    """Validate public browser barrier hints before policy generation."""
    return adapter_browser_barriers.safe_barrier_hints(value, clean_text)


def safe_count(value: Any) -> int:
    return adapter_browser_barriers.safe_count(value)


def safe_text_list(value: Any, limit: int, length: int) -> list[str]:
    return adapter_browser_barriers.safe_text_list(value, limit, length, clean_text)


globals().update(adapter_form_compat.exports())
