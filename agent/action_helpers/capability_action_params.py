"""Action parameter and field-schema helpers for capability filtering."""

from __future__ import annotations

from typing import Any

PROMPT_FIELD_SCHEMA_LIMIT = 8
PROMPT_FIELD_OPTION_LIMIT = 6
ACTION_PARAM_LIMIT = 20
ACTION_SCHEMA_LIMIT = 20
ACTION_SCHEMA_OPTION_LIMIT = 20
VALUE_PARAM_SEQUENCE_OPERATIONS: frozenset[str] = frozenset({"fill", "select", "set_value"})
FIELD_SCHEMA_ALIAS_KEYS: tuple[str, ...] = ("param", "label", "autocomplete")


def adapter_action_field_context(vertical_config: dict[str, Any]) -> str:
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict):
        return ""
    rows = [
        _action_field_line(action_name, action_config)
        for action_name, action_config in sorted(actions.items())
        if isinstance(action_config, dict)
    ]
    clean_rows = [row for row in rows if row]
    if not clean_rows:
        return ""
    return " ".join(clean_rows)


def action_config_fields(action_config: dict[str, Any]) -> list[str]:
    return unique_action_fields([
        *_configured_required_action_fields(action_config),
        *_sequence_required_action_fields(action_config),
    ])


def clean_action_fields(fields: Any) -> list[str]:
    if not isinstance(fields, list):
        return []
    return [str(field).strip() for field in fields[:ACTION_PARAM_LIMIT] if str(field).strip()]


def missing_required_action_params(action: dict[str, Any], action_config: dict[str, Any] | None) -> list[str]:
    if not isinstance(action_config, dict):
        return []
    required_params = action_config_fields(action_config)
    if not required_params:
        return []

    params = _action_params(action)
    return [
        required_param
        for required_param in required_params
        if not _has_required_action_param(action_config, params, required_param)
    ]


def unique_action_fields(fields: list[str]) -> list[str]:
    unique_fields: list[str] = []
    seen: set[str] = set()
    for field in fields:
        clean_field = str(field or "").strip()
        key = clean_field.lower()
        if not clean_field or key in seen:
            continue
        seen.add(key)
        unique_fields.append(clean_field)
        if len(unique_fields) >= ACTION_PARAM_LIMIT:
            break
    return unique_fields


def _action_field_line(action_name: str, action_config: dict[str, Any]) -> str:
    parts: list[str] = []
    fields = action_config_fields(action_config)
    if fields:
        parts.append(
            f"Action {action_name} requires params: {', '.join(fields)}. "
            "If any are missing, ask follow-up questions before emitting the action."
        )
    field_schema = _action_field_schema_text(action_config)
    if field_schema:
        parts.append(f"Action {action_name} accepts params: {field_schema}.")
    return " ".join(parts)


def _configured_required_action_fields(action_config: dict[str, Any]) -> list[str]:
    if _required_fields_known(action_config):
        return clean_action_fields(action_config.get("required_fields"))
    required_fields = clean_action_fields(action_config.get("required_fields"))
    if required_fields:
        return required_fields
    return clean_action_fields(action_config.get("fields"))


def _sequence_required_action_fields(action_config: dict[str, Any]) -> list[str]:
    steps = action_config.get("steps")
    if not isinstance(steps, list):
        return []

    fields: list[str] = []
    for step in steps:
        if not isinstance(step, dict) or step.get("optional") is True:
            continue
        operation = str(step.get("op") or step.get("type") or step.get("action") or "").strip().lower()
        if operation not in VALUE_PARAM_SEQUENCE_OPERATIONS:
            continue
        if str(step.get("value") or "").strip():
            continue
        field = str(step.get("param") or step.get("parameter") or step.get("name") or "").strip()
        if field:
            fields.append(field)
    return fields[:ACTION_PARAM_LIMIT]


def _required_fields_known(action_config: dict[str, Any]) -> bool:
    return action_config.get("required_fields_known") is True or isinstance(action_config.get("required_fields"), list)


def _action_params(action: dict[str, Any]) -> dict[str, Any]:
    params = action.get("params")
    if isinstance(params, dict):
        return params
    parameters = action.get("parameters")
    return parameters if isinstance(parameters, dict) else {}


