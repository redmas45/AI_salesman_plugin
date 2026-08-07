"""The semantic frame for one turn: constraints separated from operators.

Query-understanding work draws a hard line between two kinds of thing a request
can contain:

* **Constraints** identify *what* the customer is looking for - a brand, a
  family, a price bound. They are properties records either have or lack, so
  they can be searched for and filtered on.
* **Operators** say *how to choose* among whatever matched - a superlative
  ("best", "cheapest") with a scale, a tier ("premium", "budget"), and a limit
  ("top 3"). They are instructions to the ranker. No record has a field called
  "top", so an operator can never be a search term.

Keeping them apart structurally is the fix for the reported defect: the host
query was built from cleaned speech, so "show me the top 3 best phones from
Samsung" reached the storefront as ``top 3 phone from`` and rendered nothing.
Once operators live in their own fields they are incapable of leaking into a
query, and no list of banned words is needed to keep them out.

The operator lexicon below is English, not domain vocabulary: "best" and "top 3"
mean the same thing when ranking flights, policies or phones. Constraint values
come entirely from the tenant schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.nlu.schema import SLOT_BRAND, SLOT_FAMILY, SlotCandidate, TenantSchema

RANK_MAX = "max"
RANK_MIN = "min"

SCALE_PRICE = "price"
SCALE_RATING = "rating"
SCALE_RECENCY = "recency"
SCALE_TIER = "tier"
SCALE_UNSPECIFIED = ""

MAX_LIMIT = 20

# Superlatives, paired with the scale they quantify over. Order matters: the
# most specific phrasing is tested first so "best rated" is a rating request
# rather than an unspecified one.
_RANK_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"\b(?:best|top|highest)[-\s]?rated\b|\bmost\s+popular\b|\bhighest\s+rating\b", RANK_MAX, SCALE_RATING),
    (r"\b(?:cheapest|least\s+expensive|lowest\s+priced?|most\s+affordable)\b", RANK_MIN, SCALE_PRICE),
    (r"\b(?:most\s+expensive|costliest|priciest|highest\s+priced?)\b", RANK_MAX, SCALE_PRICE),
    (r"\b(?:newest|latest|most\s+recent)\b", RANK_MAX, SCALE_RECENCY),
    (r"\b(?:oldest)\b", RANK_MIN, SCALE_RECENCY),
    (r"\b(?:premium|flagship|high[-\s]?end|top[-\s]?of[-\s]?the[-\s]?range|luxury|pro\b)", RANK_MAX, SCALE_TIER),
    (r"\b(?:budget|entry[-\s]?level|basic|cheap|affordable)\b", RANK_MIN, SCALE_TIER),
    (r"\b(?:best|top|finest|greatest|leading|recommended)\b", RANK_MAX, SCALE_UNSPECIFIED),
    (r"\b(?:worst|lowest)\b", RANK_MIN, SCALE_UNSPECIFIED),
)

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a couple": 2, "a few": 3, "both": 2,
}

# A limit is a count attached to a request for records, not any stray number.
# "under 50000" is a price bound and must not be read as "show me 50000".
_LIMIT_RE = re.compile(
    r"\b(?:top|first|best|show|give|find|list|suggest|recommend|compare|pick|shortlist)\s+"
    r"(?:me\s+)?(?:the\s+)?(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|both)\b"
    r"|\b(\d{1,2}|two|three|four|five)\s+(?:best|top|cheapest|newest)\b",
    re.IGNORECASE,
)

# Words that are grammar rather than content. Used only to decide whether a turn
# said anything at all, never to build a query.
_FUNCTION_WORDS = frozenset({
    "a", "an", "the", "some", "any", "please", "can", "could", "would", "you",
    "me", "my", "i", "we", "us", "do", "does", "have", "has", "want", "need",
    "show", "give", "find", "get", "see", "look", "for", "from", "by", "of",
    "in", "on", "at", "to", "with", "and", "or", "is", "are", "am", "be",
    "there", "here", "hi", "hello", "hey", "ok", "okay", "yes", "no", "what",
    "which", "how", "many", "much", "about", "tell", "list", "all",
    # Demonstratives point at records already shown; they name nothing new.
    "this", "that", "these", "those", "it", "them", "one", "ones", "them",
})


@dataclass(frozen=True)
class RankOperator:
    """A superlative: a direction and the scale it quantifies over."""

    direction: str
    scale: str = SCALE_UNSPECIFIED

    @property
    def is_tier(self) -> bool:
        return self.scale == SCALE_TIER


@dataclass(frozen=True)
class SemanticFrame:
    """One turn, parsed into things to match and instructions for ranking."""

    text: str
    schema: TenantSchema
    brand_candidates: tuple[SlotCandidate, ...] = ()
    family_candidates: tuple[SlotCandidate, ...] = ()
    rank: RankOperator | None = None
    limit: int | None = None
    content_words: tuple[str, ...] = field(default_factory=tuple)

    def best(self, candidates: tuple[SlotCandidate, ...]) -> SlotCandidate | None:
        return candidates[0] if candidates else None

    @property
    def brand(self) -> str:
        chosen = self.best(self.brand_candidates)
        return chosen.value if chosen else ""

    @property
    def family(self) -> str:
        chosen = self.best(self.family_candidates)
        return chosen.value if chosen else ""

    def constraint_terms(self) -> tuple[str, ...]:
        """The searchable part of the turn, in the tenant's own words.

        Operators are structurally absent here, so no ranking word, count or
        preposition can reach a host search box.
        """
        terms = [
            candidate.searchable_value()
            for candidate in (self.best(self.brand_candidates), self.best(self.family_candidates))
            if candidate is not None
        ]
        return tuple(term for term in terms if term)

    def says_nothing_searchable(self) -> bool:
        return not self.constraint_terms() and not self.content_words


def _parse_rank(text: str) -> RankOperator | None:
    for pattern, direction, scale in _RANK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return RankOperator(direction=direction, scale=scale)
    return None


def _parse_limit(text: str) -> int | None:
    match = _LIMIT_RE.search(text)
    if not match:
        return None
    token = (match.group(1) or match.group(2) or "").lower()
    value = _NUMBER_WORDS.get(token)
    if value is None:
        try:
            value = int(token)
        except ValueError:
            return None
    return value if 1 <= value <= MAX_LIMIT else None


def _content_words(text: str, matched: tuple[str, ...]) -> tuple[str, ...]:
    """Words the turn used that neither an operator nor a slot accounted for.

    Their presence is the signal that the customer named something the tenant
    does not publish, which is a question to ask rather than a result to invent.
    """
    consumed = {word for value in matched for word in re.findall(r"[a-z0-9]+", value.lower())}
    remaining: list[str] = []
    stripped = text
    for pattern, _direction, _scale in _RANK_PATTERNS:
        stripped = re.sub(pattern, " ", stripped, flags=re.IGNORECASE)
    stripped = _LIMIT_RE.sub(" ", stripped)
    for word in re.findall(r"[a-z0-9]+", stripped.lower()):
        # Digits survive: counts and ranks have already been stripped above, so a
        # number still standing is part of what the customer named - "iPhone 17"
        # is one thing, and dropping the 17 turns it into every iPhone.
        if word in _FUNCTION_WORDS or word in consumed:
            continue
        if word not in remaining:
            remaining.append(word)
    return tuple(remaining)


def parse_frame(text: str, schema: TenantSchema) -> SemanticFrame:
    """Parse one turn against the tenant's schema. Pure and deterministic."""
    clean_text = str(text or "")
    brand_candidates = schema.candidates(SLOT_BRAND, clean_text)
    family_candidates = schema.candidates(SLOT_FAMILY, clean_text)
    matched = tuple(
        candidate.value
        for candidate in (*brand_candidates[:1], *family_candidates[:1])
    )
    return SemanticFrame(
        text=clean_text,
        schema=schema,
        brand_candidates=brand_candidates,
        family_candidates=family_candidates,
        rank=_parse_rank(clean_text),
        limit=_parse_limit(clean_text),
        content_words=_content_words(clean_text, matched),
    )
