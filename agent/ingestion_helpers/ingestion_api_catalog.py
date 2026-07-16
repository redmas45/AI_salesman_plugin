"""API catalog fetching and normalization for ingestion."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agent.ingestion_helpers import ingestion_catalog_normalizers, ingestion_html_candidates
from agent.ingestion_helpers.ingestion_catalog_urls import (
    catalog_endpoints_for,
    catalog_normalization_url,
    catalog_page_urls,
    catalog_response_reached_last_page,
    catalog_seed_candidates,
)

logger = logging.getLogger(__name__)


def normalize_catalog_payload(
    payload: Any,
    api_url: str,
    *,
    merge_same_name: bool = True,
) -> list[dict[str, Any]]:
    return ingestion_catalog_normalizers.normalize_catalog_payload(
        payload,
        api_url,
        dedupe_products=ingestion_html_candidates.dedupe_products,
        merge_same_name=merge_same_name,
    )


async def fetch_api_catalog_products(seed_url: str, timeout: int) -> list[dict[str, Any]]:
    """Fetch common public commerce catalog endpoints before rendering HTML."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        for candidate_seed_url in catalog_seed_candidates(seed_url):
            for api_url in catalog_endpoints_for(candidate_seed_url):
                deduped = await fetch_catalog_endpoint_pages(client, api_url)
                if deduped:
                    logger.info("API catalog at %s returned %d products.", api_url, len(deduped))
                    return deduped
                logger.warning("API catalog at %s did not contain a usable product list.", api_url)

    return []


async def fetch_catalog_endpoint_pages(
    client: httpx.AsyncClient,
    api_url: str,
) -> list[dict[str, Any]]:
    """Fetch one catalog endpoint, including standard Shopify/Woo pagination."""
    products: list[dict[str, Any]] = []
    seen_product_ids: set[int] = set()
    page_urls = catalog_page_urls(api_url)
    for page_url in page_urls:
        try:
            response = await client.get(page_url, headers={"Accept": "application/json"})
            if response.status_code in {401, 403, 404, 405}:
                break
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.info("No API catalog available at %s: %s", page_url, exc)
            break

        page_products = normalize_catalog_payload(
            payload,
            catalog_normalization_url(api_url, page_url),
            merge_same_name=False,
        )
        if not page_products:
            break

        new_products = []
        for product in page_products:
            product_id = int(product["id"])
            if product_id in seen_product_ids:
                continue
            new_products.append(product)
            seen_product_ids.add(product_id)
        if not new_products and products:
            break
        products.extend(new_products)

        if len(page_urls) == 1:
            break
        if catalog_response_reached_last_page(payload):
            break

    return ingestion_html_candidates.dedupe_products(products, merge_same_name=False)