def _has_required_action_param(
    action_config: dict[str, Any],
    params: dict[str, Any],
    required_param: str,
) -> bool:
    if _has_param_value(params, required_param):
        return True

    schema_item = _schema_item_for_param(action_config.get("field_schema"), required_param)
    if not schema_item:
        return False
    schema_key = _schema_param_key(schema_item, params)
    return bool(schema_key and _has_param_value(params, schema_key))


def _has_param_value(params: dict[str, Any], param: str) -> bool:
    wanted_key = _normalize_schema_key(param)
    for raw_key, value in params.items():
        if raw_key == param or _normalize_schema_key(raw_key) == wanted_key:
            return _usable_action_param_value(value)
    return False


def _usable_action_param_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _schema_item_for_param(field_schema: Any, param: str) -> dict[str, Any] | None:
    wanted_key = _normalize_schema_key(param)
    if not wanted_key:
        return None
    for item in _schema_items(field_schema):
        if wanted_key in _schema_keys_for_item(item):
            return item
    return None


def _schema_param_key(schema_item: dict[str, Any], params: dict[str, Any]) -> str:
    aliases = _schema_keys_for_item(schema_item)
    for raw_key, value in params.items():
        if _normalize_schema_key(raw_key) in aliases and _usable_action_param_value(value):
            return str(raw_key)
    return ""


def _schema_items(field_schema: Any) -> list[dict[str, Any]]:
    if not isinstance(field_schema, list):
        return []
    return [
        item
        for item in field_schema[:ACTION_SCHEMA_LIMIT]
        if isinstance(item, dict) and str(item.get("param") or "").strip()
    ]


def _schema_keys_for_item(item: dict[str, Any]) -> set[str]:
    values: list[Any] = [item.get(key) for key in FIELD_SCHEMA_ALIAS_KEYS]
    values.extend(_schema_option_text_values(item.get("options")))
    return {token for value in values for token in _schema_tokens(value) if token}


def _schema_option_text_values(options: Any) -> list[Any]:
    if not isinstance(options, list):
        return []
    values: list[Any] = []
    for option in options[:ACTION_SCHEMA_OPTION_LIMIT]:
        if not isinstance(option, dict):
            continue
        values.extend([option.get("label"), option.get("value")])
    return values


def _schema_tokens(value: Any) -> list[str]:
    normalized_text = _normalize_schema_text(value)
    if not normalized_text:
        return []
    return list({
        _normalize_schema_key(value),
        *normalized_text.split(" "),
    })


def _normalize_schema_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    return "_".join(part for part in _normalize_schema_text(text).split(" ") if part)


def _normalize_schema_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    parts = [part for part in _split_non_alnum(text) if part]
    return " ".join(parts)


def _split_non_alnum(value: str) -> list[str]:
    normalized = []
    current = []
    for char in value:
        if char.isalnum():
            current.append(char)
            continue
        if current:
            normalized.append("".join(current))
            current = []
    if current:
        normalized.append("".join(current))
    return normalized


def _action_field_schema_text(action_config: dict[str, Any]) -> str:
    schema = action_config.get("field_schema")
    if not isinstance(schema, list):
        return ""
    rows = [_field_schema_item_text(item) for item in schema[:PROMPT_FIELD_SCHEMA_LIMIT]]
    return "; ".join(row for row in rows if row)


def _field_schema_item_text(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    param = str(item.get("param") or "").strip()
    if not param:
        return ""
    details = _field_schema_details(item)
    return f"{param} ({', '.join(details)})" if details else param


def _field_schema_details(item: dict[str, Any]) -> list[str]:
    details: list[str] = []
    label = str(item.get("label") or "").strip()
    field_type = str(item.get("type") or "").strip()
    if label:
        details.append(label)
    if field_type:
        details.append(field_type)
    details.append("required" if item.get("required") is True else "optional")
    options = _field_option_text(item.get("options"))
    if options:
        details.append(f"choices: {options}")
    return details


def _field_option_text(options: Any) -> str:
    if not isinstance(options, list):
        return ""
    values = []
    for option in options[:PROMPT_FIELD_OPTION_LIMIT]:
        if isinstance(option, dict):
            value = str(option.get("label") or option.get("value") or "").strip()
        else:
            value = str(option or "").strip()
        if value:
            values.append(value)
    return " | ".join(values)
