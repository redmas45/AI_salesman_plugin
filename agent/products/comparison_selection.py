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

import re
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


# The narrowest published grouping wins, so two phones compare as phones even
# though they share the broader "electronics" category with a charger. These are
# typed catalog fields, not retail words, so a travel or policy record groups the
# same way.
FAMILY_FIELDS = ("subcategory", "product_type", "category_name", "category", "type")
_EXPLICIT_FAMILY_FIELDS = ("subcategory", "product_type", "category_name")
_CATEGORY_PATH_PATTERN = re.compile(
    r"\bcategory\s+path\s*:\s*(.+?)(?=\.\s+(?:specifications|highlights)\s*:|$)",
    re.IGNORECASE,
)


def _family_leaf(value: Any) -> str:
    levels = _family_levels(value)
    return levels[-1] if levels else ""


def _family_levels(value: Any) -> tuple[str, ...]:
    """Every level of a published grouping, broadest first."""
    text = str(value or "").strip()
    return tuple(part.strip() for part in text.split(">") if part.strip()) if text else ()


def family_path(product: Product) -> tuple[str, ...]:
    """The full published grouping path for a record, broadest level first.

    A catalogue may file a phone under "Electronics > Smartphones > Android
    Budget". Comparing only leaves would call two phone tiers different kinds of
    thing; comparing whole paths keeps them comparable.
    """
    for field in _EXPLICIT_FAMILY_FIELDS:
        levels = _family_levels(product.get(field))
        if levels:
            return levels
    description_levels = _family_levels(_description_family_path(product))
    if description_levels:
        return description_levels
    for field in ("category", "type"):
        levels = _family_levels(product.get(field))
        if levels:
            return levels
    return ()


def _description_family_path(product: Product) -> str:
    """The category path some ingestion paths record in the description text."""
    description = str(product.get("description") or product.get("summary") or "")
    match = _CATEGORY_PATH_PATTERN.search(description)
    return match.group(1) if match else ""


def _description_family(product: Product) -> str:
    return _family_leaf(_description_family_path(product))


def product_family(product: Product) -> str:
    """The narrowest published grouping this record belongs to."""
    for field in _EXPLICIT_FAMILY_FIELDS:
        family = _family_leaf(product.get(field))
        if family:
            return family

    # API ingestion preserves a source subcategory in the normalized description
    # because the database contract does not persist a separate subcategory field.
    # Prefer it over the broad top-level category so a phone is not compared with
    # a charger merely because both are classified as electronics.
    description_family = _description_family(product)
    if description_family:
        return description_family

    for field in ("category", "type"):
        family = _family_leaf(product.get(field))
        if family:
            return family
    return ""


def _same_family(first: Product, second: Product) -> bool:
    """Comparable when the published paths meet anywhere below the root.

    Two phones filed under "Android Budget" and "Android Mid-range" are the same
    kind of thing because both sit under "Smartphones"; comparing only the leaves
    would refuse a comparison the customer plainly asked for. An unknown grouping
    never blocks a comparison; it only fails to justify one.
    """
    left = _discriminating_levels(family_path(first))
    right = _discriminating_levels(family_path(second))
    return not left or not right or bool(left & right)


def _discriminating_levels(path: tuple[str, ...]) -> set[str]:
    """The levels that actually distinguish records.

    The broadest level is dropped when a finer one exists: a phone and a charger
    both sit under "Electronics", so agreeing there says nothing about whether
    they are the same kind of thing.
    """
    levels = path[1:] if len(path) > 1 else path
    return {normalize_lookup_text(part) for part in levels if part}


def comparison_family_conflict(
    products: list[Product],
    *,
    brands: tuple[str, ...] = (),
) -> tuple[str, ...] | None:
    """Report the families a brand-only request would otherwise compare across.

    Returns the sorted family names when the best candidate for each requested
    brand belongs to a different kind of thing, and ``None`` when the request is
    answerable. Comparing a phone with a charger because both brands matched is
    never a useful answer, so the caller asks which kind was meant.
    """
    if len(brands) < 2:
        return None
    best_by_brand: dict[str, Product] = {}
    for product in products:
        brand = product_brand(product)
        if brand and brand not in best_by_brand:
            best_by_brand[brand] = product
    if len(best_by_brand) < 2:
        return None
    records = list(best_by_brand.values())
    if any(not family_path(record) for record in records):
        return None
    if all(_same_family(records[0], record) for record in records[1:]):
        return None
    # Name the level that actually differs, so the question is answerable.
    return tuple(sorted({product_family(record) for record in records}))


def _records_were_named(products: list[Product], count: int) -> bool:
    """True when enough records carry retrieval's own exact-match marker.

    A record is marked when the request pinned it down by name and type rather
    than by brand alone, which is precisely the case where comparing across
    families is what the customer asked for.
    """
    matched = sum(1 for product in products if product.get("_exact_name_match"))
    return matched >= min(count, 2)


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
    records_named_explicitly: bool = False,
) -> list[Product]:
    """Return exactly ``requested_count`` eligible products when that many exist.

    Ranking order from the caller is preserved; brand diversity only reorders
    among products that already passed every hard constraint, and never at the
    cost of comparing two different kinds of thing.

    ``records_named_explicitly`` marks a request that named each record itself
    ("compare the Everyday Laptop and the Gaming Laptop"). Naming both is consent
    to compare them, so the family rule does not apply. When the caller does not
    say, it is inferred from the records' own exact-match marker.
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

    named_explicitly = records_named_explicitly or _records_were_named(eligible, count)
    anchor = eligible[0]
    selected: list[Product] = []
    used_brands: set[str] = set()
    for product in eligible:
        if len(selected) >= count:
            break
        # The best-ranked record sets the kind of thing under discussion. A
        # brand match alone is not a reason to compare a phone with a charger.
        if not named_explicitly and not _same_family(anchor, product):
            continue
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
            if not named_explicitly and not _same_family(anchor, product):
                continue
            if product not in selected:
                selected.append(product)

    return selected[:count]
