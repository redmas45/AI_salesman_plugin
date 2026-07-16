"""Crawler runtime orchestration for catalog ingestion."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from agent.ingestion_helpers.ingestion_crawl_config import PRODUCT_URL_KEYWORDS
from agent.ingestion_helpers.ingestion_reports import CrawlReport

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrawlDependencies:
    sanitize_site_id: Callable[[str], str]
    crawl_vertical_key: Callable[[str], str]
    fetch_api_catalog_products: Callable[[str, int], Awaitable[list[dict[str, Any]]]]
    discover_crawl_entrypoints: Callable[..., Awaitable[list[str]]]
    html_harvest_factory: Callable[[], Any]
    is_allowed_crawl_url: Callable[[str, str], bool]
    ranked_unique_urls: Callable[..., list[str]]
    build_candidates_from_html: Callable[..., list[dict[str, Any]]]
    dedupe_products: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
    build_crawl_report: Callable[..., CrawlReport]
    persist_catalog: Callable[..., int]
    console_print: Callable[[str], None]
    data_root: Path


async def async_web_crawl(
    start_url: str,
    *,
    deps: CrawlDependencies,
    max_pages: int = 60,
    max_depth: int = 3,
    site_id: str | None = None,
    reconcile_missing: bool = True,
    source_name: str = "custom_url_crawler",
    timeout: int = 12,
) -> str:
    from crawl4ai import AsyncWebCrawler

    crawl_started = monotonic()
    if not start_url:
        raise ValueError("Start URL is required.")
    if max_pages <= 0 or max_depth < 0:
        raise ValueError("max_pages and max_depth must be positive.")

    resolved_site_id = deps.sanitize_site_id(site_id or start_url)
    vertical_key = deps.crawl_vertical_key(resolved_site_id)
    seed = urldefrag(start_url)[0]
    parsed_seed = urlparse(seed)
    if not parsed_seed.netloc:
        raise ValueError("Start URL must include a host.")

    crawl_state = _initial_crawl_state()
    api_catalog_products = await deps.fetch_api_catalog_products(seed, timeout)
    extracted_products: list[dict[str, Any]] = list(api_catalog_products)

    if not api_catalog_products:
        html_products = await _crawl_html_products(
            seed,
            timeout,
            max_pages,
            max_depth,
            vertical_key,
            parsed_seed.netloc.lower(),
            crawl_state,
            deps,
        )
        extracted_products.extend(html_products)

    if not extracted_products:
        logger.warning("Crawler did not extract any product-like records.")

    deduped_products = deps.dedupe_products(extracted_products)
    source_label = "api catalog" if api_catalog_products else "advanced html crawl"
    source_type = "api_catalog" if api_catalog_products else "html_crawl"
    report = deps.build_crawl_report(
        site_id=resolved_site_id,
        site_url=seed,
        source_type=source_type,
        pages_visited=crawl_state["pages_seen"],
        pages_failed=crawl_state["pages_failed"],
        pages_blocked=crawl_state["pages_blocked"],
        products=deduped_products,
        failed_urls=crawl_state["failed_urls"],
        blocked_urls=crawl_state["blocked_urls"],
        stopped_by_limit=crawl_state["stopped_by_limit"],
        duration_ms=(monotonic() - crawl_started) * 1000,
    )
    deps.console_print(
        f"Crawler summary ({source_label}): visited {crawl_state['pages_seen']} pages, "
        f"extracted {len(extracted_products)} raw candidates, deduped to {len(deduped_products)}."
    )

    _write_crawl_json(deps.data_root, resolved_site_id, deduped_products)

    await asyncio.to_thread(
        deps.persist_catalog,
        resolved_site_id,
        deduped_products,
        reconcile_missing=reconcile_missing,
        source_name=source_name,
        crawl_report=report.to_dict(),
        vertical_key=vertical_key,
    )
    return resolved_site_id


def sync_web_crawl(*args: Any, **kwargs: Any) -> str:
    return asyncio.run(async_web_crawl(*args, **kwargs))


def _initial_crawl_state() -> dict[str, Any]:
    return {
        "visited": set(),
        "pages_seen": 0,
        "pages_failed": 0,
        "pages_blocked": 0,
        "failed_urls": [],
        "blocked_urls": [],
        "product_links": set(),
        "stopped_by_limit": False,
    }


async def _crawl_html_products(
    seed: str,
    timeout: int,
    max_pages: int,
    max_depth: int,
    vertical_key: str,
    allowed_host: str,
    crawl_state: dict[str, Any],
    deps: CrawlDependencies,
) -> list[dict[str, Any]]:
    entrypoints = await deps.discover_crawl_entrypoints(
        seed,
        timeout,
        max_urls=max_pages * 3,
        vertical_key=vertical_key,
    )
    if not entrypoints:
        entrypoints = [seed]

    queue: deque[tuple[str, int]] = deque((url, 0) for url in entrypoints)
    queued: set[str] = set(entrypoints)
    extracted_products: list[dict[str, Any]] = []

    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler(verbose=False) as crawler:
        while queue and len(crawl_state["visited"]) < max_pages:
            extracted_products.extend(
                await _crawl_one_page(
                    crawler,
                    queue,
                    queued,
                    max_depth,
                    vertical_key,
                    allowed_host,
                    crawl_state,
                    deps,
                )
            )

        if len(crawl_state["visited"]) >= max_pages:
            crawl_state["stopped_by_limit"] = True

    return extracted_products


async def _crawl_one_page(
    crawler: Any,
    queue: deque[tuple[str, int]],
    queued: set[str],
    max_depth: int,
    vertical_key: str,
    allowed_host: str,
    crawl_state: dict[str, Any],
    deps: CrawlDependencies,
) -> list[dict[str, Any]]:
    page_url, depth = queue.popleft()
    page_url = urldefrag(page_url)[0]
    if page_url in crawl_state["visited"]:
        return []
    crawl_state["visited"].add(page_url)

    result = await _safe_crawl_page(crawler, page_url, crawl_state)
    if result is None:
        return []

    text = result.html
    if not text:
        return []

    parser = deps.html_harvest_factory()
    parser.feed(text)
    crawl_state["pages_seen"] += 1
    _queue_discovered_links(
        parser.links,
        page_url,
        queue,
        queued,
        depth,
        max_depth,
        vertical_key,
        allowed_host,
        crawl_state,
        deps,
    )
    return deps.build_candidates_from_html(page_url, text, vertical_key=vertical_key)


async def _safe_crawl_page(crawler: Any, page_url: str, crawl_state: dict[str, Any]) -> Any | None:
    try:
        result = await crawler.arun(url=page_url)
    except Exception as exc:
        logger.info("Crawl failed for %s: %s", page_url, exc)
        _record_failed_url(crawl_state, page_url)
        return None
    if not result.success:
        _record_failed_url(crawl_state, page_url)
        return None
    return result


def _queue_discovered_links(
    links: list[str],
    page_url: str,
    queue: deque[tuple[str, int]],
    queued: set[str],
    depth: int,
    max_depth: int,
    vertical_key: str,
    allowed_host: str,
    crawl_state: dict[str, Any],
    deps: CrawlDependencies,
) -> None:
    discovered_links: list[str] = []
    for link in links:
        next_url = urldefrag(urljoin(page_url, link))[0]
        if not deps.is_allowed_crawl_url(next_url, allowed_host):
            _record_blocked_url(crawl_state, next_url)
            continue
        if any(token in next_url.lower() for token in PRODUCT_URL_KEYWORDS):
            crawl_state["product_links"].add(next_url)
        if next_url in crawl_state["visited"] or next_url in queued or depth >= max_depth:
            continue
        discovered_links.append(next_url)

    for next_url in deps.ranked_unique_urls(discovered_links, vertical_key=vertical_key):
        queued.add(next_url)
        queue.append((next_url, depth + 1))


def _record_failed_url(crawl_state: dict[str, Any], page_url: str) -> None:
    crawl_state["pages_failed"] += 1
    if len(crawl_state["failed_urls"]) < 50:
        crawl_state["failed_urls"].append(page_url)


def _record_blocked_url(crawl_state: dict[str, Any], page_url: str) -> None:
    crawl_state["pages_blocked"] += 1
    if len(crawl_state["blocked_urls"]) < 50:
        crawl_state["blocked_urls"].append(page_url)


def _write_crawl_json(data_root: Path, site_id: str, products: list[dict[str, Any]]) -> None:
    data_dir = data_root / site_id
    data_dir.mkdir(parents=True, exist_ok=True)
    crawl_json_path = data_dir / "crawl.json"
    with open(crawl_json_path, "w", encoding="utf-8") as file:
        json.dump(products, file, indent=2, ensure_ascii=False)
