"""Server-side website flow discovery for universal client onboarding."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
import httpx

import config

from agent.adapters.adapter_discovery import (
    ObservedElement,
    classify_vertical,
    discover_actions,
    discover_routes,
    parse_discovery_input,
)
from agent.flows.flow_barriers import build_flow_barrier_report
from agent.flows.flow_discovery_payload import combined_discovery_payload
from agent.flows.flow_html_snapshot import (
    FlowHtmlParser,
    base_url as _html_base_url,
    barrier_hints_from_html,
    clean_snapshot,
    clean_text,
    css_token,
    external_host,
    host_label,
    path_from_url as _html_path_from_url,
    platform_hints_from_html,
    provider_matches,
    safe_barrier_hints,
    safe_element,
    safe_elements,
    same_origin_elements,
    same_origin_url,
    snapshot_from_html,
    static_selector,
)
from agent.flows.flow_report_builder import (
    FlowAction, FlowPage, FlowReport,
    adapter_actions_from_flow as _adapter_actions_from_flow,
    empty_report as _empty_report,
    flow_actions as _flow_actions,
    flow_pages as _flow_pages,
    flow_summary as _flow_summary,
    prompt_suggestions as _prompt_suggestions,
)
from agent.flows.flow_url_discovery import parse_robots_disallow as _parse_robots_disallow
from agent.flows.flow_url_discovery import parse_sitemap_urls as _parse_sitemap_urls
from agent.flows.flow_url_discovery import prioritized_candidate_urls as _prioritized_candidate_urls
from agent.flows.flow_url_discovery import robots_disallow_paths as _robots_disallow_paths
from agent.flows.flow_url_discovery import sitemap_urls as _sitemap_urls
from agent.site_helpers.local_urls import local_runtime_url_candidates
from agent.verticals.registry import get_vertical

logger = logging.getLogger(__name__)

DEFAULT_FLOW_MAX_PAGES = 6
MAX_FLOW_PAGES = 20
FLOW_TIMEOUT_SECONDS = 12
HIGH_CONFIDENCE = 0.82
MEDIUM_CONFIDENCE = 0.66
LOW_CONFIDENCE = 0.45

COLLECT_PAGE_SCRIPT = """
() => {
  const clean = (value) => String(value || "").replace(/\\s+/g, " ").trim();
  const FIELD_SELECTOR = "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset']):not([type='image']), select, textarea";
  const MAX_FORM_FIELDS = 12;
  const MAX_FIELD_OPTIONS = 20;
  const cssEscape = (value) => window.CSS?.escape ? window.CSS.escape(value) : String(value).replace(/["\\\\]/g, "\\\\$&");
  const selectorFor = (element) => {
    if (!element || element.nodeType !== 1) return "";
    if (element.id) return `#${cssEscape(element.id)}`;
    for (const attr of ["data-testid", "data-test", "data-action", "aria-label", "name"]) {
      const value = element.getAttribute(attr);
      if (value) return `${element.tagName.toLowerCase()}[${attr}="${cssEscape(value)}"]`;
    }
    const classes = Array.from(element.classList || []).slice(0, 2);
    if (classes.length) return `${element.tagName.toLowerCase()}.${classes.map(cssEscape).join(".")}`;
    return element.tagName.toLowerCase();
  };
  const elementText = (element) => clean(element.innerText || element.value || element.getAttribute("aria-label"));
  const visibleElements = (elements) => Array.from(elements || []).filter((element) => {
    if (!element || element.hidden || element.getAttribute("aria-hidden") === "true") return false;
    const style = window.getComputedStyle?.(element);
    return !(style && (style.display === "none" || style.visibility === "hidden"));
  });
  const labelTextWithoutControls = (label) => {
    if (!label) return "";
    const clone = label.cloneNode(true);
    clone.querySelectorAll?.(`${FIELD_SELECTOR}, option`).forEach((node) => node.remove());
    return clean(clone.innerText || clone.textContent);
  };
  const explicitFieldLabel = (field) => {
    const id = field.id || field.getAttribute("id");
    if (!id) return "";
    return labelTextWithoutControls(document.querySelector(`label[for="${cssEscape(id)}"]`));
  };
  const wrappingFieldLabel = (field) => labelTextWithoutControls(field.closest?.("label"));
  const nearbyFieldLabel = (field) => {
    const containerLabel = field.parentElement?.querySelector?.("label");
    if (containerLabel && !containerLabel.contains(field)) return labelTextWithoutControls(containerLabel);
    const previous = field.previousElementSibling;
    if (clean(previous?.tagName).toLowerCase() === "label") return labelTextWithoutControls(previous);
    return "";
  };
  const fieldLabel = (field) => clean([
    explicitFieldLabel(field),
    wrappingFieldLabel(field),
    nearbyFieldLabel(field),
    field.getAttribute("aria-label"),
    field.getAttribute("title"),
  ].find(Boolean));
  const optionElements = (elements) => Array.from(elements || [])
    .slice(0, MAX_FIELD_OPTIONS)
    .map((option) => ({
      label: clean(option.label || option.innerText || option.textContent || option.getAttribute?.("aria-label")),
      value: clean(option.value || option.getAttribute?.("value") || option.getAttribute?.("data-value")),
    }))
    .filter((option) => option.label || option.value);
  const fieldOptions = (field) => {
    if (field.tagName?.toLowerCase() === "select") return optionElements(field.querySelectorAll("option"));
    const listId = field.getAttribute("list");
    if (listId) return optionElements(document.getElementById(listId)?.querySelectorAll("option"));
    return [];
  };
  const formFields = (form) => Array.from(form.querySelectorAll(FIELD_SELECTOR))
    .slice(0, MAX_FORM_FIELDS)
    .map((field) => ({
      selector: selectorFor(field),
      name: clean(field.getAttribute("name") || field.id || field.getAttribute("aria-label")),
      label: fieldLabel(field),
      type: clean(field.getAttribute("type") || field.tagName).toLowerCase(),
      placeholder: clean(field.getAttribute("placeholder")),
      autocomplete: clean(field.getAttribute("autocomplete")),
      required: Boolean(field.required || field.hasAttribute("required") || field.getAttribute("aria-required") === "true"),
      options: fieldOptions(field),
    }))
    .filter((field) => field.selector);
  const submitElementFor = (form) => {
    const explicit = visibleElements(form.querySelectorAll("button[type='submit'], input[type='submit'], input[type='image']")).at(0);
    if (explicit) return explicit;
    const buttons = visibleElements(form.querySelectorAll("button, input[type='button'], [role='button']"));
    const submitLike = buttons.find((button) => /\b(apply|book|calculate|check|checkout|compare|continue|estimate|find|get|join|next|order|pay|quote|quotes|request|reserve|save|schedule|search|send|show|submit)\b/i.test(elementText(button)));
    return submitLike || buttons.at(0) || null;
  };
  const hostFor = (value) => {
    try { return new URL(value, window.location.href).host; } catch (_err) { return ""; }
  };
  const pageText = clean(document.body?.innerText || "");
  const sourceText = Array.from(document.scripts || []).map((script) => script.src || "").join(" ").toLowerCase();
  const iframeSources = Array.from(document.querySelectorAll("iframe[src]")).slice(0, 20).map((iframe) => iframe.src || "").filter(Boolean);
  const externalActionHosts = Array.from(document.querySelectorAll("a[href]")).filter((element) => {
    const href = element.href || "";
    const text = elementText(element).toLowerCase();
    return href && hostFor(href) && hostFor(href) !== window.location.host && /(book|checkout|pay|apply|quote|claim|schedule|reserve)/i.test(text);
  }).map((element) => hostFor(element.href)).filter(Boolean).slice(0, 20);
  const providerText = `${pageText} ${sourceText} ${iframeSources.join(" ")} ${externalActionHosts.join(" ")}`.toLowerCase();
  const presentProviders = (providers) => providers.filter((provider) => provider[1].some((token) => providerText.includes(token))).map((provider) => provider[0]);
  const captchaProviders = presentProviders([
    ["recaptcha", ["recaptcha", "g-recaptcha", "google.com/recaptcha"]],
    ["hcaptcha", ["hcaptcha", "h-captcha"]],
    ["turnstile", ["turnstile", "challenges.cloudflare.com"]],
    ["cloudflare_challenge", ["cf-chl", "cloudflare challenge"]],
  ]);
  const links = Array.from(document.querySelectorAll("a[href]")).slice(0, 100).map((element) => ({
    label: elementText(element),
    selector: selectorFor(element),
    href: element.href || "",
  })).filter((item) => item.href);
  const buttons = Array.from(document.querySelectorAll("button, a, input[type='button'], input[type='submit']")).slice(0, 100).map((element) => ({
    label: elementText(element),
    selector: selectorFor(element),
    href: element.href || "",
  })).filter((item) => item.label || item.href);
  const forms = Array.from(document.querySelectorAll("form")).slice(0, 60).map((form) => {
    const input = form.querySelector("input[type='search'], input[name], input[placeholder], select, textarea");
    const submit = submitElementFor(form);
    return {
      label: clean([elementText(submit), form.innerText || input?.getAttribute("placeholder") || input?.getAttribute("name")].filter(Boolean).join(" ")),
      selector: selectorFor(form),
      input_selector: selectorFor(input),
      submit_selector: selectorFor(submit),
      fields: formFields(form),
    };
  }).filter((item) => item.input_selector);
  return {
    url: window.location.href,
    title: document.title || "",
    text_sample: pageText.slice(0, 2400),
    links,
    buttons,
    forms,
    platform_hints: {
      shopify: Boolean(window.Shopify || document.querySelector('script[src*="cdn.shopify.com"]')),
      woocommerce: Boolean(document.body?.classList?.contains("woocommerce") || window.wc_add_to_cart_params),
    },
    barrier_hints: {
      iframe_count: iframeSources.length,
      iframe_sources: iframeSources.slice(0, 8),
      password_inputs: document.querySelectorAll("input[type='password']").length,
      file_uploads: document.querySelectorAll("input[type='file']").length,
      date_inputs: document.querySelectorAll("input[type='date'], input[type='datetime-local'], input[type='time']").length,
      captcha: captchaProviders.length > 0 || Boolean(document.querySelector(".g-recaptcha, .h-captcha, [src*='recaptcha'], [src*='hcaptcha'], [src*='turnstile'], [class*='captcha' i]")) || providerText.includes("captcha"),
      captcha_providers: captchaProviders,
      payment_providers: presentProviders([
        ["stripe", ["stripe", "stripe.com", "checkout.stripe.com", "js.stripe.com"]],
        ["paypal", ["paypal", "paypal.com", "paypalobjects.com"]],
        ["razorpay", ["razorpay", "checkout.razorpay.com"]],
        ["paytm", ["paytm", "securegw.paytm.in"]],
        ["cashfree", ["cashfree", "cashfree.com"]],
        ["checkout.com", ["checkout.com", "cko-session-id"]],
        ["adyen", ["adyen", "checkoutshopper"]],
        ["square", ["squareup", "squarecdn", "square.site"]],
        ["braintree", ["braintree", "braintreegateway"]],
        ["mollie", ["mollie", "mollie.com"]],
        ["klarna", ["klarna", "klarna.com"]],
        ["afterpay", ["afterpay", "afterpay.com", "clearpay"]],
        ["payu", ["payu", "payu.in", "payu.com"]],
        ["paystack", ["paystack", "paystack.co"]],
        ["phonepe", ["phonepe", "phonepe.com"]],
        ["billdesk", ["billdesk", "billdesk.com"]],
        ["authorize.net", ["authorize.net", "accept.authorize.net"]],
      ]),
      calendar_providers: presentProviders([
        ["calendly", ["calendly", "calendly.com"]],
        ["acuity", ["acuityscheduling", "squarespace scheduling"]],
        ["booksy", ["booksy", "booksy.com"]],
        ["zocdoc", ["zocdoc", "zocdoc.com"]],
        ["appointlet", ["appointlet", "appointlet.com"]],
        ["setmore", ["setmore", "setmore.com"]],
        ["cal.com", ["cal.com", "calcom"]],
        ["google_calendar", ["calendar.google.com", "google calendar"]],
        ["microsoft_bookings", ["microsoft bookings", "outlook.office365.com/book"]],
        ["simplybook", ["simplybook", "simplybook.me"]],
        ["tidycal", ["tidycal", "tidycal.com"]],
        ["savvycal", ["savvycal", "savvycal.com"]],
        ["fresha", ["fresha", "fresha.com"]],
      ]),
      map_providers: presentProviders([
        ["google_maps", ["google.com/maps", "maps.googleapis", "maps.google"]],
        ["mapbox", ["mapbox", "mapbox.com"]],
        ["openstreetmap", ["openstreetmap", "osm.org"]],
        ["leaflet", ["leaflet", "leafletjs"]],
        ["here_maps", ["here.com", "hereapi", "wego.here.com"]],
        ["bing_maps", ["bing.com/maps", "virtualearth"]],
        ["mappls", ["mappls", "mapmyindia"]],
      ]),
      external_action_hosts: Array.from(new Set(externalActionHosts)),
    },
  };
}
"""


async def discover_site_flows(
    site_url: str,
    site_id: str,
    *,
    vertical_key: str = "",
    max_pages: int = DEFAULT_FLOW_MAX_PAGES,
    timeout: int = FLOW_TIMEOUT_SECONDS,
) -> FlowReport:
    """Discover pages, actions, routes, and prompt seeds from a live site."""
    start = time.monotonic()
    safe_max_pages = max(1, min(int(max_pages or DEFAULT_FLOW_MAX_PAGES), MAX_FLOW_PAGES))
    base_url = _base_url(site_url)
    snapshots: list[dict[str, Any]] = []
    engine = "http_fallback"
    discovered_base_url = base_url
    for candidate_base in local_runtime_url_candidates(base_url) or [base_url]:
        try:
            snapshots = await _discover_with_playwright(candidate_base, safe_max_pages, timeout)
            engine = "playwright"
        except Exception as exc:
            logger.info("Browser flow discovery fallback for %s: %s", site_id, exc)
            snapshots = await _discover_with_http(candidate_base, vertical_key, safe_max_pages, timeout)
            engine = "http_fallback"
        if snapshots:
            discovered_base_url = candidate_base
            break

    duration_ms = (time.monotonic() - start) * 1000
    return build_flow_report_from_snapshots(
        snapshots,
        site_id=site_id,
        site_url=discovered_base_url,
        requested_vertical_key=vertical_key,
        engine=engine,
        duration_ms=duration_ms,
    )


def build_flow_report_from_snapshots(
    snapshots: list[dict[str, Any]],
    *,
    site_id: str,
    site_url: str,
    requested_vertical_key: str = "",
    engine: str = "test",
    duration_ms: float = 0.0,
) -> FlowReport:
    """Build a deterministic flow report from page snapshots."""
    if not snapshots:
        return _empty_report(site_id, site_url, requested_vertical_key, engine, duration_ms)

    combined = combined_discovery_payload(snapshots, site_id, site_url)
    discovery_input = parse_discovery_input(combined)
    detected_vertical_key, confidence = classify_vertical(discovery_input)
    vertical_key = _valid_vertical_key(requested_vertical_key) or detected_vertical_key
    routes = discover_routes(discovery_input, vertical_key)
    adapter_actions = discover_actions(discovery_input, vertical_key, routes)
    flow_pages = _flow_pages(snapshots, routes)
    flow_actions = _flow_actions(snapshots, site_url, vertical_key, adapter_actions)
    merged_adapter_actions = _adapter_actions_from_flow(adapter_actions, flow_actions)
    prompt_suggestions = _prompt_suggestions(vertical_key, merged_adapter_actions, routes)
    barrier_report = build_flow_barrier_report(snapshots, site_id=site_id, site_url=site_url).to_dict()
    summary = _flow_summary(flow_pages, flow_actions, merged_adapter_actions, barrier_report)
    return FlowReport(
        site_id=site_id,
        site_url=site_url,
        vertical_key=vertical_key,
        detected_vertical_key=detected_vertical_key,
        confidence=confidence,
        engine=engine,
        pages=tuple(flow_pages),
        actions=tuple(flow_actions),
        routes=routes,
        adapter_actions=merged_adapter_actions,
        prompt_suggestions=tuple(prompt_suggestions),
        barriers=barrier_report,
        summary=summary,
        discovered_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=duration_ms,
    )


async def _discover_with_playwright(base_url: str, max_pages: int, timeout: int) -> list[dict[str, Any]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed.") from exc

    snapshots: list[dict[str, Any]] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        queue = [base_url]
        seen: set[str] = set()
        while queue and len(snapshots) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                await page.wait_for_timeout(350)
                snapshot = await page.evaluate(COLLECT_PAGE_SCRIPT)
            except Exception as exc:
                logger.debug("Flow browser page failed for %s: %s", url, exc)
                continue
            snapshots.append(_clean_snapshot(snapshot, base_url))
            for link in snapshot.get("links", []):
                href = _same_origin_url(link.get("href"), base_url)
                if href and href not in seen and href not in queue:
                    queue.append(href)
        await browser.close()
    return snapshots


async def _discover_with_http(
    base_url: str,
    vertical_key: str,
    max_pages: int,
    timeout: int,
) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        verify=config.CLIENT_TLS_VERIFY,
    ) as client:
        disallowed_paths = await _robots_disallow_paths(client, base_url)
        sitemap_urls = await _sitemap_urls(client, base_url, vertical_key)
        urls = _prioritized_candidate_urls(base_url, vertical_key, sitemap_urls, disallowed_paths)[:max_pages]
        for url in urls:
            try:
                response = await client.get(url, headers={"Accept": "text/html"})
            except (httpx.HTTPError, OSError, ValueError):
                continue
            if response.status_code >= 400 or "text/html" not in response.headers.get("content-type", ""):
                continue
            snapshots.append(_snapshot_from_html(str(response.url), response.text, base_url))
    return snapshots


def _snapshot_from_html(url: str, html_text: str, base_url: str) -> dict[str, Any]:
    return snapshot_from_html(url, html_text, base_url)


_FlowHtmlParser = FlowHtmlParser


def _clean_snapshot(snapshot: dict[str, Any], base_url: str) -> dict[str, Any]:
    return clean_snapshot(snapshot, base_url)


def _same_origin_elements(value: Any, base_url: str) -> list[dict[str, Any]]:
    return same_origin_elements(value, base_url)


def _safe_elements(value: Any) -> list[dict[str, Any]]:
    return safe_elements(value)


def _safe_element(value: Any) -> dict[str, Any]:
    return safe_element(value)


def _same_origin_url(value: Any, base_url: str) -> str:
    return same_origin_url(value, base_url)


def _base_url(site_url: str) -> str:
    return _html_base_url(site_url)


def _path_from_url(value: Any) -> str:
    return _html_path_from_url(value)


def _static_selector(tag: str, attrs: dict[str, str]) -> str:
    return static_selector(tag, attrs)


def _platform_hints_from_html(html_text: str) -> dict[str, bool]:
    return platform_hints_from_html(html_text)


def _barrier_hints_from_html(html_text: str, parser: _FlowHtmlParser) -> dict[str, Any]:
    return barrier_hints_from_html(html_text, parser)


def _safe_barrier_hints(value: Any) -> dict[str, Any]:
    return safe_barrier_hints(value)


def _provider_matches(text: str, signatures: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    return provider_matches(text, signatures)


def _external_host(href: str, base_url: str) -> str:
    return external_host(href, base_url)


def _valid_vertical_key(vertical_key: str) -> str:
    if not str(vertical_key or "").strip():
        return ""
    try:
        return get_vertical(vertical_key).key
    except ValueError:
        return ""


def _host_label(origin: str) -> str:
    return host_label(origin)


def _css_token(value: str) -> str:
    return css_token(value)


def _clean_text(value: Any) -> str:
    return clean_text(value)
