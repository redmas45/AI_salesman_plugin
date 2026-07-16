"""HTML fallback snapshot parsing for flow discovery."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from agent.adapters.adapter_discovery import parse_form_fields

MAX_FLOW_ELEMENTS = 100
MAX_FLOW_TEXT_CHARS = 2400
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
    ("payu", ("payu.in", "payu.com")),
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


def snapshot_from_html(url: str, html_text: str, base_url: str) -> dict[str, Any]:
    parser = FlowHtmlParser(url, base_url)
    parser.feed(html_text[:150_000])
    title = parser.title or host_label(base_url)
    text_sample = re.sub(r"\s+", " ", parser.text).strip()[:MAX_FLOW_TEXT_CHARS]
    return {
        "url": url,
        "title": title,
        "text_sample": text_sample,
        "links": parser.links[:MAX_FLOW_ELEMENTS],
        "buttons": parser.buttons[:MAX_FLOW_ELEMENTS],
        "forms": parser.forms[:MAX_FLOW_ELEMENTS],
        "platform_hints": platform_hints_from_html(html_text),
        "barrier_hints": barrier_hints_from_html(html_text, parser),
    }


class FlowHtmlParser(HTMLParser):
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
            self._record_input_type(attr)
        if tag == "a" and attr.get("href"):
            href = urljoin(self.page_url, attr.get("href", ""))
            self._record_external_action_host(href, attr.get("aria-label") or attr.get("title") or "")
            self._current_link = {"label": "", "selector": static_selector(tag, attr), "href": href}
        if tag in {"button"} or (tag == "input" and attr.get("type") in {"button", "submit"}):
            self._current_button = {
                "label": attr.get("aria-label") or attr.get("value") or "",
                "selector": static_selector(tag, attr),
                "href": "",
            }
        if tag == "form":
            self._current_form = {
                "label": attr.get("aria-label") or attr.get("name") or "",
                "selector": static_selector(tag, attr),
                "input_selector": "",
                "submit_selector": "",
                "fields": [],
            }
        self._record_form_child(tag, attr)
        if tag == "option" and self._current_select_field is not None:
            self._current_option = {"label": attr.get("label", ""), "value": attr.get("value", "")}

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
            self._finalize_label()
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

    def _record_input_type(self, attrs: dict[str, str]) -> None:
        input_type = attrs.get("type", "").lower()
        if input_type == "password":
            self.password_inputs += 1
        if input_type == "file":
            self.file_uploads += 1
        if input_type in {"date", "datetime-local", "time"}:
            self.date_inputs += 1

    def _record_form_child(self, tag: str, attrs: dict[str, str]) -> None:
        if self._current_form and tag in {"input", "select", "textarea"}:
            if self._should_record_field(tag, attrs):
                field = self._field_from_attrs(tag, attrs)
                self._current_form["fields"].append(field)
                if tag == "select":
                    self._current_select_field = field
            if not self._current_form.get("input_selector"):
                self._current_form["input_selector"] = static_selector(tag, attrs)
                self._current_form["label"] = (
                    self._current_form.get("label") or attrs.get("placeholder") or attrs.get("name") or ""
                )
        if self._current_form and tag in {"button", "input"} and not self._current_form.get("submit_selector"):
            if tag == "button" or attrs.get("type") == "submit":
                self._current_form["submit_selector"] = static_selector(tag, attrs)

    def _finalize_label(self) -> None:
        text = re.sub(r"\s+", " ", " ".join(self._current_label_text or [])).strip()
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
        row = {key: re.sub(r"\s+", " ", str(option.get(key) or "")).strip() for key in ("label", "value")}
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
            "selector": static_selector(tag, attrs),
            "name": field_id,
            "label": label,
            "type": input_type or "text",
            "placeholder": attrs.get("placeholder", ""),
            "autocomplete": attrs.get("autocomplete", ""),
            "required": "required" in attrs or attrs.get("aria-required") == "true",
            "options": [],
        }

    def _record_external_action_host(self, href: str, label: str) -> None:
        host = external_host(href, self.base_url)
        if not host or host in self.external_action_hosts:
            return
        if re.search(r"book|checkout|pay|apply|quote|claim|schedule|reserve", label or "", re.IGNORECASE):
            self.external_action_hosts.append(host)


def clean_snapshot(snapshot: dict[str, Any], base_url: str) -> dict[str, Any]:
    return {
        "url": same_origin_url(snapshot.get("url"), base_url) or base_url,
        "title": clean_text(snapshot.get("title"))[:180],
        "text_sample": clean_text(snapshot.get("text_sample"))[:MAX_FLOW_TEXT_CHARS],
        "links": same_origin_elements(snapshot.get("links"), base_url),
        "buttons": safe_elements(snapshot.get("buttons")),
        "forms": safe_elements(snapshot.get("forms")),
        "platform_hints": snapshot.get("platform_hints") if isinstance(snapshot.get("platform_hints"), dict) else {},
        "barrier_hints": safe_barrier_hints(snapshot.get("barrier_hints")),
    }


def same_origin_elements(value: Any, base_url: str) -> list[dict[str, Any]]:
    elements = safe_elements(value)
    return [element for element in elements if same_origin_url(element.get("href"), base_url)]


def safe_elements(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    elements: list[dict[str, Any]] = []
    for item in value[:MAX_FLOW_ELEMENTS]:
        element = safe_element(item)
        if element:
            elements.append(element)
    return elements


def safe_element(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    element: dict[str, Any] = {
        key: clean_text(value.get(key))[:500]
        for key in ("label", "selector", "href", "input_selector", "submit_selector")
    }
    fields = [dict(field) for field in parse_form_fields(value.get("fields"))]
    if fields:
        element["fields"] = fields
    return element


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


def base_url(site_url: str) -> str:
    parsed = urlparse(str(site_url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        parsed = urlparse(f"https://{site_url}")
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def path_from_url(value: Any) -> str:
    try:
        parsed = urlparse(str(value or ""))
    except ValueError:
        return ""
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.path or '/'}{query}"


def static_selector(tag: str, attrs: dict[str, str]) -> str:
    if attrs.get("id"):
        return f"#{css_token(attrs['id'])}"
    for key in ("data-testid", "data-test", "data-action", "aria-label", "name"):
        if attrs.get(key):
            return f'{tag}[{key}="{css_token(attrs[key])}"]'
    class_text = attrs.get("class", "").strip()
    if class_text:
        classes = ".".join(css_token(part) for part in class_text.split()[:2])
        return f"{tag}.{classes}" if classes else tag
    if attrs.get("href") and tag == "a":
        return f'a[href="{css_token(attrs["href"])}"]'
    return tag


def platform_hints_from_html(html_text: str) -> dict[str, bool]:
    lower = html_text.lower()
    return {
        "shopify": "cdn.shopify.com" in lower or "shopify-section" in lower,
        "woocommerce": "woocommerce" in lower or "wc_add_to_cart_params" in lower,
    }


def barrier_hints_from_html(html_text: str, parser: FlowHtmlParser) -> dict[str, Any]:
    lower = html_text.lower()
    provider_text = " ".join([lower, *parser.iframe_sources, *parser.script_sources, *parser.external_action_hosts])
    captcha_providers = provider_matches(provider_text, CAPTCHA_PROVIDER_SIGNATURES)
    return safe_barrier_hints(
        {
            "iframe_count": len(parser.iframe_sources),
            "iframe_sources": parser.iframe_sources[:8],
            "password_inputs": parser.password_inputs,
            "file_uploads": parser.file_uploads,
            "date_inputs": parser.date_inputs,
            "captcha": bool(captcha_providers) or "captcha" in provider_text,
            "captcha_providers": captcha_providers,
            "payment_providers": provider_matches(provider_text, PAYMENT_PROVIDER_SIGNATURES),
            "calendar_providers": provider_matches(provider_text, CALENDAR_PROVIDER_SIGNATURES),
            "map_providers": provider_matches(provider_text, MAP_PROVIDER_SIGNATURES),
            "external_action_hosts": parser.external_action_hosts[:20],
        }
    )


def safe_barrier_hints(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    hints: dict[str, Any] = {}
    for key in ("iframe_count", "password_inputs", "file_uploads", "date_inputs"):
        hints[key] = max(0, int(value.get(key) or 0))
    hints["captcha"] = bool(value.get("captcha"))
    for key in ("iframe_sources", "captcha_providers", "payment_providers", "calendar_providers", "map_providers", "external_action_hosts"):
        raw_items = value.get(key)
        items = raw_items if isinstance(raw_items, list) else []
        hints[key] = [clean_text(item)[:240] for item in items[:20] if clean_text(item)]
    return hints


def provider_matches(text: str, signatures: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    return [name for name, tokens in signatures if any(token in text for token in tokens)][:10]


def external_host(href: str, base_url: str) -> str:
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


def host_label(origin: str) -> str:
    parsed = urlparse(origin)
    return parsed.netloc.replace("www.", "") if parsed.netloc else ""


def css_token(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')[:120]


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
