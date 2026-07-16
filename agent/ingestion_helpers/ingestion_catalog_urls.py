"""Catalog endpoint discovery and pagination URL helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from agent.ingestion_helpers.ingestion_normalization import to_positive_int_id
from agent.site_helpers.local_urls import local_runtime_url_candidates

CATALOG_ENDPOINT_PATHS = (
    "/api/products",
    "/api/policies",
    "/api/products.json",
    "/products.json",
    "/collections/all/products.json",
    "/wp-json/wc/store/products?per_page=100",
    "/wp-json/wc/store/v1/products?per_page=100",
)
SHOPIFY_CATALOG_PAGE_LIMIT = 250
SHOPIFY_CATALOG_MAX_PAGES = 20
WOO_CATALOG_MAX_PAGES = 20
GENERIC_API_CATALOG_PAGE_SIZE = 96
GENERIC_API_CATALOG_MAX_PAGES = 100


def site_base_url(seed_url: str) -> str:
    parsed = urlparse(seed_url)
    scheme = parsed.scheme or "https"
    return f"{scheme}://{parsed.netloc}"


def catalog_endpoint_for(seed_url: str) -> str:
    return urljoin(site_base_url(seed_url), "/api/products")


def catalog_endpoints_for(seed_url: str) -> list[str]:
    base = site_base_url(seed_url)
    urls = [urljoin(base, path) for path in CATALOG_ENDPOINT_PATHS]
    return list(dict.fromkeys(urls))


def catalog_seed_candidates(seed_url: str) -> list[str]:
    return local_runtime_url_candidates(seed_url) or [seed_url]


def catalog_page_urls(api_url: str) -> list[str]:
    if "/collections/all/products.json" in api_url or api_url.endswith("/products.json"):
        separator = "&" if "?" in api_url else "?"
        return [
            f"{api_url}{separator}limit={SHOPIFY_CATALOG_PAGE_LIMIT}&page={page}"
            for page in range(1, SHOPIFY_CATALOG_MAX_PAGES + 1)
        ]
    if "/wp-json/wc/store" in api_url and "/products" in api_url:
        separator = "&" if "?" in api_url else "?"
        return [
            f"{api_url}{separator}page={page}"
            for page in range(1, WOO_CATALOG_MAX_PAGES + 1)
        ]
    if is_generic_products_api(api_url):
        return [
            catalog_url_with_params(
                api_url,
                {
                    "page": page,
                    "per_page": GENERIC_API_CATALOG_PAGE_SIZE,
                },
            )
            for page in range(1, GENERIC_API_CATALOG_MAX_PAGES + 1)
        ]
    return [api_url]


def is_generic_products_api(api_url: str) -> bool:
    parsed = urlparse(api_url)
    return parsed.path.rstrip("/") == "/api/products"


def catalog_url_with_params(api_url: str, params: dict[str, int]) -> str:
    parsed = urlparse(api_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({key: str(value) for key, value in params.items()})
    return urlunparse(parsed._replace(query=urlencode(query)))


def catalog_response_reached_last_page(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else payload
    page = to_positive_int_id(meta.get("page"))
    total_pages = to_positive_int_id(meta.get("total_pages"))
    return bool(page and total_pages and page >= total_pages)


def catalog_normalization_url(api_url: str, page_url: str) -> str:
    if is_generic_products_api(api_url):
        return api_url
    return page_url
