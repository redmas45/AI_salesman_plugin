"""Build flow discovery reports from captured page snapshots."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from agent.adapters.adapter_discovery import form_submit_mode
from agent.verticals.discovery_profiles import (
    get_discovery_profile,
    merged_action_labels,
    merged_route_actions,
)
from agent.verticals.registry import FALLBACK_VERTICAL_KEY, get_vertical

MAX_FLOW_ELEMENTS = 100
HIGH_CONFIDENCE = 0.82
MEDIUM_CONFIDENCE = 0.66
LOW_CONFIDENCE = 0.45


@dataclass(frozen=True)
class FlowAction:
    """One discovered action candidate in a client website flow."""

    action_name: str
    action_type: str
    page_url: str
    label: str = ""
    selector: str = ""
    path: str = ""
    form: str = ""
    input: str = ""
    submit: str = ""
    confidence: float = LOW_CONFIDENCE
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FlowPage:
    """One page visited by flow discovery."""

    url: str
    title: str = ""
    text_sample: str = ""
    link_count: int = 0
    button_count: int = 0
    form_count: int = 0
    route_names: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FlowReport:
    """Full flow graph evidence saved for one client."""

    site_id: str
    site_url: str
    vertical_key: str
    detected_vertical_key: str
    confidence: float
    engine: str
    pages: tuple[FlowPage, ...] = ()
    actions: tuple[FlowAction, ...] = ()
    routes: dict[str, str] = field(default_factory=dict)
    adapter_actions: dict[str, dict[str, Any]] = field(default_factory=dict)
    prompt_suggestions: tuple[str, ...] = ()
    barriers: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    discovered_at: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "site_url": self.site_url,
            "vertical_key": self.vertical_key,
            "detected_vertical_key": self.detected_vertical_key,
            "confidence": round(self.confidence, 2),
            "engine": self.engine,
            "pages": [page.to_dict() for page in self.pages],
            "actions": [action.to_dict() for action in self.actions],
            "routes": dict(self.routes),
            "adapter_actions": self.adapter_actions,
            "prompt_suggestions": list(self.prompt_suggestions),
            "barriers": self.barriers,
            "summary": self.summary,
            "discovered_at": self.discovered_at,
            "duration_ms": round(self.duration_ms, 1),
        }


def flow_pages(snapshots: list[dict[str, Any]], routes: dict[str, str]) -> list[FlowPage]:
    pages: list[FlowPage] = []
    for snapshot in snapshots:
        page_path = _path_from_url(snapshot.get("url"))
        route_names = tuple(name for name, path in routes.items() if path == page_path)
        pages.append(
            FlowPage(
                url=str(snapshot.get("url") or ""),
                title=str(snapshot.get("title") or ""),
                text_sample=str(snapshot.get("text_sample") or "")[:240],
                link_count=len(snapshot.get("links") or []),
                button_count=len(snapshot.get("buttons") or []),
                form_count=len(snapshot.get("forms") or []),
                route_names=route_names,
            )
        )
    return pages


def flow_actions(
    snapshots: list[dict[str, Any]],
    site_url: str,
    vertical_key: str,
    adapter_actions: dict[str, dict[str, Any]],
) -> list[FlowAction]:
    profile = get_discovery_profile(vertical_key)
    labels_by_action = merged_action_labels(profile)
    route_actions = merged_route_actions(profile)
    actions: list[FlowAction] = []
    for snapshot in snapshots:
        page_url = str(snapshot.get("url") or site_url)
        actions.extend(_link_actions(snapshot.get("links") or [], page_url, site_url, profile.route_keywords, route_actions))
        actions.extend(_button_actions(snapshot.get("buttons") or [], page_url, labels_by_action))
        actions.extend(_form_actions(snapshot.get("forms") or [], page_url, labels_by_action, profile.form_action))
    actions.extend(_configured_actions(adapter_actions, snapshots[0].get("url") if snapshots else site_url))
    return _unique_actions(actions)


def adapter_actions_from_flow(
    base_actions: dict[str, dict[str, Any]],
    flow_actions: list[FlowAction],
) -> dict[str, dict[str, Any]]:
    adapter_actions = dict(base_actions)
    for action in sorted(flow_actions, key=lambda item: item.confidence, reverse=True):
        existing = adapter_actions.get(action.action_name)
        config = _action_config(action)
        if config:
            if existing and _should_keep_existing_action(existing, config):
                continue
            adapter_actions[action.action_name] = config
    return adapter_actions


def prompt_suggestions(vertical_key: str, actions: dict[str, dict[str, Any]], routes: dict[str, str]) -> list[str]:
    vertical = get_vertical(vertical_key)
    suggestions = [
        f"Show me the best {vertical.entity_label_plural} for my needs.",
        f"Compare available {vertical.entity_label_plural} for me.",
        f"What should I know before choosing a {vertical.entity_label_singular}?",
    ]
    for action_name in sorted(actions)[:5]:
        suggestions.append(f"Help me {action_name.lower().replace('_', ' ')}.")
    for route_name in sorted(route for route in routes if route not in {"home", "privacy", "login"})[:3]:
        suggestions.append(f"Take me to {route_name.replace('_', ' ')}.")
    return list(dict.fromkeys(suggestions))[:10]


def flow_summary(
    pages: list[FlowPage],
    actions: list[FlowAction],
    adapter_actions: dict[str, dict[str, Any]],
    barriers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    barrier_summary = barriers.get("summary") if isinstance(barriers, dict) and isinstance(barriers.get("summary"), dict) else {}
    return {
        "pages": len(pages),
        "actions": len(actions),
        "adapter_actions": len(adapter_actions),
        "forms": sum(page.form_count for page in pages),
        "links": sum(page.link_count for page in pages),
        "buttons": sum(page.button_count for page in pages),
        "barriers": int(barrier_summary.get("total") or 0),
        "high_barriers": int(barrier_summary.get("high") or 0),
    }


def empty_report(site_id: str, site_url: str, vertical_key: str, engine: str, duration_ms: float) -> FlowReport:
    safe_vertical_key = _valid_vertical_key(vertical_key) or FALLBACK_VERTICAL_KEY
    return FlowReport(
        site_id=site_id,
        site_url=site_url,
        vertical_key=safe_vertical_key,
        detected_vertical_key=FALLBACK_VERTICAL_KEY,
        confidence=0.0,
        engine=engine,
        discovered_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=duration_ms,
    )


def _link_actions(
    links: list[dict[str, Any]],
    page_url: str,
    site_url: str,
    route_keywords: dict[str, tuple[str, ...]],
    route_actions: dict[str, str],
) -> list[FlowAction]:
    actions: list[FlowAction] = []
    for link in links:
        href = _same_origin_url(link.get("href"), site_url)
        if not href:
            continue
        label = _clean_text(link.get("label"))
        route_name = _matched_route(label, href, route_keywords)
        action_name = route_actions.get(route_name or "", "NAVIGATE_TO")
        actions.append(
            FlowAction(
                action_name=action_name,
                action_type="navigate",
                page_url=page_url,
                label=label,
                selector=_clean_text(link.get("selector")),
                path=_path_from_url(href),
                confidence=MEDIUM_CONFIDENCE if route_name else LOW_CONFIDENCE,
                evidence=f"Same-origin link matched route '{route_name or 'navigation'}'.",
            )
        )
    return actions


def _button_actions(
    buttons: list[dict[str, Any]],
    page_url: str,
    labels_by_action: dict[str, tuple[str, ...]],
) -> list[FlowAction]:
    actions: list[FlowAction] = []
    for button in buttons:
        label = _clean_text(button.get("label"))
        if not label:
            continue
        action_name = _matched_action(label, labels_by_action)
        if not action_name:
            continue
        actions.append(
            FlowAction(
                action_name=action_name,
                action_type="click",
                page_url=page_url,
                label=label,
                selector=_clean_text(button.get("selector")),
                confidence=HIGH_CONFIDENCE,
                evidence="Button label matched vertical action vocabulary.",
            )
        )
    return actions


def _form_actions(
    forms: list[dict[str, Any]],
    page_url: str,
    labels_by_action: dict[str, tuple[str, ...]],
    fallback_action: str,
) -> list[FlowAction]:
    actions: list[FlowAction] = []
    for form in forms:
        label = _clean_text(form.get("label"))
        action_name = _matched_action(label, labels_by_action) or fallback_action
        actions.append(
            FlowAction(
                action_name=action_name,
                action_type="form",
                page_url=page_url,
                label=label,
                form=_clean_text(form.get("selector")),
                input=_clean_text(form.get("input_selector")),
                submit=_clean_text(form.get("submit_selector")),
                confidence=MEDIUM_CONFIDENCE,
                evidence="Form can be filled safely by generated adapter before user confirmation.",
            )
        )
    return actions


def _configured_actions(adapter_actions: dict[str, dict[str, Any]], page_url: str) -> list[FlowAction]:
    actions: list[FlowAction] = []
    for action_name, config in adapter_actions.items():
        actions.append(
            FlowAction(
                action_name=action_name,
                action_type=str(config.get("type") or "generated"),
                page_url=page_url,
                label=str(config.get("label") or ""),
                selector=str(config.get("selector") or ""),
                path=str(config.get("path") or ""),
                form=str(config.get("form") or ""),
                input=str(config.get("input") or ""),
                submit=str(config.get("submit") or ""),
                confidence=float(config.get("confidence") or MEDIUM_CONFIDENCE),
                evidence="Existing generated adapter action included in flow graph.",
            )
        )
    return actions


def _should_keep_existing_action(existing: dict[str, Any], incoming: dict[str, Any]) -> bool:
    existing_score = _action_contract_score(existing)
    incoming_score = _action_contract_score(incoming)
    if existing_score != incoming_score:
        return existing_score > incoming_score
    return float(existing.get("confidence") or 0) >= float(incoming.get("confidence") or 0)


def _action_contract_score(action_config: dict[str, Any]) -> int:
    action_type = str(action_config.get("type") or "")
    steps = action_config.get("steps") if isinstance(action_config.get("steps"), list) else []
    fields = action_config.get("fields") if isinstance(action_config.get("fields"), list) else []
    required_fields = action_config.get("required_fields") if isinstance(action_config.get("required_fields"), list) else []
    field_schema = action_config.get("field_schema") if isinstance(action_config.get("field_schema"), list) else []
    param_steps = [step for step in steps if isinstance(step, dict) and step.get("param") and step.get("selector")]
    submit_steps = [step for step in steps if isinstance(step, dict) and step.get("op") == "submit" and step.get("selector")]

    type_score = {
        "sequence": 12,
        "form": 8,
        "navigate": 5,
        "click": 4,
        "handoff": 3,
    }.get(action_type, 1)
    score = type_score
    score += len(param_steps) * 6
    score += len(field_schema) * 5
    score += len(fields) * 4
    score += len(required_fields) * 2
    score += len(submit_steps)
    if action_config.get("required_fields_known") is True:
        score += 2
    if action_config.get("form") and action_config.get("input"):
        score += 3
    if action_config.get("selector") or action_config.get("path"):
        score += 1
    if action_type == "sequence" and steps and not param_steps:
        score -= 8
    return score


def _action_config(action: FlowAction) -> dict[str, Any]:
    config: dict[str, Any] = {"type": action.action_type, "confidence": round(action.confidence, 2), "source": "flow_discovery"}
    if action.action_type == "navigate" and action.path:
        config["path"] = action.path
    elif action.action_type == "click" and action.selector:
        config["selector"] = action.selector
        config["label"] = action.label
        config["page_path"] = _path_from_url(action.page_url)
    elif action.action_type == "form" and action.input:
        config["form"] = action.form
        config["input"] = action.input
        config["submit"] = action.submit
        config["label"] = action.label
        config["page_path"] = _path_from_url(action.page_url)
        config["submit_mode"] = form_submit_mode(action.action_name)
    else:
        return {}
    return config


def _unique_actions(actions: list[FlowAction]) -> list[FlowAction]:
    best: dict[tuple[str, str, str, str], FlowAction] = {}
    for action in actions:
        key = (action.action_name, action.action_type, action.path or action.selector or action.input, action.page_url)
        current = best.get(key)
        if current is None or action.confidence > current.confidence:
            best[key] = action
    return sorted(best.values(), key=lambda item: (item.action_name, -item.confidence))[:MAX_FLOW_ELEMENTS]


def _matched_route(label: str, href: str, route_keywords: dict[str, tuple[str, ...]]) -> str:
    haystack = f"{label} {_path_from_url(href)}".lower()
    for route_name, keywords in route_keywords.items():
        if any(keyword in haystack for keyword in keywords):
            return route_name
    return ""


def _matched_action(label: str, labels_by_action: dict[str, tuple[str, ...]]) -> str:
    haystack = label.lower()
    for action_name, labels in labels_by_action.items():
        if any(action_label in haystack for action_label in labels):
            return action_name
    return ""


def _same_origin_url(value: Any, base_url: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        url = urljoin(base_url, text)
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
    except ValueError:
        return ""
    if parsed_url.scheme not in {"http", "https"} or parsed_url.netloc != parsed_base.netloc:
        return ""
    return url


def _path_from_url(value: Any) -> str:
    try:
        parsed = urlparse(str(value or ""))
    except ValueError:
        return ""
    return f"{parsed.path or '/'}{('?' + parsed.query) if parsed.query else ''}"


def _valid_vertical_key(vertical_key: str) -> str:
    if not str(vertical_key or "").strip():
        return ""
    try:
        return get_vertical(vertical_key).key
    except ValueError:
        return ""


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
