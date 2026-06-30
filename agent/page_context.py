"""Privacy-safe browser page context for action planning."""

from __future__ import annotations

import json
from typing import Any

MAX_TEXT_LENGTH = 180
MAX_LIST_ITEMS = 12
MAX_FIELDS = 8
MAX_JSON_CHARS = 1200
SENSITIVE_FIELD_TYPES = frozenset({"password", "file", "hidden"})


def parse_page_context(raw_context: str | None) -> dict[str, Any]:
    """Parse and sanitize browser page context from public widget transports."""
    if not raw_context:
        return {}
    try:
        decoded = json.loads(raw_context)
    except json.JSONDecodeError:
        return {}
    return sanitize_page_context(decoded)


def sanitize_page_context(raw_context: Any) -> dict[str, Any]:
    """Return a capped, prompt-safe context without user-entered field values."""
    if not isinstance(raw_context, dict):
        return {}
    controls = _dict(raw_context.get("controls"))
    adapter = _dict(raw_context.get("adapter"))
    capabilities = _dict(raw_context.get("capabilities"))
    return {
        "title": _text(raw_context.get("title")),
        "url": _safe_url(raw_context.get("url")),
        "path": _text(raw_context.get("path")),
        "product_id": _text(raw_context.get("productId") or raw_context.get("product_id")),
        "vertical": _text(capabilities.get("vertical") or raw_context.get("vertical")),
        "platform": _text(capabilities.get("platform") or raw_context.get("platform")),
        "capabilities": _text_list(capabilities.get("actions") or raw_context.get("capabilities")),
        "routes": _string_map(adapter.get("routes") or raw_context.get("routes")),
        "actions": _text_list(adapter.get("actions") or raw_context.get("actions")),
        "blocked_actions": _text_list(adapter.get("blocked_actions") or raw_context.get("blocked_actions")),
        "runtime_blocked_actions": _text_list(adapter.get("runtime_blocked_actions") or raw_context.get("runtime_blocked_actions")),
        "handoff_actions": _text_list(adapter.get("handoff_actions") or raw_context.get("handoff_actions")),
        "handoff_flows": _handoff_flow_rows(adapter.get("handoff_flows") or raw_context.get("handoff_flows")),
        "buttons": _control_rows(controls.get("buttons") or raw_context.get("buttons"), ("label", "selector")),
        "links": _control_rows(controls.get("links") or raw_context.get("links"), ("label", "href", "selector")),
        "forms": _form_rows(controls.get("forms") or raw_context.get("forms")),
    }


def format_page_context(raw_context: Any) -> str:
    """Format sanitized page context for LLM action planning."""
    context = sanitize_page_context(raw_context)
    if not context:
        return ""

    lines = [
        "## Current Browser Page",
        f"Title: {context['title'] or 'unknown'}",
        f"Path: {context['path'] or 'unknown'}",
        f"Vertical: {context['vertical'] or 'unknown'} | Platform: {context['platform'] or 'unknown'}",
    ]
    if context["routes"]:
        lines.append("Routes: " + ", ".join(f"{key} -> {value}" for key, value in context["routes"].items()))
    if context["actions"]:
        lines.append("Generated adapter actions on this site: " + ", ".join(context["actions"]))
    if context["blocked_actions"]:
        lines.append("Blocked actions right now: " + ", ".join(context["blocked_actions"]))
    if context["handoff_actions"]:
        lines.append("Safe handoff actions: " + ", ".join(context["handoff_actions"]))
    if context["handoff_flows"]:
        lines.extend(_handoff_flow_lines(context["handoff_flows"]))
    lines.extend(_control_lines("Buttons", context["buttons"], ("label", "selector")))
    lines.extend(_control_lines("Links", context["links"], ("label", "href")))
    lines.extend(_form_lines(context["forms"]))
    lines.append(
        "Use this browser context for NAVIGATE_TO, form params, and page actions. "
        "Do not invent selectors; prefer generated adapter actions when available."
    )
    return "\n".join(lines)[:MAX_JSON_CHARS]


