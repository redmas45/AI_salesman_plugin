"""URL candidate discovery for server-side flow discovery."""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from agent.verticals.discovery_profiles import discovery_paths_for, high_value_url_keywords_for

MAX_SITEMAP_URLS = 80
SITEMAP_PATHS = ("/sitemap.xml", "/sitemap_index.xml")
ROBOTS_PATH = "/robots.txt"


def candidate_urls(base_url: str, vertical_key: str) -> list[str]:
    paths = discovery_paths_for(vertical_key)
    keywords = set(high_value_url_keywords_for(vertical_key))
    urls = [base_url]
    urls.extend(urljoin(base_url, path) for path in paths)
    urls.extend(urljoin(base_url, f"/{keyword}") for keyword in sorted(keywords)[:8])
    return list(dict.fromkeys(urls))


def prioritized_candidate_urls(
    base_url: str,
    vertical_key: str,
    sitemap_urls: list[str],
    disallowed_paths: list[str],
) -> list[str]:
    urls = [*sitemap_urls, *candidate_urls(base_url, vertical_key)]
    allowed = [url for url in urls if _same_origin_url(url, base_url) and _robots_allowed(url, disallowed_paths)]
    keywords = tuple(high_value_url_keywords_for(vertical_key))
    sitemap_set = set(sitemap_urls)
    return sorted(dict.fromkeys(allowed), key=lambda url: _url_priority(url, base_url, keywords, sitemap_set))


async def robots_disallow_paths(client: httpx.AsyncClient, base_url: str) -> list[str]:
    try:
        response = await client.get(urljoin(base_url, ROBOTS_PATH), headers={"Accept": "text/plain"})
    except (httpx.HTTPError, OSError, ValueError):
        return []
    if response.status_code >= 400:
        return []
    return parse_robots_disallow(response.text)


async def sitemap_urls(client: httpx.AsyncClient, base_url: str, vertical_key: str) -> list[str]:
    urls: list[str] = []
    keywords = tuple(high_value_url_keywords_for(vertical_key))
    for path in SITEMAP_PATHS:
        try:
            response = await client.get(urljoin(base_url, path), headers={"Accept": "application/xml,text/xml,text/plain"})
        except (httpx.HTTPError, OSError, ValueError):
            continue
        if response.status_code >= 400:
            continue
        urls.extend(parse_sitemap_urls(response.text, base_url, keywords))
    return list(dict.fromkeys(urls))[:MAX_SITEMAP_URLS]


def parse_robots_disallow(robots_text: str) -> list[str]:
    paths: list[str] = []
    active = False
    for raw_line in str(robots_text or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            active = value == "*"
            continue
        if active and key == "disallow" and value:
            paths.append(value)
    return paths[:MAX_SITEMAP_URLS]


def parse_sitemap_urls(sitemap_text: str, base_url: str, keywords: tuple[str, ...]) -> list[str]:
    urls: list[str] = []
    for match in re.findall(r"<loc>\s*(.*?)\s*</loc>", str(sitemap_text or ""), flags=re.IGNORECASE | re.DOTALL):
        url = html.unescape(match.strip())
        same_origin = _same_origin_url(url, base_url)
        if same_origin and _is_high_value_url(same_origin, keywords):
            urls.append(same_origin)
    return urls[:MAX_SITEMAP_URLS]


def _robots_allowed(url: str, disallowed_paths: list[str]) -> bool:
    path = urlparse(url).path or "/"
    for raw_path in disallowed_paths:
        rule = str(raw_path or "").strip()
        if rule and rule != "/" and path.startswith(rule.rstrip("*")):
            return False
        if rule == "/":
            return False
    return True


def _url_priority(url: str, base_url: str, keywords: tuple[str, ...], sitemap_urls: set[str]) -> tuple[int, str]:
    if url.rstrip("/") == base_url.rstrip("/"):
        return (0, url)
    if url in sitemap_urls and _is_high_value_url(url, keywords):
        return (1, url)
    return (2 if _is_high_value_url(url, keywords) else 3, url)


def _is_high_value_url(url: str, keywords: tuple[str, ...]) -> bool:
    path = urlparse(url).path.lower()
    return any(keyword.replace(" ", "-").lower() in path for keyword in keywords)


def _same_origin_url(value: Any, base_url: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        url = urljoin(base_url, text)
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
    except ValueError:
        return ""
    if parsed_url.scheme not in {"http", "https"}:
        return ""
    if parsed_url.netloc != parsed_base.netloc:
        return ""
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path or '/'}{('?' + parsed_url.query) if parsed_url.query else ''}"
