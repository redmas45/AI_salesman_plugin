"""Deterministic precedence for cart requests.

A cart request must never be reinterpreted as a different transaction. The
planner previously treated *any* mention of a cart container that was not an
explicit "add ... to cart" as a checkout request, so "clear my cart", "remove
all the items from the cart" and even "what is in my cart" all tried to open
the checkout step. Emptying a cart and paying for it are opposite intentions,
and guessing between them costs the customer money.

Precedence is fixed and evaluated in this order:

1. ``clear_cart``        - the whole cart is the object of the request
2. ``remove_from_cart``  - one named item is taken out
3. ``add_to_cart``       - an item goes in
4. ``checkout``          - only for explicit checkout language

A question about the cart resolves to no transactional intent at all, so it is
answered rather than acted on.

The vocabulary is ordinary English plus the container nouns a cart is called
by; nothing here depends on a retail catalog, so the same rules hold for a
travel add-on basket or a policy bundle.
"""

from __future__ import annotations

import re

INTENT_CLEAR_CART = "clear_cart"
INTENT_REMOVE_FROM_CART = "remove_from_cart"
INTENT_ADD_TO_CART = "add_to_cart"
INTENT_CHECKOUT = "checkout"
INTENT_NONE = ""

# What the customer may call the container.
_CONTAINER = r"(?:cart|basket|bag|tray|trolley)"

# How far apart a verb and its object may sit and still be one request.
_NEAR = r".{0,45}?"

# "Everything" quantifiers turn a removal into a full clear, whatever verb is
# used: "remove all the items from the cart" empties it just as "clear" does.
_EVERYTHING = r"(?:all|everything|every\s+item|each\s+item|the\s+lot|whole|entire)"

_CLEAR_VERBS = r"(?:clear|empty|wipe|flush|reset|dump|purge)"
_REMOVE_VERBS = r"(?:remove|delete|discard|take\s+out|take|get\s+rid\s+of|drop|pull)"
_ADD_VERBS = r"(?:add|put|place|drop|throw|stick|chuck)"

# The cart itself is the object: "clear my cart", "empty my booking basket".
# Determiners and adjectives may sit between the verb and the container, but a
# preposition may not - that would make some *other* noun the object, as in
# "remove the jacket from my cart".
_CLEAR_CONTAINER_RE = re.compile(
    rf"\b{_CLEAR_VERBS}\s+(?:out\s+)?(?:(?!from\b|of\b|off\b)\w+\s+){{0,3}}{_CONTAINER}\b",
    re.IGNORECASE,
)

# An explicit "everything" removal, in either word order.
_CLEAR_EVERYTHING_RE = re.compile(
    rf"\b(?:{_CLEAR_VERBS}|{_REMOVE_VERBS})\b{_NEAR}\b{_EVERYTHING}\b{_NEAR}\b{_CONTAINER}\b"
    rf"|\b{_CONTAINER}\b{_NEAR}\b(?:{_CLEAR_VERBS}|{_REMOVE_VERBS})\b{_NEAR}\b{_EVERYTHING}\b",
    re.IGNORECASE,
)

_REMOVE_RE = re.compile(
    rf"\b{_REMOVE_VERBS}\b{_NEAR}\b{_CONTAINER}\b|\b{_CONTAINER}\b{_NEAR}\b{_REMOVE_VERBS}\b",
    re.IGNORECASE,
)

_ADD_RE = re.compile(
    rf"\b{_ADD_VERBS}\b{_NEAR}\b{_CONTAINER}\b|\b{_CONTAINER}\b{_NEAR}\b{_ADD_VERBS}\b",
    re.IGNORECASE,
)

# Explicit checkout language only. A bare container word is not one of these.
_CHECKOUT_RE = re.compile(
    r"\b(?:checkout|check\s*out)\b"
    r"|\bplace\s+(?:my|the)?\s*order\b"
    r"|\b(?:complete|finish|confirm)\s+(?:my|the)?\s*(?:order|purchase|payment)\b"
    r"|\bpay\s+(?:now|for\s+(?:it|this|these))\b"
    r"|\bproceed\s+to\s+(?:pay|payment|purchase)\b",
    re.IGNORECASE,
)

# A question about the cart's contents is answered, never executed.
_CART_QUESTION_RE = re.compile(
    r"^\s*(?:what|which|how\s+many|how\s+much|is|are|does|do|anything|"
    r"can\s+you\s+(?:tell|show)|show\s+me\s+what)\b",
    re.IGNORECASE,
)


def mentions_cart(text: str) -> bool:
    """True when the turn names a cart container at all."""
    return bool(re.search(rf"\b{_CONTAINER}\b", str(text or ""), re.IGNORECASE))


def _is_cart_question(text: str) -> bool:
    """A request for the cart's state, with no verb asking to change it."""
    if not _CART_QUESTION_RE.search(text):
        return False
    return not (
        _CLEAR_CONTAINER_RE.search(text)
        or _CLEAR_EVERYTHING_RE.search(text)
        or _ADD_RE.search(text)
        or _CHECKOUT_RE.search(text)
    )


def cart_intent(text: str) -> str:
    """Resolve one turn to exactly one cart intent, in fixed precedence order.

    Returns ``INTENT_NONE`` when the turn is not a cart transaction, including
    when it merely asks what the cart contains.
    """
    clean_text = str(text or "")
    mentions_container = mentions_cart(clean_text)
    if not mentions_container:
        return INTENT_CHECKOUT if _CHECKOUT_RE.search(clean_text) else INTENT_NONE

    if _is_cart_question(clean_text):
        return INTENT_NONE

    # Emptying the cart outranks every other reading, so a correction such as
    # "no, clear the cart - I don't want to buy it" can never become a purchase.
    if _CLEAR_CONTAINER_RE.search(clean_text) or _CLEAR_EVERYTHING_RE.search(clean_text):
        return INTENT_CLEAR_CART
    if _REMOVE_RE.search(clean_text):
        return INTENT_REMOVE_FROM_CART
    if _ADD_RE.search(clean_text):
        return INTENT_ADD_TO_CART
    if _CHECKOUT_RE.search(clean_text):
        return INTENT_CHECKOUT
    return INTENT_NONE
