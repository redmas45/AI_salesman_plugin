"""Canonical grounded-fact builder for product comparisons.

One builder produces the facts used by BOTH the spoken/typed response and the
SHOW_COMPARISON overlay payload, so the customer never sees the widget and the
answer disagree.

Every fact is copied from a retrieved product record. Nothing is inferred,
averaged, or parsed back out of the assistant's natural-language reply, and a
product that does not publish a field simply has no row for it rather than a
guessed one. Values are trimmed and length-bounded because they are rendered in
a fixed-width comparison column.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agent.products.product_response_text import numeric_value, plain_text

Product = dict[str, Any]

MAX_FACT_LABEL_CHARS = 24
MAX_FACT_VALUE_CHARS = 120
MAX_DETAIL_FACTS = 3
MAX_TOTAL_FACTS = 6
MIN_DETAIL_FACT_CHARS = 12

# A trailing conjunction/preposition means the source text was cut mid-clause;
# rendering it produces the "... and" fragments seen in the overlay.
_DANGLING_WORD_RE = re.compile(
    r"\s+(?:and|or|with|for|but|the|a|an|to|of|in|on|at|by|from|that|which|plus)\s*[.,;:]?\s*$",
    re.IGNORECASE,
)
_SPEC_LABEL_RE = re.compile(r"[^a-z0-9 ]+", re.IGNORECASE)


def _clean_value(value: Any) -> str:
    """Plain, single-line, length-bounded text with no dangling connector."""
    text = plain_text(value)
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_FACT_VALUE_CHARS:
        text = text[:MAX_FACT_VALUE_CHARS].rsplit(" ", 1)[0].rstrip(" ,;:-")
    previous = None
    while previous != text:
        previous = text
        text = _DANGLING_WORD_RE.sub("", text).rstrip(" ,;:-")
    return text.strip()


def _label(value: str) -> str:
    text = _SPEC_LABEL_RE.sub(" ", str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:MAX_FACT_LABEL_CHARS].strip().title()


def format_price(product: Product) -> str:
    """Published price only. Never invents a number or a zero."""
    price = numeric_value(product.get("price"))
    if price is None:
        return ""
    currency = str(product.get("currency") or "").strip().upper()
    symbols = {"INR": "₹", "GBP": "£", "USD": "$", "EUR": "€"}
    prefix = symbols.get(currency, f"{currency} " if currency else "")
    rendered = f"{int(price):,}" if float(price).is_integer() else f"{price:,.2f}"
    return f"{prefix}{rendered}"


def availability_text(product: Product) -> str:
    stock = numeric_value(product.get("stock"))
    if stock is None:
        in_stock = product.get("in_stock")
        if in_stock is None:
            return ""
        return "In stock" if in_stock else "Out of stock"
    if stock <= 0:
        return "Out of stock"
    return "In stock"


def rating_text(product: Product) -> str:
    """Published score only.

    A missing score and a zero score both mean "nobody has rated this yet".
    Rendering the zero would advertise the worst possible rating for a product
    that simply has no reviews, so neither produces a rating claim.
    """
    rating = numeric_value(product.get("rating"))
    if rating is None or rating <= 0:
        return ""
    reviews = numeric_value(product.get("review_count"))
    if reviews is None or reviews <= 0:
        return f"{rating:g}/5"
    return f"{rating:g}/5 ({int(reviews)} reviews)"


def _tags(product: Product) -> list[str]:
    raw = product.get("tags")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = [part.strip() for part in raw.split(",")]
    return [str(item).strip() for item in raw if str(item or "").strip()] if isinstance(raw, list) else []


def _detail_facts(product: Product) -> list[dict[str, str]]:
    """Up to three published detail facts: specs, then highlights, then summary."""
    facts: list[dict[str, str]] = []

    specs = product.get("specs")
    if isinstance(specs, dict):
        for key, value in specs.items():
            if len(facts) >= MAX_DETAIL_FACTS:
                return facts
            cleaned = _clean_value(value)
            label = _label(key)
            if cleaned and label:
                facts.append({"label": label, "value": cleaned})

    highlights = product.get("highlights")
    if isinstance(highlights, list):
        for item in highlights:
            if len(facts) >= MAX_DETAIL_FACTS:
                return facts
            cleaned = _clean_value(item)
            if len(cleaned) >= MIN_DETAIL_FACT_CHARS:
                facts.append({"label": "Highlight", "value": cleaned})

    if len(facts) < MAX_DETAIL_FACTS:
        summary = _clean_value(product.get("description") or product.get("summary"))
        if len(summary) >= MIN_DETAIL_FACT_CHARS:
            facts.append({"label": "Summary", "value": summary})

    if len(facts) < MAX_DETAIL_FACTS:
        tags = ", ".join(_tags(product)[:4])
        cleaned_tags = _clean_value(tags)
        if cleaned_tags:
            facts.append({"label": "Tags", "value": cleaned_tags})

    return facts[:MAX_DETAIL_FACTS]


def build_comparison_facts(product: Product) -> list[dict[str, str]]:
    """Ordered, grounded facts for one product. Only published fields appear."""
    facts: list[dict[str, str]] = []
    published_price = format_price(product)

    for label, value in (
        ("Brand", _clean_value(product.get("brand") or product.get("vendor"))),
        ("Price", published_price or "Not published"),
        ("Availability", availability_text(product)),
        ("Rating", rating_text(product)),
        (
            "Category",
            _clean_value(
                product.get("category_name") or product.get("category") or product.get("subcategory")
            ),
        ),
    ):
        if value:
            facts.append({"label": label, "value": value})

    facts.extend(_detail_facts(product))
    return facts[:MAX_TOTAL_FACTS]


def comparison_facts_payload(products: list[Product]) -> list[dict[str, Any]]:
    """Per-product comparison payload for the SHOW_COMPARISON action."""
    payload: list[dict[str, Any]] = []
    for product in products:
        product_id = str(product.get("id") or "").strip()
        if not product_id:
            continue
        payload.append(
            {
                "product_id": product_id,
                "name": _clean_value(product.get("name") or product.get("title")) or "Product",
                "facts": build_comparison_facts(product),
            }
        )
    return payload


def comparison_fact_sentence(product: Product) -> str:
    """The same grounded facts rendered for the spoken/typed answer."""
    facts = build_comparison_facts(product)
    if not facts:
        return "No published details are available for this item."
    parts: list[str] = []
    for fact in facts:
        value = fact["value"]
        suffix = "" if value.endswith((".", "!", "?")) else "."
        parts.append(f"{fact['label']}: {value}{suffix}")
    return " ".join(parts)
