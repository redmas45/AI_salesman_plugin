"""Flow rehearsal models, action specs, and summary helpers."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from agent.actions.registry import get_action, normalize_action_name

DEFAULT_REHEARSAL_MAX_STEPS = 24
MAX_REHEARSAL_STEPS = 80
REHEARSAL_TIMEOUT_SECONDS = 12

LOW_CONFIDENCE = 0.35
MEDIUM_CONFIDENCE = 0.62
HIGH_CONFIDENCE = 0.88

LEAD_ACTION_PREFIXES = (
    "START_",
    "REQUEST_",
    "CAPTURE_",
    "BOOK_",
    "JOIN_",
)
FINALIZATION_ACTIONS = {
    "CHECKOUT",
    "CHECKOUT_HANDOFF",
    "SCHEDULE_ORDER",
    "START_APPLICATION",
    "START_BOOKING",
    "START_TICKET_PURCHASE",
    "START_QUOTE",
    "OPEN_CLAIM_FLOW",
    "OPEN_RENEWAL_FLOW",
}


@dataclass(frozen=True)
class FlowRehearsalStep:
    """One safely checked action target."""

    action_name: str
    action_type: str
    page_url: str
    target: str = ""
    status: str = "unknown"
    supported: bool = False
    safe_to_execute: bool = False
    requires_confirmation: bool = False
    risk_level: str = "low"
    confidence: float = LOW_CONFIDENCE
    evidence: str = ""
    blocker: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confidence"] = round(self.confidence, 2)
        return data


@dataclass(frozen=True)
class FlowRehearsalReport:
    """Safe flow rehearsal evidence saved for one client."""

    site_id: str
    site_url: str
    engine: str
    steps: tuple[FlowRehearsalStep, ...] = ()
    summary: dict[str, Any] = field(default_factory=dict)
    rehearsed_at: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "site_url": self.site_url,
            "engine": self.engine,
            "steps": [step.to_dict() for step in self.steps],
            "summary": self.summary,
            "rehearsed_at": self.rehearsed_at,
            "duration_ms": round(self.duration_ms, 1),
        }


def build_static_report(
    flow_report: dict[str, Any],
    *,
    site_id: str = "",
    site_url: str = "",
    engine: str = "static",
    duration_ms: float = 0.0,
) -> FlowRehearsalReport:
    base_url = base_url_from(site_url) or base_url_from(flow_report.get("site_url"))
    specs = action_specs_from_flow(flow_report, base_url)
    steps = [static_step(spec) for spec in specs]
    return FlowRehearsalReport(
        site_id=str(site_id or flow_report.get("site_id") or ""),
        site_url=base_url,
        engine=engine,
        steps=tuple(steps),
        summary=summary(steps),
        rehearsed_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=max(0.0, float(duration_ms or 0.0)),
    )


def static_step(spec: dict[str, Any]) -> FlowRehearsalStep:
    if spec["type"] == "navigate":
        if not spec.get("target"):
            return blocked_step(spec, "missing_target", "Navigation action has no path.")
        return supported_step(
            spec,
            status="static_route_recorded",
            confidence=MEDIUM_CONFIDENCE,
            evidence="Same-origin route was recorded by flow discovery; live navigation is pending.",
        )
    if spec["type"] in {"click", "form"} and target_selectors(spec):
        if spec["type"] == "form" and not spec.get("input"):
            return blocked_step(spec, "missing_input", "Generated form action has no input selector.")
        status = "static_selector_recorded" if spec["type"] == "click" else "static_prepare_only"
        return supported_step(
            spec,
            status=status,
            confidence=MEDIUM_CONFIDENCE,
            evidence="Selector was recorded by flow discovery; live browser rehearsal is pending.",
        )
    return blocked_step(spec, "missing_target", "No safe target was recorded for this action.")


def supported_step(
    spec: dict[str, Any],
    *,
    status: str,
    confidence: float,
    evidence: str,
) -> FlowRehearsalStep:
    policy = action_policy(spec["name"], spec["type"])
    return FlowRehearsalStep(
        action_name=spec["name"],
        action_type=spec["type"],
        page_url=spec["page_url"],
        target=str(spec.get("target") or ""),
        status=status,
        supported=True,
        safe_to_execute=True,
        requires_confirmation=policy["requires_confirmation"],
        risk_level=policy["risk_level"],
        confidence=confidence,
        evidence=evidence,
    )


def blocked_step(spec: dict[str, Any], status: str, blocker: str) -> FlowRehearsalStep:
    policy = action_policy(spec["name"], spec["type"])
    return FlowRehearsalStep(
        action_name=spec["name"],
        action_type=spec["type"],
        page_url=spec["page_url"],
        target=str(spec.get("target") or ""),
        status=status,
        supported=False,
        safe_to_execute=False,
        requires_confirmation=policy["requires_confirmation"],
        risk_level=policy["risk_level"],
        confidence=LOW_CONFIDENCE,
        evidence="Rehearsal could not verify a safe executable target.",
        blocker=blocker,
    )


def action_specs_from_flow(flow_report: dict[str, Any], base_url: str) -> list[dict[str, Any]]:
    if not isinstance(flow_report, dict):
        return []
    action_pages = action_pages_from_flow(flow_report.get("actions"), base_url)
    adapter_actions = flow_report.get("adapter_actions")
    specs: list[dict[str, Any]] = []
    if isinstance(adapter_actions, dict):
        for raw_name, raw_config in adapter_actions.items():
            spec = spec_from_config(raw_name, raw_config, action_pages, base_url)
            if spec:
                specs.append(spec)
    if not specs:
        specs.extend(
            spec_from_flow_action(action, base_url)
            for action in flow_report.get("actions") or []
            if isinstance(action, dict)
        )
    return unique_specs(spec for spec in specs if spec)


def spec_from_config(
    raw_name: Any,
    raw_config: Any,
    action_pages: dict[str, str],
    base_url: str,
) -> dict[str, Any]:
    if not isinstance(raw_config, dict):
        return {}
    action_name = normalize_action_name(str(raw_name or ""))
    action_type = str(raw_config.get("type") or "").strip().lower()
    page_url = same_origin_url(action_pages.get(action_name), base_url) or base_url
    target = target_from_config(action_type, raw_config, base_url)
    if not action_name or action_type not in {"navigate", "click", "form"}:
        return {}
    return {
        "name": action_name,
        "type": action_type,
        "page_url": page_url,
        "target": target,
        "selector": str(raw_config.get("selector") or ""),
        "form": str(raw_config.get("form") or ""),
        "input": str(raw_config.get("input") or ""),
        "submit": str(raw_config.get("submit") or ""),
    }


def spec_from_flow_action(action: dict[str, Any], base_url: str) -> dict[str, Any]:
    action_type = str(action.get("action_type") or action.get("type") or "").strip().lower()
    config = {
        "type": action_type,
        "path": action.get("path"),
        "selector": action.get("selector"),
        "form": action.get("form"),
        "input": action.get("input"),
        "submit": action.get("submit"),
    }
    spec = spec_from_config(action.get("action_name") or action.get("name"), config, {}, base_url)
    if spec:
        spec["page_url"] = same_origin_url(action.get("page_url"), base_url) or base_url
    return spec


def target_from_config(action_type: str, config: dict[str, Any], base_url: str) -> str:
    if action_type == "navigate":
        return same_origin_url(config.get("path"), base_url)
    if action_type == "click":
        return str(config.get("selector") or "")
    if action_type == "form":
        return str(config.get("form") or config.get("input") or "")
    return ""


def target_selectors(spec: dict[str, Any]) -> list[str]:
    if spec["type"] == "click":
        return [str(spec.get("selector") or "").strip()] if spec.get("selector") else []
    if spec["type"] == "form":
        selectors = [str(spec.get("input") or "").strip()]
        selectors.extend(str(spec.get(key) or "").strip() for key in ("form", "submit"))
        return [selector for selector in selectors if selector]
    return []


def action_pages_from_flow(raw_actions: Any, base_url: str) -> dict[str, str]:
    if not isinstance(raw_actions, list):
        return {}
    pages: dict[str, str] = {}
    for action in raw_actions:
        if not isinstance(action, dict):
            continue
        action_name = normalize_action_name(str(action.get("action_name") or ""))
        page_url = same_origin_url(action.get("page_url"), base_url)
        if action_name and page_url and action_name not in pages:
            pages[action_name] = page_url
    return pages


def unique_specs(specs: Any) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        key = (spec["name"], spec["type"], str(spec.get("target") or ""))
        unique.setdefault(key, spec)
    return list(unique.values())[:MAX_REHEARSAL_STEPS]


def action_policy(action_name: str, action_type: str) -> dict[str, Any]:
    name = normalize_action_name(action_name)
    action = get_action(name)
    family = action.family if action else ""
    is_final = name in FINALIZATION_ACTIONS or family in {"commerce", "lead"}
    is_lead = family == "lead" or name.startswith(LEAD_ACTION_PREFIXES)
    requires_confirmation = bool(is_final or is_lead or action_type == "form")
    risk_level = "high" if name in FINALIZATION_ACTIONS else "medium" if requires_confirmation else "low"
    return {"requires_confirmation": requires_confirmation, "risk_level": risk_level}


def report(
    site_id: str,
    site_url: str,
    engine: str,
    steps: list[FlowRehearsalStep],
    start: float,
) -> FlowRehearsalReport:
    duration_ms = (time.monotonic() - start) * 1000
    return FlowRehearsalReport(
        site_id=str(site_id or ""),
        site_url=site_url,
        engine=engine,
        steps=tuple(steps),
        summary=summary(steps),
        rehearsed_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=duration_ms,
    )


def summary(steps: list[FlowRehearsalStep]) -> dict[str, Any]:
    total = len(steps)
    supported = sum(1 for step in steps if step.supported)
    safe = sum(1 for step in steps if step.safe_to_execute)
    needs_confirmation = sum(1 for step in steps if step.requires_confirmation)
    blocked = total - supported
    return {
        "total": total,
        "supported": supported,
        "safe": safe,
        "needs_confirmation": needs_confirmation,
        "blocked": blocked,
        "success_rate": round(supported / total, 2) if total else 0.0,
    }


def base_url_from(site_url: Any) -> str:
    parsed = urlparse(str(site_url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        parsed = urlparse(f"https://{site_url}")
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def same_origin_url(value: Any, base_url: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        url = urljoin(base_url, text)
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
    except ValueError:
        return ""
    if parsed_url.scheme not in {"http", "https"}:
        return ""
    if parsed_url.netloc != parsed_base.netloc:
        return ""
    query = f"?{parsed_url.query}" if parsed_url.query else ""
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path or '/'}{query}"
