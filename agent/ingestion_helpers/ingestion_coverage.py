"""Coverage scoring helpers for ingestion crawl reports."""

from __future__ import annotations

from typing import Any


def count_product_variants(products: list[dict[str, Any]]) -> int:
    return sum(
        len(product.get("variants") or [])
        for product in products
        if isinstance(product.get("variants"), list)
    )


def coverage_score(
    *,
    stopped_by_limit: bool,
    pages_visited: int,
    pages_failed: int,
    product_count: int,
    variant_count: int,
    source_type: str,
) -> float:
    score = 1.0
    if product_count <= 0:
        score -= 0.55
    if stopped_by_limit:
        score -= 0.2
    total_pages = max(1, pages_visited + pages_failed)
    score -= min(0.25, (pages_failed / total_pages) * 0.25)
    if source_type == "api_catalog" and variant_count <= 0:
        score -= 0.1
    return max(0.0, min(1.0, score))
