"""Attach host-matchable product identity to outgoing browser actions.

A client website owns its own product ids. The Hub's ingested copy of a catalog
often keys the same product differently (an internal numeric id here, a slug on
the site), so an action carrying only the Hub's `product_id` can be perfectly
grounded and still be unmatchable in the host's DOM - the browser then finds no
control and the turn fails for a reason that looks like a website fault.

This module adds the one identity both sides always share - the exact catalog
name of the already-validated record - so the browser executor can fall back to
an exact, unique name match. It only ever copies the name of a record the turn
already resolved; it never invents, guesses, or broadens identity, and the
executor treats a non-unique name as ambiguous rather than picking one.
"""

from __future__ import annotations

from typing import Any

from api.contracts.models import (
    ACTION_ADD_TO_CART,
    ACTION_NAVIGATE_TO,
    ACTION_OPEN_ENTITY_DETAIL,
    ACTION_REMOVE_FROM_CART,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_UPDATE_CART_QUANTITY,
    ENTITY_ID_PARAM,
    PRODUCT_ID_PARAM,
    PRODUCT_NAME_PARAM,
)

# Actions that operate on ONE specific record and therefore need to be able to
# find that record's own control or link in the host page.
SINGLE_RECORD_ACTIONS: frozenset[str] = frozenset(
    {
        ACTION_ADD_TO_CART,
        ACTION_REMOVE_FROM_CART,
        ACTION_UPDATE_CART_QUANTITY,
        ACTION_SHOW_PRODUCT_DETAIL,
        ACTION_OPEN_ENTITY_DETAIL,
        ACTION_NAVIGATE_TO,
    }
)


def attach_host_product_identity(
    actions: list[dict[str, Any]] | None,
    records_by_id: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Copy each single-record action's resolved record name into its params."""
    records = records_by_id or {}
    if not records:
        return actions or []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        if str(action.get("action") or "").upper() not in SINGLE_RECORD_ACTIONS:
            continue
        params = action.get("params")
        if not isinstance(params, dict) or params.get(PRODUCT_NAME_PARAM):
            continue
        name = _record_name(params, records)
        if name:
            params[PRODUCT_NAME_PARAM] = name
    return actions or []


def _record_name(params: dict[str, Any], records: dict[str, dict[str, Any]]) -> str:
    for key in (PRODUCT_ID_PARAM, ENTITY_ID_PARAM):
        record_id = str(params.get(key) or "").strip()
        if not record_id:
            continue
        record = records.get(record_id)
        if record:
            return str(record.get("name") or record.get("title") or "").strip()
    return ""
