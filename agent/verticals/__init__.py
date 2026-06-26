"""Vertical definitions for tenant-specific AI Hub behavior."""

from agent.verticals.registry import (
    DEFAULT_VERTICAL_KEY,
    FALLBACK_VERTICAL_KEY,
    get_vertical,
    list_verticals,
    normalize_vertical_key,
)

__all__ = [
    "DEFAULT_VERTICAL_KEY",
    "FALLBACK_VERTICAL_KEY",
    "get_vertical",
    "list_verticals",
    "normalize_vertical_key",
]
