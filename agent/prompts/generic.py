"""Generic vertical prompt assembly."""

from __future__ import annotations

import json
from typing import Any

from agent.capabilities import get_allowed_actions
from agent.verticals.registry import get_vertical
from db.prompts import prompt_profile_context


GENERIC_RESPONSE_SCHEMA = """{
  "response_text": "<concise source-backed answer>",
  "intent": "<discovery | compare | lead_capture | handoff | navigate | chitchat | unknown>",
  "confidence": <0.0 to 1.0>,
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
) -> str:
    """Build a non-commerce prompt from vertical metadata and knowledge context."""
    vertical = get_vertical(vertical_key)
    actions = sorted(get_allowed_actions(site_id))
    custom_context = prompt_profile_context(site_id)
    sections = [
        _platform_policy(vertical.risk_level),
        _vertical_block(vertical, actions),
        _custom_prompt_block(custom_context),
        _profile_block(profile_context),
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
        "Use SHOW_ENTITIES, COMPARE_ENTITIES, or OPEN_ENTITY_DETAIL only with exact IDs from the Retrieved Knowledge section."
    )


def _custom_prompt_block(custom_context: str) -> str:
    if not custom_context.strip():
        return ""
    return f"## Published Client Prompt\n{custom_context.strip()}"


def _profile_block(profile_context: str) -> str:
    text = profile_context.strip() or "No session profile data is available."
    return f"## Session Profile\n{text}"


def _knowledge_block(knowledge_context: str) -> str:
    text = knowledge_context.strip() or "No matching source-backed records were retrieved."
    return f"## Retrieved Knowledge\n{text}"


def _response_block() -> str:
    return (
        "## Response Format\n"
        "Return this JSON object only:\n"
        f"```json\n{GENERIC_RESPONSE_SCHEMA}\n```"
    )


def _item_line(item: dict[str, Any]) -> str:
    item_id = str(item.get("id") or "").strip()
    title = str(item.get("title") or item.get("name") or "Untitled").strip()
    entity_type = str(item.get("entity_type") or "knowledge_item").strip()
    summary = str(item.get("summary") or item.get("body") or "").strip()
    pricing = _compact_json(item.get("pricing"))
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
    if url:
        parts.append(f"Source: {url}")
    return " | ".join(parts)


def _compact_json(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    clean = {key: val for key, val in value.items() if val not in ("", None, [], {})}
    return json.dumps(clean, ensure_ascii=False, default=str) if clean else ""
