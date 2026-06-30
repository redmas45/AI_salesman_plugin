"""Generate client adapter configuration from one-line script observations."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

from agent.actions.registry import get_action, normalize_action_name
from agent.adapter_repair import repair_actions_from_html
from agent.flow_barriers import build_flow_barrier_report
from agent.sales_intake import intake_questions_for
from agent.verticals.discovery_profiles import (
    get_discovery_profile,
    list_discovery_profiles,
    merged_action_labels,
    merged_route_actions,
    merged_route_keywords,
)
from agent.verticals.registry import get_vertical

MAX_TEXT_SAMPLE_CHARS = 3000
MAX_HTML_SAMPLE_CHARS = 6000
MAX_ITEMS_PER_KIND = 80
MAX_ACTION_CANDIDATES = 80
MAX_FIELD_SCHEMA_OPTIONS = 20
DEFAULT_CONFIDENCE = 0.45
HIGH_CONFIDENCE = 0.82
MEDIUM_CONFIDENCE = 0.66
LOW_CONFIDENCE = 0.35
RESULT_SUBMIT_ACTIONS: frozenset[str] = frozenset({
    "CHECK_AVAILABILITY",
    "CHECK_DELIVERY_AVAILABILITY",
    "FILTER_ENTITIES",
    "FILTER_PRODUCTS",
    "MATCH_JOBS",
    "RUN_AFFORDABILITY_CALCULATOR",
    "RUN_CALCULATOR",
    "SEARCH_AVAILABILITY",
    "SET_LOCATION",
    "START_QUOTE",
})
RESULT_SUBMIT_TERMS: tuple[str, ...] = (
    "availability",
    "available",
    "calculate",
    "calculator",
    "compare",
    "find",
    "get plans",
    "get quote",
    "get quotes",
    "plans",
    "quote",
    "quotes",
    "results",
    "search",
    "show",
)
FINAL_SUBMIT_TERMS: tuple[str, ...] = (
    "apply",
    "book now",
    "buy",
    "checkout",
    "confirm",
    "pay",
    "payment",
    "purchase",
    "reserve",
    "submit application",
)
SENSITIVE_FIELD_TERMS: tuple[str, ...] = (
    "aadhaar",
    "account",
    "address",
    "card",
    "condition",
    "diagnosis",
    "dob",
    "email",
    "file",
    "income",
    "medical",
    "mobile",
    "name",
    "otp",
    "pan",
    "passport",
    "password",
    "payment",
    "phone",
    "registration",
    "ssn",
    "telephone",
    "upload",
    "whatsapp",
)


@dataclass(frozen=True)
class ObservedElement:
    label: str = ""
    selector: str = ""
    href: str = ""
    input_selector: str = ""
    submit_selector: str = ""
    fields: tuple[dict[str, Any], ...] = ()


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
    """Map observed links to normalized route names."""
    profile = get_discovery_profile(vertical_key)
    route_keywords = merged_route_keywords(profile)
    routes = {"home": "/"}
    for link in data.links:
        label = link.label.lower()
        path = path_from_href(link.href, data.origin)
        if not path:
            continue
        for route_name, keywords in route_keywords.items():
            if route_name in routes:
                continue
            if any(keyword in label or keyword in path.lower() for keyword in keywords):
                routes[route_name] = path
                break
    return routes


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
    """Create a client-specific prompt draft for CRM review."""
    vertical = get_vertical(vertical_key)
    site_name = data.title or host_label(data.origin) or data.site_id
    routes = discover_routes(data, vertical_key)
    actions = discover_actions(data, vertical_key, routes)
    platform = detect_platform(data)
    barriers = browser_barrier_report(data)
    return "\n\n".join(
        section
        for section in (
            "## Role\n"
            f"You are Maya, the universal AI sales assistant embedded on {site_name}. "
            f"The website was automatically detected as {vertical.label} with primary records named "
            f"{vertical.entity_label_plural}. Your job is to act like a knowledgeable in-store sales "
            "consultant for this exact website: understand what the visitor wants, explain matching "
            "options from source data, compare tradeoffs, navigate the visitor to the right page, and "
            "start only the actions the site actually supports.",
            "## Client And Website Context\n"
            f"- Site ID: {data.site_id or 'unknown'}\n"
            f"- Origin: {data.origin or 'unknown'}\n"
            f"- Current discovery URL: {data.url or data.origin or 'unknown'}\n"
            f"- Detected platform: {platform}\n"
            f"- Detected vertical: {vertical.label} ({vertical.key})\n"
            f"- Primary entity wording: singular={vertical.entity_label_singular}; plural={vertical.entity_label_plural}\n"
            f"- Supported entity types: {', '.join(vertical.entity_types) or 'unknown'}",
            _site_evidence_prompt_block(data),
            _routes_prompt_block(routes),
            _actions_prompt_block(actions),
            _form_prompt_block(data.forms),
            _barrier_prompt_block(barriers),
            _vertical_sales_prompt_block(vertical.key),
            "## RAG Grounding Rules\n"
            "- Treat retrieved knowledge rows, catalog records, policy pages, source URLs, and live browser context as the only facts.\n"
            "- Never invent prices, premiums, inclusions, exclusions, dates, availability, eligibility, stock, coverage, financing, medical, legal, or compliance details.\n"
            "- If a record is missing a price or premium, say that the website did not expose that value and offer a safe next step such as opening the detail page, quote flow, contact flow, or callback form.\n"
            "- When comparing records, use exact retrieved IDs in UI actions and explain practical tradeoffs in plain language.\n"
            "- If the user asks to sort, filter, open, compare, navigate, start a quote/application/booking, or contact the team, return a UI action whenever that action is allowed.\n"
            "- Keep source uncertainty explicit: say what the website confirms, what is not shown, and what should be confirmed with the provider or licensed/human team.",
            "## Conversation Style\n"
            "- Speak as Maya in a calm professional female sales-assistant voice.\n"
            "- Ask short follow-up questions only when required information is missing for the next supported action.\n"
            "- Prefer useful guidance over generic disclaimers, but add a boundary when the vertical is regulated or the website does not confirm an outcome.\n"
            "- Be specific to this client and its detected pages, forms, labels, and records. Do not answer like a generic chatbot.",
        )
        if section
    )


def generated_developer_rules(vertical_key: str, actions: dict[str, dict[str, Any]]) -> str:
    """Create safety/action rules matching generated adapter actions."""
    vertical = get_vertical(vertical_key)
    allowed = "; ".join(adapter_action_summary(name, config) for name, config in sorted(actions.items()))
    allowed = allowed or "navigation and information actions"
    base = (
        "Generated adapter action contract:\n"
        f"- Detected actions: {allowed}.\n"
        "- Use only actions supported by the adapter config or runtime capability engine.\n"
        "- For page movement, prefer NAVIGATE_TO with a discovered route key.\n"
        f"- For record display, use SHOW_ENTITIES, COMPARE_ENTITIES, OPEN_ENTITY_DETAIL, FILTER_ENTITIES, or SORT_ENTITIES for {vertical.entity_label_plural}.\n"
        "- If confidence is low, explain the exact missing website data and offer handoff or a safe next click instead of pretending the action completed.\n"
    )
    if vertical.risk_level == "high":
        return (
            base
            + "- High-risk vertical: never make regulated decisions, diagnoses, underwriting decisions, eligibility approvals, legal conclusions, financial suitability recommendations, or claim guarantees.\n"
            + "- You may explain website-published information and start website-supported forms, but final outcomes require the website/provider/human confirmation."
        )
    return base


def _site_evidence_prompt_block(data: DiscoveryInput) -> str:
    labels = unique_texts(
        [
            *(element.label for element in data.buttons),
            *(element.label for element in data.links),
            *(element.label for element in data.forms),
        ],
        24,
    )
    sample = clean_text(data.text_sample)[:900]
    parts = ["## Website Evidence From Auto Discovery"]
    if labels:
        parts.append("- Visible labels/buttons/routes: " + "; ".join(labels))
    if sample:
        parts.append(f"- Text sample: {sample}")
    if len(parts) == 1:
        parts.append("- No visible browser evidence was captured yet; rely on retrieved source data and live page context.")
    return "\n".join(parts)


def _routes_prompt_block(routes: dict[str, str]) -> str:
    if not routes:
        return ""
    route_lines = [f"- {name}: {path}" for name, path in sorted(routes.items())]
    return "## Navigation Map\nUse these route keys when users ask to move around the site.\n" + "\n".join(route_lines)


def _actions_prompt_block(actions: dict[str, dict[str, Any]]) -> str:
    if not actions:
        return "## Detected Website Actions\nNo concrete actions were detected yet; answer from source data and offer contact/handoff when needed."
    rows = [f"- {adapter_action_summary(name, config)}" for name, config in sorted(actions.items())]
    return "## Detected Website Actions\nThese are the action handles Maya should prefer when the user asks the site to do something.\n" + "\n".join(rows)


def _form_prompt_block(forms: tuple[ObservedElement, ...]) -> str:
    rows: list[str] = []
    for form in forms[:8]:
        fields = [
            clean_text(field.get("label") or field.get("name") or field.get("placeholder") or field.get("type"))
            for field in form.fields[:10]
        ]
        field_text = ", ".join(field for field in fields if field) or "fields not captured"
        rows.append(f"- {form.label or form.selector or 'Form'}: {field_text}")
    if not rows:
        return ""
    return "## Form/Intake Clues\nUse these fields to ask for missing values before starting a form sequence.\n" + "\n".join(rows)


def _barrier_prompt_block(barriers: dict[str, Any]) -> str:
    if not isinstance(barriers, dict) or not barriers:
        return ""
    flags = [
        key.replace("_", " ")
        for key, value in barriers.items()
        if value not in (False, None, "", [], {})
    ]
    if not flags:
        return ""
    return (
        "## Runtime/Compliance Barriers\n"
        "- Detected barriers or sensitive steps: " + "; ".join(flags[:12]) + "\n"
        "- Do not claim completion across these barriers; guide the visitor to the website step or handoff."
    )


def _vertical_sales_prompt_block(vertical_key: str) -> str:
    blocks = {
        "insurance": (
            "## Insurance Sales Playbook\n"
            "- Help visitors compare plan type, premium visibility, sum insured/coverage amount, waiting periods, exclusions, deductibles/copay, riders/add-ons, cashless network clues, claim flow, renewal flow, and document requirements when those facts are present.\n"
            "- Ask for only the minimum next details needed for the website flow, such as coverage type, age band, family size, budget, city, existing condition disclosure, callback details, or claim/renewal intent.\n"
            "- Do not say a user is eligible, covered, approved, medically accepted, or guaranteed a claim unless the website itself confirms it after submission.\n"
            "- When premiums are not exposed, do not sort by fake zero values; explain that premiums require the website quote flow and offer to open/start that flow."
        ),
        "ecommerce": (
            "## E-commerce Sales Playbook\n"
            "- Compare products by price, specs, compatibility, variants, stock, delivery/return clues, ratings, and bundle fit when source data contains it.\n"
            "- Use product actions for showing, sorting, filtering, opening details, adding to cart, and checkout only when the runtime allows them.\n"
            "- Do not claim checkout, payment, discount, or delivery completion until the website confirms it."
        ),
        "travel": (
            "## Travel Sales Playbook\n"
            "- Help compare destinations, tickets, tours, dates, availability windows, inclusions, cancellation clues, pickup/location details, and itinerary fit.\n"
            "- Dates and availability can change; use website-supported availability/search/booking actions rather than promising a booking."
        ),
        "finance_broker": (
            "## Finance Broker Sales Playbook\n"
            "- Explain published rates, product types, fees, tenure, documents, calculators, and application steps from source data only.\n"
            "- Do not recommend financial suitability, approve loans, guarantee rates, or assess credit eligibility."
        ),
        "healthcare": (
            "## Healthcare Sales Playbook\n"
            "- Explain provider/service information, appointment routes, location, timings, documents, and published preparation notes.\n"
            "- Do not diagnose, triage emergencies, prescribe, or promise clinical outcomes."
        ),
        "construction": (
            "## Construction Sales Playbook\n"
            "- Help visitors understand services, project types, estimates, site visits, materials, timelines, warranty clues, and portfolio examples from source data.\n"
            "- Do not guarantee pricing, permits, safety approval, structural decisions, or completion dates without provider confirmation."
        ),
    }
    return blocks.get(
        vertical_key,
        "## Domain Sales Playbook\n"
        "- Identify the visitor's need, map it to retrieved records, explain tradeoffs, navigate to relevant pages, and start supported lead/contact/action flows.\n"
        "- Never overstate completion or certainty beyond what the website confirms.",
    )


def generated_prompt_suggestions(vertical_key: str, actions: dict[str, dict[str, Any]], routes: dict[str, str]) -> list[str]:
    """Create immediate prompt ideas from first-page discovery before deeper flow discovery."""
    vertical = get_vertical(vertical_key)
    suggestions: list[str] = []
    for action_name in sorted(actions):
        prompt = prompt_for_action(action_name, vertical.entity_label_plural)
        if prompt:
            suggestions.append(prompt)
    if "contact" in routes:
        suggestions.append("Help me contact the team.")
    if not suggestions:
        suggestions.append(f"Show me available {vertical.entity_label_plural}.")
    return unique_texts(suggestions, 10)


def prompt_for_action(action_name: str, entity_plural: str) -> str:
    prompts = {
        "ADD_TO_CART": f"Help me choose and add a {entity_plural.rstrip('s')} to cart.",
        "CHECKOUT": "Help me review checkout options.",
        "FILTER_PRODUCTS": "Find products that match what I need.",
        "SEARCH_AVAILABILITY": "Find available options for my dates or needs.",
        "START_BOOKING": "Help me start a booking.",
        "START_QUOTE": "Help me get a quote.",
        "START_APPLICATION": "Help me start an application.",
        "REQUEST_APPOINTMENT": "Help me request an appointment.",
        "REQUEST_CALLBACK": "Request a callback for me.",
        "REQUEST_CONSULTATION": "Help me request a consultation.",
        "REQUEST_ESTIMATE": "Help me request an estimate.",
        "REQUEST_SITE_VISIT": "Help me book a site visit.",
        "REQUEST_TEST_DRIVE": "Help me request a test drive.",
        "REQUEST_VIEWING": "Help me request a viewing.",
        "START_ENROLLMENT": "Help me start enrollment.",
        "START_TICKET_PURCHASE": "Help me buy tickets.",
        "CAPTURE_LEAD": "Help me send an enquiry.",
        "OPEN_CONTACT": "Take me to contact or support.",
        "OPEN_POLICY": "Show me policy or coverage details.",
        "OPEN_PROJECTS": "Show me completed projects.",
        "OPEN_SERVICES": "Show me available services.",
    }
    return prompts.get(action_name, "")


def adapter_action_summary(action_name: str, action_config: dict[str, Any]) -> str:
    action_type = clean_text(action_config.get("type") or "unknown")
    if action_type == "sequence":
        fields = action_config.get("fields") if isinstance(action_config.get("fields"), list) else []
        field_text = ", ".join(str(field) for field in fields[:8])
        return f"{action_name}(sequence fields: {field_text or 'none'})"
    if action_type == "handoff":
        return f"{action_name}(handoff)"
    return f"{action_name}({action_type})"


def generated_action_candidates(actions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action_name, config in sorted(actions.items()):
        rows.append(
            {
                "kind": "generated_action",
                "action": action_name,
                "type": clean_text(config.get("type") or ""),
                "label": clean_text(config.get("label") or action_name.replace("_", " ").title()),
                "selector": clean_text(config.get("selector") or config.get("input") or config.get("form")),
                "path": clean_text(config.get("path")),
                "confidence": safe_confidence(config.get("confidence"), MEDIUM_CONFIDENCE),
                "source": clean_text(config.get("source") or "adapter_discovery"),
                "fields": safe_field_list(config.get("fields")),
                "required_fields": safe_field_list(config.get("required_fields")),
                "required_fields_known": bool(config.get("required_fields_known") is True),
                "field_schema": safe_field_schema(config.get("field_schema")),
            }
        )
    return rows


def button_action_candidates(
    data: DiscoveryInput,
    labels_by_action: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for button in data.buttons:
        action_name, confidence = likely_action_for_label(button.label, labels_by_action)
        rows.append(
            {
                "kind": "button",
                "action": action_name,
                "type": "click",
                "label": button.label,
                "selector": button.selector,
                "path": path_from_href(button.href, data.origin),
                "confidence": confidence,
                "source": "browser_button",
            }
        )
    return rows


def form_action_candidates(
    data: DiscoveryInput,
    labels_by_action: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for form in data.forms:
        action_name, confidence = likely_action_for_label(" ".join([form.label, form_fields_text(form)]), labels_by_action)
        rows.append(
            {
                "kind": "form",
                "action": action_name,
                "type": "sequence" if form.fields else "form",
                "label": form.label,
                "selector": form.selector,
                "confidence": confidence,
                "source": "browser_form",
                "fields": field_param_names(form.fields),
                "required_fields": required_field_params(form.fields),
                "required_fields_known": bool(form.fields),
                "field_schema": form_field_schema(form.fields),
            }
        )
    return rows


def route_action_candidates(routes: dict[str, str], route_actions: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route_name, path in sorted(routes.items()):
        action_name = route_actions.get(route_name, "NAVIGATE_TO")
        rows.append(
            {
                "kind": "route",
                "action": action_name,
                "type": "navigate",
                "label": route_name.replace("_", " ").title(),
                "path": path,
                "confidence": MEDIUM_CONFIDENCE if action_name != "NAVIGATE_TO" else LOW_CONFIDENCE,
                "source": "browser_link",
            }
        )
    return rows


def likely_action_for_label(
    label: str,
    labels_by_action: dict[str, tuple[str, ...]],
) -> tuple[str, float]:
    text = clean_text(label).lower()
    if not text:
        return "", LOW_CONFIDENCE
    for action_name, labels in labels_by_action.items():
        if any(value in text for value in labels):
            return action_name, MEDIUM_CONFIDENCE
    return "", LOW_CONFIDENCE


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for candidate in candidates:
        key = (
            clean_text(candidate.get("kind")),
            clean_text(candidate.get("action")),
            clean_text(candidate.get("selector")),
            clean_text(candidate.get("path")),
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(candidate)
    return rows


def unique_texts(values: list[str], limit: int) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        rows.append(text)
        if len(rows) >= limit:
            break
    return rows


def safe_field_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_text(item)[:80] for item in value[:20] if clean_text(item)]


def safe_field_schema(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = [safe_field_schema_item(item) for item in value[:20] if isinstance(item, dict)]
    return [row for row in rows if row]


def safe_field_schema_item(item: dict[str, Any]) -> dict[str, Any]:
    param = clean_text(item.get("param"))[:80]
    if not param:
        return {}
    row: dict[str, Any] = {"param": param, "required": bool(item.get("required") is True)}
    for key in ("label", "type", "autocomplete"):
        value = clean_text(item.get(key))[:120]
        if value:
            row[key] = value
    options = safe_field_options(item.get("options"))
    if options:
        row["options"] = options
    return row


def safe_field_options(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows = [safe_field_option(item) for item in value[:MAX_FIELD_SCHEMA_OPTIONS]]
    return [row for row in rows if row]


def safe_field_option(item: Any) -> dict[str, str]:
    if isinstance(item, dict):
        label = clean_text(item.get("label"))[:120]
        value = clean_text(item.get("value"))[:120]
    else:
        label = clean_text(item)[:120]
        value = label
    if not label and not value:
        return {}
    return {"label": label or value, "value": value or label}


def safe_confidence(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(number, 1.0)), 2)


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
    form = first_search_form(data.forms)
    if not form:
        return
    page_path = path_from_href(data.url, data.origin)
    sequence_steps = form_sequence_steps(form, action_name) if should_generate_sequence_action(action_name) else []
    if sequence_steps:
        field_config = form_action_field_config(form)
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
    field_config = form_action_field_config(form)
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
    form = first_matching_form(data.forms, labels_by_action.get(action_name, ()))
    if not form:
        return
    steps = form_sequence_steps(form, action_name)
    if not steps:
        return
    field_config = form_action_field_config(form)
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
    for route_name, action_name in route_actions.items():
        if route_name not in routes or action_name in actions:
            continue
        actions[action_name] = {"type": "navigate", "path": routes[route_name], "confidence": MEDIUM_CONFIDENCE}


def add_contact_route_fallback_actions(
    actions: dict[str, dict[str, Any]],
    routes: dict[str, str],
    vertical_key: str,
) -> None:
    """Map expected lead/handoff actions to contact when no exact control was found."""
    contact_path = contact_route_path(routes)
    if not contact_path:
        return
    try:
        expected_actions = [normalize_action_name(action) for action in get_vertical(vertical_key).action_types]
    except ValueError:
        expected_actions = []

    if "CAPTURE_LEAD" in expected_actions and "CAPTURE_LEAD" not in actions:
        actions["CAPTURE_LEAD"] = {
            "type": "navigate",
            "path": contact_path,
            "label": "Open contact or enquiry page",
            "confidence": MEDIUM_CONFIDENCE,
            "source": "contact_route_fallback",
            "note": "No dedicated lead form was detected; route the visitor to the contact path for lead capture.",
        }

    for action_name in expected_actions:
        if action_name in actions or not is_handoff_action(action_name):
            continue
        action = get_action(action_name)
        actions[action_name] = {
            "type": "handoff",
            "path": contact_path,
            "label": action.label if action else action_name.replace("_", " ").title(),
            "confidence": MEDIUM_CONFIDENCE,
            "source": "contact_route_fallback",
            "message": "This step needs a human follow-up. I can open the contact path so the site team can continue.",
            "reason": "Human confirmation required for this website flow.",
        }


def contact_route_path(routes: dict[str, str]) -> str:
    for key in ("contact", "support", "help", "callback"):
        path = clean_text(routes.get(key))
        if path:
            return path
    return ""


def is_handoff_action(action_name: str) -> bool:
    action = get_action(action_name)
    return bool(action and action.family == "lead" and normalize_action_name(action_name).startswith("HANDOFF_TO_"))


def form_sequence_steps(form: ObservedElement, action_name: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    seen_checkable_params: set[str] = set()
    for field in form.fields:
        if should_skip_duplicate_checkable_step(field, seen_checkable_params):
            continue
        step = form_field_step(field)
        if step:
            steps.append(step)
    if form_submit_mode(action_name, form) == "submit" and form.submit_selector:
        steps.append({"op": "submit", "selector": form.submit_selector})
    return steps


def should_skip_duplicate_checkable_step(field: dict[str, Any], seen_params: set[str]) -> bool:
    field_type = clean_text(field.get("type")).lower()
    if field_type not in {"checkbox", "radio"}:
        return False
    param = field_param_name(field)
    if param in seen_params:
        return True
    seen_params.add(param)
    return False


def should_generate_sequence_action(action_name: str) -> bool:
    action = get_action(normalize_action_name(action_name))
    return bool(action and action.family == "lead")


def form_field_step(field: dict[str, Any]) -> dict[str, Any]:
    selector = clean_selector(field.get("selector"))
    if not selector:
        return {}
    field_type = clean_text(field.get("type")).lower()
    param = field_param_name(field)
    if field_type in {"file", "submit", "button"}:
        return {}
    if field_type in {"checkbox", "radio"}:
        return {"op": "check", "selector": selector, "param": param, "optional": not field_required(field)}
    if field_type == "select":
        return {"op": "select", "selector": selector, "param": param, "optional": not field_required(field)}
    return {"op": "fill", "selector": selector, "param": param, "optional": not field_required(field)}


def field_param_name(field: dict[str, Any]) -> str:
    source = field_param_source(field).lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", source).strip("_")
    return normalized[:60] or "value"


def field_param_source(field: dict[str, Any]) -> str:
    """Choose a stable semantic parameter source for anonymous website fields."""
    name = clean_text(field.get("name"))
    if field_is_checkable(field) and name:
        return name

    label = clean_text(field.get("label"))
    if label:
        return label

    if name and not looks_like_example_placeholder(name):
        return name

    placeholder = clean_text(field.get("placeholder"))
    if placeholder and not looks_like_example_placeholder(placeholder):
        return placeholder

    autocomplete = clean_text(field.get("autocomplete"))
    if autocomplete:
        return autocomplete

    return "value"


def field_is_checkable(field: dict[str, Any]) -> bool:
    return clean_text(field.get("type")).lower() in {"checkbox", "radio"}


def looks_like_example_placeholder(value: str) -> bool:
    text = clean_text(value).lower()
    return bool(
        text.startswith(("e.g.", "eg ", "example", "for example"))
        or text in {"search", "select", "choose", "enter"}
    )


def form_action_field_config(form: ObservedElement) -> dict[str, Any]:
    fields = field_param_names(form.fields)
    required_fields = required_field_params(form.fields)
    field_schema = form_field_schema(form.fields)
    config: dict[str, Any] = {}
    if fields:
        config["fields"] = fields
    if form.fields:
        config["required_fields"] = required_fields
        config["required_fields_known"] = True
    if field_schema:
        config["field_schema"] = field_schema
    return config


def field_param_names(fields: tuple[dict[str, Any], ...]) -> list[str]:
    names = [field_param_name(field) for field in fields]
    return sorted({name for name in names if name})


def required_field_params(fields: tuple[dict[str, Any], ...]) -> list[str]:
    return sorted({field_param_name(field) for field in fields if field_required(field)})


def form_field_schema(fields: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    rows = [form_field_schema_item(field) for field in fields]
    return merged_field_schema([row for row in rows if row])


def merged_field_schema(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        param = clean_text(row.get("param"))
        if not param:
            continue
        if param not in merged:
            merged[param] = row
            continue
        merged[param] = merge_field_schema_item(merged[param], row)
    return list(merged.values())


def merge_field_schema_item(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    row = dict(existing)
    row["required"] = bool(existing.get("required") or incoming.get("required"))
    for key in ("label", "type", "autocomplete"):
        if not row.get(key) and incoming.get(key):
            row[key] = incoming[key]
    row["options"] = merged_field_options(existing.get("options"), incoming.get("options"))
    if not row["options"]:
        row.pop("options", None)
    return row


def merged_field_options(*groups: Any) -> list[dict[str, str]]:
    merged: dict[tuple[str, str], dict[str, str]] = {}
    for group in groups:
        for option in safe_field_options(group):
            key = (option["label"].lower(), option["value"].lower())
            merged[key] = option
    return list(merged.values())


def form_field_schema_item(field: dict[str, Any]) -> dict[str, Any]:
    param = field_param_name(field)
    if not param:
        return {}
    row: dict[str, Any] = {"param": param, "required": field_required(field)}
    for key in ("label", "name", "placeholder", "type", "autocomplete"):
        value = clean_text(field.get(key))[:120]
        if value and key != "name":
            row[key] = value
        if value and key == "name" and "label" not in row:
            row["label"] = value
    options = safe_field_options(field.get("options"))
    if options:
        row["options"] = options
    return row


def field_required(field: dict[str, Any]) -> bool:
    return bool(field.get("required") is True)


def form_submit_mode(action_name: str, form: ObservedElement | None = None) -> str:
    """Return whether a generated form may submit or should only be prepared."""
    normalized = normalize_action_name(action_name)
    if form and safe_result_form_submit(normalized, form):
        return "submit"
    if form and form_requires_prepare_only(form):
        return "fill_only"
    action = get_action(normalized)
    if action and action.family in {"lead", "commerce"}:
        return "fill_only"
    if normalized.startswith(("START_", "REQUEST_", "CAPTURE_", "BOOK_", "JOIN_")):
        return "fill_only"
    return "submit"


def safe_result_form_submit(action_name: str, form: ObservedElement) -> bool:
    """Allow submit only for low-sensitivity forms that display/search options."""
    if action_name not in RESULT_SUBMIT_ACTIONS:
        return False
    if not form.submit_selector:
        return False
    form_text = normalized_form_text(form)
    if form_requires_prepare_only(form, form_text):
        return False
    return contains_any_term(form_text, RESULT_SUBMIT_TERMS)


def form_requires_prepare_only(form: ObservedElement, form_text: str | None = None) -> bool:
    text = form_text if form_text is not None else normalized_form_text(form)
    return form_has_sensitive_fields(form) or contains_any_term(text, FINAL_SUBMIT_TERMS)


def form_has_sensitive_fields(form: ObservedElement) -> bool:
    if not form.fields:
        selector_text = normalized_text(" ".join([form.selector, form.input_selector]))
        return contains_any_term(selector_text, SENSITIVE_FIELD_TERMS)
    return any(field_has_sensitive_term(field) for field in form.fields)


def field_has_sensitive_term(field: dict[str, Any]) -> bool:
    field_text = normalized_text(
        " ".join(
            str(field.get(key) or "")
            for key in ("label", "name", "placeholder", "type", "autocomplete")
        )
    )
    tokens = set(field_text.split())
    return any(term in tokens or term in field_text for term in SENSITIVE_FIELD_TERMS)


def normalized_form_text(form: ObservedElement) -> str:
    field_text = " ".join(
        " ".join(str(field.get(key) or "") for key in ("label", "name", "placeholder", "type"))
        for field in form.fields
    )
    return normalized_text(" ".join([form.label, form.selector, form.input_selector, form.submit_selector, field_text]))


def contains_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def normalized_text(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def detect_platform(data: DiscoveryInput) -> str:
    hints = data.platform_hints
    if hints.get("shopify"):
        return "shopify"
    if hints.get("woocommerce"):
        return "woocommerce"
    return "auto"


def browser_barrier_report(data: DiscoveryInput) -> dict[str, Any]:
    """Convert first-page browser barrier hints into the standard barrier report."""
    report = build_flow_barrier_report(
        [
            {
                "url": data.url,
                "title": data.title,
                "text_sample": data.text_sample,
                "platform_hints": data.platform_hints,
                "barrier_hints": data.barrier_hints,
            }
        ],
        site_id=data.site_id,
        site_url=data.origin,
    )
    return report.to_dict()


def safe_barrier_hints(value: Any) -> dict[str, Any]:
    """Validate public browser barrier hints before policy generation."""
    if not isinstance(value, dict):
        return {}
    hints: dict[str, Any] = {}
    for key in ("iframe_count", "password_inputs", "file_uploads", "date_inputs"):
        hints[key] = safe_count(value.get(key))
    hints["captcha"] = bool(value.get("captcha"))
    for key in ("iframe_sources", "captcha_providers", "payment_providers", "calendar_providers", "map_providers", "external_action_hosts"):
        hints[key] = safe_text_list(value.get(key), 20, 240)
    return hints


def safe_count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def safe_text_list(value: Any, limit: int, length: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_text(item)[:length] for item in value[:limit] if clean_text(item)]


def parse_elements(value: Any) -> tuple[ObservedElement, ...]:
    if not isinstance(value, list):
        return ()
    elements: list[ObservedElement] = []
    for item in value[:MAX_ITEMS_PER_KIND]:
        if not isinstance(item, dict):
            continue
        elements.append(
            ObservedElement(
                label=clean_text(item.get("label"))[:120],
                selector=clean_selector(item.get("selector")),
                href=clean_text(item.get("href"))[:500],
                input_selector=clean_selector(item.get("input_selector")),
                submit_selector=clean_selector(item.get("submit_selector")),
                fields=parse_form_fields(item.get("fields")),
            )
        )
    return tuple(elements)


def first_search_form(forms: tuple[ObservedElement, ...]) -> ObservedElement | None:
    for form in forms:
        label = form.label.lower()
        if form.input_selector and ("search" in label or "where" in label or "destination" in label):
            return form
    return next((form for form in forms if form.input_selector), None)


def first_matching_element(elements: tuple[ObservedElement, ...], labels: tuple[str, ...]) -> ObservedElement | None:
    matches: list[ObservedElement] = []
    for element in elements:
        text = element.label.lower()
        if element.selector and any(label in text for label in labels):
            matches.append(element)
    if not matches:
        return None
    return sorted(matches, key=lambda element: matching_element_rank(element, labels))[0]


def matching_element_rank(element: ObservedElement, labels: tuple[str, ...]) -> tuple[int, int, int]:
    text = element.label.lower()
    selector = element.selector.lower()
    if any(text == label for label in labels):
        label_rank = 0
    elif any(text.startswith(label) for label in labels):
        label_rank = 1
    else:
        label_rank = 2

    if selector.startswith(("button", "input")) or "[role=\"button\"]" in selector or "[role='button']" in selector:
        selector_rank = 0
    elif selector.startswith("a"):
        selector_rank = 2
    else:
        selector_rank = 1

    return label_rank, selector_rank, len(text)


def first_matching_form(forms: tuple[ObservedElement, ...], labels: tuple[str, ...]) -> ObservedElement | None:
    if not labels:
        return None
    for form in forms:
        text = " ".join([form.label, form_fields_text(form)]).lower()
        if form.fields and any(label in text for label in labels):
            return form
    return None


def form_fields_text(form: ObservedElement) -> str:
    return " ".join(
        clean_text(field.get("label") or field.get("name") or field.get("placeholder") or field.get("type"))
        for field in form.fields
    )


def parse_form_fields(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    fields: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        selector = clean_selector(item.get("selector"))
        if not selector:
            continue
        fields.append(
            {
                "selector": selector,
                "name": clean_text(item.get("name"))[:120],
                "label": clean_text(item.get("label"))[:120],
                "type": clean_text(item.get("type"))[:40],
                "placeholder": clean_text(item.get("placeholder"))[:120],
                "autocomplete": clean_text(item.get("autocomplete"))[:80],
                "required": bool(item.get("required") is True),
                "options": safe_field_options(item.get("options")),
            }
        )
    return tuple(fields)


def path_from_href(href: str, origin: str) -> str:
    if not href:
        return ""
    try:
        parsed = urlparse(href)
        if parsed.scheme and f"{parsed.scheme}://{parsed.netloc}" != origin:
            return ""
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{path}{query}"[:240]
    except ValueError:
        return ""


def same_origin_url(url: Any, origin: Any) -> str:
    clean_url = clean_text(url)[:500]
    clean_origin = safe_origin(origin)
    if not clean_url:
        return clean_origin
    try:
        parsed = urlparse(clean_url)
    except ValueError:
        return clean_origin
    if not parsed.scheme or not parsed.netloc:
        return clean_origin
    if f"{parsed.scheme}://{parsed.netloc}" != clean_origin:
        return clean_origin
    return clean_url


def safe_origin(value: Any) -> str:
    text = clean_text(value)[:240]
    try:
        parsed = urlparse(text)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def clean_selector(value: Any) -> str:
    selector = clean_text(value)[:240]
    if not selector or any(token in selector.lower() for token in ("<script", "javascript:")):
        return ""
    return selector


def labels_text(elements: tuple[ObservedElement, ...]) -> str:
    return " ".join(element.label for element in elements if element.label)


def host_label(origin: str) -> str:
    parsed = urlparse(origin)
    return parsed.netloc.replace("www.", "") if parsed.netloc else ""


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_html_sample(value: Any) -> str:
    html = str(value or "").replace("\x00", "").strip()
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
