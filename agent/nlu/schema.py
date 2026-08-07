"""The tenant's own data, expressed as a slot schema.

Following the schema-guided approach (Rastogi et al., DSTC8/SGD), the assistant
carries no domain ontology of its own. Each tenant's records *are* the schema:
the brands they publish become the ``brand`` slot's vocabulary, the groupings
they publish become the ``family`` slot's vocabulary, and so on. A travel or
policy catalog produces a schema of the same shape with different values, so
nothing here needs to know which vertical it is serving.

Slot names are structural roles, not domain words: "brand" is whoever supplies
the record, "family" is the kind of thing it is. Both are read from typed fields
the ingestion layer already normalizes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.nlu.lexical import build_vocabulary, contains_alignment

Record = dict[str, Any]

SLOT_BRAND = "brand"
SLOT_FAMILY = "family"

# Fields a record may publish for each slot, narrowest grouping first. These are
# the typed names the ingestion layer normalizes to, never tenant-specific keys.
_BRAND_FIELDS = ("brand", "vendor", "supplier", "operator", "provider", "issuer")
_FAMILY_FIELDS = ("subcategory", "product_type", "category_name", "category", "type")


def _published_value(record: Record, fields: tuple[str, ...]) -> str:
    for name in fields:
        value = str(record.get(name) or "").strip()
        if value:
            return value
    return ""


def family_levels(record: Record) -> tuple[str, ...]:
    """Every level of the grouping a record publishes, broadest first.

    A path such as "Electronics > Smartphones > Android Budget" offers three
    names for the same records. Registering only the leaf meant a shopper asking
    for "phones" matched nothing, and the request silently lost its family.
    """
    published = _published_value(record, _FAMILY_FIELDS)
    return tuple(part.strip() for part in published.split(">") if part.strip())


def record_brand(record: Record) -> str:
    return _published_value(record, _BRAND_FIELDS)


def record_family(record: Record) -> str:
    """The narrowest published grouping, used where one label is needed."""
    levels = family_levels(record)
    return levels[-1] if levels else ""


@dataclass(frozen=True)
class SlotCandidate:
    """One published value a spoken phrase might be naming, with a confidence."""

    slot: str
    value: str
    confidence: float
    matched_terms: tuple[str, ...] = ()

    def searchable_value(self) -> str:
        """The published words the customer actually named.

        A partial match on "Books Stationery" searches for "books", because that
        is the published word they used; sending the whole label would search for
        a phrase they never said.
        """
        return " ".join(self.matched_terms) if self.matched_terms else self.value


@dataclass(frozen=True)
class TenantSchema:
    """Slot vocabularies derived from the records under discussion."""

    brands: tuple[str, ...] = ()
    families: tuple[str, ...] = ()
    vocabulary: frozenset[str] = field(default_factory=frozenset)

    def values_for(self, slot: str) -> tuple[str, ...]:
        if slot == SLOT_BRAND:
            return self.brands
        if slot == SLOT_FAMILY:
            return self.families
        return ()

    def candidates(self, slot: str, spoken: str) -> tuple[SlotCandidate, ...]:
        """Every published value the phrase could name, best confidence first."""
        scored: list[SlotCandidate] = []
        for value in self.values_for(slot):
            confidence, matched = contains_alignment(spoken, value, self.vocabulary)
            if confidence > 0.0:
                scored.append(
                    SlotCandidate(
                        slot=slot,
                        value=value,
                        confidence=confidence,
                        matched_terms=matched,
                    )
                )
        scored.sort(key=lambda candidate: (-candidate.confidence, len(candidate.value)))
        return tuple(scored)


def _distinct(values: list[str]) -> tuple[str, ...]:
    seen: dict[str, str] = {}
    for value in values:
        key = value.casefold()
        if value and key not in seen:
            seen[key] = value
    return tuple(seen.values())


def build_schema(records: list[Record]) -> TenantSchema:
    """Derive one turn's slot vocabularies from the records in play."""
    valid = [record for record in records or [] if isinstance(record, dict)]
    brands = _distinct([record_brand(record) for record in valid])
    families = _distinct([level for record in valid for level in family_levels(record)])
    # The vocabulary spans every published word, including record names, because
    # it is what validates a compound split such as "smart|phone".
    names = [str(record.get("name") or record.get("title") or "") for record in valid]
    return TenantSchema(
        brands=brands,
        families=families,
        vocabulary=build_vocabulary([*brands, *families, *names]),
    )
