"""Safe rehearsal for discovered website flows.

Flow discovery maps possible routes/actions. Rehearsal verifies those targets
without submitting forms, completing payments, or finishing regulated flows.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from agent.actions.registry import get_action, normalize_action_name
from agent.local_urls import local_runtime_url_candidates

logger = logging.getLogger(__name__)

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


async def rehearse_site_flows(
    site_url: str,
    site_id: str,
    flow_report: dict[str, Any],
    *,
    max_steps: int = DEFAULT_REHEARSAL_MAX_STEPS,
    timeout: int = REHEARSAL_TIMEOUT_SECONDS,
) -> FlowRehearsalReport:
    """Safely rehearse a saved flow report against the live client site."""
    start = time.monotonic()
    safe_max_steps = max(1, min(int(max_steps or DEFAULT_REHEARSAL_MAX_STEPS), MAX_REHEARSAL_STEPS))
    base_url = _base_url(site_url) or _base_url(flow_report.get("site_url"))
    candidates = local_runtime_url_candidates(base_url) or [base_url]

    steps: list[FlowRehearsalStep] = []
    engine = "empty"
    rehearsed_base_url = base_url
    for candidate_base in candidates:
        specs = _action_specs_from_flow(flow_report, candidate_base)[:safe_max_steps]
        if not specs:
            continue
        try:
            steps = await _rehearse_with_playwright(candidate_base, specs, timeout)
            engine = "playwright"
        except Exception as exc:
            logger.info("Browser flow rehearsal fallback for %s: %s", site_id, exc)
            steps = await _rehearse_with_http(candidate_base, specs, timeout)
            engine = "http_fallback"
        rehearsed_base_url = candidate_base
        if any(step.supported for step in steps):
            break

    return _report(site_id, rehearsed_base_url, engine, steps, start)


def build_rehearsal_report_from_flow(
    flow_report: dict[str, Any],
    *,
    site_id: str = "",
    site_url: str = "",
    engine: str = "static",
    duration_ms: float = 0.0,
) -> FlowRehearsalReport:
    """Build deterministic static rehearsal evidence from a flow report."""
    base_url = _base_url(site_url) or _base_url(flow_report.get("site_url"))
    specs = _action_specs_from_flow(flow_report, base_url)
    steps = [_static_step(spec) for spec in specs]
    return FlowRehearsalReport(
        site_id=str(site_id or flow_report.get("site_id") or ""),
        site_url=base_url,
        engine=engine,
        steps=tuple(steps),
        summary=_summary(steps),
        rehearsed_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=max(0.0, float(duration_ms or 0.0)),
    )


async def _rehearse_with_playwright(
    base_url: str,
    specs: list[dict[str, Any]],
    timeout: int,
) -> list[FlowRehearsalStep]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed.") from exc

    steps: list[FlowRehearsalStep] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        try:
            for spec in specs:
                if spec["type"] == "navigate":
                    steps.append(await _rehearse_navigation(page, base_url, spec, timeout))
                    continue
                steps.append(await _rehearse_dom_target(page, spec, timeout))
        finally:
            await browser.close()
    return steps


async def _rehearse_navigation(page: Any, base_url: str, spec: dict[str, Any], timeout: int) -> FlowRehearsalStep:
    target_url = _same_origin_url(spec.get("target"), base_url)
    if not target_url:
        return _blocked_step(spec, "external_target", "Navigation target is missing or external.")
    try:
        response = await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout * 1000)
    except Exception as exc:
        return _blocked_step(spec, "navigation_failed", f"Navigation failed during rehearsal: {exc}")
    status_code = response.status if response else 0
    if status_code and status_code >= 400:
        return _blocked_step(spec, "http_error", f"Navigation returned HTTP {status_code}.")
    return _supported_step(
        spec,
        status="verified",
        confidence=HIGH_CONFIDENCE,
        evidence="Same-origin navigation reached a live page without completing a final action.",
    )


async def _rehearse_dom_target(page: Any, spec: dict[str, Any], timeout: int) -> FlowRehearsalStep:
    try:
        await page.goto(spec["page_url"], wait_until="domcontentloaded", timeout=timeout * 1000)
    except Exception as exc:
        return _blocked_step(spec, "page_failed", f"Action page could not be loaded: {exc}")

    selectors = _target_selectors(spec)
    if not selectors:
        return _blocked_step(spec, "missing_selector", "No selector was generated for this action.")

    if spec["type"] == "form":
        input_selector = str(spec.get("input") or "").strip()
        if not input_selector:
            return _blocked_step(spec, "missing_input", "Generated form action has no input selector.")
        if not await _selector_exists(page, input_selector):
            return _blocked_step(
                spec,
                "missing_target",
                "Generated form input selector was not found on the rehearsed page.",
            )
        return _supported_step(
            spec,
            status="verified_prepare_only",
            confidence=HIGH_CONFIDENCE,
            evidence="Generated form input selector exists; rehearsal did not submit the form.",
        )

    found_selector = ""
    for selector in selectors:
        if not await _selector_exists(page, selector):
            continue
        found_selector = selector
        break

    if not found_selector:
        return _blocked_step(
            spec,
            "missing_target",
            "Generated selector was not found on the rehearsed page.",
        )

    status = "verified"
    evidence = "Generated selector exists on the rehearsed page; no click or submit was performed."
    confidence = HIGH_CONFIDENCE
    return _supported_step(spec, status=status, confidence=confidence, evidence=evidence)


async def _selector_exists(page: Any, selector: str) -> bool:
    try:
        locator = page.locator(selector)
        return await locator.count() > 0
    except Exception:
        return False


async def _rehearse_with_http(base_url: str, specs: list[dict[str, Any]], timeout: int) -> list[FlowRehearsalStep]:
    steps: list[FlowRehearsalStep] = []
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, verify=False) as client:
        for spec in specs:
            if spec["type"] == "navigate":
                steps.append(await _http_navigation_step(client, base_url, spec))
            else:
                steps.append(_static_step(spec))
    return steps


async def _http_navigation_step(client: httpx.AsyncClient, base_url: str, spec: dict[str, Any]) -> FlowRehearsalStep:
    target_url = _same_origin_url(spec.get("target"), base_url)
    if not target_url:
        return _blocked_step(spec, "external_target", "Navigation target is missing or external.")
    try:
        response = await client.get(target_url, headers={"Accept": "text/html"})
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return _blocked_step(spec, "navigation_failed", f"Navigation probe failed: {exc}")
    if response.status_code >= 400:
        return _blocked_step(spec, "http_error", f"Navigation returned HTTP {response.status_code}.")
    return _supported_step(
        spec,
        status="verified_http",
        confidence=MEDIUM_CONFIDENCE,
        evidence="Same-origin route responded successfully; DOM interaction requires browser validation.",
    )


def _static_step(spec: dict[str, Any]) -> FlowRehearsalStep:
    if spec["type"] == "navigate":
        if not spec.get("target"):
            return _blocked_step(spec, "missing_target", "Navigation action has no path.")
        return _supported_step(
            spec,
            status="static_route_recorded",
            confidence=MEDIUM_CONFIDENCE,
            evidence="Same-origin route was recorded by flow discovery; live navigation is pending.",
        )
    if spec["type"] in {"click", "form"} and _target_selectors(spec):
        if spec["type"] == "form" and not spec.get("input"):
            return _blocked_step(spec, "missing_input", "Generated form action has no input selector.")
        status = "static_selector_recorded" if spec["type"] == "click" else "static_prepare_only"
        return _supported_step(
            spec,
            status=status,
            confidence=MEDIUM_CONFIDENCE,
            evidence="Selector was recorded by flow discovery; live browser rehearsal is pending.",
        )
    return _blocked_step(spec, "missing_target", "No safe target was recorded for this action.")


def _supported_step(
    spec: dict[str, Any],
    *,
    status: str,
    confidence: float,
    evidence: str,
) -> FlowRehearsalStep:
    policy = _action_policy(spec["name"], spec["type"])
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


def _blocked_step(spec: dict[str, Any], status: str, blocker: str) -> FlowRehearsalStep:
    policy = _action_policy(spec["name"], spec["type"])
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


def _action_specs_from_flow(flow_report: dict[str, Any], base_url: str) -> list[dict[str, Any]]:
    if not isinstance(flow_report, dict):
        return []
    action_pages = _action_pages(flow_report.get("actions"), base_url)
    adapter_actions = flow_report.get("adapter_actions")
    specs: list[dict[str, Any]] = []
    if isinstance(adapter_actions, dict):
        for raw_name, raw_config in adapter_actions.items():
            spec = _spec_from_config(raw_name, raw_config, action_pages, base_url)
            if spec:
                specs.append(spec)
    if not specs:
        specs.extend(_spec_from_flow_action(action, base_url) for action in flow_report.get("actions") or [] if isinstance(action, dict))
    return _unique_specs(spec for spec in specs if spec)


def _spec_from_config(
    raw_name: Any,
    raw_config: Any,
    action_pages: dict[str, str],
    base_url: str,
) -> dict[str, Any]:
    if not isinstance(raw_config, dict):
        return {}
    action_name = normalize_action_name(str(raw_name or ""))
    action_type = str(raw_config.get("type") or "").strip().lower()
    page_url = _same_origin_url(action_pages.get(action_name), base_url) or base_url
    target = _target_from_config(action_type, raw_config, base_url)
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


def _spec_from_flow_action(action: dict[str, Any], base_url: str) -> dict[str, Any]:
    action_type = str(action.get("action_type") or action.get("type") or "").strip().lower()
    config = {
        "type": action_type,
        "path": action.get("path"),
        "selector": action.get("selector"),
        "form": action.get("form"),
        "input": action.get("input"),
        "submit": action.get("submit"),
    }
    spec = _spec_from_config(action.get("action_name") or action.get("name"), config, {}, base_url)
    if spec:
        spec["page_url"] = _same_origin_url(action.get("page_url"), base_url) or base_url
    return spec


def _target_from_config(action_type: str, config: dict[str, Any], base_url: str) -> str:
    if action_type == "navigate":
        return _same_origin_url(config.get("path"), base_url)
    if action_type == "click":
        return str(config.get("selector") or "")
    if action_type == "form":
        return str(config.get("form") or config.get("input") or "")
    return ""


def _target_selectors(spec: dict[str, Any]) -> list[str]:
    if spec["type"] == "click":
        return [str(spec.get("selector") or "").strip()] if spec.get("selector") else []
    if spec["type"] == "form":
        selectors = [str(spec.get("input") or "").strip()]
        selectors.extend(str(spec.get(key) or "").strip() for key in ("form", "submit"))
        return [selector for selector in selectors if selector]
    return []


def _action_pages(raw_actions: Any, base_url: str) -> dict[str, str]:
    if not isinstance(raw_actions, list):
        return {}
    pages: dict[str, str] = {}
    for action in raw_actions:
        if not isinstance(action, dict):
            continue
        action_name = normalize_action_name(str(action.get("action_name") or ""))
        page_url = _same_origin_url(action.get("page_url"), base_url)
        if action_name and page_url and action_name not in pages:
            pages[action_name] = page_url
    return pages


def _unique_specs(specs: Any) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        key = (spec["name"], spec["type"], str(spec.get("target") or ""))
        unique.setdefault(key, spec)
    return list(unique.values())[:MAX_REHEARSAL_STEPS]


def _action_policy(action_name: str, action_type: str) -> dict[str, Any]:
    name = normalize_action_name(action_name)
    action = get_action(name)
    family = action.family if action else ""
    is_final = name in FINALIZATION_ACTIONS or family in {"commerce", "lead"}
    is_lead = family == "lead" or name.startswith(LEAD_ACTION_PREFIXES)
    requires_confirmation = bool(is_final or is_lead or action_type == "form")
    risk_level = "high" if name in FINALIZATION_ACTIONS else "medium" if requires_confirmation else "low"
    return {"requires_confirmation": requires_confirmation, "risk_level": risk_level}


def _report(
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
        summary=_summary(steps),
        rehearsed_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=duration_ms,
    )


def _summary(steps: list[FlowRehearsalStep]) -> dict[str, Any]:
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


def _base_url(site_url: Any) -> str:
    parsed = urlparse(str(site_url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        parsed = urlparse(f"https://{site_url}")
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


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
    if parsed_url.scheme not in {"http", "https"}:
        return ""
    if parsed_url.netloc != parsed_base.netloc:
        return ""
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path or '/'}{('?' + parsed_url.query) if parsed_url.query else ''}"
