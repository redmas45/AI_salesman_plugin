"""Generic vertical prompt assembly."""

from __future__ import annotations

import json
from typing import Any

from agent.capabilities import capability_prompt_context, get_allowed_actions
from agent.sales_intake import sales_intake_prompt_context
from agent.verticals.registry import get_vertical
from db.prompts import prompt_profile_context


GENERIC_RESPONSE_SCHEMA = """{
  "response_text": "<concise source-backed answer>",
  "intent": "<discovery | compare | lead_capture | handoff | navigate | chitchat | unknown>",
  "confidence": <0.0 to 1.0>,
  "answer_scope": "<grounded_fact | buying_guidance | website_action | unsupported_or_offsite>",
  "ui_actions": [
    {
      "action": "<allowed action>",
      "params": {}
    }
  ]
}"""


def build_generic_system_prompt(
    *,
    site_id: str,
    vertical_key: str,
    knowledge_context: str,
    profile_context: str = "",
    page_context: str = "",
) -> str:
    """Build a non-commerce prompt from vertical metadata and knowledge context."""
    vertical = get_vertical(vertical_key)
    actions = sorted(get_allowed_actions(site_id))
    custom_context = prompt_profile_context(site_id)
    sections = [
        _platform_policy(vertical.risk_level),
        _vertical_block(vertical, actions),
        _conversation_intelligence_block(vertical.key),
        _intake_block(sales_intake_prompt_context(vertical.key)),
        _capability_block(capability_prompt_context(site_id)),
        _custom_prompt_block(custom_context),
        _sales_relevance_block(),
        _profile_block(profile_context),
        _page_context_block(page_context),
        _knowledge_block(knowledge_context),
        _response_block(),
    ]
    return "\n\n".join(section for section in sections if section)


def format_knowledge_for_prompt(items: list[dict[str, Any]]) -> str:
    """Format knowledge rows into compact, ID-preserving context."""
    if not items:
        return "No matching source-backed records were retrieved."
    return "\n".join(_item_line(item) for item in items)


def _platform_policy(risk_level: str) -> str:
    rules = [
        "You are a client website assistant inside AI Hub.",
        "Answer only from retrieved source data and client-published prompt instructions.",
        "Do not invent prices, terms, availability, eligibility, professional advice, or policy details.",
        "If data is missing, say what is missing and offer a safe next step.",
        "If the user asks to go to, open, visit, switch to, or navigate to a site page, return NAVIGATE_TO instead of explaining the page.",
        "If conversation history contains BROWSER_ACTION_RESULTS, treat it as browser execution proof. If the latest action failed or was blocked, acknowledge that and choose a safe recovery instead of claiming success.",
        "Return valid JSON only.",
    ]
    if risk_level == "high":
        rules.extend(
            [
                "This is a high-risk vertical. Do not diagnose, underwrite, approve, decide eligibility, provide legal conclusions, or give personalized financial advice.",
                "Use handoff actions when the user asks for regulated decisions or sensitive personal assessment.",
            ]
        )
    return "## Platform Policy\n" + "\n".join(f"- {rule}" for rule in rules)


def _vertical_block(vertical, actions: list[str]) -> str:
    entity_types = ", ".join(vertical.entity_types)
    action_text = ", ".join(actions) or "none"
    return (
        "## Vertical Context\n"
        f"Vertical: {vertical.label} ({vertical.key}).\n"
        f"Primary entity: {vertical.entity_label_singular}; plural: {vertical.entity_label_plural}.\n"
        f"Supported entity types: {entity_types}.\n"
        f"Allowed UI actions for this client: {action_text}.\n"
        "Use NAVIGATE_TO with params {\"page\":\"<page-key>\"} for page movement such as home, plans, claims, quote, contact, checkout, support, or any route visible in browser context.\n"
        "Use SHOW_ENTITIES, COMPARE_ENTITIES, SORT_ENTITIES, FILTER_ENTITIES, or OPEN_ENTITY_DETAIL only with exact IDs from the Retrieved Knowledge section or for records already visible in the widget overlay.\n"
        "If the user says sort these, lowest first, highest first, cheapest, premium low to high, rating, newest, or similar, return a sorting action instead of explaining why sorting cannot be done.\n"
        f"{_vertical_playbook(vertical.key)}"
    )


