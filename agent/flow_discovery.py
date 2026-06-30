"""Server-side website flow discovery for universal client onboarding."""

from __future__ import annotations

import html
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from agent.adapter_discovery import form_submit_mode
from agent.adapter_discovery import (
    ObservedElement,
    classify_vertical,
    discover_actions,
    discover_routes,
    parse_form_fields,
    parse_discovery_input,
)
from agent.flow_barriers import build_flow_barrier_report
from agent.local_urls import local_runtime_url_candidates
from agent.verticals.discovery_profiles import (
    discovery_paths_for,
    get_discovery_profile,
    high_value_url_keywords_for,
    merged_action_labels,
    merged_route_actions,
)
from agent.verticals.registry import FALLBACK_VERTICAL_KEY, get_vertical

logger = logging.getLogger(__name__)

DEFAULT_FLOW_MAX_PAGES = 6
MAX_FLOW_PAGES = 20
MAX_FLOW_ELEMENTS = 100
MAX_FLOW_TEXT_CHARS = 2400
FLOW_TIMEOUT_SECONDS = 12
HIGH_CONFIDENCE = 0.82
MEDIUM_CONFIDENCE = 0.66
LOW_CONFIDENCE = 0.45
MAX_SITEMAP_URLS = 80
SITEMAP_PATHS = ("/sitemap.xml", "/sitemap_index.xml")
ROBOTS_PATH = "/robots.txt"
PAYMENT_PROVIDER_SIGNATURES = (
    ("stripe", ("stripe", "stripe.com", "checkout.stripe.com", "js.stripe.com")),
    ("paypal", ("paypal", "paypal.com", "paypalobjects.com")),
    ("razorpay", ("razorpay", "checkout.razorpay.com")),
    ("paytm", ("paytm", "securegw.paytm.in")),
    ("cashfree", ("cashfree", "cashfree.com")),
    ("checkout.com", ("checkout.com", "cko-session-id")),
    ("adyen", ("adyen", "checkoutshopper")),
    ("square", ("squareup", "squarecdn", "square.site")),
    ("braintree", ("braintree", "braintreegateway")),
    ("mollie", ("mollie", "mollie.com")),
    ("klarna", ("klarna", "klarna.com")),
    ("afterpay", ("afterpay", "afterpay.com", "clearpay")),
    ("payu", ("payu", "payu.in", "payu.com")),
    ("paystack", ("paystack", "paystack.co")),
    ("phonepe", ("phonepe", "phonepe.com")),
    ("billdesk", ("billdesk", "billdesk.com")),
    ("authorize.net", ("authorize.net", "accept.authorize.net")),
)
CALENDAR_PROVIDER_SIGNATURES = (
    ("calendly", ("calendly", "calendly.com")),
    ("acuity", ("acuityscheduling", "squarespace scheduling")),
    ("booksy", ("booksy", "booksy.com")),
    ("zocdoc", ("zocdoc", "zocdoc.com")),
    ("appointlet", ("appointlet", "appointlet.com")),
    ("setmore", ("setmore", "setmore.com")),
    ("cal.com", ("cal.com", "calcom")),
    ("google_calendar", ("calendar.google.com", "google calendar")),
    ("microsoft_bookings", ("microsoft bookings", "outlook.office365.com/book")),
    ("simplybook", ("simplybook", "simplybook.me")),
    ("tidycal", ("tidycal", "tidycal.com")),
    ("savvycal", ("savvycal", "savvycal.com")),
    ("fresha", ("fresha", "fresha.com")),
)
MAP_PROVIDER_SIGNATURES = (
    ("google_maps", ("google.com/maps", "maps.googleapis", "maps.google")),
    ("mapbox", ("mapbox", "mapbox.com")),
    ("openstreetmap", ("openstreetmap", "osm.org")),
    ("leaflet", ("leaflet", "leafletjs")),
    ("here_maps", ("here.com", "hereapi", "wego.here.com")),
    ("bing_maps", ("bing.com/maps", "virtualearth")),
    ("mappls", ("mappls", "mapmyindia")),
)
CAPTCHA_PROVIDER_SIGNATURES = (
    ("recaptcha", ("recaptcha", "g-recaptcha", "google.com/recaptcha")),
    ("hcaptcha", ("hcaptcha", "h-captcha")),
    ("turnstile", ("turnstile", "challenges.cloudflare.com")),
    ("cloudflare_challenge", ("cf-chl", "cloudflare challenge")),
)

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

    combined = _combined_discovery_payload(snapshots, site_id, site_url)
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
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, verify=False) as client:
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
    parser = _FlowHtmlParser(url, base_url)
    parser.feed(html_text[:150_000])
    title = parser.title or _host_label(base_url)
    text_sample = re.sub(r"\s+", " ", parser.text).strip()[:MAX_FLOW_TEXT_CHARS]
    return {
        "url": url,
        "title": title,
        "text_sample": text_sample,
        "links": parser.links[:MAX_FLOW_ELEMENTS],
        "buttons": parser.buttons[:MAX_FLOW_ELEMENTS],
        "forms": parser.forms[:MAX_FLOW_ELEMENTS],
        "platform_hints": _platform_hints_from_html(html_text),
        "barrier_hints": _barrier_hints_from_html(html_text, parser),
    }


