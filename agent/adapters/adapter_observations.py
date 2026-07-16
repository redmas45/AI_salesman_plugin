"""Browser observation parsing and matching helpers for adapter discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from agent.adapters import adapter_action_candidates, adapter_form_contracts

MAX_ITEMS_PER_KIND = 80


@dataclass(frozen=True)
class ObservedElement:
    label: str = ""
    selector: str = ""
    href: str = ""
    input_selector: str = ""
    submit_selector: str = ""
    fields: tuple[dict[str, Any], ...] = ()


def parse_elements(value: Any) -> tuple[ObservedElement, ...]:
    if not isinstance(value, list):
        return ()
    elements: list[ObservedElement] = []
    for item in value[:MAX_ITEMS_PER_KIND]:
        if not isinstance(item, dict):
            continue
        elements.append(
            ObservedElement(
                label=clean_text(item.get("label"))[:120],
                selector=clean_selector(item.get("selector")),
                href=clean_text(item.get("href"))[:500],
                input_selector=clean_selector(item.get("input_selector")),
                submit_selector=clean_selector(item.get("submit_selector")),
                fields=parse_form_fields(item.get("fields")),
            )
        )
    return tuple(elements)


def first_search_form(forms: tuple[ObservedElement, ...], action_name: str) -> ObservedElement | None:
    for form in forms:
        if form_is_rejected_for_action(action_name, form):
            continue
        label = form.label.lower()
        if form.input_selector and ("search" in label or "where" in label or "destination" in label):
            return form
    return next((form for form in forms if form.input_selector and not form_is_rejected_for_action(action_name, form)), None)


def first_matching_element(elements: tuple[ObservedElement, ...], labels: tuple[str, ...]) -> ObservedElement | None:
    matches: list[ObservedElement] = []
    for element in elements:
        text = element.label.lower()
        if element.selector and any(label in text for label in labels):
            matches.append(element)
    if not matches:
        return None
    return sorted(matches, key=lambda element: matching_element_rank(element, labels))[0]


def matching_element_rank(element: ObservedElement, labels: tuple[str, ...]) -> tuple[int, int, int]:
    text = element.label.lower()
    selector = element.selector.lower()
    if any(text == label for label in labels):
        label_rank = 0
    elif any(text.startswith(label) for label in labels):
        label_rank = 1
    else:
        label_rank = 2

    if selector.startswith(("button", "input")) or "[role=\"button\"]" in selector or "[role='button']" in selector:
        selector_rank = 0
    elif selector.startswith("a"):
        selector_rank = 2
    else:
        selector_rank = 1

    return label_rank, selector_rank, len(text)


def first_matching_form(forms: tuple[ObservedElement, ...], labels: tuple[str, ...], action_name: str) -> ObservedElement | None:
    if not labels:
        return None
    for form in forms:
        text = " ".join([form.label, form_fields_text(form)]).lower()
        if form.fields and any(label in text for label in labels) and not form_is_rejected_for_action(action_name, form):
            return form
    return None


def form_fields_text(form: ObservedElement) -> str:
    return " ".join(
        clean_text(field.get("label") or field.get("name") or field.get("placeholder") or field.get("type"))
        for field in form.fields
    )


def parse_form_fields(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    fields: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        selector = clean_selector(item.get("selector"))
        if not selector:
            continue
        fields.append(
            {
                "selector": selector,
                "name": clean_text(item.get("name"))[:120],
                "label": clean_text(item.get("label"))[:120],
                "type": clean_text(item.get("type"))[:40],
                "placeholder": clean_text(item.get("placeholder"))[:120],
                "autocomplete": clean_text(item.get("autocomplete"))[:80],
                "required": bool(item.get("required") is True),
                "options": adapter_action_candidates.safe_field_options(item.get("options"), clean_text),
            }
        )
    return tuple(fields)


def path_from_href(href: str, origin: str) -> str:
    if not href:
        return ""
    try:
        parsed = urlparse(href)
        if parsed.scheme and f"{parsed.scheme}://{parsed.netloc}" != origin:
            return ""
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{path}{query}"[:240]
    except ValueError:
        return ""


def same_origin_url(url: Any, origin: Any) -> str:
    clean_url = clean_text(url)[:500]
    clean_origin = safe_origin(origin)
    if not clean_url:
        return clean_origin
    try:
        parsed = urlparse(clean_url)
    except ValueError:
        return clean_origin
    if not parsed.scheme or not parsed.netloc:
        return clean_origin
    if f"{parsed.scheme}://{parsed.netloc}" != clean_origin:
        return clean_origin
    return clean_url


def safe_origin(value: Any) -> str:
    text = clean_text(value)[:240]
    try:
        parsed = urlparse(text)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def clean_selector(value: Any) -> str:
    selector = clean_text(value)[:240]
    if not selector or any(token in selector.lower() for token in ("<script", "javascript:")):
        return ""
    return selector


def labels_text(elements: tuple[ObservedElement, ...]) -> str:
    return " ".join(element.label for element in elements if element.label)


def host_label(origin: str) -> str:
    parsed = urlparse(origin)
    return parsed.netloc.replace("www.", "") if parsed.netloc else ""


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_html_sample(value: Any) -> str:
    html = str(value or "").replace("\x00", "").strip()
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)


def form_is_rejected_for_action(action_name: str, form: ObservedElement) -> bool:
    return adapter_form_contracts.form_is_rejected_for_action(action_name, form)
