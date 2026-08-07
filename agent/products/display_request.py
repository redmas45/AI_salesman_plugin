"""The canonical display request for one turn.

A turn that shows records has to agree with itself in five places: what Maya
says, which ids the UI action carries, what the browser executes against the
host, what the session remembers, and what the CRM log records. Deriving any of
those separately is what let the answer name three real products while the
storefront rendered ``0 results for "top 3 phone from"``.

The host query used to be built by cleaning the transcript and keeping its first
few surviving words. That is the wrong source: "top", "best", "3", "from" and
"by" describe *how to choose* among records, not anything a catalog can be
searched for. This module builds the query from the slots the turn actually
filled, using the tenant's own published values for them.

Ranking and counting stay here as separate, explicit values: ``requested_count``
is how many Maya was asked to recommend, ``matching_total`` is how many records
qualified. They are different numbers and the wording must never merge them.

Nothing here knows a vendor, a catalog or a vertical: every value comes from the
tenant's own schema via the turn's ``SemanticFrame``.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import Any

from agent.nlu.frame import SemanticFrame
from agent.nlu.lexical import (
    MIN_COMPOUND_HEAD_LENGTH,
    MIN_COMPOUND_MODIFIER_LENGTH,
    word_forms,
)

Record = dict[str, Any]

# A host search box matches literal catalog text. More than a few terms and even
# a correct query starts returning nothing, so the canonical query stays short.
MAX_QUERY_TERMS = 3

# A record's own name may need more terms than a category query to stay unique.
MAX_RECORD_NAME_TERMS = 4

# Spoken counts, written out for the shortlist wording.
_COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def canonical_host_query(
    frame: SemanticFrame, records: list[Record], *, detail_turn: bool = False
) -> str:
    """A query the host's own search can answer, in decreasing order of proof.

    Three sources are tried, and the order is the whole point - each step is a
    weaker guarantee that the records the answer names survive on the page:

    1. The tenant's *published* values for the slots this turn filled. A record
       carrying "Smartphones" is found by searching "smartphones", because that
       is its own catalog text. Measured against the local storefront, this is
       also the only step that is guaranteed: "smartphones" returns all 53
       smartphones while the customer's own word "phone" returns 33 of them and
       drops 20.
    2. The customer's own words, but only those the selected records actually
       publish, and rendered in the records' spelling. Someone asking for
       "smartwatches" gets "smartwatches" - never the vendor and full label of
       whatever happened to match, which is how a request for a category turned
       into "amazfit smartwatches fitness bands".
    3. The record's own name, when a single record is the answer and the turn
       named no concept the records publish. Its identity is the one query that
       puts exactly it on the page. A turn already known to be about one record
       (``detail_turn``) takes this route first rather than last.

    Ranking words, counts and prepositions live in the frame's operator fields
    and have no path into any of the three, which is what makes
    `0 results for "top 3 phone from"` unreachable.

    A turn that reaches none of them contributes no query. That is deliberate:
    sending truncated speech instead is exactly the defect being fixed, and an
    empty query makes the host executor decline the action rather than claim a
    search it cannot stand behind.
    """
    identity = _lone_record_name(records)[:MAX_RECORD_NAME_TERMS]
    if detail_turn and identity:
        # The turn is about one record. Its name is the exact host identity, and
        # using it means nothing else the customer mentioned in passing - an
        # accessory, a use case - can AND that record off its own page.
        return " ".join(identity)

    terms: list[str] = []
    for value in frame.constraint_terms():
        terms.extend(word for word in str(value).lower().split() if word)
    if terms:
        return " ".join(_distinct_terms(terms)[:MAX_QUERY_TERMS])

    published = _published_concept_terms(frame.content_words, records)
    if published:
        return " ".join(_distinct_terms(published)[:MAX_QUERY_TERMS])

    return " ".join(identity)


# The record text a customer word is checked against: the tenant's own labels.
# Descriptions are deliberately excluded - they are prose, and matching against
# them let ordinary verbs qualify as concepts ("phone should" was a real query
# built from a product paragraph containing the word "should").
_SEARCHABLE_FIELDS = (
    "name",
    "title",
    "brand",
    "vendor",
    "category",
    "category_name",
    "subcategory",
    "product_type",
)


def _published_concept_terms(content_words: tuple[str, ...], records: list[Record]) -> list[str]:
    """The customer's words that the selected records actually publish.

    A word the records do not carry is dropped rather than searched for. That is
    what stops an accessory the customer merely *mentioned* from being ANDed into
    the query and narrowing the product they asked about off the page.

    Which spelling is returned depends on how the word was recognised:

    * The record publishes the same word, possibly in another number ("phones"
      against a "Phone") - the published form wins, because it is the spelling
      proven to exist in the host's text.
    * The record publishes a longer compound the word heads ("watches" against
      "Smartwatches") - the customer's word wins. The compound is a *different,
      narrower* thing, and substituting it would answer a question about watches
      with smart ones only.
    """
    published = _record_word_forms(records)
    chosen: list[str] = []
    for word in content_words:
        spoken_forms = word_forms(word)
        for surface, forms in published:
            if spoken_forms & forms:
                term = surface
            elif _heads_published_compound(spoken_forms, forms):
                term = word
            else:
                continue
            if term not in chosen:
                chosen.append(term)
            break
    return chosen


def _heads_published_compound(spoken_forms: frozenset[str], published_forms: frozenset[str]) -> bool:
    """True when a published word is a compound the customer named the head of.

    Slot resolution asks a stricter question, because there a compound match
    *substitutes* the tenant's word for the customer's and a wrong one silently
    changes the request. Here the customer's own word is what gets searched, so
    the only thing a loose match can do is search exactly what was said - and the
    length bounds still reject the fragment case ("tr|ipod", "tri|pod") that
    started all of this.
    """
    for head in spoken_forms:
        if len(head) < MIN_COMPOUND_HEAD_LENGTH:
            continue
        for whole in published_forms:
            if whole != head and whole.endswith(head) and len(whole) - len(head) >= MIN_COMPOUND_MODIFIER_LENGTH:
                return True
    return False


def _record_word_forms(records: list[Record]) -> list[tuple[str, frozenset[str]]]:
    """Every distinct word the records publish, with its comparable forms."""
    seen: dict[str, frozenset[str]] = {}
    for record in records or []:
        if not isinstance(record, dict):
            continue
        values = [record.get(field_name) for field_name in _SEARCHABLE_FIELDS]
        tags = record.get("tags")
        if isinstance(tags, (list, tuple)):
            values.extend(tags)
        for value in values:
            for word in _normalized_words(str(value or "")):
                if word not in seen:
                    seen[word] = word_forms(word)
    return list(seen.items())


def _lone_record_name(records: list[Record]) -> list[str]:
    """The published name of the single record being displayed, if there is one."""
    valid = [record for record in records or [] if isinstance(record, dict) and record.get("id")]
    if len(valid) != 1:
        return []
    name = str(valid[0].get("name") or valid[0].get("title") or "")
    return [word for word in _normalized_words(name) if word]


def _normalized_words(value: str) -> list[str]:
    """Lowercase words with punctuation dropped, so a name is searchable text."""
    return re.findall(r"[a-z0-9]+", str(value or "").lower())


def _distinct_terms(terms: list[str]) -> list[str]:
    """Drop terms that are only another term's singular, plural, or compound form.

    A catalog publishing "Smartphones" recognises both "smartphone" and
    "phones", and a turn naming the family can resolve to more than one of them.
    Sending all of them narrows a host search to nothing.
    """
    kept: list[str] = []
    for term in terms:
        if any(term in existing or existing in term for existing in kept):
            continue
        kept.append(term)
    return kept


@dataclass(frozen=True)
class CanonicalDisplayRequest:
    """One turn's display contract, shared by speech, UI, browser, log."""

    host_query: str
    frame: SemanticFrame
    selected_records: tuple[Record, ...] = field(default_factory=tuple)
    matching_total: int = 0
    requested_count: int | None = None

    @property
    def selected_ids(self) -> tuple[str, ...]:
        """The ids, in display order, that every surface must agree on."""
        return tuple(str(record.get("id")) for record in self.selected_records if record.get("id"))

    @property
    def displayed_count(self) -> int:
        return len(self.selected_records)

    @property
    def page_shows_more_than_selected(self) -> bool:
        """True when the host listing holds records the answer does not name."""
        return self.matching_total > self.displayed_count

    def count_summary(self) -> str:
        """Wording that states both numbers rather than merging them.

        Saying "I found 4" and then naming three is only honest if the shortlist
        is described as a shortlist; claiming the page holds three would be false.
        """
        subject = self.host_query or "matching records"
        if not self.page_shows_more_than_selected:
            if self.matching_total == 1:
                return f"I found one {subject}."
            return f"I found {self.matching_total} {subject} results."
        shortlist = _COUNT_WORDS.get(self.displayed_count, str(self.displayed_count))
        return f"I found {self.matching_total} {subject} results. My top {shortlist} are"


def build_display_request(
    frame: SemanticFrame,
    *,
    matching_records: list[Record],
    requested_count: int | None = None,
) -> CanonicalDisplayRequest:
    """Resolve one turn into the display contract every surface reads from.

    ``requested_count`` defaults to the limit the turn itself asked for, so
    "the top 3" shortlists three of however many matched.
    """
    limit = requested_count if requested_count is not None else frame.limit
    qualified = [record for record in matching_records if record.get("id")]
    selected = qualified[:limit] if limit else qualified
    return CanonicalDisplayRequest(
        host_query=canonical_host_query(frame, selected or qualified),
        frame=frame,
        selected_records=tuple(selected),
        matching_total=len(qualified),
        requested_count=limit,
    )