class _FlowHtmlParser(HTMLParser):
    def __init__(self, page_url: str, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.forms: list[dict[str, Any]] = []
        self.iframe_sources: list[str] = []
        self.script_sources: list[str] = []
        self.external_action_hosts: list[str] = []
        self.password_inputs = 0
        self.file_uploads = 0
        self.date_inputs = 0
        self.text_parts: list[str] = []
        self.title = ""
        self._tag_stack: list[dict[str, str]] = []
        self._current_link: dict[str, str] | None = None
        self._current_button: dict[str, str] | None = None
        self._current_form: dict[str, Any] | None = None
        self._labels_by_for: dict[str, str] = {}
        self._current_label_for = ""
        self._current_label_text: list[str] | None = None
        self._last_label_text = ""
        self._current_select_field: dict[str, Any] | None = None
        self._current_option: dict[str, str] | None = None
        self._inside_title = False

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name.lower(): value or "" for name, value in attrs}
        self._tag_stack.append({"tag": tag, **attr})
        if tag == "title":
            self._inside_title = True
        if tag == "label":
            self._current_label_for = attr.get("for", "")
            self._current_label_text = []
        if tag == "script" and attr.get("src"):
            self.script_sources.append(urljoin(self.page_url, attr.get("src", "")))
        if tag == "iframe" and attr.get("src"):
            self.iframe_sources.append(urljoin(self.page_url, attr.get("src", "")))
        if tag == "input":
            input_type = attr.get("type", "").lower()
            if input_type == "password":
                self.password_inputs += 1
            if input_type == "file":
                self.file_uploads += 1
            if input_type in {"date", "datetime-local", "time"}:
                self.date_inputs += 1
        if tag == "a" and attr.get("href"):
            href = urljoin(self.page_url, attr.get("href", ""))
            self._record_external_action_host(href, attr.get("aria-label") or attr.get("title") or "")
            self._current_link = {
                "label": "",
                "selector": _static_selector(tag, attr),
                "href": href,
            }
        if tag in {"button"} or (tag == "input" and attr.get("type") in {"button", "submit"}):
            self._current_button = {
                "label": attr.get("aria-label") or attr.get("value") or "",
                "selector": _static_selector(tag, attr),
                "href": "",
            }
        if tag == "form":
            self._current_form = {
                "label": attr.get("aria-label") or attr.get("name") or "",
                "selector": _static_selector(tag, attr),
                "input_selector": "",
                "submit_selector": "",
                "fields": [],
            }
        if self._current_form and tag in {"input", "select", "textarea"}:
            if self._should_record_field(tag, attr):
                field = self._field_from_attrs(tag, attr)
                self._current_form["fields"].append(field)
                if tag == "select":
                    self._current_select_field = field
            if not self._current_form.get("input_selector"):
                self._current_form["input_selector"] = _static_selector(tag, attr)
                self._current_form["label"] = self._current_form.get("label") or attr.get("placeholder") or attr.get("name") or ""
        if self._current_form and tag in {"button", "input"} and not self._current_form.get("submit_selector"):
            if tag == "button" or attr.get("type") == "submit":
                self._current_form["submit_selector"] = _static_selector(tag, attr)
        if tag == "option" and self._current_select_field is not None:
            self._current_option = {
                "label": attr.get("label", ""),
                "value": attr.get("value", ""),
            }

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        if tag == "option" and self._current_option is not None:
            option = self._clean_option(self._current_option)
            if option and self._current_select_field is not None:
                self._current_select_field.setdefault("options", []).append(option)
            self._current_option = None
        if tag == "select":
            self._current_select_field = None
        if tag == "label" and self._current_label_text is not None:
            text = re.sub(r"\s+", " ", " ".join(self._current_label_text)).strip()
            if text:
                self._last_label_text = text
                if self._current_label_for:
                    self._labels_by_for[self._current_label_for] = text
                if self._current_form and not self._current_label_for and self._current_form.get("fields"):
                    last_field = self._current_form["fields"][-1]
                    if not last_field.get("label"):
                        last_field["label"] = text
            self._current_label_for = ""
            self._current_label_text = None
        if tag == "a" and self._current_link:
            self.links.append(self._clean_element(self._current_link))
            self._current_link = None
        if tag == "button" and self._current_button:
            self.buttons.append(self._clean_element(self._current_button))
            self._current_button = None
        if tag == "form" and self._current_form:
            if self._current_form.get("input_selector"):
                self.forms.append(self._clean_form(self._current_form))
            self._current_form = None
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        clean_data = html.unescape(data or "").strip()
        if not clean_data:
            return
        if self._inside_title:
            self.title = f"{self.title} {clean_data}".strip()
            return
        self.text_parts.append(clean_data)
        if self._current_label_text is not None:
            self._current_label_text.append(clean_data)
        if self._current_option is not None:
            self._current_option["label"] = f"{self._current_option.get('label', '')} {clean_data}".strip()
        if self._current_link is not None:
            self._current_link["label"] = f"{self._current_link.get('label', '')} {clean_data}".strip()
            self._record_external_action_host(self._current_link.get("href", ""), clean_data)
        if self._current_button is not None:
            self._current_button["label"] = f"{self._current_button.get('label', '')} {clean_data}".strip()
        if self._current_form is not None and not self._current_form.get("label"):
            self._current_form["label"] = clean_data[:120]

    def _clean_element(self, element: dict[str, str]) -> dict[str, str]:
        return {key: re.sub(r"\s+", " ", str(value or "")).strip() for key, value in element.items()}

    def _clean_form(self, form: dict[str, Any]) -> dict[str, Any]:
        cleaned = {
            key: re.sub(r"\s+", " ", str(form.get(key) or "")).strip()
            for key in ("label", "selector", "input_selector", "submit_selector")
        }
        fields = [self._clean_field(field) for field in form.get("fields", []) if isinstance(field, dict)]
        cleaned["fields"] = [field for field in fields if field.get("selector")]
        return cleaned

    def _clean_field(self, field: dict[str, Any]) -> dict[str, Any]:
        row: dict[str, Any] = {
            key: re.sub(r"\s+", " ", str(field.get(key) or "")).strip()
            for key in ("selector", "name", "label", "type", "placeholder", "autocomplete")
        }
        row["required"] = bool(field.get("required"))
        options = [self._clean_option(option) for option in field.get("options", []) if isinstance(option, dict)]
        row["options"] = [option for option in options if option]
        return row

    def _clean_option(self, option: dict[str, str]) -> dict[str, str]:
        row = {
            key: re.sub(r"\s+", " ", str(option.get(key) or "")).strip()
            for key in ("label", "value")
        }
        return row if row.get("label") or row.get("value") else {}

    def _should_record_field(self, tag: str, attrs: dict[str, str]) -> bool:
        if tag != "input":
            return True
        return attrs.get("type", "text").lower() not in {"hidden", "submit", "button", "reset", "image"}

    def _field_from_attrs(self, tag: str, attrs: dict[str, str]) -> dict[str, Any]:
        input_type = attrs.get("type") if tag == "input" else tag
        field_id = attrs.get("id") or attrs.get("name") or ""
        label = (
            self._labels_by_for.get(attrs.get("id", ""))
            or self._labels_by_for.get(attrs.get("name", ""))
            or attrs.get("aria-label")
            or attrs.get("title")
            or (re.sub(r"\s+", " ", " ".join(self._current_label_text)).strip() if self._current_label_text else "")
            or attrs.get("placeholder")
            or self._last_label_text
            or attrs.get("name")
            or ""
        )
        self._last_label_text = ""
        return {
            "selector": _static_selector(tag, attrs),
            "name": field_id,
            "label": label,
            "type": input_type or "text",
            "placeholder": attrs.get("placeholder", ""),
            "autocomplete": attrs.get("autocomplete", ""),
            "required": "required" in attrs or attrs.get("aria-required") == "true",
            "options": [],
        }

    def _record_external_action_host(self, href: str, label: str) -> None:
        host = _external_host(href, self.base_url)
        if not host or host in self.external_action_hosts:
            return
        if re.search(r"book|checkout|pay|apply|quote|claim|schedule|reserve", label or "", re.IGNORECASE):
            self.external_action_hosts.append(host)