def _handoff_flow_lines(flows: list[dict[str, str]]) -> list[str]:
    lines = ["Handoff flows:"]
    for flow in flows[:4]:
        provider = f" via {flow['provider']}" if flow.get("provider") else ""
        title = flow.get("title") or flow.get("key") or "handoff"
        action = flow.get("action") or "HANDOFF_TO_HUMAN"
        handling = flow.get("handling") or ""
        boundary = flow.get("automation_boundary") or ""
        recovery = flow.get("recovery") or ""
        lines.append(f"- {title}: use {action}{provider}. {handling} {boundary} {recovery}".strip())
    return lines


def _control_lines(title: str, rows: list[dict[str, str]], fields: tuple[str, ...]) -> list[str]:
    if not rows:
        return []
    lines = [f"{title}:"]
    for row in rows[:6]:
        parts = [row.get(field, "") for field in fields if row.get(field)]
        if parts:
            lines.append("- " + " | ".join(parts))
    return lines


def _form_lines(forms: list[dict[str, Any]]) -> list[str]:
    if not forms:
        return []
    lines = ["Forms:"]
    for form in forms[:4]:
        label = form.get("label") or form.get("selector") or "form"
        fields = ", ".join(_field_summary(field) for field in form.get("fields", [])[:MAX_FIELDS])
        lines.append(f"- {label}: {fields or 'no visible fields'}")
    return lines


def _field_summary(field: dict[str, Any]) -> str:
    name = field.get("name") or field.get("placeholder") or field.get("selector") or "field"
    field_type = field.get("type") or "field"
    options = field.get("options") if isinstance(field.get("options"), list) else []
    option_text = f" options={', '.join(options[:5])}" if options else ""
    return f"{name} ({field_type}){option_text}"


def _form_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value[:MAX_LIST_ITEMS]:
        form = _dict(item)
        fields = [_field_row(field) for field in _list(form.get("fields"))[:MAX_FIELDS]]
        clean_fields = [field for field in fields if field]
        if clean_fields:
            rows.append({
                "label": _text(form.get("label")),
                "selector": _text(form.get("selector")),
                "submit_selector": _text(form.get("submit_selector")),
                "fields": clean_fields,
            })
    return rows


def _field_row(value: Any) -> dict[str, Any]:
    field = _dict(value)
    field_type = _text(field.get("type")).lower()
    if field_type in SENSITIVE_FIELD_TYPES:
        return {}
    return {
        "selector": _text(field.get("selector")),
        "name": _text(field.get("name")),
        "type": field_type,
        "placeholder": _text(field.get("placeholder")),
        "autocomplete": _text(field.get("autocomplete")),
        "options": _text_list(field.get("options"), limit=8),
    }


def _control_rows(value: Any, fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value[:MAX_LIST_ITEMS]:
        row = {field: _text(_dict(item).get(field)) for field in fields}
        if any(row.values()):
            rows.append(row)
    return rows


def _handoff_flow_rows(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value[:MAX_LIST_ITEMS]:
        flow = _dict(item)
        row = {
            "key": _text(flow.get("key")),
            "title": _text(flow.get("title")),
            "provider": _text(flow.get("provider")),
            "provider_label": _text(flow.get("provider_label")),
            "action": _text(flow.get("action")),
            "severity": _text(flow.get("severity")),
            "handling": _text(flow.get("handling")),
            "automation_boundary": _text(flow.get("automation_boundary")),
            "admin_action": _text(flow.get("admin_action")),
            "recovery": _text(flow.get("recovery")),
        }
        if row["key"] or row["action"]:
            rows.append(row)
    return rows


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    rows: dict[str, str] = {}
    for raw_key, raw_value in list(value.items())[:MAX_LIST_ITEMS]:
        key = _text(raw_key)
        text = _text(raw_value)
        if key and text:
            rows[key] = text
    return rows


def _text_list(value: Any, *, limit: int = MAX_LIST_ITEMS) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value[:limit] if _text(item)]


def _safe_url(value: Any) -> str:
    text = _text(value)
    if text.lower().startswith(("javascript:", "data:")):
        return ""
    return text


def _text(value: Any) -> str:
    return str(value or "").replace("\x00", "").replace("\n", " ").strip()[:MAX_TEXT_LENGTH]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
