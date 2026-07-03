"""Action readiness summaries for generated website controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agent.actions.registry import get_action, normalize_action_name
from agent.sales_intake import intake_questions_for

MAX_ACTION_READINESS_ROWS = 40
MAX_PARAM_ITEMS = 20
VALUE_PARAM_SEQUENCE_OPERATIONS = frozenset({"fill", "select", "set_value"})


@dataclass(frozen=True)
class ActionReadiness:
    """Prompt/CRM-facing contract for one generated action."""

    action: str
    status: str
    required_params: tuple[str, ...] = ()
    optional_params: tuple[str, ...] = ()
    question: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def action_readiness_for(vertical_config: dict[str, Any], vertical_key: str) -> list[dict[str, Any]]:
    """Return readiness rows for generated actions that need or accept user params."""
    actions = vertical_config.get("actions") if isinstance(vertical_config, dict) else {}
    if not isinstance(actions, dict):
        return []
    rows = [
        _action_readiness(action_name, action_config, vertical_key)
        for action_name, action_config in sorted(actions.items())
        if isinstance(action_config, dict) and get_action(str(action_name))
    ]
    return [row.to_dict() for row in rows if _should_show_readiness(row)][:MAX_ACTION_READINESS_ROWS]


def sanitize_action_readiness(value: Any) -> list[dict[str, Any]]:
    """Validate action readiness rows before exposing them through runtime config."""
    if not isinstance(value, list):
        return []
    rows = [_sanitize_row(item) for item in value[:MAX_ACTION_READINESS_ROWS] if isinstance(item, dict)]
    return [row for row in rows if row]


def action_readiness_prompt_context(vertical_config: dict[str, Any], vertical_key: str) -> str:
    """Build prompt guidance that ties action params to intake questions."""
    rows = action_readiness_for(vertical_config, vertical_key)
    needs_params = [row for row in rows if row["status"] == "requires_params"]
    if not needs_params:
        return ""
    lines = ["Action readiness before execution:"]
    for row in needs_params[:8]:
        params = ", ".join(row["required_params"])
        line = f"{row['action']} requires {params} before emitting the action."
        if row.get("question"):
            line = f"{line} Ask: {row['question']}"
        lines.append(line)
    return " ".join(lines)


def _action_readiness(action_name: str, action_config: dict[str, Any], vertical_key: str) -> ActionReadiness:
    action = normalize_action_name(action_name)
    required_params = tuple(_required_params(action_config))
    optional_params = tuple(_optional_params(action_config, required_params))
    question = _question_for_action(vertical_key, action, required_params)
    status = "requires_params" if required_params else "ready_without_required_params"
    return ActionReadiness(
        action=action,
        status=status,
        required_params=required_params,
        optional_params=optional_params,
        question=question,
        reason=_reason_for_action(vertical_key, action),
    )


def _should_show_readiness(row: ActionReadiness) -> bool:
    return bool(row.required_params or row.optional_params or row.question)


def _required_params(action_config: dict[str, Any]) -> list[str]:
    if action_config.get("required_fields_known") is True or isinstance(action_config.get("required_fields"), list):
        return _unique_params(_clean_param_list(action_config.get("required_fields")))
    configured = _clean_param_list(action_config.get("required_fields"))
    if configured:
        return _unique_params(configured)
    return _unique_params([*_clean_param_list(action_config.get("fields")), *_sequence_required_params(action_config)])


def _optional_params(action_config: dict[str, Any], required_params: tuple[str, ...]) -> list[str]:
    required_keys = {_param_key(param) for param in required_params}
    fields = [*_clean_param_list(action_config.get("fields")), *_schema_params(action_config.get("field_schema"))]
    return [param for param in _unique_params(fields) if _param_key(param) not in required_keys]


def _sequence_required_params(action_config: dict[str, Any]) -> list[str]:
    steps = action_config.get("steps")
    if not isinstance(steps, list):
        return []
    params: list[str] = []
    for step in steps[:MAX_PARAM_ITEMS]:
        if not isinstance(step, dict) or step.get("optional") is True:
            continue
        operation = str(step.get("op") or step.get("type") or step.get("action") or "").strip().lower()
        if operation not in VALUE_PARAM_SEQUENCE_OPERATIONS:
            continue
        if str(step.get("value") or "").strip():
            continue
        param = str(step.get("param") or step.get("parameter") or step.get("name") or "").strip()
        if param:
            params.append(param)
    return params


def _question_for_action(vertical_key: str, action_name: str, required_params: tuple[str, ...]) -> str:
    if required_params:
        return f"Please provide {', '.join(_humanize_param(param) for param in required_params)}."
    for question in intake_questions_for(vertical_key):
        actions = {normalize_action_name(action) for action in question.get("actions", [])}
        if action_name in actions:
            return str(question.get("question") or "")
    return ""


def _reason_for_action(vertical_key: str, action_name: str) -> str:
    for question in intake_questions_for(vertical_key):
        actions = {normalize_action_name(action) for action in question.get("actions", [])}
        if action_name in actions:
            return str(question.get("why") or "")
    return "Required before the website flow can be started safely."


def _schema_params(field_schema: Any) -> list[str]:
    if not isinstance(field_schema, list):
        return []
    return [str(item.get("param") or "").strip() for item in field_schema[:MAX_PARAM_ITEMS] if isinstance(item, dict) and str(item.get("param") or "").strip()]


def _clean_param_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item or "").strip() for item in value[:MAX_PARAM_ITEMS] if str(item or "").strip()]


def _unique_params(params: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for param in params:
        key = _param_key(param)
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(param)
    return rows[:MAX_PARAM_ITEMS]


def _sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    action = normalize_action_name(str(row.get("action") or ""))
    if not get_action(action):
        return {}
    return {
        "action": action,
        "status": _clean_text(row.get("status"), 80) or "unknown",
        "required_params": _clean_param_list(row.get("required_params")),
        "optional_params": _clean_param_list(row.get("optional_params")),
        "question": _clean_text(row.get("question"), 240),
        "reason": _clean_text(row.get("reason"), 240),
    }


def _param_key(value: str) -> str:
    return "_".join(part for part in _humanize_param(value).lower().split() if part)


def _humanize_param(value: str) -> str:
    return " ".join(part for part in str(value or "").replace("_", " ").replace("-", " ").split() if part)


def _clean_text(value: Any, limit: int) -> str:
    return str(value or "").replace("\x00", "").replace("\n", " ").strip()[:limit]
