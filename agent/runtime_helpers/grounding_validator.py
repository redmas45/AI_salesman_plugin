"""Deterministic final grounding + hard-constraint validator.

Identity grounding (every actioned product id must be in the retrieved set) is
handled earlier by the output guardrails. This module adds the missing final
guarantee: every product referenced by a product-list action must also obey the
turn's hard constraints (price floor/ceiling). If enforcing the constraint
removes products, the response text is re-grounded from the survivors; if nothing
survives an explicit request, a grounded no-match/clarification is returned
instead of leaking an ungrounded answer.

This is defense-in-depth: retrieval already price-filters, so in the common case
this pass is a no-op. It exists so an over-budget item can never reach the user
even if an upstream filter is bypassed.
"""

from __future__ import annotations

from typing import Any

from agent.products.product_response_text import numeric_value
from api.contracts.models import PRODUCT_IDS_PARAM

Product = dict[str, Any]


def product_within_price(product: Product, price_constraints: dict[str, float]) -> bool:
    """True when the product satisfies the price floor/ceiling.

    A product with an unknown/unparseable price is rejected when the user set a
    hard price constraint. Unknown cannot be represented as "within budget".
    """
    if not price_constraints:
        return True
    price = numeric_value(product.get("price"))
    if price is None:
        return False
    max_price = price_constraints.get("max_price")
    min_price = price_constraints.get("min_price")
    if max_price is not None and price > max_price:
        return False
    if min_price is not None and price < min_price:
        return False
    return True


def _allowed_products(retrieved_products: list[Product], price_constraints: dict[str, float]) -> dict[str, Product]:
    allowed: dict[str, Product] = {}
    for product in retrieved_products:
        product_id = str(product.get("id") or "").strip()
        if product_id and product_within_price(product, price_constraints):
            allowed[product_id] = product
    return allowed


def _product_ids(action: dict[str, Any]) -> list[str]:
    params = action.get("params") if isinstance(action, dict) else None
    if not isinstance(params, dict):
        return []
    ids = params.get(PRODUCT_IDS_PARAM)
    return [str(pid) for pid in ids] if isinstance(ids, list) else []


def enforce_grounded_constraints(
    response: dict[str, Any],
    retrieved_products: list[Product],
    price_constraints: dict[str, float] | None,
) -> dict[str, Any]:
    """Filter product-list actions to retrieved products that obey the price
    constraint; re-ground the text when anything is removed."""
    price_constraints = price_constraints or {}
    if not price_constraints:
        return response

    allowed = _allowed_products(retrieved_products, price_constraints)
    actions = response.get("ui_actions") or []
    removed_any = False
    surviving_ids: list[str] = []
    new_actions: list[dict[str, Any]] = []

    for action in actions:
        ids = _product_ids(action)
        if not ids:
            new_actions.append(action)
            continue
        kept = [pid for pid in ids if pid in allowed]
        if len(kept) != len(ids):
            removed_any = True
        if not kept:
            # Every product in this action violated the constraint: drop the action.
            continue
        action = {**action, "params": {**action["params"], PRODUCT_IDS_PARAM: kept}}
        surviving_ids.extend(kept)
        new_actions.append(action)

    if not removed_any:
        return response

    response = {**response, "ui_actions": new_actions}
    response["response_text"] = _regrounded_text(surviving_ids, allowed, price_constraints)
    response["answer_scope"] = "product_search"
    return response


def _regrounded_text(
    surviving_ids: list[str],
    allowed: dict[str, Product],
    price_constraints: dict[str, float],
) -> str:
    if not surviving_ids:
        ceiling = price_constraints.get("max_price")
        budget_hint = f" under ₹{int(ceiling)}" if ceiling else ""
        return (
            f"I couldn't find any products{budget_hint} that match what you asked for. "
            "Want to adjust the budget or try a different category?"
        )
    names = []
    for pid in surviving_ids[:3]:
        product = allowed.get(pid) or {}
        name = str(product.get("name") or product.get("title") or "").strip()
        if name:
            names.append(name)
    shown = ", ".join(names)
    noun = "option" if len(surviving_ids) == 1 else "options"
    text = f"I found {len(surviving_ids)} {noun} within your budget"
    return f"{text}: {shown}." if shown else f"{text}."
