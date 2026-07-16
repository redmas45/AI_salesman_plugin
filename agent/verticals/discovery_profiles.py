"""Registry-driven website discovery hints for vertical automation.

These profiles are deliberately data-only. The crawler and adapter generator use
the same profile fields for every industry so adding a vertical does not require
new crawler branches.
"""

from __future__ import annotations

from agent.verticals.discovery_profile_catalog import (
    COMMON_ACTION_LABELS,
    COMMON_DISCOVERY_PATHS,
    COMMON_HIGH_VALUE_URL_KEYWORDS,
    COMMON_ROUTE_ACTIONS,
    COMMON_ROUTE_KEYWORDS,
    GENERIC_PROFILE,
    PROFILE_BY_KEY,
)
from agent.verticals.discovery_profile_model import VerticalDiscoveryProfile
from agent.verticals.registry import FALLBACK_VERTICAL_KEY, get_vertical, list_verticals


def get_discovery_profile(vertical_key: str | None) -> VerticalDiscoveryProfile:
    """Return discovery hints for a vertical, falling back to generic."""
    try:
        normalized = get_vertical(vertical_key).key
    except ValueError:
        normalized = FALLBACK_VERTICAL_KEY
    return PROFILE_BY_KEY.get(normalized) or GENERIC_PROFILE


def list_discovery_profiles() -> list[VerticalDiscoveryProfile]:
    """Return profiles in backend vertical display order."""
    ordered_keys = [vertical.key for vertical in list_verticals()]
    return [PROFILE_BY_KEY[key] for key in ordered_keys if key in PROFILE_BY_KEY]


def merged_route_keywords(profile: VerticalDiscoveryProfile) -> dict[str, tuple[str, ...]]:
    """Return common and vertical route keyword maps."""
    return {**COMMON_ROUTE_KEYWORDS, **profile.route_keywords}


def merged_route_actions(profile: VerticalDiscoveryProfile) -> dict[str, str]:
    """Return route-to-action mapping for adapter generation."""
    return {**COMMON_ROUTE_ACTIONS, **profile.route_actions}


def merged_action_labels(profile: VerticalDiscoveryProfile) -> dict[str, tuple[str, ...]]:
    """Return common and vertical action label hints."""
    merged = dict(COMMON_ACTION_LABELS)
    for action, labels in profile.action_labels.items():
        merged[action] = tuple(dict.fromkeys((*merged.get(action, ()), *labels)))
    return merged


def discovery_paths_for(vertical_key: str | None) -> tuple[str, ...]:
    profile = get_discovery_profile(vertical_key)
    return tuple(dict.fromkeys((*COMMON_DISCOVERY_PATHS, *profile.discovery_paths)))


def high_value_url_keywords_for(vertical_key: str | None) -> tuple[str, ...]:
    profile = get_discovery_profile(vertical_key)
    return tuple(dict.fromkeys((*COMMON_HIGH_VALUE_URL_KEYWORDS, *profile.high_value_url_keywords)))


def knowledge_entity_type_for(vertical_key: str | None) -> str:
    profile = get_discovery_profile(vertical_key)
    if profile.entity_type:
        return profile.entity_type
    try:
        vertical = get_vertical(vertical_key)
        return vertical.entity_types[0] if vertical.entity_types else "knowledge_item"
    except ValueError:
        return "knowledge_item"