def _vertical_playbook(vertical_key: str) -> str:
    playbooks = {
        "insurance": (
            "\nInsurance behavior: act like a source-grounded insurance sales advisor. Compare plan type, premium visibility, sum insured/coverage amount, waiting periods, exclusions, deductibles/copay, riders/add-ons, claim process, renewal steps, documents, and insurer/support details only when those facts are retrieved. "
            "If premiums are missing, do not treat zero as a real premium; say the website requires quote details and use START_QUOTE, OPEN_POLICY, OPEN_CLAIM_FLOW, OPEN_RENEWAL_FLOW, HANDOFF_TO_AGENT, SHOW_ENTITIES, COMPARE_ENTITIES, SORT_ENTITIES, or NAVIGATE_TO when allowed. "
            "Ask only the minimum next intake question needed for the website flow, such as coverage type, age band, family size, budget, city, phone, or claim/renewal intent. Reuse direct facts the user already gave, for example city, age, self/family, plan type, and budget, instead of asking again. Never promise eligibility, approval, coverage, claim payout, medical acceptance, or regulatory outcome."
        ),
        "travel": (
            "\nTravel behavior: compare destinations, activities, tickets, dates, availability windows, inclusions, pickup/location clues, cancellation clues, and itinerary fit from source data. Use availability/search/booking/navigation actions when asked to do site work, and never claim a booking is complete unless the website confirms it."
        ),
        "finance_broker": (
            "\nFinance broker behavior: explain published product information, rates, fees, tenure, documents, calculators, and application routes from source data. Do not make suitability recommendations, credit decisions, loan approvals, rate guarantees, tax/legal claims, or investment advice."
        ),
        "healthcare": (
            "\nHealthcare behavior: explain provider/service information, appointment flow, location, timings, documents, and published preparation notes. Do not diagnose, prescribe, triage emergencies, or promise clinical outcomes."
        ),
        "construction": (
            "\nConstruction behavior: explain services, project types, estimate flow, site visit flow, materials, timelines, warranty clues, and portfolio evidence from source data. Do not guarantee price, permits, structural decisions, safety approval, or completion dates."
        ),
        "legal_services": (
            "\nLegal services behavior: explain published services, consultation steps, practice areas, document requirements, and handoff routes. Do not provide legal conclusions, attorney-client assurances, filing guarantees, or jurisdiction-specific advice beyond source text."
        ),
    }
    return playbooks.get(
        vertical_key,
        "\nGeneral sales behavior: identify the visitor's goal, retrieve matching records, explain tradeoffs from source data, navigate to relevant pages, and start supported website actions. Do not claim completion beyond website confirmation.",
    )


def _conversation_intelligence_block(vertical_key: str) -> str:
    lines = [
        "## Conversation Intelligence",
        "- Treat the latest user message, previous turns, session profile, and live page context as structured facts before asking anything.",
        "- Use the Website Capability Policy and action field schema as the source of truth for required action params.",
        "- Never ask again for a required field already supplied in normal language; fill the matching action param and continue.",
        "- Match natural language to the exact discovered field labels, input types, placeholders, and select/radio options for every vertical.",
        "- If the user asks to buy, get, take, start, apply for, book, or request something the website supports, start that supported website flow instead of navigating to home.",
        "- If a supported action still lacks required params after extraction, ask one short question for only the exact missing field.",
        '- Example: if a discovered action requires fields "Start location", "End location", "Service date", and "Party size", and the user supplies those values, emit the action with exactly those params instead of asking again.',
    ]
    return "\n".join(lines)


def _capability_block(capability_context: str) -> str:
    text = capability_context.strip()
    if not text:
        return ""
    return f"## Website Capability Policy\n{text}"


def _intake_block(intake_context: str) -> str:
    return intake_context.strip()


def _custom_prompt_block(custom_context: str) -> str:
    if not custom_context.strip():
        return ""
    return f"## Published Client Prompt\n{custom_context.strip()}"


