"""
Runtime Capability Engine — filter AI actions by site readiness.

Reads the readiness report for a site and determines which UI actions
the AI is allowed to perform. Unsupported actions are filtered out
before being sent to the client widget.
"""

from __future__ import annotations

import logging
from typing import Any

import config
from db import admin as admin_db

logger = logging.getLogger(__name__)

# Actions that are always safe — they only show information or navigate
ALWAYS_ALLOWED_ACTIONS: frozenset[str] = frozenset({
    "SHOW_PRODUCTS",
    "SHOW_COMPARISON",
    "FILTER_PRODUCTS",
    "NAVIGATE_TO",
    "SORT_PRODUCTS",
    "SHOW_PRODUCT_DETAIL",
    "CLEAR_FILTERS",
    "CLEAR_HISTORY",
    "UPDATE_PREFERENCES",
})

# Actions that require cart capability
CART_ACTIONS: frozenset[str] = frozenset({
    "ADD_TO_CART",
    "REMOVE_FROM_CART",
    "CLEAR_CART",
    "UPDATE_CART_QUANTITY",
})

# Actions that require checkout capability
CHECKOUT_ACTIONS: frozenset[str] = frozenset({
    "CHECKOUT",
})


def get_allowed_actions(site_id: str) -> set[str]:
    """Return the set of UI action types this site supports."""
    report = admin_db.get_readiness_report(site_id)
    if not report:
        # No scan yet — allow everything for backward compatibility
        return set(config.VALID_UI_ACTIONS)

    capabilities = {
        cap["name"]: cap
        for cap in report.get("capabilities", [])
    }

    allowed: set[str] = set(ALWAYS_ALLOWED_ACTIONS)

    cart_cap = capabilities.get("cart", {})
    if cart_cap.get("supported", False):
        allowed |= CART_ACTIONS

    checkout_cap = capabilities.get("checkout", {})
    if checkout_cap.get("supported", False):
        allowed |= CHECKOUT_ACTIONS

    return allowed


def filter_actions(site_id: str, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove actions that the site does not support."""
    allowed = get_allowed_actions(site_id)
    filtered = [
        action for action in actions
        if action.get("action") in allowed
    ]

    removed_count = len(actions) - len(filtered)
    if removed_count > 0:
        removed_names = [
            action.get("action") for action in actions
            if action.get("action") not in allowed
        ]
        logger.info(
            "Capability filter removed %d action(s) for %s: %s",
            removed_count,
            site_id,
            removed_names,
        )

    return filtered


def capability_summary(site_id: str) -> dict[str, Any]:
    """Return a human-readable capability summary for the CRM."""
    report = admin_db.get_readiness_report(site_id)
    if not report:
        return {
            "scanned": False,
            "platform": "unknown",
            "platform_confidence": 0.0,
            "supported": [],
            "unsupported": [],
        }

    capabilities = report.get("capabilities", [])
    supported = [
        cap["name"] for cap in capabilities
        if cap.get("supported", False)
    ]
    unsupported = [
        cap["name"] for cap in capabilities
        if not cap.get("supported", False)
    ]

    return {
        "scanned": True,
        "platform": report.get("platform", "unknown"),
        "platform_confidence": report.get("platform_confidence", 0.0),
        "supported": supported,
        "unsupported": unsupported,
        "scanned_at": report.get("scanned_at", ""),
    }


def capability_prompt_context(site_id: str) -> str:
    """
    Return a prompt fragment describing the site's capabilities.

    Injected into the LLM system prompt to prevent the AI from suggesting
    actions the website does not support.
    """
    report = admin_db.get_readiness_report(site_id)
    if not report:
        return ""

    capabilities = report.get("capabilities", [])
    supported = [cap["name"] for cap in capabilities if cap.get("supported")]
    unsupported = [cap["name"] for cap in capabilities if not cap.get("supported")]
    platform = report.get("platform", "unknown")

    lines: list[str] = []
    lines.append(f"Client website platform: {platform}.")
    if supported:
        lines.append(f"Supported capabilities: {', '.join(supported)}.")
    if unsupported:
        lines.append(f"Unsupported capabilities: {', '.join(unsupported)}.")
    if "cart" not in supported:
        lines.append("Do NOT suggest adding items to cart or cart operations.")
    if "checkout" not in supported:
        lines.append("Do NOT suggest checkout or order placement.")
    if "variants" not in supported:
        lines.append("Do NOT ask about product sizes or color variants.")

    return " ".join(lines)
