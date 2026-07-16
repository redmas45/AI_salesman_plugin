"""Prompt and adapter-rule generation for discovered website adapters."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import urlparse

from agent.verticals.registry import get_vertical


DiscoverRoutes = Callable[[Any, str], dict[str, str]]
DiscoverActions = Callable[[Any, str, dict[str, str]], dict[str, dict[str, Any]]]
PlatformDetector = Callable[[Any], str]
BarrierReporter = Callable[[Any], dict[str, Any]]


def generated_system_prompt(
    data: Any,
    vertical_key: str,
    *,
    discover_routes: DiscoverRoutes,
    discover_actions: DiscoverActions,
    detect_platform: PlatformDetector,
    browser_barrier_report: BarrierReporter,
) -> str:
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
            _conversation_intelligence_prompt_block(),
            _generated_few_shots_prompt_block(data, actions),
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
            "- First answer the visitor's practical question, then ask at most one short follow-up only when it materially narrows the recommendation or unlocks the next supported action.\n"
            "- Do not ask for details already stated by the user; acknowledge them naturally and move to the next missing step.\n"
            "- For general trivia, politics, live news, weather, or unrelated requests, decline briefly and pivot back to this website.\n"
            "- Emit one coherent primary UI path per turn; do not combine a comparison with a competing record list or search navigation for the same options.\n"
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
        "- Before asking for missing action params, extract matching values from the latest user message, conversation history, session profile, and live page context.\n"
        "- Do not ask again for params the user already supplied in natural language; emit the supported action with those params when all required fields are known.\n"
        "- If confidence is low, explain the exact missing website data and offer handoff or a safe next click instead of pretending the action completed.\n"
    )
    if vertical.risk_level == "high":
        return (
            base
            + "- High-risk vertical: never make regulated decisions, diagnoses, underwriting decisions, eligibility approvals, legal conclusions, financial suitability recommendations, or claim guarantees.\n"
            + "- You may explain website-published information and start website-supported forms, but final outcomes require the website/provider/human confirmation."
        )
    return base


def generated_prompt_suggestions(
    vertical_key: str,
    actions: dict[str, dict[str, Any]],
    routes: dict[str, str],
) -> list[str]:
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


def _conversation_intelligence_prompt_block() -> str:
    lines = [
        "## Conversation Intelligence And Slot Filling",
        "- Convert natural user statements into action params before asking follow-up questions.",
        "- Reuse facts from the latest message, previous turns, session profile, and live browser context.",
        "- Use discovered action fields, labels, select/radio options, and required params as the source of truth for slot filling.",
        "- Ask only for exact missing fields required by the next supported website action.",
        "- This applies across domains: map user facts to whatever field names the current website exposes, not to hardcoded site or industry assumptions.",
        "- Treat buy/get/start/book/apply/request language as intent to run the supported website flow, not as a request to go home.",
        "- Example: if a discovered action requires fields named 'Start location', 'End location', 'Service date', and 'Party size', and the user gives those values, emit the action with those params instead of asking again.",
    ]
    return "\n".join(lines)


def _generated_few_shots_prompt_block(data: Any, actions: dict[str, dict[str, Any]]) -> str:
    rows: list[str] = []
    for action_name, action_config in sorted(actions.items())[:3]:
        params = _few_shot_params_for_action(action_config)
        label = clean_text(action_config.get("label") or action_config.get("title") or action_name.replace("_", " ").title())
        user = _few_shot_user_request(label, params)
        answer = {
            "response_text": _few_shot_response_text(action_name, params),
            "intent": "lead_capture" if params else "navigate",
            "confidence": 0.92,
            "answer_scope": "website_action",
            "ui_actions": [{"action": action_name, "params": params}],
        }
        rows.append(f"User: {user}\nAssistant JSON: {json.dumps(answer, ensure_ascii=False)}")

    if data.text_sample:
        answer = {
            "response_text": "I can answer from the website data I have, or help you open the relevant page.",
            "intent": "discovery",
            "confidence": 0.8,
            "answer_scope": "grounded_fact",
            "ui_actions": [],
        }
        rows.append(
            "User: What can this website help me with?\n"
            f"Assistant JSON: {json.dumps(answer, ensure_ascii=False)}"
        )

    if not rows:
        return ""
    return (
        "## Setup-Generated Few-Shot Examples\n"
        "These examples are generated from this website's detected routes, labels, and action schema. Follow the pattern, not the literal domain wording.\n"
        + "\n".join(f"- {row}" for row in rows)
    )


def _few_shot_params_for_action(action_config: dict[str, Any]) -> dict[str, str]:
    params: dict[str, str] = {}
    for field in _few_shot_field_specs(action_config)[:5]:
        param = clean_text(field.get("param") or field.get("name") or "")
        if not param:
            continue
        params[param] = _few_shot_value_for_field(param, field)
    return params


def _few_shot_field_specs(action_config: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    field_schema = action_config.get("field_schema")
    if isinstance(field_schema, list):
        specs.extend(item for item in field_schema if isinstance(item, dict))
    for param in action_config.get("required_fields") or []:
        if str(param or "").strip():
            specs.append({"param": str(param).strip()})
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for spec in specs:
        key = clean_text(spec.get("param") or spec.get("name") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(spec)
    return unique


def _few_shot_value_for_field(param: str, field: dict[str, Any]) -> str:
    options = field.get("options")
    if isinstance(options, list):
        for option in options:
            if isinstance(option, dict):
                value = clean_text(option.get("value") or option.get("label"))
            else:
                value = clean_text(option)
            if value:
                return value
    text = clean_text(param).lower()
    if "age" in text:
        return "34"
    if any(term in text for term in ("city", "location", "area", "station", "port")):
        return "Pune"
    if any(term in text for term in ("date", "day", "when")):
        return "tomorrow"
    if any(term in text for term in ("email",)):
        return "customer@example.com"
    if any(term in text for term in ("phone", "mobile")):
        return "[PHONE]"
    if any(term in text for term in ("count", "guest", "traveler", "passenger", "quantity", "size")):
        return "2"
    return "customer provided value"


def _few_shot_user_request(label: str, params: dict[str, str]) -> str:
    if not params:
        return f"Please open {label or 'that page'}."
    details = ", ".join(f"{param}: {value}" for param, value in params.items())
    return f"I want to start {label or 'this website flow'}; {details}."


def _few_shot_response_text(action_name: str, params: dict[str, str]) -> str:
    if params:
        return "I have those details. Starting the website flow now."
    if action_name == "NAVIGATE_TO":
        return "Opening that page now."
    return "I can start that website action now."


def _site_evidence_prompt_block(data: Any) -> str:
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


def _form_prompt_block(forms: tuple[Any, ...]) -> str:
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


def unique_texts(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        text = clean_text(value)
        key = text.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(text)
        if len(rows) >= limit:
            break
    return rows


def host_label(origin: str) -> str:
    host = urlparse(origin).netloc or origin
    return host.replace("www.", "").split(":")[0]


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())
