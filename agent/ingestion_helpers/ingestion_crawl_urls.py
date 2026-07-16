"""Crawl URL filtering, ranking, and sitemap parsing helpers."""

from __future__ import annotations

import gzip
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urldefrag, urljoin, urlparse

import httpx

from agent.ingestion_helpers.ingestion_catalog_urls import site_base_url
from agent.ingestion_helpers.ingestion_normalization import clean_text
from agent.verticals.discovery_profiles import discovery_paths_for, high_value_url_keywords_for
from agent.verticals.registry import DEFAULT_VERTICAL_KEY

logger = logging.getLogger(__name__)


PRODUCT_URL_KEYWORDS = (
    "/product/",
    "/products/",
    "/item/",
    "/items/",
    "/p/",
    "product_id=",
    "variant=",
    "sku=",
)
LOW_VALUE_URL_KEYWORDS = (
    "/blog",
    "/news",
    "/about",
    "/contact",
    "/privacy",
    "/terms",
    "/support",
    "/faq",
)
SKIP_PATH_MARKERS = (
    "/admin",
    "/wp-admin",
    "/account",
    "/login",
    "/logout",
    "/register",
    "/checkout",
    "/cart",
    "/wishlist",
    "/auth",
)
SKIP_URL_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".pdf",
    ".zip",
)


def path_has_marker(path: str, marker: str) -> bool:
    marker = marker.rstrip("/")
    return path == marker or path.startswith(f"{marker}/") or f"{marker}/" in path


def is_allowed_crawl_url(url: str, allowed_host: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() != allowed_host:
        return False

    path = parsed.path.lower() or "/"
    if any(path_has_marker(path, marker) for marker in SKIP_PATH_MARKERS):
        return False
    if path.endswith(SKIP_URL_EXTENSIONS):
        return False
    return True


def url_priority(url: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> int:
    parsed = urlparse(url)
    target = f"{parsed.path.lower()}?{parsed.query.lower()}"
    score = 0
    if any(token in target for token in PRODUCT_URL_KEYWORDS):
        score += 100
    if any(token in target for token in high_value_url_keywords_for(vertical_key)):
        score += 50
    if "page=" in target or "paged=" in target:
        score += 10
    if any(token in target for token in LOW_VALUE_URL_KEYWORDS):
        score -= 40
    return score


def ranked_unique_urls(urls: list[str], vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for url in urls:
        clean = urldefrag(url)[0]
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return sorted(unique, key=lambda item: (-url_priority(item, vertical_key), len(urlparse(item).path), item))


def common_discovery_urls(seed_url: str, vertical_key: str) -> list[str]:
    base = site_base_url(seed_url)
    return [urljoin(base, path) for path in discovery_paths_for(vertical_key)]


def extract_sitemap_locations(xml_text: str) -> list[str]:
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return []

    locations: list[str] = []
    for element in root.iter():
        if element.tag.lower().endswith("loc") and element.text:
            loc = clean_text(element.text)
            if loc:
                locations.append(loc)
    return locations


def extract_robots_sitemaps(robots_text: str) -> list[str]:
    urls: list[str] = []
    for line in (robots_text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("sitemap:"):
            url = clean_text(line.split(":", 1)[1])
            if url:
                urls.append(url)
    return urls


def decode_sitemap_response(response: httpx.Response, sitemap_url: str) -> str:
    content = response.content
    if sitemap_url.lower().endswith(".gz"):
        try:
            return gzip.decompress(content).decode(response.encoding or "utf-8", errors="replace")
        except (gzip.BadGzipFile, OSError, UnicodeDecodeError) as exc:
            logger.debug("Sitemap gzip decode failed for %s: %s", sitemap_url, exc)
            return response.text
    return response.text


async def fetch_sitemap_tree(
    client: httpx.AsyncClient,
    sitemap_url: str,
    allowed_host: str,
    *,
    max_urls: int,
    seen_sitemaps: set[str],
    vertical_key: str,
) -> list[str]:
    sitemap_url = urldefrag(sitemap_url)[0]
    if sitemap_url in seen_sitemaps or len(seen_sitemaps) >= 25:
        return []
    seen_sitemaps.add(sitemap_url)

    try:
        response = await client.get(sitemap_url, headers={"Accept": "application/xml,text/xml,*/*"})
        if response.status_code in {401, 403, 404, 405}:
            return []
        response.raise_for_status()
    except Exception as exc:
        logger.info("Sitemap unavailable at %s: %s", sitemap_url, exc)
        return []

    locations = extract_sitemap_locations(decode_sitemap_response(response, sitemap_url))
    urls: list[str] = []
    for loc in locations:
        if len(urls) >= max_urls:
            break
        loc_url = urljoin(sitemap_url, loc)
        parsed = urlparse(loc_url)
        if parsed.netloc.lower() != allowed_host:
            continue
        lower_path = parsed.path.lower()
        if lower_path.endswith((".xml", ".xml.gz")) or "sitemap" in lower_path:
            nested = await fetch_sitemap_tree(
                client,
                loc_url,
                allowed_host,
                max_urls=max_urls - len(urls),
                seen_sitemaps=seen_sitemaps,
                vertical_key=vertical_key,
            )
            urls.extend(nested)
            continue
        if is_allowed_crawl_url(loc_url, allowed_host):
            urls.append(urldefrag(loc_url)[0])

    return urls[:max_urls]


async def discover_sitemap_urls(
    seed_url: str,
    timeout: int,
    max_urls: int,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
) -> list[str]:
    allowed_host = urlparse(seed_url).netloc.lower()
    base = site_base_url(seed_url)
    sitemap_candidates = [urljoin(base, "/sitemap.xml")]

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        try:
            robots = await client.get(urljoin(base, "/robots.txt"))
            if robots.status_code < 400:
                sitemap_candidates.extend(extract_robots_sitemaps(robots.text))
        except Exception as exc:
            logger.info("robots.txt unavailable for %s: %s", base, exc)

        urls: list[str] = []
        seen_sitemaps: set[str] = set()
        for sitemap_url in list(dict.fromkeys(sitemap_candidates)):
            if len(urls) >= max_urls:
                break
            urls.extend(
                await fetch_sitemap_tree(
                    client,
                    sitemap_url,
                    allowed_host,
                    max_urls=max_urls - len(urls),
                    seen_sitemaps=seen_sitemaps,
                    vertical_key=vertical_key,
                )
            )

    return ranked_unique_urls(urls, vertical_key=vertical_key)[:max_urls]


async def discover_crawl_entrypoints(
    seed_url: str,
    timeout: int,
    max_urls: int,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
) -> list[str]:
    allowed_host = urlparse(seed_url).netloc.lower()
    sitemap_urls = await discover_sitemap_urls(seed_url, timeout, max_urls=max_urls, vertical_key=vertical_key)
    candidates = [seed_url, *sitemap_urls, *common_discovery_urls(seed_url, vertical_key)]
    candidates = [url for url in candidates if is_allowed_crawl_url(url, allowed_host)]
    return ranked_unique_urls(candidates, vertical_key=vertical_key)[:max_urls]
