"""Catalog ingestion utilities for crawler-based sources."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

import httpx

from agent.ingestion_helpers import (
    ingestion_api_catalog,
    ingestion_catalog_normalizers,
    ingestion_crawl_urls,
    ingestion_crawler_runtime,
    ingestion_html_candidates,
    ingestion_persistence,
)
from agent.ingestion_helpers.ingestion_catalog_urls import (
    CATALOG_ENDPOINT_PATHS,
    GENERIC_API_CATALOG_MAX_PAGES,
    GENERIC_API_CATALOG_PAGE_SIZE,
    SHOPIFY_CATALOG_MAX_PAGES,
    SHOPIFY_CATALOG_PAGE_LIMIT,
    WOO_CATALOG_MAX_PAGES,
    catalog_endpoint_for as _catalog_endpoint_for,
    catalog_endpoints_for as _catalog_endpoints_for,
    catalog_normalization_url as _catalog_normalization_url,
    catalog_page_urls as _catalog_page_urls,
    catalog_response_reached_last_page as _catalog_response_reached_last_page,
    catalog_seed_candidates as _catalog_seed_candidates,
    catalog_url_with_params as _catalog_url_with_params,
    is_generic_products_api as _is_generic_products_api,
    site_base_url as _site_base_url,
)
from agent.ingestion_helpers.ingestion_normalization import (
    clean_text as _clean_text,
    first as _first,
    looks_like_noise_name as _looks_like_noise_name,
    normalized_candidate_name as _normalized_candidate_name,
    parse_price as _parse_price,
    sanitize_site_id,
    stable_id as _stable_id,
    strip_html as _strip_html,
    to_float as _to_float_impl,
    to_positive_int_id as _to_positive_int_id,
)
from agent.ingestion_helpers.ingestion_product_rows import (
    derive_category_from_url as _derive_category_from_url_impl,
    image_url_from_value as _image_url_from_value_impl,
    normalize_product_row as _normalize_product_row_impl,
    optional_int as _optional_int_impl,
    term_names as _term_names_impl,
    to_tags as _to_tags_impl,
)
from agent.ingestion_helpers.ingestion_reports import CrawlReport
from agent.verticals.registry import DEFAULT_VERTICAL_KEY

logger = logging.getLogger(__name__)


def _safe_console_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_message = str(message).encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_message)


def _legacy_normalized_candidate_name(value: str) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"(?:\s+|^)(?:₹|rs\.?|inr|\$)\s*[0-9]+(?:[.,][0-9]{1,2})?\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _legacy_looks_like_noise_name(value: str) -> bool:
    lowered = _normalized_candidate_name(value)
    if not lowered:
        return True

    utility_tokens = {
        "relative",
        "block",
        "inline-block",
        "h-full",
        "w-full",
        "aspect-square",
        "sr-only",
        "pointer-events-none",
    }
    tokens = set(lowered.split())
    if len(tokens & utility_tokens) >= 2:
        return True

    if lowered.startswith(("relative ", "block ", "inline-block ")):
        return True

    if "," in lowered and float(_parse_price(lowered)) <= 0:
        return True

    return False


_decode_next_payload = ingestion_html_candidates.decode_next_payload
_collect_react_node_texts = ingestion_html_candidates._collect_react_node_texts
_extract_product_from_react_payload = ingestion_html_candidates._extract_product_from_react_payload
_extract_nextjs_flight_products = ingestion_html_candidates.extract_nextjs_flight_products
_image_url_from_value = _image_url_from_value_impl
_term_names = _term_names_impl
_looks_like_shopify_product = ingestion_catalog_normalizers.looks_like_shopify_product
_normalize_shopify_product = ingestion_catalog_normalizers.normalize_shopify_product
_woocommerce_price = ingestion_catalog_normalizers.woocommerce_price
_looks_like_woocommerce_product = ingestion_catalog_normalizers.looks_like_woocommerce_product
_normalize_woocommerce_product = ingestion_catalog_normalizers.normalize_woocommerce_product


def _extract_platform_variants(
    raw: dict[str, Any],
    product: dict[str, Any],
    source_url: str,
) -> list[dict[str, Any]]:
    return ingestion_catalog_normalizers.extract_platform_variants(raw, product, source_url)


def _normalize_with_platform_adapter(
    raw: dict[str, Any],
    source_url: str,
) -> dict[str, Any] | None:
    return ingestion_catalog_normalizers.normalize_with_platform_adapter(raw, source_url)


def _with_platform_variants(
    raw: dict[str, Any],
    product: dict[str, Any] | None,
    source_url: str,
) -> dict[str, Any] | None:
    return ingestion_catalog_normalizers.with_platform_variants(raw, product, source_url)


_normalize_embedded_json_product = ingestion_catalog_normalizers.normalize_embedded_json_product
_extract_products_from_json_tree = ingestion_catalog_normalizers.extract_products_from_json_tree
_iter_script_json_payloads = ingestion_catalog_normalizers.iter_script_json_payloads


def _extract_embedded_json_products(html_text: str, source_url: str) -> list[dict[str, Any]]:
    return ingestion_catalog_normalizers.extract_embedded_json_products(
        html_text,
        source_url,
        dedupe_products=_dedupe_products,
    )


_to_tags = _to_tags_impl
_normalize_product_row = _normalize_product_row_impl
_normalize_api_catalog_product = ingestion_catalog_normalizers.normalize_api_catalog_product
_looks_like_insurance_policy_api = ingestion_catalog_normalizers.looks_like_insurance_policy_api
_normalize_policy_catalog_product = ingestion_catalog_normalizers.normalize_policy_catalog_product
_insurance_category_label = ingestion_catalog_normalizers.insurance_category_label
_policy_catalog_description = ingestion_catalog_normalizers.policy_catalog_description
_policy_catalog_tags = ingestion_catalog_normalizers.policy_catalog_tags
_policy_catalog_policy_payload = ingestion_catalog_normalizers.policy_catalog_policy_payload
_policy_catalog_risk_tags = ingestion_catalog_normalizers.policy_catalog_risk_tags
_optional_int = _optional_int_impl
_to_float = _to_float_impl


def _normalize_catalog_payload(payload: Any, api_url: str, *, merge_same_name: bool = True) -> list[dict[str, Any]]:
    return ingestion_api_catalog.normalize_catalog_payload(
        payload,
        api_url,
        merge_same_name=merge_same_name,
    )


async def _fetch_api_catalog_products(seed_url: str, timeout: int) -> list[dict[str, Any]]:
    return await ingestion_api_catalog.fetch_api_catalog_products(seed_url, timeout)


async def _fetch_catalog_endpoint_pages(
    client: httpx.AsyncClient,
    api_url: str,
) -> list[dict[str, Any]]:
    return await ingestion_api_catalog.fetch_catalog_endpoint_pages(client, api_url)


_HtmlHarvest = ingestion_html_candidates.HtmlHarvest


def _extract_jsonld_products(html_text: str, source_url: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[dict[str, Any]]:
    return ingestion_html_candidates.extract_jsonld_products(html_text, source_url, vertical_key=vertical_key)


def _jsonld_type_text(value: Any) -> str:
    return ingestion_html_candidates.jsonld_type_text(value)


def _jsonld_type_texts(value: Any) -> set[str]:
    return ingestion_html_candidates.jsonld_type_texts(value)


def _normalize_jsonld_item(raw: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    return ingestion_html_candidates.normalize_jsonld_item(raw, source_url)


def _normalize_generic_jsonld_item(
    raw: dict[str, Any],
    source_url: str,
    *,
    vertical_key: str,
) -> dict[str, Any] | None:
    return ingestion_html_candidates.normalize_generic_jsonld_item(raw, source_url, vertical_key=vertical_key)


def _derive_category_from_url(url: str) -> str:
    return _derive_category_from_url_impl(url)


def _build_candidates_from_html(url: str, html_text: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[dict[str, Any]]:
    return ingestion_html_candidates.build_candidates_from_html(url, html_text, vertical_key=vertical_key)


def _has_vertical_signal(text: str, url: str, *, vertical_key: str) -> bool:
    return ingestion_html_candidates._has_vertical_signal(text, url, vertical_key=vertical_key)


def _matched_vertical_signals(text: str, url: str, *, vertical_key: str) -> list[str]:
    return ingestion_html_candidates._matched_vertical_signals(text, url, vertical_key=vertical_key)


def _candidate_title_from_block(text: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> str:
    return ingestion_html_candidates.candidate_title_from_block(text, vertical_key=vertical_key)


def _candidate_score(product: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return ingestion_html_candidates.candidate_score(product)


def _merge_product_candidates(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    return ingestion_html_candidates.merge_product_candidates(existing, incoming)


def _dedupe_products(products: list[dict[str, Any]], *, merge_same_name: bool = True) -> list[dict[str, Any]]:
    return ingestion_html_candidates.dedupe_products(products, merge_same_name=merge_same_name)


_path_has_marker = ingestion_crawl_urls.path_has_marker
_is_allowed_crawl_url = ingestion_crawl_urls.is_allowed_crawl_url
_url_priority = ingestion_crawl_urls.url_priority
_ranked_unique_urls = ingestion_crawl_urls.ranked_unique_urls
_common_discovery_urls = ingestion_crawl_urls.common_discovery_urls
_extract_sitemap_locations = ingestion_crawl_urls.extract_sitemap_locations
_extract_robots_sitemaps = ingestion_crawl_urls.extract_robots_sitemaps
_decode_sitemap_response = ingestion_crawl_urls.decode_sitemap_response


async def _fetch_sitemap_tree(
    client: httpx.AsyncClient,
    sitemap_url: str,
    allowed_host: str,
    *,
    max_urls: int,
    seen_sitemaps: set[str],
    vertical_key: str,
) -> list[str]:
    return await ingestion_crawl_urls.fetch_sitemap_tree(
        client,
        sitemap_url,
        allowed_host,
        max_urls=max_urls,
        seen_sitemaps=seen_sitemaps,
        vertical_key=vertical_key,
    )


async def _discover_sitemap_urls(seed_url: str, timeout: int, max_urls: int, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[str]:
    return await ingestion_crawl_urls.discover_sitemap_urls(seed_url, timeout, max_urls, vertical_key)


async def _discover_crawl_entrypoints(seed_url: str, timeout: int, max_urls: int, vertical_key: str = DEFAULT_VERTICAL_KEY) -> list[str]:
    return await ingestion_crawl_urls.discover_crawl_entrypoints(seed_url, timeout, max_urls, vertical_key)


def _ensure_category(conn, category_name: str, site_id: str) -> int:
    return ingestion_persistence.ensure_category(
        conn,
        category_name,
        site_id,
        clean_text=_clean_text,
        stable_id=_stable_id,
    )


_vectorize = ingestion_persistence.vectorize


def _persist_catalog(
    site_id: str,
    products: list[dict[str, Any]],
    reconcile_missing: bool,
    source_name: str,
    crawl_report: dict[str, Any] | None = None,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
) -> int:
    return ingestion_persistence.persist_catalog(
        site_id,
        products,
        reconcile_missing,
        source_name,
        clean_text=_clean_text,
        stable_id=_stable_id,
        first_value=_first,
        console_print=_safe_console_print,
        crawl_report=crawl_report,
        vertical_key=vertical_key,
    )


_sync_catalog_knowledge = ingestion_persistence.sync_catalog_knowledge
_count_product_variants = ingestion_persistence.count_product_variants


def _coverage_score(
    *,
    stopped_by_limit: bool,
    pages_visited: int,
    pages_failed: int,
    product_count: int,
    variant_count: int,
    source_type: str,
) -> float:
    return ingestion_persistence.coverage_score(
        stopped_by_limit=stopped_by_limit,
        pages_visited=pages_visited,
        pages_failed=pages_failed,
        product_count=product_count,
        variant_count=variant_count,
        source_type=source_type,
    )


def _build_crawl_report(
    *,
    site_id: str,
    site_url: str,
    source_type: str,
    pages_visited: int,
    pages_failed: int,
    pages_blocked: int,
    products: list[dict[str, Any]],
    failed_urls: list[str],
    blocked_urls: list[str],
    stopped_by_limit: bool,
    duration_ms: float,
) -> CrawlReport:
    return ingestion_persistence.build_crawl_report(
        site_id=site_id,
        site_url=site_url,
        source_type=source_type,
        pages_visited=pages_visited,
        pages_failed=pages_failed,
        pages_blocked=pages_blocked,
        products=products,
        failed_urls=failed_urls[:50],
        blocked_urls=blocked_urls[:50],
        stopped_by_limit=stopped_by_limit,
        duration_ms=duration_ms,
        report_factory=CrawlReport,
        clean_text=_clean_text,
    )


async def async_web_crawl(
    start_url: str,
    *,
    max_pages: int = 60,
    max_depth: int = 3,
    site_id: str | None = None,
    reconcile_missing: bool = True,
    source_name: str = "custom_url_crawler",
    timeout: int = 12,
) -> str:
    return await ingestion_crawler_runtime.async_web_crawl(
        start_url,
        deps=_crawler_dependencies(),
        max_pages=max_pages,
        max_depth=max_depth,
        site_id=site_id,
        reconcile_missing=reconcile_missing,
        source_name=source_name,
        timeout=timeout,
    )


def sync_web_crawl(*args: Any, **kwargs: Any) -> str:
    return ingestion_crawler_runtime.sync_web_crawl(*args, **kwargs, deps=_crawler_dependencies())


def _crawler_dependencies() -> ingestion_crawler_runtime.CrawlDependencies:
    return ingestion_crawler_runtime.CrawlDependencies(
        sanitize_site_id=sanitize_site_id,
        crawl_vertical_key=_crawl_vertical_key,
        fetch_api_catalog_products=_fetch_api_catalog_products,
        discover_crawl_entrypoints=_discover_crawl_entrypoints,
        html_harvest_factory=_HtmlHarvest,
        is_allowed_crawl_url=_is_allowed_crawl_url,
        ranked_unique_urls=_ranked_unique_urls,
        build_candidates_from_html=_build_candidates_from_html,
        dedupe_products=_dedupe_products,
        build_crawl_report=_build_crawl_report,
        persist_catalog=_persist_catalog,
        console_print=_safe_console_print,
        data_root=Path(__file__).resolve().parents[2] / "data",
    )


def _crawl_vertical_key(site_id: str) -> str:
    try:
        from db.client_domain.client_facade import get_client_vertical_key

        return get_client_vertical_key(site_id)
    except Exception as exc:
        logger.debug("Crawler vertical lookup failed for %s: %s", site_id, exc)
        return DEFAULT_VERTICAL_KEY
