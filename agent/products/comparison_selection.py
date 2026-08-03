"""Deterministic comparison selection.

A comparison is only useful if every item is actually eligible and the items
differ in a way the customer cares about. Selection therefore happens in two
strictly ordered stages:

1. Hard constraints filter the candidate set. Price, stock, brand, product type
   and exclusions are pass/fail, so a semantic score, an LLM suggestion, or a
   cached answer can never promote an ineligible product.
2. Only the survivors are ranked, and when the customer did not name a brand the
   selection prefers distinct brands so the comparison contrasts real
   alternatives instead of two variants of one model.

When the customer explicitly names one brand, a same-brand comparison is correct
and diversity is not forced. When only one brand can satisfy the constraints, the
result falls back honestly to that brand rather than padding with ineligible items.
"""

from __future__ import annotations

from typing import Any

from agent.products.product_response_text import normalize_lookup_text, numeric_value

Product = dict[str, Any]

DEFAULT_COMPARISON_COUNT = 2
MAX_COMPARISON_COUNT = 4


def _price_ok(product: Product, price_constraints: dict[str, float] | None) -> bool:
    """Price is a hard constraint. An unpublished price cannot be proven eligible."""
    if not price_constraints:
        return True
    price = numeric_value(product.get("price"))
    maximum = price_constraints.get("max_price")
    minimum = price_constraints.get("min_price")
    if price is None:
        # With an active budget an unknown price must not be shown as compliant.
        return maximum is None and minimum is None
    if maximum is not None and price > maximum:
        return False
    if minimum is not None and price < minimum:
        return False
    return True


def _in_stock(product: Product) -> bool:
    stock = numeric_value(product.get("stock"))
    if stock is not None:
        return stock > 0
    in_stock = product.get("in_stock")
    return True if in_stock is None else bool(in_stock)


def product_brand(product: Product) -> str:
    return normalize_lookup_text(product.get("brand") or product.get("vendor") or "")


def _brand_ok(product: Product, brands: tuple[str, ...]) -> bool:
    if not brands:
        return True
    brand = product_brand(product)
    return any(brand == requested or requested in brand for requested in brands)


def _excluded(product: Product, exclusions: tuple[str, ...]) -> bool:
    if not exclusions:
        return False
    haystack = normalize_lookup_text(
        " ".join(
            str(product.get(field) or "")
            for field in ("name", "title", "brand", "vendor", "category_name", "category")
        )
    )
    return any(term and term in haystack for term in exclusions)


def eligible_comparison_products(
    products: list[Product],
    *,
    brands: tuple[str, ...] = (),
    price_constraints: dict[str, float] | None = None,
    exclusions: tuple[str, ...] = (),
    require_in_stock: bool = True,
) -> list[Product]:
    """Apply every hard constraint, preserving the incoming (ranked) order."""
    normalized_brands = tuple(normalize_lookup_text(brand) for brand in brands if str(brand or "").strip())
    normalized_exclusions = tuple(
        normalize_lookup_text(term) for term in exclusions if str(term or "").strip()
    )
    eligible: list[Product] = []
    for product in products:
        if not str(product.get("id") or "").strip():
            continue
        if require_in_stock and not _in_stock(product):
            continue
        if not _price_ok(product, price_constraints):
            continue
        if not _brand_ok(product, normalized_brands):
            continue
        if _excluded(product, normalized_exclusions):
            continue
        eligible.append(product)
    return eligible


def select_comparison_products(
    products: list[Product],
    *,
    requested_count: int | None = None,
    brands: tuple[str, ...] = (),
    price_constraints: dict[str, float] | None = None,
    exclusions: tuple[str, ...] = (),
    require_in_stock: bool = True,
) -> list[Product]:
    """Return exactly ``requested_count`` eligible products when that many exist.

    Ranking order from the caller is preserved; brand diversity only reorders
    among products that already passed every hard constraint.
    """
    count = requested_count or DEFAULT_COMPARISON_COUNT
    count = max(1, min(int(count), MAX_COMPARISON_COUNT))

    eligible = eligible_comparison_products(
        products,
        brands=brands,
        price_constraints=price_constraints,
        exclusions=exclusions,
        require_in_stock=require_in_stock,
    )
    if len(eligible) <= 1:
        return eligible[:count]

    # One explicitly requested brand means same-brand comparison is the intent.
    # Two or more requested brands still need diversity so each named alternative
    # is represented when eligible products exist.
    if len(brands) == 1:
        return eligible[:count]

    selected: list[Product] = []
    used_brands: set[str] = set()
    for product in eligible:
        if len(selected) >= count:
            break
        brand = product_brand(product)
        if brand and brand in used_brands:
            continue
        selected.append(product)
        if brand:
            used_brands.add(brand)

    # Only one brand could satisfy the constraints: fall back honestly rather than
    # dropping otherwise-valid items to manufacture variety.
    if len(selected) < count:
        for product in eligible:
            if len(selected) >= count:
                break
            if product not in selected:
                selected.append(product)

    return selected[:count]
