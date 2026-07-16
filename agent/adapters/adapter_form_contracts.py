"""Universal form action contract helpers for adapter discovery."""

from __future__ import annotations

import re
from typing import Any

from agent.actions.registry import get_action, normalize_action_name

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
RESULT_QUERY_ACTIONS: frozenset[str] = frozenset({
    "CHECK_AVAILABILITY",
    "CHECK_DELIVERY_AVAILABILITY",
    "FILTER_ENTITIES",
    "FILTER_PRODUCTS",
    "MATCH_JOBS",
    "RUN_AFFORDABILITY_CALCULATOR",
    "RUN_CALCULATOR",
    "SEARCH_AVAILABILITY",
    "SET_LOCATION",
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
CREDENTIAL_FIELD_TERMS: tuple[str, ...] = (
    "current password",
    "login",
    "one time password",
    "otp",
    "passcode",
    "password",
    "sign in",
    "signin",
    "username",
    "verification code",
)
MAX_FIELD_SCHEMA_OPTIONS = 20


def form_sequence_steps(form: Any, action_name: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    seen_checkable_params: set[str] = set()
    force_required = form_submit_mode(action_name, form) == "submit"
    for field in form.fields:
        if should_skip_duplicate_checkable_step(field, seen_checkable_params):
            continue
        step = form_field_step(field, force_required=force_required)
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


def form_field_step(field: dict[str, Any], *, force_required: bool = False) -> dict[str, Any]:
    selector = clean_selector(field.get("selector"))
    if not selector:
        return {}
    field_type = clean_text(field.get("type")).lower()
    param = field_param_name(field)
    optional = not (force_required or field_required(field))
    if field_type in {"file", "submit", "button"}:
        return {}
    if field_type in {"checkbox", "radio"}:
        return {"op": "check", "selector": selector, "param": param, "optional": optional}
    if field_type == "select":
        return {"op": "select", "selector": selector, "param": param, "optional": optional}
    return {"op": "fill", "selector": selector, "param": param, "optional": optional}


def field_param_name(field: dict[str, Any]) -> str:
    source = field_param_source(field).lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", source).strip("_")
    return normalized[:60] or "value"


def field_param_source(field: dict[str, Any]) -> str:
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


def form_action_field_config(form: Any, action_name: str = "") -> dict[str, Any]:
    fields = field_param_names(form.fields)
    required_fields = action_required_field_params(form, action_name)
    field_schema = form_field_schema(form.fields, required_fields)
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


def action_required_field_params(form: Any, action_name: str = "") -> list[str]:
    if action_name and form_submit_mode(action_name, form) == "submit":
        return field_param_names(form.fields)
    return required_field_params(form.fields)


def form_field_schema(fields: tuple[dict[str, Any], ...], required_fields: list[str] | None = None) -> list[dict[str, Any]]:
    required = set(required_fields or [])
    rows = [form_field_schema_item(field, force_required=field_param_name(field) in required) for field in fields]
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


def form_field_schema_item(field: dict[str, Any], *, force_required: bool = False) -> dict[str, Any]:
    param = field_param_name(field)
    if not param:
        return {}
    row: dict[str, Any] = {"param": param, "required": force_required or field_required(field)}
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


def form_submit_mode(action_name: str, form: Any | None = None) -> str:
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


def safe_result_form_submit(action_name: str, form: Any) -> bool:
    if action_name not in RESULT_SUBMIT_ACTIONS:
        return False
    if not form.submit_selector:
        return False
    form_text = normalized_form_text(form)
    if form_requires_prepare_only(form, form_text):
        return False
    return contains_any_term(form_text, RESULT_SUBMIT_TERMS)


def form_is_rejected_for_action(action_name: str, form: Any) -> bool:
    normalized = normalize_action_name(action_name)
    return bool(normalized in RESULT_QUERY_ACTIONS and form_has_credential_fields(form))


def form_requires_prepare_only(form: Any, form_text: str | None = None) -> bool:
    text = form_text if form_text is not None else normalized_form_text(form)
    return form_has_sensitive_fields(form) or contains_any_term(text, FINAL_SUBMIT_TERMS)


def form_has_sensitive_fields(form: Any) -> bool:
    if not form.fields:
        selector_text = normalized_text(" ".join([form.selector, form.input_selector]))
        return contains_any_term(selector_text, SENSITIVE_FIELD_TERMS)
    return any(field_has_sensitive_term(field) for field in form.fields)


def form_has_credential_fields(form: Any) -> bool:
    if not form.fields:
        selector_text = normalized_text(" ".join([form.label, form.selector, form.input_selector, form.submit_selector]))
        return contains_any_term(selector_text, CREDENTIAL_FIELD_TERMS)
    return contains_any_term(normalized_form_text(form), CREDENTIAL_FIELD_TERMS)


def field_has_sensitive_term(field: dict[str, Any]) -> bool:
    field_text = normalized_text(
        " ".join(str(field.get(key) or "") for key in ("label", "name", "placeholder", "type", "autocomplete"))
    )
    tokens = set(field_text.split())
    return any(term in tokens or term in field_text for term in SENSITIVE_FIELD_TERMS)


def normalized_form_text(form: Any) -> str:
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


def clean_selector(value: Any) -> str:
    return clean_text(value)


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())
