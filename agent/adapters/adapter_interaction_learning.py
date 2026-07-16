"""Infer adapter actions from privacy-safe browser interaction events."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from agent.actions.registry import get_action, normalize_action_name
from agent.verticals.discovery_profiles import get_discovery_profile, merged_action_labels

INTERACTION_CLICK = "click"
INTERACTION_SUBMIT = "submit"
INTERACTION_SOURCE = "browser_interaction"
MIN_CONFIG_CONFIDENCE = 0.65
BASE_CLICK_CONFIDENCE = 0.45
BASE_SUBMIT_CONFIDENCE = 0.5
EXACT_LABEL_CONFIDENCE = 0.92
CONTAINED_LABEL_CONFIDENCE = 0.82
TOKEN_MATCH_CONFIDENCE = 0.74
PRIMARY_ACTION_BONUS = 0.03
FORM_ACTION_FALLBACK_CONFIDENCE = 0.62
MAX_LABEL_TEXT_LENGTH = 300
MAX_FIELD_PARAM_LENGTH = 60
SKIPPED_FIELD_TYPES = {"button", "checkbox", "file", "hidden", "image", "radio", "reset", "submit"}


def enrich_interaction_event(event: dict[str, Any], vertical_key: str) -> dict[str, Any]:
    """Return an interaction event with vertical-aware action inference attached."""
    clean_event = dict(event)
    inference = infer_interaction_action(clean_event, vertical_key)
    clean_event["vertical_key"] = inference["vertical_key"]
    clean_event["inferred_action"] = inference["action"]
    clean_event["inference_confidence"] = inference["confidence"]
    clean_event["matched_label"] = inference["matched_label"]
    return clean_event


def infer_interaction_action(event: dict[str, Any], vertical_key: str) -> dict[str, Any]:
    """Infer the best known action for a click or submit event."""
    profile = get_discovery_profile(vertical_key)
    best_action = ""
    best_label = ""
    best_score = 0.0
    event_text = _interaction_text(event)
    event_type = _text(event.get("event_type"))
    form_action = normalize_action_name(profile.form_action)

    for action_name, labels in merged_action_labels(profile).items():
        normalized_action = normalize_action_name(action_name)
        if not _action_allowed_for_event(normalized_action, event_type, form_action):
            continue
        score, label = _best_label_score(event_text, labels)
        if normalized_action in profile.primary_actions and score:
            score = min(score + PRIMARY_ACTION_BONUS, 1.0)
        if score > best_score and get_action(normalized_action):
            best_action = normalized_action
            best_label = label
            best_score = score

    if not best_action and event_type == INTERACTION_SUBMIT:
        best_action = form_action
        best_score = FORM_ACTION_FALLBACK_CONFIDENCE if get_action(best_action) else 0.0

    return {
        "vertical_key": profile.key,
        "action": best_action,
        "confidence": _bounded_confidence(best_score),
        "matched_label": best_label,
    }


def candidate_from_interaction(event: dict[str, Any]) -> dict[str, Any]:
    """Build a CRM-visible candidate row from a learned interaction."""
    event_type = _text(event.get("event_type"))
    if event_type == INTERACTION_CLICK:
        return _click_candidate(event)
    if event_type == INTERACTION_SUBMIT:
        return _submit_candidate(event)
    return {}


def action_config_from_interaction(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return a safe adapter action config when the interaction is high-confidence."""
    action_name = normalize_action_name(_text(event.get("inferred_action")))
    action = get_action(action_name)
    confidence = _bounded_confidence(event.get("inference_confidence"))
    if not action or confidence < MIN_CONFIG_CONFIDENCE:
        return "", {}

    if event.get("event_type") == INTERACTION_CLICK:
        return _click_action_config(event, action_name, confidence)
    if event.get("event_type") == INTERACTION_SUBMIT and action.family == "lead":
        return _submit_action_config(event, action_name, confidence)
    return "", {}


def _action_allowed_for_event(action_name: str, event_type: str, form_action: str) -> bool:
    action = get_action(action_name)
    if not action:
        return False
    if event_type != INTERACTION_SUBMIT:
        return True
    return action.name == form_action or action.family in {"commerce", "discovery", "lead", "tool"}


def _click_candidate(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "observed_click",
        "action": _text(event.get("inferred_action")),
        "type": "click",
        "label": _text(event.get("label")),
        "selector": _text(event.get("selector")),
        "path": _text(event.get("href")),
        "confidence": _candidate_confidence(event, BASE_CLICK_CONFIDENCE),
        "source": INTERACTION_SOURCE,
        "matched_label": _text(event.get("matched_label")),
    }


