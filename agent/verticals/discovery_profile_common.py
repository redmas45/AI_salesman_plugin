"""Common discovery hints shared by vertical profile definitions."""

from __future__ import annotations

COMMON_ROUTE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "home": ("home",),
    "about": ("about", "company", "who we are"),
    "contact": ("contact", "support", "help", "callback", "enquiry", "inquiry"),
    "faq": ("faq", "faqs", "questions"),
    "login": ("login", "sign in", "account"),
    "privacy": ("privacy", "terms", "disclaimer"),
}

COMMON_ROUTE_ACTIONS: dict[str, str] = {
    "contact": "OPEN_CONTACT",
    "faq": "OPEN_POLICY",
    "privacy": "OPEN_POLICY",
}

COMMON_ACTION_LABELS: dict[str, tuple[str, ...]] = {
    "OPEN_CONTACT": ("contact", "support", "help"),
    "CAPTURE_LEAD": ("contact", "submit", "send message", "enquire", "inquire"),
    "REQUEST_CALLBACK": ("request callback", "call me", "schedule call"),
    "HANDOFF_TO_HUMAN": ("talk to human", "speak to team", "contact team"),
}

COMMON_DISCOVERY_PATHS: tuple[str, ...] = (
    "/",
    "/about",
    "/services",
    "/contact",
    "/faq",
)

COMMON_HIGH_VALUE_URL_KEYWORDS: tuple[str, ...] = (
    "service",
    "services",
    "solutions",
    "catalog",
    "category",
    "categories",
    "contact",
    "quote",
    "booking",
    "appointment",
)
