"""Route discovery and route-backed adapter actions."""

from __future__ import annotations

from typing import Any

from agent.actions.registry import get_action, normalize_action_name
from agent.adapters.adapter_observations import clean_text, path_from_href
from agent.verticals.discovery_profiles import get_discovery_profile, merged_route_keywords
from agent.verticals.registry import get_vertical

MEDIUM_CONFIDENCE = 0.66


def discover_routes(data: Any, vertical_key: str) -> dict[str, str]:
    """Map observed links to normalized route names."""
    profile = get_discovery_profile(vertical_key)
    route_keywords = merged_route_keywords(profile)
    routes = {"home": "/"}
    for link in data.links:
        label = link.label.lower()
        path = path_from_href(link.href, data.origin)
        if not path:
            continue
        for route_name, keywords in route_keywords.items():
            if route_name in routes:
                continue
            if any(keyword in label or keyword in path.lower() for keyword in keywords):
                routes[route_name] = path
                break
    return routes


def add_route_actions(
    actions: dict[str, dict[str, Any]],
    routes: dict[str, str],
    route_actions: dict[str, str],
) -> None:
    for route_name, action_name in route_actions.items():
        if route_name not in routes or action_name in actions:
            continue
        actions[action_name] = {"type": "navigate", "path": routes[route_name], "confidence": MEDIUM_CONFIDENCE}


def add_contact_route_fallback_actions(
    actions: dict[str, dict[str, Any]],
    routes: dict[str, str],
    vertical_key: str,
) -> None:
    """Map expected lead/handoff actions to contact when no exact control was found."""
    contact_path = contact_route_path(routes)
    if not contact_path:
        return
    try:
        expected_actions = [normalize_action_name(action) for action in get_vertical(vertical_key).action_types]
    except ValueError:
        expected_actions = []

    if "CAPTURE_LEAD" in expected_actions and "CAPTURE_LEAD" not in actions:
        actions["CAPTURE_LEAD"] = {
            "type": "navigate",
            "path": contact_path,
            "label": "Open contact or enquiry page",
            "confidence": MEDIUM_CONFIDENCE,
            "source": "contact_route_fallback",
            "note": "No dedicated lead form was detected; route the visitor to the contact path for lead capture.",
        }

    for action_name in expected_actions:
        if action_name in actions or not is_handoff_action(action_name):
            continue
        action = get_action(action_name)
        actions[action_name] = {
            "type": "handoff",
            "path": contact_path,
            "label": action.label if action else action_name.replace("_", " ").title(),
            "confidence": MEDIUM_CONFIDENCE,
            "source": "contact_route_fallback",
            "message": "This step needs a human follow-up. I can open the contact path so the site team can continue.",
            "reason": "Human confirmation required for this website flow.",
        }


def contact_route_path(routes: dict[str, str]) -> str:
    for key in ("contact", "support", "help", "callback"):
        path = clean_text(routes.get(key))
        if path:
            return path
    return ""


def is_handoff_action(action_name: str) -> bool:
    action = get_action(action_name)
    return bool(action and action.family == "lead" and normalize_action_name(action_name).startswith("HANDOFF_TO_"))
