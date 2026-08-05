"""Ensure every turn result carries its spoken lead-in and confirmed outcome text.

The orchestrator has one richly-finalized path plus several early-return branches
(greeting, planned buy/add-to-cart/navigation flows, inventory answers, cached
answers). Only the main path computed the concise `spoken_text` and the confirmed
`success_text`; the early-return branches did not, so an add-to-cart planned flow
reached the widget with no confirmed outcome and the tentative promise stayed as
the final word. This leaf helper fills both fields for whichever branch produced
the result, keeping the two transports and every branch consistent.
"""

from __future__ import annotations

from typing import Any

from agent.responses.action_confirmation import confirmed_action_success_text
from agent.responses.spoken_text import concise_spoken_text


def products_by_id(retrieved_products: Any) -> dict[str, dict[str, Any]]:
    """Index retrieved records by id so a verified action can be confirmed by name."""
    indexed: dict[str, dict[str, Any]] = {}
    for product in retrieved_products or []:
        if isinstance(product, dict) and product.get("id") is not None:
            indexed[str(product["id"])] = product
    return indexed


def ensure_action_texts(
    result: dict[str, Any],
    retrieved_products: Any = None,
) -> dict[str, Any]:
    """Fill `spoken_text`/`success_text` on a result dict when a branch left them out.

    Uses `setdefault` semantics: a branch that already computed either field (the
    main path) keeps its value; only missing fields are derived from the response
    text and the turn's actions. Passing the retrieved records lets a confirmed
    add-to-cart or navigation name the product instead of falling back to generic.
    """
    if not isinstance(result, dict):
        return result
    response_text = str(result.get("response_text") or "")
    actions = result.get("ui_actions") or []
    if "spoken_text" not in result:
        result["spoken_text"] = concise_spoken_text(response_text, actions)
    if "success_text" not in result:
        result["success_text"] = confirmed_action_success_text(
            response_text, actions, products_by_id(retrieved_products)
        )
    return result
