"""Cart request recovery helpers for ecommerce turns."""

from __future__ import annotations

import re
from typing import Any

from agent.products.product_response import (
    ProductCatalogFormatter,
    normalize_lookup_text,
    numeric_value,
    phrase_in_text,
)
from api.contracts.models import ACTION_ADD_TO_CART, PRODUCT_ID_PARAM, QUANTITY_PARAM


def ensure_cart_request_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
    formatter: ProductCatalogFormatter,
) -> None:
    """Recover an explicit add-to-cart request when the LLM omits the action."""
    if not wants_cart_add(transcript):
        return
    existing_action = next(
        (
            action
            for action in response.get("ui_actions", [])
            if action.get("action") == ACTION_ADD_TO_CART
        ),
        None,
    )
    if existing_action and existing_action.get("params", {}).get(PRODUCT_ID_PARAM):
        return

    response_text = str(response.get("response_text") or "")
    product = named_product_in_text(response_text, retrieved_products)
    if not product:
        product = cart_target_product(transcript, retrieved_products, formatter)
    if not product:
        product = cart_target_product(
            response_text,
            retrieved_products,
            formatter,
        )
    if not product:
        if existing_action:
            response["ui_actions"] = [
                action for action in response.get("ui_actions", []) if action is not existing_action
            ]
        return

    product_id = str(product.get("id") or "")
    if not product_id:
        return

    stock = product_stock(product, formatter)
    if stock is not None and stock <= 0:
        response["intent"] = "out_of_stock"
        response["ui_actions"] = []
        response["response_text"] = (
            f"{product_display_name(product, formatter)} is sold out right now, so I cannot add it to your cart."
        )
        return

    quantity = cart_quantity(transcript)
    if stock is not None:
        quantity = min(quantity, stock)

    action = {"action": ACTION_ADD_TO_CART, "params": {PRODUCT_ID_PARAM: product_id}}
    if quantity > 1:
        action["params"][QUANTITY_PARAM] = quantity

    response["intent"] = "add_to_cart"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
    response["ui_actions"] = [
        item for item in response.get("ui_actions", []) if item is not existing_action
    ]
    response["ui_actions"].append(action)
    response["response_text"] = cart_confirmation_text(product, quantity, formatter)


def wants_cart_add(text: str) -> bool:
    normalized = normalize_lookup_text(text)
    if not normalized:
        return False
    cart_words = {"cart", "basket", "bag", "tray"}
    if not any(phrase_in_text(word, normalized) for word in cart_words):
        return False
    return bool(
        re.search(r"\b(add|put|place|drop|send)\b.{0,45}\b(cart|basket|bag|tray)\b", normalized)
        or re.search(r"\b(cart|basket|bag|tray)\b.{0,45}\b(add|put|place|drop|send)\b", normalized)
        or re.search(r"\b(i will take|i ll take|i want|buy|get me)\b", normalized)
    )


def cart_target_product(
    transcript: str,
    products: list[dict],
    formatter: ProductCatalogFormatter,
) -> dict | None:
    candidates = [product for product in products if product.get("id")]
    if not candidates:
        return None

    normalized = normalize_lookup_text(transcript)
    if re.search(r"\b(that comparison|the comparison|those compared|these compared)\b", normalized):
        history_candidates = [product for product in candidates if product.get("_history_context")]
        if history_candidates:
            candidates = history_candidates
    index = ordinal_index(normalized)
    if index is not None and index < len(candidates):
        return candidates[index]

    if any(phrase_in_text(token, normalized) for token in ("cheaper", "cheapest", "lowest price", "least expensive")):
        return min(candidates, key=lambda product: product_price(product, formatter) or float("inf"))
    if any(phrase_in_text(token, normalized) for token in ("expensive", "costliest", "premium")):
        return max(candidates, key=lambda product: product_price(product, formatter) or 0)

    for product in candidates:
        name = normalize_lookup_text(product.get("name") or product.get("title") or "")
        if name and phrase_in_text(name, normalized):
            return product

    choice_count = delegated_choice_count(normalized)
    if choice_count:
        return best_store_backed_product(candidates[:choice_count], formatter)
    if re.search(r"\b(better|best|top|better rated|best rated)\b", normalized):
        return best_store_backed_product(candidates, formatter)

    if len(candidates) == 1:
        return candidates[0]
    return None


def named_product_in_text(text: str, products: list[dict]) -> dict | None:
    normalized = normalize_lookup_text(text)
    for product in products:
        if not product.get("id"):
            continue
        name = normalize_lookup_text(product.get("name") or product.get("title") or "")
        if name and phrase_in_text(name, normalized):
            return product
    return None


def delegated_choice_count(text: str) -> int | None:
    if not re.search(r"\b(choose|pick|select|recommend|better|best|top)\b", text):
        return None
    if re.search(r"\b(both|(?:those|these|the)\s+(?:two|2))\b", text):
        return 2
    if re.search(r"\b(?:those|these|the)\s+(?:three|3)\b", text):
        return 3
    if re.search(r"\b(?:those|these|the)\s+(?:four|4)\b", text):
        return 4
    return None


def best_store_backed_product(
    products: list[dict],
    formatter: ProductCatalogFormatter,
) -> dict | None:
    if not products:
        return None
    return max(products, key=lambda product: product_recommendation_rank(product, formatter))


def product_recommendation_rank(
    product: dict,
    formatter: ProductCatalogFormatter,
) -> tuple[float, float, int, float]:
    rating = numeric_value(product.get("rating")) or 0.0
    review_count = numeric_value(product.get("review_count")) or 0.0
    stock = product_stock(product, formatter) or 0
    price = product_price(product, formatter)
    return rating, review_count, stock, -(price if price is not None else float("inf"))


def ordinal_index(text: str) -> int | None:
    ordinals = {
        "first": 0,
        "1st": 0,
        "option 1": 0,
        "second": 1,
        "2nd": 1,
        "option 2": 1,
        "third": 2,
        "3rd": 2,
        "option 3": 2,
        "fourth": 3,
        "4th": 3,
        "option 4": 3,
    }
    for token, index in ordinals.items():
        if phrase_in_text(token, text):
            return index
    return None


def cart_quantity(text: str) -> int:
    normalized = normalize_lookup_text(text)
    normalized = re.sub(
        r"\b(?:both|(?:those|these|the)\s+(?:two|three|four|2|3|4))\b",
        " ",
        normalized,
    )
    quantity_text = re.sub(r"\b(option|item|product|choice)\s+[1-9][0-9]?\b", " ", normalized)
    quantity_text = re.sub(
        r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\b",
        " ",
        quantity_text,
    )
    word_numbers = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    for word, number in word_numbers.items():
        if phrase_in_text(word, quantity_text):
            return number
    match = re.search(r"\b([1-9][0-9]?)\b", quantity_text)
    if not match:
        return 1
    return max(1, min(99, int(match.group(1))))


def product_stock(product: dict, formatter: ProductCatalogFormatter) -> int | None:
    return formatter.stock(product)


def product_price(product: dict, formatter: ProductCatalogFormatter) -> float | None:
    return formatter.price(product)


def product_display_name(product: dict, formatter: ProductCatalogFormatter) -> str:
    return formatter.display_name(product)


def cart_confirmation_text(
    product: dict,
    quantity: int,
    formatter: ProductCatalogFormatter,
) -> str:
    return formatter.cart_confirmation_text(product, quantity)
