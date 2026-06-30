"""Vertical registry used by backend APIs and runtime tenant metadata."""

from __future__ import annotations

import re

from agent.verticals.automotive import VERTICAL as AUTOMOTIVE
from agent.verticals.construction import VERTICAL as CONSTRUCTION
from agent.verticals.ecommerce import VERTICAL as ECOMMERCE
from agent.verticals.education import VERTICAL as EDUCATION
from agent.verticals.events_ticketing import VERTICAL as EVENTS_TICKETING
from agent.verticals.finance_broker import VERTICAL as FINANCE_BROKER
from agent.verticals.food import VERTICAL as FOOD
from agent.verticals.generic import VERTICAL as GENERIC
from agent.verticals.healthcare import VERTICAL as HEALTHCARE
from agent.verticals.insurance import VERTICAL as INSURANCE
from agent.verticals.jobs_recruiting import VERTICAL as JOBS_RECRUITING
from agent.verticals.legal_services import VERTICAL as LEGAL_SERVICES
from agent.verticals.real_estate import VERTICAL as REAL_ESTATE
from agent.verticals.travel import VERTICAL as TRAVEL
from agent.verticals.base import VerticalDefinition

DEFAULT_VERTICAL_KEY = "generic"
FALLBACK_VERTICAL_KEY = "generic"

_VERTICALS: tuple[VerticalDefinition, ...] = (
    ECOMMERCE,
    INSURANCE,
    TRAVEL,
    FINANCE_BROKER,
    HEALTHCARE,
    FOOD,
    REAL_ESTATE,
    EDUCATION,
    AUTOMOTIVE,
    LEGAL_SERVICES,
    JOBS_RECRUITING,
    EVENTS_TICKETING,
    CONSTRUCTION,
    GENERIC,
)
_VERTICAL_BY_KEY = {vertical.key: vertical for vertical in _VERTICALS}


def normalize_vertical_key(raw: str | None) -> str:
    """Normalize user/API vertical input to registry key format."""
    text = re.sub(r"[^a-z0-9]+", "_", str(raw or "").strip().lower())
    return re.sub(r"_+", "_", text).strip("_")


def get_vertical(key: str | None) -> VerticalDefinition:
    """Return a vertical definition or raise for an unsupported key."""
    normalized_key = normalize_vertical_key(key) or DEFAULT_VERTICAL_KEY
    vertical = _VERTICAL_BY_KEY.get(normalized_key)
    if vertical is None:
        raise ValueError(f"Unsupported vertical '{key}'.")
    return vertical


def list_verticals() -> list[VerticalDefinition]:
    """Return every built-in vertical in CRM display order."""
    return list(_VERTICALS)
