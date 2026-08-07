"""Resolving "premium" and "budget" from a tenant's own data.

"Compare Apple Premium versus Samsung Premium" asks for the top of each brand's
range. "Premium" is not a slot value - no catalogue has a product called
Premium - it is a *ranking operator over a tier scale*, so it selects among the
records that already satisfy the brand and family constraints.

Which signal expresses tier is a property of the tenant, not of the assistant,
so the signals are tried in order of how explicitly they state it:

1. A published tier or flagship marker (a tag, or the record's own grouping).
2. Rating and review volume, where the catalogue publishes them.
3. Price, last, and only when nothing better exists - because price alone is a
   weak proxy for "premium" and the answer has to say so.

The last point matters for honesty: when price is the only evidence, the caller
is told, so Maya can state the basis rather than implying the catalogue declared
a flagship. Nothing here names a vendor, a model, or a vertical.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.nlu.frame import RANK_MAX, RANK_MIN, SCALE_TIER, SemanticFrame
from agent.products.comparison_selection import family_path
from agent.products.product_response_text import normalize_lookup_text, numeric_value

Product = dict[str, Any]

BASIS_PUBLISHED_TIER = "published_tier"
BASIS_RATING = "rating"
BASIS_PRICE = "price"

# Words a catalogue uses to mark the top or bottom of its own range. These are
# ordinary English tier vocabulary, matched against the tenant's published tags
# and groupings - never against a list of product names.
_TOP_TIER_WORDS = frozenset({
    "premium", "flagship", "elite", "pro", "ultra", "max", "plus", "luxury",
    "signature", "highend", "high-end", "top", "prestige",
})
_ENTRY_TIER_WORDS = frozenset({
    "budget", "entry", "entry-level", "basic", "essential", "lite", "starter", "value",
})

_TIER_FIELDS = ("tags", "labels", "tier", "collection", "series", "badges")


@dataclass(frozen=True)
class TierRanking:
    """Records ordered by tier, with the evidence that ordered them."""

    records: tuple[Product, ...]
    basis: str

    @property
    def price_only(self) -> bool:
        """True when price was the sole signal, so the answer must say so."""
        return self.basis == BASIS_PRICE


def _published_words(product: Product) -> set[str]:
    """Tier vocabulary a record publishes about itself."""
    words: set[str] = set()
    for field in _TIER_FIELDS:
        value = product.get(field)
        items = value if isinstance(value, (list, tuple)) else [value]
        for item in items:
            words.update(normalize_lookup_text(item).replace("-", " ").split())
    for level in family_path(product):
        words.update(normalize_lookup_text(level).replace("-", " ").split())
    # A record's own name is published text too, and is where many catalogues
    # put the tier word.
    words.update(normalize_lookup_text(product.get("name") or product.get("title") or "").split())
    return words


def published_tier_score(product: Product) -> int:
    """+1 when the record is published as top of range, -1 for entry, else 0."""
    words = _published_words(product)
    if words & _TOP_TIER_WORDS:
        return 1
    if words & _ENTRY_TIER_WORDS:
        return -1
    return 0


def _rating_score(product: Product) -> tuple[float, float]:
    return (numeric_value(product.get("rating")) or 0.0, numeric_value(product.get("review_count")) or 0.0)


def _price(product: Product) -> float:
    return numeric_value(product.get("price")) or 0.0


def _catalogue_publishes_tier(products: list[Product]) -> bool:
    return any(published_tier_score(product) != 0 for product in products)


def _catalogue_publishes_ratings(products: list[Product]) -> bool:
    return any(numeric_value(product.get("rating")) is not None for product in products)


def rank_by_tier(products: list[Product], *, direction: str = RANK_MAX) -> TierRanking:
    """Order records from the top (or bottom) of the tenant's own range.

    The strongest available signal decides, and the ranking reports which one it
    used so the answer can be honest about its basis.
    """
    records = [product for product in products if isinstance(product, dict)]
    if not records:
        return TierRanking(records=(), basis=BASIS_PRICE)

    descending = direction != RANK_MIN
    if _catalogue_publishes_tier(records):
        basis = BASIS_PUBLISHED_TIER
        key = lambda product: (published_tier_score(product), _rating_score(product), _price(product))
    elif _catalogue_publishes_ratings(records):
        basis = BASIS_RATING
        key = lambda product: (_rating_score(product), _price(product))
    else:
        basis = BASIS_PRICE
        key = _price

    ordered = sorted(records, key=key, reverse=descending)
    return TierRanking(records=tuple(ordered), basis=basis)


def frame_requests_tier(frame: SemanticFrame | None) -> bool:
    """True when the turn ranked over a tier scale ("premium", "budget")."""
    return bool(frame and frame.rank and frame.rank.scale == SCALE_TIER)


def tier_basis_note(ranking: TierRanking) -> str:
    """Wording for a ranking the catalogue did not justify on its own terms."""
    if not ranking.price_only:
        return ""
    return "This catalogue does not publish a tier, so I ranked by price."


def top_record_per_brand(
    products: list[Product],
    brands: tuple[str, ...],
    *,
    direction: str = RANK_MAX,
) -> tuple[list[Product], str]:
    """One record per requested brand, each the top of that brand's range.

    This is what "compare <brand A> premium versus <brand B> premium" means: not
    the best-matching record per brand, but the highest-tier one.
    """
    ranking = rank_by_tier(products, direction=direction)
    wanted = {normalize_lookup_text(brand) for brand in brands if str(brand or "").strip()}
    selected: list[Product] = []
    seen: set[str] = set()
    for product in ranking.records:
        brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
        if wanted and brand not in wanted:
            continue
        if brand in seen:
            continue
        seen.add(brand)
        selected.append(product)
    return selected, ranking.basis
