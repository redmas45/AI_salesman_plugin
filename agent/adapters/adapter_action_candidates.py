"""Admin-reviewable adapter action candidate generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


MAX_FIELD_SCHEMA_OPTIONS = 20
MEDIUM_CONFIDENCE = 0.66
LOW_CONFIDENCE = 0.35


class ObservedControl(Protocol):
    label: str
    selector: str
    href: str
    fields: tuple[dict[str, Any], ...]


class CandidateDiscoveryInput(Protocol):
    origin: str
    buttons: tuple[ObservedControl, ...]
    forms: tuple[ObservedControl, ...]


@dataclass(frozen=True)
class CandidateDependencies:
    clean_text: Callable[[Any], str]
    path_from_href: Callable[[str, str], str]
    form_fields_text: Callable[[ObservedControl], str]
    form_is_rejected_for_action: Callable[[str, ObservedControl], bool]
    field_param_names: Callable[[tuple[dict[str, Any], ...]], list[str]]
    action_required_field_params: Callable[[ObservedControl, str], list[str]]
    form_field_schema: Callable[[tuple[dict[str, Any], ...], list[str] | None], list[dict[str, Any]]]


def generated_action_candidates(
    actions: dict[str, dict[str, Any]],
    deps: CandidateDependencies,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action_name, config in sorted(actions.items()):
        rows.append(
            {
                "kind": "generated_action",
                "action": action_name,
                "type": deps.clean_text(config.get("type") or ""),
                "label": deps.clean_text(config.get("label") or action_name.replace("_", " ").title()),
                "selector": deps.clean_text(config.get("selector") or config.get("input") or config.get("form")),
                "path": deps.clean_text(config.get("path")),
                "confidence": safe_confidence(config.get("confidence"), MEDIUM_CONFIDENCE),
                "source": deps.clean_text(config.get("source") or "adapter_discovery"),
                "fields": safe_field_list(config.get("fields"), deps.clean_text),
                "required_fields": safe_field_list(config.get("required_fields"), deps.clean_text),
                "required_fields_known": bool(config.get("required_fields_known") is True),
                "field_schema": safe_field_schema(config.get("field_schema"), deps.clean_text),
            }
        )
    return rows


def button_action_candidates(
    data: CandidateDiscoveryInput,
    labels_by_action: dict[str, tuple[str, ...]],
    deps: CandidateDependencies,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for button in data.buttons:
        action_name, confidence = likely_action_for_label(button.label, labels_by_action, deps.clean_text)
        rows.append(
            {
                "kind": "button",
                "action": action_name,
                "type": "click",
                "label": button.label,
                "selector": button.selector,
                "path": deps.path_from_href(button.href, data.origin),
                "confidence": confidence,
                "source": "browser_button",
            }
        )
    return rows


def form_action_candidates(
    data: CandidateDiscoveryInput,
    labels_by_action: dict[str, tuple[str, ...]],
    deps: CandidateDependencies,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for form in data.forms:
        action_name, confidence = likely_action_for_label(
            " ".join([form.label, deps.form_fields_text(form)]),
            labels_by_action,
            deps.clean_text,
        )
        if deps.form_is_rejected_for_action(action_name, form):
            action_name = ""
            confidence = LOW_CONFIDENCE
        required_fields = deps.action_required_field_params(form, action_name)
        rows.append(
            {
                "kind": "form",
                "action": action_name,
                "type": "sequence" if form.fields else "form",
                "label": form.label,
                "selector": form.selector,
                "confidence": confidence,
                "source": "browser_form",
                "fields": deps.field_param_names(form.fields),
                "required_fields": required_fields,
                "required_fields_known": bool(form.fields),
                "field_schema": deps.form_field_schema(form.fields, required_fields),
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
    clean_text: Callable[[Any], str],
) -> tuple[str, float]:
    text = clean_text(label).lower()
    if not text:
        return "", LOW_CONFIDENCE
    for action_name, labels in labels_by_action.items():
        if any(value in text for value in labels):
            return action_name, MEDIUM_CONFIDENCE
    return "", LOW_CONFIDENCE


def dedupe_candidates(
    candidates: list[dict[str, Any]],
    clean_text: Callable[[Any], str],
) -> list[dict[str, Any]]:
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


def unique_texts(values: list[str], limit: int, clean_text: Callable[[Any], str]) -> list[str]:
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


def safe_field_list(value: Any, clean_text: Callable[[Any], str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_text(item)[:80] for item in value[:20] if clean_text(item)]


def safe_field_schema(value: Any, clean_text: Callable[[Any], str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = [safe_field_schema_item(item, clean_text) for item in value[:20] if isinstance(item, dict)]
    return [row for row in rows if row]


def safe_field_schema_item(item: dict[str, Any], clean_text: Callable[[Any], str]) -> dict[str, Any]:
    param = clean_text(item.get("param"))[:80]
    if not param:
        return {}
    row: dict[str, Any] = {"param": param, "required": bool(item.get("required") is True)}
    for key in ("label", "type", "autocomplete"):
        value = clean_text(item.get(key))[:120]
        if value:
            row[key] = value
    options = safe_field_options(item.get("options"), clean_text)
    if options:
        row["options"] = options
    return row


def safe_field_options(value: Any, clean_text: Callable[[Any], str]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows = [safe_field_option(item, clean_text) for item in value[:MAX_FIELD_SCHEMA_OPTIONS]]
    return [row for row in rows if row]


def safe_field_option(item: Any, clean_text: Callable[[Any], str]) -> dict[str, str]:
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
