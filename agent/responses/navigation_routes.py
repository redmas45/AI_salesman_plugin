"""Navigation route maps and text matching helpers."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from agent.responses.navigation_aliases import is_generic_route_alias, route_alias_key, semantic_route_alias_keys

GENERIC_NAVIGATION_TERMS = {
    "about",
    "cart",
    "checkout",
    "claim",
    "claims",
    "contact",
    "help",
    "home",
    "main",
    "plan",
    "plans",
    "policy",
    "policies",
    "quote",
    "quotes",
    "renew",
    "renewal",
    "shop",
    "start",
    "store",
    "support",
}


def navigation_route_terms(
    site_id: str,
    page_context: dict[str, Any] | None = None,
    *,
    route_map: Any,
) -> list[tuple[str, str]]:
    routes = route_map(site_id, page_context)
    terms: dict[str, str] = {
        "home": "home",
        "main": "home",
        "start": "home",
        "shop": "shop",
        "store": "shop",
        "cart": "cart",
        "basket": "cart",
        "checkout": "checkout",
        "support": "support",
        "help": "support",
        "contact": "contact",
        "about": "about",
        "plans": "plans",
        "plan": "plans",
        "policies": "policies",
        "policy": "policies",
        "claims": "claims",
        "claim": "claims",
        "renewal": "renewal",
        "renew": "renewal",
        "quote": "quote",
        "quotes": "quote",
    }
    for key, path in routes.items():
        page = route_page_key(key, path)
        if not page:
            continue
        terms[normalize_navigation_text(key)] = page
        terms[normalize_navigation_text(page)] = page
        last_segment = route_last_segment(path)
        if last_segment:
            terms[normalize_navigation_text(last_segment)] = page
    return sorted(terms.items(), key=lambda item: len(item[0]), reverse=True)


def navigation_match_rank(term: str) -> tuple[int, int]:
    clean_term = normalize_navigation_text(term)
    specificity = 0 if clean_term in GENERIC_NAVIGATION_TERMS else 1
    return specificity, len(clean_term)


def client_navigation_route_map(
    site_id: str,
    page_context: dict[str, Any] | None = None,
    *,
    get_client_detail: Any,
    recoverable_errors: tuple[type[BaseException], ...],
    logger: Any,
) -> dict[str, str]:
    try:
        client = get_client_detail(site_id)
    except recoverable_errors as exc:
        logger.info("PIPELINE | navigation routes unavailable for %s: %s", site_id, exc)
        client_routes: dict[str, str] = {}
    else:
        vertical_config = client.get("vertical_config") if isinstance(client, dict) else {}
        client_routes = navigation_route_map_from_config(vertical_config if isinstance(vertical_config, dict) else {})
    runtime_routes = navigation_route_map_from_config(page_context or {})
    return {**client_routes, **runtime_routes}


def navigation_route_map_from_config(vertical_config: dict[str, Any]) -> dict[str, str]:
    routes: dict[str, str] = {}
    raw_routes = vertical_config.get("routes")
    if isinstance(raw_routes, dict):
        for key, path in raw_routes.items():
            add_navigation_route(routes, key, path)

    actions = vertical_config.get("actions")
    if isinstance(actions, dict):
        _add_action_routes(routes, actions)

    _add_candidate_routes(routes, safe_config_list(vertical_config.get("action_candidates")))
    _add_interaction_routes(routes, safe_config_list(vertical_config.get("interaction_events")))
    _add_link_routes(routes, safe_config_list(vertical_config.get("links")), vertical_config.get("url") or vertical_config.get("origin"))
    return routes


def add_navigation_route(routes: dict[str, str], alias: Any, raw_path: Any) -> None:
    path = observed_navigation_path(raw_path)
    key = safe_page_key(alias)
    if not key or not path or is_generic_route_alias(key):
        return
    page = path.strip("/") or "home"
    routes.setdefault(key, path)
    routes.setdefault(page, path)
    last_segment = route_last_segment(path)
    if last_segment:
        routes.setdefault(safe_page_key(last_segment), path)
    for semantic_alias in semantic_route_alias_keys(key, last_segment, page):
        routes.setdefault(semantic_alias, path)


def observed_navigation_path(value: Any, origin: Any = "") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower().startswith(("http://", "https://")):
        return _observed_absolute_navigation_path(text, origin)
    return same_origin_path(text)


def same_origin_path(path: Any) -> str:
    text = str(path or "").strip()
    lowered = text.lower()
    if (
        not text
        or text.startswith("//")
        or lowered.startswith(("http://", "https://", "javascript:", "data:"))
    ):
        return ""
    return text if text.startswith("/") else f"/{text}"


def safe_config_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def route_page_key(key: str, path: str) -> str:
    clean_path = same_origin_path(path)
    if clean_path:
        return clean_path.strip("/") or "home"
    clean_key = safe_page_key(key)
    if clean_key:
        return clean_key
    return safe_page_key(route_last_segment(path))


def route_last_segment(path: str) -> str:
    text = str(path or "").split("?", 1)[0].split("#", 1)[0].strip("/")
    if not text:
        return "home"
    return text.split("/")[-1]


def safe_page_key(value: Any) -> str:
    text = route_alias_key(value).strip("-/")
    if not text:
        return ""
    return text[:80]


def navigation_term_matches(text: str, term: str) -> bool:
    clean_term = normalize_navigation_text(term)
    if not clean_term:
        return False
    return bool(re.search(rf"\b{re.escape(clean_term)}\b", text))


def normalize_navigation_text(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s_-]+", " ", str(value or "").lower())
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _add_action_routes(routes: dict[str, str], actions: dict[Any, Any]) -> None:
    for _action_name, config in actions.items():
        if not isinstance(config, dict):
            continue
        if str(config.get("type") or "").lower() not in {"navigate", "route"}:
            continue
        path = observed_navigation_path(config.get("path") or config.get("page_path") or config.get("pagePath"))
        if path:
            add_navigation_route(routes, config.get("label"), path)


def _add_candidate_routes(routes: dict[str, str], candidates: list[Any]) -> None:
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
            add_navigation_route(routes, candidate.get("label"), path)


def _add_interaction_routes(routes: dict[str, str], events: list[Any]) -> None:
    for event in events:
        if not isinstance(event, dict):
            continue
        path = observed_navigation_path(event.get("href"), event.get("origin"))
        if not path:
            continue
        add_navigation_route(routes, event.get("label"), path)
        add_navigation_route(routes, event.get("matched_label"), path)


def _add_link_routes(routes: dict[str, str], links: list[Any], origin: Any) -> None:
    for link in links:
        if not isinstance(link, dict):
            continue
        path = observed_navigation_path(link.get("href"), origin)
        if not path:
            continue
        add_navigation_route(routes, link.get("label"), path)
        add_navigation_route(routes, link.get("text"), path)


def _observed_absolute_navigation_path(value: str, origin: Any = "") -> str:
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
        return same_origin_path(path)
    except ValueError:
        return ""
