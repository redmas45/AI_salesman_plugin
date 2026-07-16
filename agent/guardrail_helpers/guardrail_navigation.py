"""Navigation route validation helpers for output guardrails."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from agent.responses.navigation_aliases import is_generic_route_alias, route_alias_key, semantic_route_alias_keys


def validate_navigation_params(
    params: dict,
    *,
    valid_pages: set[str],
    adapter_routes: dict[str, str] | None = None,
) -> dict | None:
    page = str(params.get("page", "")).strip().lower().strip("/")
    if page in valid_pages or page.startswith("category/") or page.startswith("shop?q="):
        return {"page": page}
    route_target = adapter_route_target(page, adapter_routes or {})
    if route_target:
        return {"page": route_target}
    return None


def adapter_route_target(page: str, adapter_routes: dict[str, str]) -> str:
    if not page:
        return ""
    normalized_page = page.strip("/")
    normalized_page_key = route_alias_key(normalized_page)
    for key, path in adapter_routes.items():
        route_key = str(key or "").strip().lower().strip("/")
        route_path = clean_same_origin_path(path)
        if (normalized_page == route_key or normalized_page_key == route_key) and route_path:
            return route_path.strip("/") or route_key
        if route_path and normalized_page == route_path.strip("/"):
            return route_path.strip("/")
    return ""


def clean_same_origin_path(value: Any) -> str:
    path = str(value or "").strip()
    lowered = path.lower()
    if (
        not path
        or path.startswith("//")
        or lowered.startswith(("http://", "https://", "javascript:", "data:"))
    ):
        return ""
    return path if path.startswith("/") else f"/{path}"


def navigation_route_map(vertical_config: dict[str, Any]) -> dict[str, str]:
    routes: dict[str, str] = {}
    raw_routes = vertical_config.get("routes")
    if isinstance(raw_routes, dict):
        for name, path in raw_routes.items():
            add_route_alias(routes, name, path)

    raw_actions = vertical_config.get("actions")
    if isinstance(raw_actions, dict):
        add_action_routes(routes, raw_actions)

    add_candidate_routes(routes, safe_list(vertical_config.get("action_candidates")))
    add_interaction_routes(routes, safe_list(vertical_config.get("interaction_events")))
    add_link_routes(routes, safe_list(vertical_config.get("links")), vertical_config.get("url") or vertical_config.get("origin"))
    return routes


def add_action_routes(routes: dict[str, str], raw_actions: dict[Any, Any]) -> None:
    for _action_name, config in raw_actions.items():
        if not isinstance(config, dict):
            continue
        if str(config.get("type") or "").lower() not in {"navigate", "route"}:
            continue
        path = observed_navigation_path(config.get("path") or config.get("page_path") or config.get("pagePath"))
        if not path:
            continue
        add_route_alias(routes, config.get("label"), path)


def add_candidate_routes(routes: dict[str, str], candidates: list[Any]) -> None:
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if (
            str(candidate.get("type") or "").lower() not in {"navigate", "route"}
            and str(candidate.get("kind") or "").lower() != "route"
        ):
            continue
        path = observed_navigation_path(candidate.get("path"), candidate.get("origin"))
        if path:
            add_route_alias(routes, candidate.get("label"), path)


def add_interaction_routes(routes: dict[str, str], events: list[Any]) -> None:
    for event in events:
        if not isinstance(event, dict):
            continue
        path = observed_navigation_path(event.get("href"), event.get("origin"))
        if not path:
            continue
        add_route_alias(routes, event.get("label"), path)
        add_route_alias(routes, event.get("matched_label"), path)


def add_link_routes(routes: dict[str, str], links: list[Any], origin: Any) -> None:
    for link in links:
        if not isinstance(link, dict):
            continue
        path = observed_navigation_path(link.get("href"), origin)
        if not path:
            continue
        add_route_alias(routes, link.get("label"), path)
        add_route_alias(routes, link.get("text"), path)


def add_route_alias(routes: dict[str, str], alias: Any, raw_path: Any) -> None:
    path = observed_navigation_path(raw_path)
    key = route_alias_key(alias)
    if is_generic_route_alias(key):
        return
    if not key or not path:
        return
    routes.setdefault(key, path)
    routes.setdefault(path.strip("/").lower(), path)
    last_segment = path.split("?", 1)[0].split("#", 1)[0].strip("/").split("/")[-1]
    if last_segment:
        routes.setdefault(route_alias_key(last_segment), path)
    for semantic_alias in semantic_route_alias_keys(key, last_segment):
        routes.setdefault(semantic_alias, path)


def observed_navigation_path(value: Any, origin: Any = "") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower().startswith(("http://", "https://")):
        return observed_absolute_navigation_path(text, origin)
    return clean_same_origin_path(text)


def observed_absolute_navigation_path(value: str, origin: Any = "") -> str:
    try:
        parsed = urlparse(value)
        if origin:
            parsed_origin = urlparse(str(origin))
            if (parsed.scheme, parsed.netloc) != (parsed_origin.scheme, parsed_origin.netloc):
                return ""
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        if parsed.fragment:
            path += f"#{parsed.fragment}"
        return clean_same_origin_path(path)
    except ValueError:
        return ""


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
