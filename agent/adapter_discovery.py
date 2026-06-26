"""Generate client adapter configuration from one-line script observations."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

from agent.verticals.registry import get_vertical

MAX_TEXT_SAMPLE_CHARS = 3000
MAX_ITEMS_PER_KIND = 80
DEFAULT_CONFIDENCE = 0.45
HIGH_CONFIDENCE = 0.82
MEDIUM_CONFIDENCE = 0.66

VERTICAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ecommerce": ("shop", "store", "cart", "checkout", "product", "sale", "wishlist", "brand"),
    "travel": ("travel", "tour", "ticket", "activity", "destination", "hotel", "flight", "booking", "attraction"),
    "insurance": ("insurance", "policy", "premium", "claim", "coverage", "quote", "renewal"),
    "finance_broker": ("loan", "mortgage", "broker", "investment", "finance", "rate", "eligibility"),
    "healthcare": ("doctor", "clinic", "appointment", "patient", "treatment", "hospital"),
    "food": ("menu", "restaurant", "delivery", "order food", "reservation", "dish"),
    "real_estate": ("property", "real estate", "apartment", "listing", "rent", "buy home", "viewing"),
    "education": ("course", "class", "learning", "enroll", "syllabus", "program"),
    "automotive": ("car", "vehicle", "test drive", "dealer", "auto", "service"),
    "legal_services": ("lawyer", "legal", "attorney", "case", "consultation"),
    "jobs_recruiting": ("job", "career", "recruit", "resume", "apply now", "vacancy"),
    "events_ticketing": ("event", "ticket", "concert", "show", "venue", "seat"),
}

ROUTE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "home": ("home",),
    "shop": ("shop", "store", "products", "catalog", "inventory", "things to do", "activities"),
    "cart": ("cart", "basket", "bag"),
    "checkout": ("checkout", "payment"),
    "contact": ("contact", "support", "help"),
    "login": ("login", "sign in", "account"),
    "booking": ("book", "booking", "reserve", "availability"),
    "quote": ("quote", "estimate", "premium"),
}

ACTION_LABELS: dict[str, tuple[str, ...]] = {
    "ADD_TO_CART": ("add to cart", "add cart", "add to bag", "buy now"),
    "CHECKOUT": ("checkout", "continue to payment", "place order"),
    "START_BOOKING": ("book now", "reserve", "select tickets", "check availability"),
    "SEARCH_AVAILABILITY": ("search", "find", "check availability"),
    "START_QUOTE": ("get quote", "request quote", "start quote"),
    "REQUEST_APPOINTMENT": ("book appointment", "schedule appointment"),
    "CAPTURE_LEAD": ("contact", "submit", "send message"),
    "REQUEST_CALLBACK": ("request callback", "call me"),
    "OPEN_CONTACT": ("contact", "support", "help"),
}

VERTICAL_PRIMARY_ACTIONS: dict[str, tuple[str, ...]] = {
    "ecommerce": ("FILTER_PRODUCTS", "ADD_TO_CART", "CHECKOUT"),
    "travel": ("SEARCH_AVAILABILITY", "START_BOOKING", "OPEN_CONTACT"),
    "events_ticketing": ("SEARCH_AVAILABILITY", "START_TICKET_PURCHASE", "START_BOOKING"),
    "insurance": ("START_QUOTE", "OPEN_CLAIM_FLOW", "REQUEST_CALLBACK"),
    "finance_broker": ("RUN_CALCULATOR", "START_APPLICATION", "HANDOFF_TO_ADVISOR"),
    "healthcare": ("REQUEST_APPOINTMENT", "CHECK_APPOINTMENT_AVAILABILITY", "HANDOFF_TO_CLINIC"),
    "food": ("FILTER_ENTITIES", "SCHEDULE_ORDER", "CHECKOUT_HANDOFF"),
    "real_estate": ("REQUEST_VIEWING", "CONTACT_AGENT", "RUN_AFFORDABILITY_CALCULATOR"),
    "education": ("START_ENROLLMENT", "OPEN_SYLLABUS", "REQUEST_COUNSELOR_CALLBACK"),
    "automotive": ("REQUEST_TEST_DRIVE", "CONTACT_AGENT"),
    "legal_services": ("REQUEST_CONSULTATION", "HANDOFF_TO_LAWYER"),
    "jobs_recruiting": ("MATCH_JOBS", "START_APPLICATION", "HANDOFF_TO_RECRUITER"),
}


@dataclass(frozen=True)
class ObservedElement:
    label: str = ""
    selector: str = ""
    href: str = ""
    input_selector: str = ""
    submit_selector: str = ""


@dataclass(frozen=True)
class DiscoveryInput:
    site_id: str
    origin: str
    url: str
    title: str = ""
    text_sample: str = ""
    buttons: tuple[ObservedElement, ...] = ()
    links: tuple[ObservedElement, ...] = ()
    forms: tuple[ObservedElement, ...] = ()
    platform_hints: dict[str, Any] = field(default_factory=dict)


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
    routes = discover_routes(data)
    actions = discover_actions(data, vertical_key, routes)
    selectors = discover_selectors(actions)
    vertical_config = {
        "platform": detect_platform(data),
        "routes": routes,
        "actions": actions,
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
        buttons=parse_elements(raw.get("buttons")),
        links=parse_elements(raw.get("links")),
        forms=parse_elements(raw.get("forms")),
        platform_hints=dict(raw.get("platform_hints") or {}),
    )


def classify_vertical(data: DiscoveryInput) -> tuple[str, float]:
    """Classify the website vertical using deterministic keyword scoring."""
    text = " ".join([data.title, data.text_sample, labels_text(data.buttons), labels_text(data.links)]).lower()
    scores = {
        vertical: sum(1 for keyword in keywords if keyword in text)
        for vertical, keywords in VERTICAL_KEYWORDS.items()
    }
    best_key, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        return "generic", DEFAULT_CONFIDENCE
    second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
    confidence = min(0.95, 0.55 + (best_score * 0.06) + max(0, best_score - second_score) * 0.04)
    return best_key, round(confidence, 2)


def discover_routes(data: DiscoveryInput) -> dict[str, str]:
    """Map observed links to normalized route names."""
    routes = {"home": "/"}
    for link in data.links:
        label = link.label.lower()
        path = path_from_href(link.href, data.origin)
        if not path:
            continue
        for route_name, keywords in ROUTE_KEYWORDS.items():
            if route_name in routes:
                continue
            if any(keyword in label or keyword in path.lower() for keyword in keywords):
                routes[route_name] = path
    return routes


def discover_actions(data: DiscoveryInput, vertical_key: str, routes: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Build runtime action map from observed forms, buttons, and routes."""
    actions: dict[str, dict[str, Any]] = {}
    add_search_action(actions, data, vertical_key)
    for action_name in VERTICAL_PRIMARY_ACTIONS.get(vertical_key, ()):
        add_button_action(actions, data, action_name)
    add_route_actions(actions, routes)
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