def _profile_block(profile_context: str) -> str:
    text = profile_context.strip() or "No session profile data is available."
    return f"## Session Profile\n{text}"


def _page_context_block(page_context: str) -> str:
    text = page_context.strip()
    if not text:
        return ""
    return text


def _knowledge_block(knowledge_context: str) -> str:
    text = knowledge_context.strip() or "No matching source-backed records were retrieved."
    return f"## Retrieved Knowledge\n{text}"


def _sales_relevance_block() -> str:
    return (
        "## Sales Relevance And Grounding\n"
        "- Maya is a sales assistant for this exact website, not a general research chatbot.\n"
        "- Answer buying-relevant questions about products, plans, services, policies, specs, reviews, pricing, availability, documents, flow steps, or comparisons only from retrieved/source/client data.\n"
        "- If the user asks for deep off-site theory, internals, architecture, research, legal/medical/financial conclusions, or anything not supported by retrieved website data, give a brief boundary and offer to compare website-confirmed buying facts instead.\n"
        "- Do not expose chain-of-thought, hidden scoring, or private reasoning. Provide only the concise customer-facing answer.\n"
        "- Set answer_scope to grounded_fact for source-backed facts, buying_guidance for practical recommendations, website_action for navigation/forms/actions, and unsupported_or_offsite for bounded unsupported questions."
    )


def _response_block() -> str:
    return (
        "## Response Format\n"
        "Navigation example: {\"response_text\":\"Opening plans.\",\"intent\":\"navigate\",\"confidence\":1.0,\"answer_scope\":\"website_action\",\"ui_actions\":[{\"action\":\"NAVIGATE_TO\",\"params\":{\"page\":\"plans\"}}]}\n"
        "Return this JSON object only:\n"
        f"```json\n{GENERIC_RESPONSE_SCHEMA}\n```"
    )


def _item_line(item: dict[str, Any]) -> str:
    item_id = str(item.get("id") or "").strip()
    title = str(item.get("title") or item.get("name") or "Untitled").strip()
    entity_type = str(item.get("entity_type") or "knowledge_item").strip()
    summary = str(item.get("summary") or item.get("body") or "").strip()
    pricing = _compact_pricing_json(item.get("pricing"))
    availability = _compact_json(item.get("availability"))
    url = str(item.get("url") or "").strip()
    parts = [
        f'[ID:"{item_id}"] {title}',
        f"Type: {entity_type}",
        f"Summary: {summary[:260]}",
    ]
    if pricing:
        parts.append(f"Pricing: {pricing}")
    if availability:
        parts.append(f"Availability: {availability}")

    attributes = _compact_json(item.get("attributes_json"))
    if attributes:
        parts.append(f"Attributes: {attributes}")

    if url:
        parts.append(f"Source: {url}")
    return " | ".join(parts)


def _compact_json(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    clean = {key: val for key, val in value.items() if val not in ("", None, [], {})}
    return json.dumps(clean, ensure_ascii=False, default=str) if clean else ""


def _compact_pricing_json(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    meaningful: dict[str, Any] = {}
    for key, val in value.items():
        if val in ("", None, [], {}):
            continue
        if isinstance(val, (int, float)) and val == 0:
            continue
        if isinstance(val, str) and val.strip().replace(",", "") in {"0", "0.0", "0.00"}:
            continue
        meaningful[key] = val
    if not meaningful:
        return ""
    money_keys = {
        "price",
        "amount",
        "premium",
        "premium_min",
        "monthly_premium",
        "annual_premium",
        "min_price",
        "starting_price",
    }
    has_amount = any(_positive_number(meaningful.get(key)) for key in money_keys)
    has_textual_pricing = any(key not in {"currency", *money_keys} for key in meaningful)
    if not has_amount and not has_textual_pricing:
        return ""
    return json.dumps(meaningful, ensure_ascii=False, default=str)


def _positive_number(value: Any) -> bool:
    try:
        return float(str(value).replace(",", "")) > 0
    except (TypeError, ValueError):
        return False
