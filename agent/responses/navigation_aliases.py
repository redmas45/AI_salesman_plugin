"""Small semantic aliases for mapping human route words to discovered labels."""

from __future__ import annotations

import re
from typing import Any


ROUTE_SEMANTIC_ALIASES: dict[str, tuple[str, ...]] = {
    "appointment": ("booking", "consultation", "reservation", "schedule", "visit"),
    "apply": ("application", "admission", "enroll", "register", "signup"),
    "application": ("apply", "admission", "enroll", "register", "signup"),
    "auto": ("car", "automobile", "motor", "vehicle"),
    "automobile": ("auto", "car", "motor", "vehicle"),
    "bag": ("basket", "cart"),
    "basket": ("bag", "cart"),
    "bike": ("motor", "motorcycle", "scooter", "two wheeler", "vehicle"),
    "boat": ("cruise", "ferry", "ship"),
    "booking": ("appointment", "consultation", "reservation", "schedule", "visit"),
    "callback": ("call", "contact", "enquiry", "inquiry", "phone"),
    "car": ("auto", "automobile", "motor", "vehicle"),
    "cart": ("bag", "basket"),
    "case-study": ("portfolio", "project", "work"),
    "catalog": ("catalogue", "collection", "inventory", "products", "shop", "store"),
    "catalogue": ("catalog", "collection", "inventory", "products", "shop", "store"),
    "class": ("course", "lesson", "program"),
    "clinic": ("doctor", "healthcare", "hospital", "medical"),
    "collection": ("catalog", "catalogue", "inventory", "products", "shop", "store"),
    "consultation": ("appointment", "booking", "reservation", "schedule", "visit"),
    "course": ("class", "lesson", "program"),
    "cruise": ("boat", "ferry", "ship"),
    "demo": ("consultation", "trial"),
    "doctor": ("clinic", "healthcare", "hospital", "medical", "physician"),
    "estimate": ("quote", "rate", "request"),
    "event": ("show", "ticket"),
    "fare": ("price", "rate", "ticket"),
    "ferry": ("boat", "cruise", "ship"),
    "flight": ("air", "airline", "ticket"),
    "food": ("menu", "order", "restaurant"),
    "health": ("medical", "mediclaim"),
    "home": ("house", "property"),
    "hospital": ("clinic", "doctor", "healthcare", "medical"),
    "hotel": ("lodging", "room", "stay"),
    "house": ("home", "property"),
    "inquiry": ("callback", "contact", "enquiry"),
    "inventory": ("catalog", "catalogue", "collection", "products", "shop", "store"),
    "job": ("career", "opening", "position", "role", "vacancy"),
    "journey": ("travel", "trip"),
    "lawyer": ("attorney", "legal"),
    "lesson": ("class", "course", "program"),
    "listing": ("property", "real estate", "unit"),
    "lodging": ("hotel", "room", "stay"),
    "medical": ("health", "mediclaim"),
    "menu": ("food", "order", "restaurant"),
    "order": ("food", "menu", "restaurant"),
    "portfolio": ("case-study", "project", "work"),
    "position": ("career", "job", "opening", "role", "vacancy"),
    "price": ("fare", "premium", "rate"),
    "program": ("class", "course", "lesson"),
    "project": ("case-study", "portfolio", "work"),
    "quote": ("estimate", "premium", "rate", "request"),
    "rate": ("estimate", "fare", "price", "quote"),
    "reservation": ("appointment", "booking", "schedule", "visit"),
    "return": ("returns", "refund", "shipping and returns"),
    "returns": ("return", "refund", "shipping and returns"),
    "restaurant": ("food", "menu", "order"),
    "room": ("hotel", "lodging", "stay"),
    "schedule": ("appointment", "booking", "reservation", "visit"),
    "service": ("solution", "support"),
    "services": ("solutions", "support"),
    "shop": ("catalog", "catalogue", "collection", "inventory", "products", "store"),
    "show": ("event", "ticket"),
    "solution": ("service", "support"),
    "solutions": ("services", "support"),
    "stay": ("hotel", "lodging", "room"),
    "store": ("catalog", "catalogue", "collection", "inventory", "products", "shop"),
    "support": ("contact", "help", "service"),
    "ticket": ("event", "fare", "flight", "show"),
    "trial": ("demo",),
    "unit": ("listing", "property", "real estate"),
    "vacancy": ("career", "job", "opening", "position", "role"),
    "visit": ("appointment", "booking", "consultation", "reservation", "schedule"),
    "life": ("term", "term life"),
    "mediclaim": ("health", "medical"),
    "mobile": ("cellphone", "phone", "smartphone"),
    "motor": ("auto", "automobile", "bike", "car", "motorcycle", "scooter", "two wheeler", "vehicle"),
    "motorcycle": ("bike", "motor", "scooter", "two wheeler", "vehicle"),
    "phone": ("cellphone", "mobile", "smartphone"),
    "property": ("home", "house"),
    "rail": ("railway", "train"),
    "railway": ("rail", "train"),
    "ship": ("boat", "cruise", "ferry"),
    "shipping": ("delivery", "return", "returns", "shipping and returns"),
    "smartphone": ("cellphone", "mobile", "phone"),
    "term": ("life", "term life"),
    "train": ("rail", "railway"),
    "travel": ("journey", "trip"),
    "trip": ("journey", "travel"),
    "vehicle": ("auto", "automobile", "bike", "car", "motor", "motorcycle", "scooter"),
}

GENERIC_ROUTE_ALIAS_KEYS = frozenset(
    {
        "add-to-cart",
        "capture-lead",
        "checkout-handoff",
        "clear-cart",
        "clear-filters",
        "compare-entities",
        "compare-products",
        "filter-entities",
        "filter-products",
        "navigate-to",
        "remove-from-cart",
        "run-dom-sequence",
        "show-comparison",
        "show-entities",
        "show-product-detail",
        "show-products",
        "sort-entities",
        "sort-products",
        "start-intake",
        "update-cart-quantity",
        "update-preferences",
    }
)


def route_alias_key(value: Any) -> str:
    text = re.sub(r"[^a-z0-9/_\s-]+", " ", str(value or "").lower())
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace(" ", "-")[:120]


def is_generic_route_alias(value: Any) -> bool:
    return route_alias_key(value) in GENERIC_ROUTE_ALIAS_KEYS


def semantic_route_alias_keys(*values: Any) -> set[str]:
    aliases: set[str] = set()
    for value in values:
        normalized = route_alias_key(value)
        if not normalized:
            continue
        terms = {normalized}
        terms.update(part for part in re.split(r"[-/]+", normalized) if part)
        for term in terms:
            aliases.update(route_alias_key(alias) for alias in ROUTE_SEMANTIC_ALIASES.get(term, ()))
            if term in _REVERSE_ALIASES:
                aliases.add(_REVERSE_ALIASES[term])
    aliases.discard("")
    return aliases


_REVERSE_ALIASES: dict[str, str] = {
    route_alias_key(alias): route_alias_key(canonical)
    for canonical, aliases in ROUTE_SEMANTIC_ALIASES.items()
    for alias in aliases
}