def generated_system_prompt(data: DiscoveryInput, vertical_key: str) -> str:
    """Create a client-specific prompt draft for CRM review."""
    vertical = get_vertical(vertical_key)
    site_name = data.title or host_label(data.origin) or data.site_id
    return (
        f"You are the AI assistant for {site_name}. The detected website vertical is {vertical.label}. "
        f"Answer from retrieved {vertical.entity_label_plural} and website source data only. "
        "Help users navigate the site and start supported actions, but do not claim that payment, booking, "
        "eligibility, medical, legal, or financial outcomes are complete unless the website confirms them."
    )


def generated_developer_rules(vertical_key: str, actions: dict[str, dict[str, Any]]) -> str:
    """Create safety/action rules matching generated adapter actions."""
    vertical = get_vertical(vertical_key)
    allowed = ", ".join(sorted(actions)) or "navigation and information actions"
    base = (
        f"Generated adapter actions currently detected: {allowed}. "
        "Use only actions supported by the adapter config. If confidence is low, explain the next step and hand off."
    )
    if vertical.risk_level == "high":
        return base + " High-risk vertical: never make regulated decisions or promises; use human handoff."
    return base


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


def add_search_action(actions: dict[str, dict[str, Any]], data: DiscoveryInput, vertical_key: str) -> None:
    form = first_search_form(data.forms)
    if not form:
        return
    action_name = "FILTER_PRODUCTS" if vertical_key == "ecommerce" else "SEARCH_AVAILABILITY"
    actions[action_name] = {
        "type": "form",
        "form": form.selector,
        "input": form.input_selector,
        "submit": form.submit_selector,
        "confidence": MEDIUM_CONFIDENCE,
    }


def add_button_action(actions: dict[str, dict[str, Any]], data: DiscoveryInput, action_name: str) -> None:
    labels = ACTION_LABELS.get(action_name, ())
    button = first_matching_element(data.buttons, labels)
    if not button:
        return
    actions[action_name] = {
        "type": "click",
        "selector": button.selector,
        "label": button.label,
        "confidence": HIGH_CONFIDENCE,
    }


def add_route_actions(actions: dict[str, dict[str, Any]], routes: dict[str, str]) -> None:
    if "contact" in routes and "OPEN_CONTACT" not in actions:
        actions["OPEN_CONTACT"] = {"type": "navigate", "path": routes["contact"], "confidence": MEDIUM_CONFIDENCE}
    if "booking" in routes and "START_BOOKING" not in actions:
        actions["START_BOOKING"] = {"type": "navigate", "path": routes["booking"], "confidence": MEDIUM_CONFIDENCE}
    if "checkout" in routes and "CHECKOUT" not in actions:
        actions["CHECKOUT"] = {"type": "navigate", "path": routes["checkout"], "confidence": MEDIUM_CONFIDENCE}


def detect_platform(data: DiscoveryInput) -> str:
    hints = data.platform_hints
    if hints.get("shopify"):
        return "shopify"
    if hints.get("woocommerce"):
        return "woocommerce"
    return "auto"


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
    for element in elements:
        text = element.label.lower()
        if element.selector and any(label in text for label in labels):
            return element
    return None


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
