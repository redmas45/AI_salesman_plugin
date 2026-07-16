"""Corrections for false inventory-empty claims."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable


def prevent_false_empty_inventory_claim(
    response: dict[str, Any],
    transcript: str,
    site_id: str,
    *,
    inventory_summary: Callable[[str], dict[str, Any]],
    load_products: Callable[[str, int], list[dict[str, Any]]],
    available_categories: Callable[[list[dict[str, Any]]], list[str]],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> None:
    text = str(response.get("response_text") or "")
    if not claims_store_inventory_empty(text):
        return

    try:
        stats = inventory_summary(site_id)
        in_stock = int(stats.get("in_stock_products") or 0)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | inventory summary unavailable: %s", exc)
        in_stock = 0

    if in_stock <= 0:
        return

    categories: list[str] = []
    try:
        categories = available_categories(load_products(site_id, 1000))
    except recoverable_errors as exc:
        logger.warning("PIPELINE | category lookup unavailable: %s", exc)
        categories = []

    category_text = f" We have categories like {', '.join(categories[:5])}." if categories else ""
    if mentions_cart_or_tray(transcript):
        response["response_text"] = (
            "Your cart or tray looks empty right now, but we do have plenty of products in stock."
            f"{category_text} Tell me what you need and I'll help you find it."
        )
    else:
        response["response_text"] = (
            "We do have plenty of products in stock. I just couldn't find an exact match for that request."
            f"{category_text} Tell me what you need and I'll help you shop."
        )
    response["intent"] = "chitchat"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
    response["ui_actions"] = []


def claims_store_inventory_empty(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    patterns = [
        r"\b(no|not|don't|do not|doesn't|does not|couldn't|could not)\b.{0,40}\b(items?|products?)\b.{0,40}\b(inventory|catalog|store)\b",
        r"\b(inventory|catalog|store)\b.{0,30}\b(empty|no items|no products|nothing available)\b",
        r"\b(no items|no products|nothing)\b.{0,30}\bavailable\b.{0,30}\b(inventory|catalog|store)\b",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def mentions_cart_or_tray(text: str) -> bool:
    normalized = re.sub(r"[^a-z\s]", " ", (text or "").lower())
    words = set(normalized.split())
    return bool(words & {"cart", "tray", "basket", "bag"})