def _combined_discovery_payload(snapshots: list[dict[str, Any]], site_id: str, site_url: str) -> dict[str, Any]:
    first = snapshots[0]
    return {
        "site_id": site_id,
        "origin": site_url,
        "url": first.get("url") or site_url,
        "title": first.get("title") or "",
        "text_sample": " ".join(str(snapshot.get("text_sample") or "") for snapshot in snapshots)[:MAX_FLOW_TEXT_CHARS],
        "buttons": _merged_elements(snapshots, "buttons"),
        "links": _merged_elements(snapshots, "links"),
        "forms": _merged_elements(snapshots, "forms"),
        "platform_hints": _merged_platform_hints(snapshots),
    }


def _flow_pages(snapshots: list[dict[str, Any]], routes: dict[str, str]) -> list[FlowPage]:
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


def _flow_actions(
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


def _adapter_actions_from_flow(
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


def _should_keep_existing_action(existing: dict[str, Any], incoming: dict[str, Any]) -> bool:
    existing_score = _action_contract_score(existing)
    incoming_score = _action_contract_score(incoming)
    if existing_score != incoming_score:
        return existing_score > incoming_score
    return float(existing.get("confidence") or 0) >= float(incoming.get("confidence") or 0)


def _has_field_contract(action_config: dict[str, Any]) -> bool:
    return bool(
        action_config.get("field_schema")
        or action_config.get("fields")
        or action_config.get("required_fields")
        or action_config.get("steps")
    )


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


def _prompt_suggestions(vertical_key: str, actions: dict[str, dict[str, Any]], routes: dict[str, str]) -> list[str]:
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


def _flow_summary(
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


def _empty_report(site_id: str, site_url: str, vertical_key: str, engine: str, duration_ms: float) -> FlowReport:
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


def _candidate_urls(base_url: str, vertical_key: str) -> list[str]:
    paths = discovery_paths_for(vertical_key)
    keywords = set(high_value_url_keywords_for(vertical_key))
    urls = [base_url]
    urls.extend(urljoin(base_url, path) for path in paths)
    urls.extend(urljoin(base_url, f"/{keyword}") for keyword in sorted(keywords)[:8])
    return list(dict.fromkeys(urls))


def _prioritized_candidate_urls(
    base_url: str,
    vertical_key: str,
    sitemap_urls: list[str],
    disallowed_paths: list[str],
) -> list[str]:
    urls = [*sitemap_urls, *_candidate_urls(base_url, vertical_key)]
    allowed = [url for url in urls if _same_origin_url(url, base_url) and _robots_allowed(url, disallowed_paths)]
    keywords = tuple(high_value_url_keywords_for(vertical_key))
    sitemap_set = set(sitemap_urls)
    return sorted(dict.fromkeys(allowed), key=lambda url: _url_priority(url, base_url, keywords, sitemap_set))


async def _robots_disallow_paths(client: httpx.AsyncClient, base_url: str) -> list[str]:
    try:
        response = await client.get(urljoin(base_url, ROBOTS_PATH), headers={"Accept": "text/plain"})
    except (httpx.HTTPError, OSError, ValueError):
        return []
    if response.status_code >= 400:
        return []
    return _parse_robots_disallow(response.text)


async def _sitemap_urls(client: httpx.AsyncClient, base_url: str, vertical_key: str) -> list[str]:
    urls: list[str] = []
    keywords = tuple(high_value_url_keywords_for(vertical_key))
    for path in SITEMAP_PATHS:
        try:
            response = await client.get(urljoin(base_url, path), headers={"Accept": "application/xml,text/xml,text/plain"})
        except (httpx.HTTPError, OSError, ValueError):
            continue
        if response.status_code >= 400:
            continue
        urls.extend(_parse_sitemap_urls(response.text, base_url, keywords))
    return list(dict.fromkeys(urls))[:MAX_SITEMAP_URLS]


def _parse_robots_disallow(robots_text: str) -> list[str]:
    paths: list[str] = []
    active = False
    for raw_line in str(robots_text or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            active = value == "*"
            continue
        if active and key == "disallow" and value:
            paths.append(value)
    return paths[:MAX_SITEMAP_URLS]


def _parse_sitemap_urls(sitemap_text: str, base_url: str, keywords: tuple[str, ...]) -> list[str]:
    urls: list[str] = []
    for match in re.findall(r"<loc>\s*(.*?)\s*</loc>", str(sitemap_text or ""), flags=re.IGNORECASE | re.DOTALL):
        url = html.unescape(match.strip())
        same_origin = _same_origin_url(url, base_url)
        if same_origin and _is_high_value_url(same_origin, keywords):
            urls.append(same_origin)
    return urls[:MAX_SITEMAP_URLS]


def _robots_allowed(url: str, disallowed_paths: list[str]) -> bool:
    path = urlparse(url).path or "/"
    for raw_path in disallowed_paths:
        rule = str(raw_path or "").strip()
        if rule and rule != "/" and path.startswith(rule.rstrip("*")):
            return False
        if rule == "/":
            return False
    return True


def _url_priority(url: str, base_url: str, keywords: tuple[str, ...], sitemap_urls: set[str]) -> tuple[int, str]:
    if url.rstrip("/") == base_url.rstrip("/"):
        return (0, url)
    if url in sitemap_urls and _is_high_value_url(url, keywords):
        return (1, url)
    return (2 if _is_high_value_url(url, keywords) else 3, url)


def _is_high_value_url(url: str, keywords: tuple[str, ...]) -> bool:
    path = urlparse(url).path.lower()
    return any(keyword.replace(" ", "-").lower() in path for keyword in keywords)


def _unique_actions(actions: list[FlowAction]) -> list[FlowAction]:
    best: dict[tuple[str, str, str, str], FlowAction] = {}
    for action in actions:
        key = (action.action_name, action.action_type, action.path or action.selector or action.input, action.page_url)
        current = best.get(key)
        if current is None or action.confidence > current.confidence:
            best[key] = action
    return sorted(best.values(), key=lambda item: (item.action_name, -item.confidence))[:MAX_FLOW_ELEMENTS]


def _merged_elements(snapshots: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for snapshot in snapshots:
        for item in snapshot.get(key, []) or []:
            element = _safe_element(item)
            identity = (element.get("label", ""), element.get("href", ""), element.get("selector", ""))
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(element)
    return merged[:MAX_FLOW_ELEMENTS]


def _merged_platform_hints(snapshots: list[dict[str, Any]]) -> dict[str, bool]:
    hints: dict[str, bool] = {}
    for snapshot in snapshots:
        raw_hints = snapshot.get("platform_hints") if isinstance(snapshot.get("platform_hints"), dict) else {}
        for key, value in raw_hints.items():
            hints[key] = bool(hints.get(key) or value)
    return hints


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


def _clean_snapshot(snapshot: dict[str, Any], base_url: str) -> dict[str, Any]:
    return {
        "url": _same_origin_url(snapshot.get("url"), base_url) or base_url,
        "title": _clean_text(snapshot.get("title"))[:180],
        "text_sample": _clean_text(snapshot.get("text_sample"))[:MAX_FLOW_TEXT_CHARS],
        "links": _same_origin_elements(snapshot.get("links"), base_url),
        "buttons": _safe_elements(snapshot.get("buttons")),
        "forms": _safe_elements(snapshot.get("forms")),
        "platform_hints": snapshot.get("platform_hints") if isinstance(snapshot.get("platform_hints"), dict) else {},
        "barrier_hints": _safe_barrier_hints(snapshot.get("barrier_hints")),
    }


def _same_origin_elements(value: Any, base_url: str) -> list[dict[str, Any]]:
    elements = _safe_elements(value)
    return [element for element in elements if _same_origin_url(element.get("href"), base_url)]


def _safe_elements(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    elements: list[dict[str, Any]] = []
    for item in value[:MAX_FLOW_ELEMENTS]:
        element = _safe_element(item)
        if element:
            elements.append(element)
    return elements


def _safe_element(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    element: dict[str, Any] = {
        key: _clean_text(value.get(key))[:500]
        for key in ("label", "selector", "href", "input_selector", "submit_selector")
    }
    fields = [dict(field) for field in parse_form_fields(value.get("fields"))]
    if fields:
        element["fields"] = fields
    return element


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


def _base_url(site_url: str) -> str:
    parsed = urlparse(str(site_url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        parsed = urlparse(f"https://{site_url}")
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _path_from_url(value: Any) -> str:
    try:
        parsed = urlparse(str(value or ""))
    except ValueError:
        return ""
    return f"{parsed.path or '/'}{('?' + parsed.query) if parsed.query else ''}"


def _static_selector(tag: str, attrs: dict[str, str]) -> str:
    if attrs.get("id"):
        return f"#{_css_token(attrs['id'])}"
    for key in ("data-testid", "data-test", "data-action", "aria-label", "name"):
        if attrs.get(key):
            return f'{tag}[{key}="{_css_token(attrs[key])}"]'
    class_text = attrs.get("class", "").strip()
    if class_text:
        classes = ".".join(_css_token(part) for part in class_text.split()[:2])
        return f"{tag}.{classes}" if classes else tag
    if attrs.get("href") and tag == "a":
        return f'a[href="{_css_token(attrs["href"])}"]'
    return tag


def _platform_hints_from_html(html_text: str) -> dict[str, bool]:
    lower = html_text.lower()
    return {
        "shopify": "cdn.shopify.com" in lower or "shopify-section" in lower,
        "woocommerce": "woocommerce" in lower or "wc_add_to_cart_params" in lower,
    }


def _barrier_hints_from_html(html_text: str, parser: _FlowHtmlParser) -> dict[str, Any]:
    lower = html_text.lower()
    provider_text = " ".join([lower, *parser.iframe_sources, *parser.script_sources, *parser.external_action_hosts])
    captcha_providers = _provider_matches(provider_text, CAPTCHA_PROVIDER_SIGNATURES)
    return _safe_barrier_hints(
        {
            "iframe_count": len(parser.iframe_sources),
            "iframe_sources": parser.iframe_sources[:8],
            "password_inputs": parser.password_inputs,
            "file_uploads": parser.file_uploads,
            "date_inputs": parser.date_inputs,
            "captcha": bool(captcha_providers) or "captcha" in provider_text,
            "captcha_providers": captcha_providers,
            "payment_providers": _provider_matches(provider_text, PAYMENT_PROVIDER_SIGNATURES),
            "calendar_providers": _provider_matches(provider_text, CALENDAR_PROVIDER_SIGNATURES),
            "map_providers": _provider_matches(provider_text, MAP_PROVIDER_SIGNATURES),
            "external_action_hosts": parser.external_action_hosts[:20],
        }
    )


def _safe_barrier_hints(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    hints: dict[str, Any] = {}
    for key in ("iframe_count", "password_inputs", "file_uploads", "date_inputs"):
        hints[key] = max(0, int(value.get(key) or 0))
    hints["captcha"] = bool(value.get("captcha"))
    for key in ("iframe_sources", "captcha_providers", "payment_providers", "calendar_providers", "map_providers", "external_action_hosts"):
        raw_items = value.get(key)
        items = raw_items if isinstance(raw_items, list) else []
        hints[key] = [_clean_text(item)[:240] for item in items[:20] if _clean_text(item)]
    return hints


def _provider_matches(text: str, signatures: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    return [name for name, tokens in signatures if any(token in text for token in tokens)][:10]


def _external_host(href: str, base_url: str) -> str:
    try:
        parsed_href = urlparse(href)
        parsed_base = urlparse(base_url)
    except ValueError:
        return ""
    if parsed_href.scheme not in {"http", "https"} or not parsed_href.netloc:
        return ""
    if parsed_href.netloc == parsed_base.netloc:
        return ""
    return parsed_href.netloc[:160]


def _valid_vertical_key(vertical_key: str) -> str:
    if not str(vertical_key or "").strip():
        return ""
    try:
        return get_vertical(vertical_key).key
    except ValueError:
        return ""


def _host_label(origin: str) -> str:
    parsed = urlparse(origin)
    return parsed.netloc.replace("www.", "") if parsed.netloc else ""


def _css_token(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')[:120]


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
