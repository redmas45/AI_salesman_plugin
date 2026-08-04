"""Deterministic catalog operations: hard filtering, aggregates, exact counts.

Superlative and count questions were previously answered by ranking whatever the
similarity search happened to return. That produced three separate defects:

* the cheapest item "in Fashion Women" was the cheapest item in the *catalog*,
  because the minimum-price pick ran before the category was applied;
* "best rated" could pick a record whose rating had no review behind it, and
  ties between equal records resolved differently from run to run;
* "how many X do you have" counted a randomly sampled retrieval window and
  presented it as whole-catalog truth.

Every operation here therefore follows the same order: apply every hard
constraint conjunctively, THEN select or count over the surviving set, with a
total ordering so the same catalog always produces the same answer.

The module is vertical-independent. It reads generic record fields (price,
rating, review evidence, availability, category label) and takes its brand,
type, and category vocabulary from the tenant's own data. Nothing here knows any
particular retailer, catalogue, or category name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent.products.product_matching_lexical import canonical_type_token, product_strong_text
from agent.products.product_response import normalize_lookup_text, phrase_in_text
from agent.retrieval.query_constraints import QueryConstraints
from agent.runtime_helpers.grounding_validator import product_within_price

Record = dict[str, Any]

AGGREGATE_CHEAPEST = "cheapest"
AGGREGATE_MOST_EXPENSIVE = "most_expensive"
AGGREGATE_BEST_RATED = "best_rated"
SUPPORTED_AGGREGATES = frozenset({AGGREGATE_CHEAPEST, AGGREGATE_MOST_EXPENSIVE, AGGREGATE_BEST_RATED})

# The largest number of records one turn will scan. Beyond this the answer is
# reported as a lower bound rather than an exact catalog total.
CATALOG_SCAN_CAP = 5000
DEFAULT_AGGREGATE_LIMIT = 3
# A rating with no review behind it is a default value, not evidence.
MIN_REVIEWS_FOR_RATING = 1
MIN_CATEGORY_TOKEN_LENGTH = 3


@dataclass(frozen=True)
class CatalogFacts:
    """Counts that a response may state, each measuring a different thing."""

    matching_records: int
    variant_count: int
    stock_units: int
    truncated: bool

    def exact(self) -> bool:
        """True when ``matching_records`` is the whole catalog truth."""
        return not self.truncated


@dataclass(frozen=True)
class CatalogSelection:
    """Records that satisfied every hard constraint, plus their counts."""

    records: tuple[Record, ...]
    facts: CatalogFacts
    applied_categories: tuple[str, ...] = ()

    def ids(self) -> tuple[str, ...]:
        return tuple(str(record.get("id")) for record in self.records if record.get("id") is not None)


def numeric(value: Any) -> float | None:
    """Parse a price/rating/stock field that may arrive as text or currency."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = re.sub(r"[^\d.\-]", "", str(value or ""))
    try:
        return float(text)
    except ValueError:
        return None


def record_price(record: Record) -> float | None:
    return numeric(record.get("price"))


def record_rating(record: Record) -> float:
    return numeric(record.get("rating")) or 0.0


def record_review_count(record: Record) -> int:
    return int(numeric(record.get("review_count")) or 0)


def record_stock_units(record: Record) -> int:
    """Stock units for this record; absent stock means "not tracked", not zero."""
    if "stock" not in record:
        return 0
    return max(0, int(numeric(record.get("stock")) or 0))


def is_available(record: Record) -> bool:
    """Availability is a hard constraint: an unbuyable record is not a match."""
    if "stock" not in record:
        return True
    return record_stock_units(record) > 0


def matches_brands(record: Record, brands: tuple[str, ...], strong_text: str) -> bool:
    if not brands:
        return True
    brand_field = normalize_lookup_text(record.get("brand") or record.get("vendor") or "")
    return any(
        brand_field == brand or phrase_in_text(brand, brand_field) or phrase_in_text(brand, strong_text)
        for brand in brands
    )


def matches_types(record: Record, product_types: tuple[str, ...], strong_text: str) -> bool:
    if not product_types:
        return True
    name = normalize_lookup_text(record.get("name") or record.get("title") or "")
    tokens = {canonical_type_token(term) for term in product_types if term}
    return any(phrase_in_text(token, name) or phrase_in_text(token, strong_text) for token in tokens if token)


def matches_categories(record: Record, category_names: tuple[str, ...]) -> bool:
    if not category_names:
        return True
    label = normalize_lookup_text(record.get("category_name") or record.get("category") or "")
    return any(label == normalize_lookup_text(name) for name in category_names)


def excluded_by(record: Record, exclusions: tuple[str, ...], strong_text: str) -> bool:
    return any(phrase_in_text(normalize_lookup_text(term), strong_text) for term in exclusions if term)


