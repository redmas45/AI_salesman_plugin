"""Deterministic constrained catalog count for a turn's spoken result total.

Maya's "I found N matching products" must equal the number of catalog records
that satisfy the turn's resolved HARD CONSTRAINTS - the same brand/category/price
facets a filtered storefront page would apply - not the size of the RAG candidate
window (RAG_TOP_N), which is an arbitrary retrieval slice. Counting the window
let Maya claim "I found 3" when twelve matched, or assert a whole-catalog total
from a sample (rule 14, "Never claim whole-catalog truth from a retrieval
window").

This path is deterministic (no LLM) and vertical-neutral: brand/category/type
vocabularies come from the records themselves, and the count runs the same
conjunctive validator (:func:`select_records`) used elsewhere. To avoid an
O(catalog) scan on turns that carry no hard constraint, the count is computed
ONLY when at least one facet (price/brand/category/type) resolves; otherwise the
caller keeps today's displayed-count behaviour untouched.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

from agent.catalog import catalog_operations as ops
from agent.products.comparison_selection import product_brand, product_family
from agent.retrieval.query_constraints import QueryConstraints, extract_ecommerce_constraints

# Response keys the answer composer reads. The bounded flag is set when the scan
# hit its cap, so the composer can say "N+" instead of asserting a wrong exact.
MATCHING_TOTAL_KEY = "matching_total"
MATCHING_TOTAL_BOUNDED_KEY = "matching_total_is_lower_bound"

CatalogLoader = Callable[[], list[dict]]


def _turn_constraints(
    transcript: str,
    display_records: list[dict],
    price_constraints: dict[str, Any] | None,
) -> tuple[QueryConstraints, list[dict]]:
    """Resolve the turn's constraints, grounding vocab in the displayed records."""
    records = [record for record in display_records or [] if isinstance(record, dict)]
    catalog_brands = tuple(
        dict.fromkeys(brand for brand in (product_brand(record) for record in records) if brand)
    )
    catalog_types = tuple(
        dict.fromkeys(family for family in (product_family(record) for record in records) if family)
    )
    constraints = extract_ecommerce_constraints(
        transcript,
        catalog_brands=catalog_brands,
        catalog_types=catalog_types,
    )
    return _with_authoritative_price(constraints, price_constraints), records


def _with_authoritative_price(
    constraints: QueryConstraints,
    price_constraints: dict[str, Any] | None,
) -> QueryConstraints:
    """The pipeline's resolved price bound is authoritative over a re-parse."""
    price = price_constraints or {}
    if "min_price" not in price and "max_price" not in price:
        return constraints
    return replace(
        constraints,
        min_price=price.get("min_price", constraints.min_price),
        max_price=price.get("max_price", constraints.max_price),
    )


def _has_hard_constraint(constraints: QueryConstraints, categories: tuple[str, ...]) -> bool:
    return bool(
        constraints.has_price_constraint()
        or constraints.brands
        or constraints.product_types
        or categories
    )


def constrained_catalog_total(
    transcript: str,
    display_records: list[dict],
    price_constraints: dict[str, Any] | None,
    load_catalog: CatalogLoader,
) -> tuple[int, bool] | None:
    """Count catalog records satisfying the turn's hard constraints.

    Returns ``(matching_records, is_lower_bound)`` when at least one hard
    constraint resolved, or ``None`` when none did (so the caller does no catalog
    work and keeps today's behaviour). ``is_lower_bound`` is True when the scan
    was capped, meaning the real total may be higher.
    """
    constraints, records = _turn_constraints(transcript, display_records, price_constraints)
    categories = ops.matching_category_names(constraints.raw_query, records)
    if not _has_hard_constraint(constraints, categories):
        return None

    catalog = list(load_catalog() or [])
    if not catalog:
        return None

    selection = ops.select_records(catalog, constraints, category_names=categories)
    return selection.facts.matching_records, selection.facts.truncated


def annotate_matching_total(
    response: dict[str, Any],
    transcript: str,
    display_records: list[dict],
    price_constraints: dict[str, Any] | None,
    load_catalog: CatalogLoader,
) -> None:
    """Record the deterministic constrained total on the response for the composer.

    A no-op when no hard constraint resolves, so the no-filter path stays exactly
    as it was and no catalog scan is triggered.
    """
    result = constrained_catalog_total(transcript, display_records, price_constraints, load_catalog)
    if result is None:
        return
    count, bounded = result
    response[MATCHING_TOTAL_KEY] = int(count)
    response[MATCHING_TOTAL_BOUNDED_KEY] = bool(bounded)


def response_matching_total(
    response: dict[str, Any],
    fallback_records: list[dict],
) -> tuple[int, bool]:
    """The total the composer should claim, preferring the deterministic count.

    Falls back to the displayed/retrieved size when no deterministic count was
    recorded, which keeps every no-hard-constraint turn byte-for-byte unchanged.
    """
    total = response.get(MATCHING_TOTAL_KEY)
    bounded = bool(response.get(MATCHING_TOTAL_BOUNDED_KEY))
    if isinstance(total, int) and not isinstance(total, bool):
        return total, bounded
    return len(fallback_records or []), False
