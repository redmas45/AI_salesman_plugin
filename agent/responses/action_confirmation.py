"""Confirmed-outcome wording for a browser action the widget has verified.

The server cannot observe the customer's browser, so it de-claims every optimistic
sentence into a tentative "I'll try to ..." promise (see
`agent.action_helpers.action_response_filters.neutralize_pending_action_claims`)
and lets the widget decide the final word after it executes and verifies the
action. This module supplies the sentence the widget speaks once the action is
observed to have succeeded, so a verified add-to-cart or navigation is stated as
done instead of staying tentative.

It is vertical-neutral: it reads the outcome action type and the already-grounded
record title or navigation label, never a site-specific route, brand, or catalog
name. Display actions (showing or comparing records) are intentionally excluded —
their wording lists records already named in the answer, so it is independently
true and must not be replaced.
"""

from __future__ import annotations

from typing import Any

from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_CLEAR_FILTERS,
    ACTION_FILTER_PRODUCTS,
    ACTION_NAVIGATE_TO,
    ACTION_OPEN_ENTITY_DETAIL,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_SORT_ENTITIES,
    ACTION_SORT_PRODUCTS,
    ENTITY_ID_PARAM,
    PAGE_PARAM,
    PRODUCT_ID_PARAM,
    QUANTITY_PARAM,
)

# Outcome actions change the website and can be confirmed by name/label once the
# browser proves them. Order matters only for choosing the primary action of a turn.
_CART_ADD_ACTIONS = frozenset({ACTION_ADD_TO_CART})
_DETAIL_ACTIONS = frozenset({ACTION_SHOW_PRODUCT_DETAIL, ACTION_OPEN_ENTITY_DETAIL})
_NAVIGATION_ACTIONS = frozenset({ACTION_NAVIGATE_TO})
_RESULT_UPDATE_ACTIONS = frozenset(
    {ACTION_SORT_PRODUCTS, ACTION_SORT_ENTITIES, ACTION_FILTER_PRODUCTS, ACTION_CLEAR_FILTERS}
)
_OUTCOME_ACTIONS = _CART_ADD_ACTIONS | _DETAIL_ACTIONS | _NAVIGATION_ACTIONS | _RESULT_UPDATE_ACTIONS

_RESULT_UPDATE_TEXT = "I updated the results on the page."
_GENERIC_NAVIGATION_TEXT = "I opened that page for you."
_GENERIC_DETAIL_TEXT = "I opened those details for you."
_GENERIC_CART_TEXT = "That item is now in your cart."
_MAX_QUANTITY = 99


def confirmed_action_success_text(
    response_text: str,
    actions: list[dict[str, Any]] | None,
    products_by_id: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Return what to say once the primary outcome action is verified, or ""."""
    primary = _primary_outcome_action(actions)
    if not primary:
        return ""
    name = str(primary.get("action") or "").upper()
    params = primary.get("params") if isinstance(primary.get("params"), dict) else {}
    records = products_by_id or {}
    if name in _CART_ADD_ACTIONS:
        return _cart_success_text(params, records)
    if name in _DETAIL_ACTIONS:
        return _detail_success_text(params, records)
    if name in _NAVIGATION_ACTIONS:
        return _navigation_success_text(params, records)
    if name in _RESULT_UPDATE_ACTIONS:
        return _RESULT_UPDATE_TEXT
    return ""


def _primary_outcome_action(actions: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    for action in actions or []:
        if isinstance(action, dict) and str(action.get("action") or "").upper() in _OUTCOME_ACTIONS:
            return action
    return None


def _cart_success_text(params: dict[str, Any], records: dict[str, dict[str, Any]]) -> str:
    name = _record_title(params, records)
    quantity = _safe_quantity(params.get(QUANTITY_PARAM))
    if name:
        if quantity > 1:
            return f"{quantity} x {name} are now in your cart."
        return f"{name} is now in your cart."
    if quantity > 1:
        return f"{quantity} items are now in your cart."
    return _GENERIC_CART_TEXT


def _detail_success_text(params: dict[str, Any], records: dict[str, dict[str, Any]]) -> str:
    name = _record_title(params, records)
    return f"I opened {name}." if name else _GENERIC_DETAIL_TEXT


def _navigation_success_text(params: dict[str, Any], records: dict[str, dict[str, Any]]) -> str:
    name = _record_title(params, records)
    if name:
        return f"I opened {name}."
    label = _navigation_label(params.get(PAGE_PARAM))
    return f"I opened {label}." if label else _GENERIC_NAVIGATION_TEXT


def _record_title(params: dict[str, Any], records: dict[str, dict[str, Any]]) -> str:
    for key in (PRODUCT_ID_PARAM, ENTITY_ID_PARAM):
        record_id = str(params.get(key) or "").strip()
        if not record_id:
            continue
        record = records.get(record_id)
        if record:
            title = str(record.get("name") or record.get("title") or "").strip()
            if title:
                return title
    return ""


def _navigation_label(page: Any) -> str:
    """Humanize a same-origin nav target into a readable section name.

    The most specific readable part of the target is used. A section is often
    addressed as `shop?category=electronics`, where the path names the listing and
    the query names the section actually asked for - reporting the path alone told
    the customer "I opened shop" when they asked for Electronics.

    Routes are only surfaced when they read as a plain section name; a raw URL or
    an ambiguous token falls back to a generic confirmation, so the customer is
    never told a page opened under a wrong or cryptic label.
    """
    raw = str(page or "").strip()
    if not raw or "://" in raw:
        return ""
    path, _, query = raw.partition("?")
    segment = query.split("&")[-1].partition("=")[2] if query else ""
    if not segment:
        segment = path.strip("/").split("/")[-1]
    words = segment.replace("-", " ").replace("_", " ").split()
    if not words or any(len(word) > 24 for word in words):
        return ""
    return " ".join(words)


def _safe_quantity(value: Any) -> int:
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return 1
    if quantity < 1:
        return 1
    return min(quantity, _MAX_QUANTITY)