def _submit_candidate(event: dict[str, Any]) -> dict[str, Any]:
    form = _dict(event.get("form"))
    fields = [_field_label(field) for field in _list(form.get("fields"))]
    return {
        "kind": "observed_form",
        "action": _text(event.get("inferred_action")),
        "type": "sequence",
        "label": _text(event.get("label")),
        "selector": _text(form.get("selector") or event.get("selector")),
        "confidence": _candidate_confidence(event, BASE_SUBMIT_CONFIDENCE),
        "source": INTERACTION_SOURCE,
        "fields": [field for field in fields if field],
        "matched_label": _text(event.get("matched_label")),
    }


def _click_action_config(event: dict[str, Any], action_name: str, confidence: float) -> tuple[str, dict[str, Any]]:
    selector = _text(event.get("selector"))
    path = _same_origin_path(_text(event.get("href")), _text(event.get("origin")))
    if selector:
        return action_name, _base_action_config("click", event, confidence, selector=selector)
    if path:
        return action_name, _base_action_config("navigate", event, confidence, path=path)
    return "", {}


def _submit_action_config(event: dict[str, Any], action_name: str, confidence: float) -> tuple[str, dict[str, Any]]:
    form = _dict(event.get("form"))
    steps = [_field_step(field) for field in _list(form.get("fields"))]
    clean_steps = [step for step in steps if step]
    if not clean_steps:
        return "", {}
    config = _base_action_config("sequence", event, confidence, selector=_text(form.get("selector")))
    config["steps"] = clean_steps
    config["fields"] = sorted({step["param"] for step in clean_steps if step.get("param")})
    config["submit_mode"] = "fill_only"
    return action_name, config


def _base_action_config(action_type: str, event: dict[str, Any], confidence: float, **target: str) -> dict[str, Any]:
    config = {
        "type": action_type,
        "label": _text(event.get("label")),
        "source": INTERACTION_SOURCE,
        "confidence": confidence,
        "note": "Learned from browser interaction evidence.",
    }
    config.update({key: value for key, value in target.items() if value})
    return config


def _field_step(field: Any) -> dict[str, Any]:
    row = _dict(field)
    selector = _text(row.get("selector"))
    field_type = _text(row.get("type")).lower()
    if not selector or field_type in SKIPPED_FIELD_TYPES:
        return {}
    operation = "select" if field_type == "select" else "fill"
    return {"op": operation, "selector": selector, "param": _field_param(row), "optional": True}


def _interaction_text(event: dict[str, Any]) -> str:
    form = _dict(event.get("form"))
    fields = " ".join(_field_label(field) for field in _list(form.get("fields")))
    return _normalize_phrase(
        " ".join(
            [
                _text(event.get("label")),
                _text(event.get("selector")),
                _text(event.get("href")),
                _text(form.get("selector")),
                fields,
            ]
        )
    )


def _best_label_score(event_text: str, labels: tuple[str, ...]) -> tuple[float, str]:
    best_score = 0.0
    best_label = ""
    for label in labels:
        score = _label_score(event_text, _normalize_phrase(label))
        if score > best_score:
            best_score = score
            best_label = label
    return best_score, best_label


def _label_score(event_text: str, label: str) -> float:
    if not event_text or not label:
        return 0.0
    if event_text == label:
        return EXACT_LABEL_CONFIDENCE
    if f" {label} " in f" {event_text} ":
        return CONTAINED_LABEL_CONFIDENCE
    label_tokens = set(label.split())
    event_tokens = set(event_text.split())
    if label_tokens and label_tokens.issubset(event_tokens):
        return TOKEN_MATCH_CONFIDENCE
    return 0.0


def _field_param(field: dict[str, Any]) -> str:
    source = _field_label(field) or "value"
    normalized = re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")
    return normalized[:MAX_FIELD_PARAM_LENGTH] or "value"


def _field_label(field: Any) -> str:
    row = _dict(field)
    return _text(row.get("name") or row.get("placeholder"))


def _same_origin_path(href: str, origin: str) -> str:
    if not href:
        return ""
    if href.startswith("/"):
        return href
    parsed = urlparse(href)
    if not parsed.scheme or not parsed.netloc:
        return ""
    if origin and f"{parsed.scheme}://{parsed.netloc}".lower() != origin.lower().rstrip("/"):
        return ""
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    if parsed.fragment:
        path = f"{path}#{parsed.fragment}"
    return path


def _candidate_confidence(event: dict[str, Any], fallback: float) -> float:
    confidence = _bounded_confidence(event.get("inference_confidence"))
    return confidence or fallback


def _bounded_confidence(value: Any) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(number, 1.0)), 2)


def _normalize_phrase(value: Any) -> str:
    text = _text(value).lower()[:MAX_LABEL_TEXT_LENGTH]
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()
