"""Resolved hard constraints as a typed, host-mappable filter set for display.

The Hub half of "phones under 20000 must navigate to a filtered page": a turn's
resolved HARD CONSTRAINTS are carried on the SHOW_PRODUCTS action as a typed
``filters`` object so a host contract can later map them onto the storefront's
own URL. This is kept strictly separate from the semantic ``search_query`` text
(a hard constraint filters a page; it is not a word to match), and it never
hardcodes a vertical's taxonomy - brand and category are grounded against the
displayed records' own vocabulary.
"""

from __future__ import annotations

from typing import Any

from agent.products.comparison_selection import product_brand, product_family
from agent.retrieval.query_constraints import extract_ecommerce_constraints

# Canonical, host-mappable filter keys. A host contract maps these onto its own
# storefront URL params; anything outside this set is intentionally dropped so a
# new vertical never has to teach the Hub a bespoke key.
FILTER_MAX_PRICE = "max_price"
FILTER_MIN_PRICE = "min_price"
FILTER_BRAND = "brand"
FILTER_CATEGORY = "category"


def host_display_filters(
    transcript: str,
    display_records: list[dict],
) -> dict[str, Any]:
    """The turn's resolved HARD CONSTRAINTS as a typed, host-mappable filter set.

    A host contract later maps these canonical keys onto the storefront's own URL
    (so "phones under 20000" lands on a filtered page) while the semantic search
    text stays in ``search_query``. Every value is grounded: price is parsed from
    the utterance, and brand/category are matched against the displayed records'
    own vocabulary - never guessed from the page or a default (rule 14). When
    nothing resolves an empty dict is returned so the caller can leave the
    no-filter path byte-for-byte unchanged.
    """
    records = [record for record in display_records or [] if isinstance(record, dict)]
    if not records:
        return {}

    # The brand and category vocabularies come from the records themselves, so the
    # extractor matches the customer's words against what this store actually
    # sells rather than a hardcoded taxonomy.
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

    filters: dict[str, Any] = {}
    if constraints.max_price is not None:
        filters[FILTER_MAX_PRICE] = float(constraints.max_price)
    if constraints.min_price is not None:
        filters[FILTER_MIN_PRICE] = float(constraints.min_price)
    # A single resolved brand is a hard constraint; two competing brands are not a
    # single storefront brand filter, so only an unambiguous one is carried.
    if len(constraints.brands) == 1:
        filters[FILTER_BRAND] = constraints.brands[0]
    if constraints.product_types:
        filters[FILTER_CATEGORY] = constraints.product_types[0]
    # Rating is intentionally omitted: the e-commerce extractor exposes no grounded
    # min-rating bound and no other grounded parse of a stated rating exists.
    # Inventing one from a brittle regex would violate "Ask, Never Assume" (rule
    # 14), so min_rating is left out until a grounded parse is added upstream.
    return filters