def satisfies_hard_constraints(
    record: Record,
    constraints: QueryConstraints,
    category_names: tuple[str, ...],
) -> bool:
    """Every hard facet must hold. One satisfied facet is not a match."""
    if not is_available(record):
        return False
    if not product_within_price(record, constraints.price_constraints()):
        return False
    if not matches_categories(record, category_names):
        return False
    strong_text = product_strong_text(record)
    return (
        matches_brands(record, constraints.brands, strong_text)
        and matches_types(record, constraints.product_types, strong_text)
        and not excluded_by(record, constraints.exclusions, strong_text)
    )


def select_records(
    records: list[Record],
    constraints: QueryConstraints,
    *,
    category_names: tuple[str, ...] = (),
    scan_cap: int = CATALOG_SCAN_CAP,
) -> CatalogSelection:
    """Apply every hard constraint conjunctively, before any ranking happens."""
    source = list(records or [])
    truncated = len(source) > scan_cap
    survivors = tuple(
        record
        for record in source[:scan_cap]
        if satisfies_hard_constraints(record, constraints, category_names)
    )
    return CatalogSelection(
        records=survivors,
        facts=catalog_facts(survivors, truncated=truncated),
        applied_categories=tuple(category_names),
    )


def catalog_facts(records: tuple[Record, ...] | list[Record], *, truncated: bool = False) -> CatalogFacts:
    """Distinguish matching records, purchasable variants, and stock units."""
    variant_ids = {
        str(record.get("variant_id"))
        for record in records
        if record.get("variant_id") not in (None, "")
    }
    return CatalogFacts(
        matching_records=len(records),
        variant_count=len(variant_ids) or len(records),
        stock_units=sum(record_stock_units(record) for record in records),
        truncated=truncated,
    )


def _identity_key(record: Record) -> tuple[int, float, str]:
    """A total, stable ordering key so equal records never swap places."""
    raw_id = str(record.get("id") or "")
    numeric_id = numeric(raw_id)
    return (0, numeric_id, "") if numeric_id is not None else (1, 0.0, raw_id)


def _name_key(record: Record) -> str:
    return normalize_lookup_text(record.get("name") or record.get("title") or "")


def _cheapest_key(record: Record) -> tuple:
    return (record_price(record), -record_rating(record), _name_key(record), _identity_key(record))


def _most_expensive_key(record: Record) -> tuple:
    return (-(record_price(record) or 0.0), -record_rating(record), _name_key(record), _identity_key(record))


def _best_rated_key(record: Record) -> tuple:
    return (
        -record_rating(record),
        -record_review_count(record),
        record_price(record) if record_price(record) is not None else float("inf"),
        _name_key(record),
        _identity_key(record),
    )


def aggregate_records(
    selection: CatalogSelection,
    aggregate: str,
    *,
    limit: int = DEFAULT_AGGREGATE_LIMIT,
) -> list[Record]:
    """Order the validated set by the requested superlative, deterministically."""
    if aggregate not in SUPPORTED_AGGREGATES:
        return []
    candidates = [record for record in selection.records if record_price(record) is not None]
    if aggregate == AGGREGATE_BEST_RATED:
        # A default rating with no reviews behind it is not review evidence.
        candidates = [
            record
            for record in selection.records
            if record_review_count(record) >= MIN_REVIEWS_FOR_RATING and record_rating(record) > 0
        ]
        return sorted(candidates, key=_best_rated_key)[:limit]
    key = _cheapest_key if aggregate == AGGREGATE_CHEAPEST else _most_expensive_key
    return sorted(candidates, key=key)[:limit]


def matching_category_names(text: str, records: list[Record]) -> tuple[str, ...]:
    """Category labels from the tenant's own data that the customer named.

    Data-driven on purpose: the vocabulary is whatever categories the catalog
    actually contains, so no taxonomy is hard-coded into the Hub.
    """
    normalized_text = normalize_lookup_text(text)
    if not normalized_text:
        return ()
    matched: list[str] = []
    seen: set[str] = set()
    for label in _distinct_category_labels(records):
        tokens = [
            token for token in normalize_lookup_text(label).split() if len(token) >= MIN_CATEGORY_TOKEN_LENGTH
        ]
        if not tokens or not all(phrase_in_text(token, normalized_text) for token in tokens):
            continue
        if label.lower() not in seen:
            seen.add(label.lower())
            matched.append(label)
    return tuple(matched)


def _distinct_category_labels(records: list[Record]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for record in records or []:
        label = str(record.get("category_name") or record.get("category") or "").strip()
        if label and label.lower() not in seen:
            seen.add(label.lower())
            labels.append(label)
    # Longest first so "Fashion Women" wins over a bare "Fashion" when both exist.
    return sorted(labels, key=lambda value: (-len(value), value))


def count_phrase(facts: CatalogFacts, noun: str) -> str:
    """Render a count without ever overstating a bounded scan as a total."""
    from agent.responses.inventory_responses import pluralize

    word = pluralize(noun or "product", facts.matching_records)
    if facts.truncated:
        return f"at least {facts.matching_records} {word}"
    return f"{facts.matching_records} {word}"
