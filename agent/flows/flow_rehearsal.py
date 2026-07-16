"""Safe rehearsal for discovered website flows.

Flow discovery maps possible routes/actions. Rehearsal verifies those targets
without submitting forms, completing payments, or finishing regulated flows.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

import config

from agent.flows import flow_rehearsal_specs
from agent.flows.flow_rehearsal_specs import (
    DEFAULT_REHEARSAL_MAX_STEPS,
    HIGH_CONFIDENCE,
    LOW_CONFIDENCE,
    MAX_REHEARSAL_STEPS,
    MEDIUM_CONFIDENCE,
    REHEARSAL_TIMEOUT_SECONDS,
    FlowRehearsalReport,
    FlowRehearsalStep,
)
from agent.site_helpers.local_urls import local_runtime_url_candidates

logger = logging.getLogger(__name__)


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
    return flow_rehearsal_specs.build_static_report(
        flow_report,
        site_id=site_id,
        site_url=site_url,
        engine=engine,
        duration_ms=duration_ms,
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
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        verify=config.CLIENT_TLS_VERIFY,
    ) as client:
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


_static_step = flow_rehearsal_specs.static_step
_supported_step = flow_rehearsal_specs.supported_step
_blocked_step = flow_rehearsal_specs.blocked_step
_action_specs_from_flow = flow_rehearsal_specs.action_specs_from_flow
_spec_from_config = flow_rehearsal_specs.spec_from_config
_spec_from_flow_action = flow_rehearsal_specs.spec_from_flow_action
_target_from_config = flow_rehearsal_specs.target_from_config
_target_selectors = flow_rehearsal_specs.target_selectors
_action_pages = flow_rehearsal_specs.action_pages_from_flow
_unique_specs = flow_rehearsal_specs.unique_specs
_action_policy = flow_rehearsal_specs.action_policy
_report = flow_rehearsal_specs.report
_summary = flow_rehearsal_specs.summary
_base_url = flow_rehearsal_specs.base_url_from
_same_origin_url = flow_rehearsal_specs.same_origin_url
