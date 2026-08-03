"""Vertical-independent structured query constraints + the e-commerce extractor.

A :class:`QueryConstraints` value is the typed, normalized representation of
what a user asked for on the current turn. The container is deliberately
vertical-independent: it carries generic fields, and each vertical supplies its
own extractor that maps raw text onto the subset of fields it understands.

``extract_ecommerce_constraints`` is the e-commerce mapping: it resolves a query
to brand, product type, budget (min/max price), recipient, occasion, requested
attributes, exclusions, ambiguity, and follow-up references. Travel, insurance,
and other verticals keep their own extractors and their own domain fields; they
are expected to reuse only the generic container and the price/ambiguity helpers.

Design notes:
* Budget parsing lives in :func:`parse_budget` so there is a single source of
  truth for price. ``agent.retrieval.product_rag.extract_price_constraints``
  delegates here, which keeps price a hard invariant across retrieval, actions,
  the formatter, the cache, and the final response.
* Nothing in this module performs I/O; brand and type vocabularies are passed in
  by the caller (derived from the tenant catalog) so the extractor stays pure and
  testable and never hard-codes AI-KART's taxonomy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Budget parsing (single source of truth for price) ----------------------

# A currency-tolerant amount: optional ₹/Rs/INR/rupees on either side, optional
# thousands separators, optional decimal, optional "k" multiplier ("1.5k").
_CURRENCY = r"(?:₹|rs\.?|inr|rupees?)"
_AMOUNT = r"(\d[\d,]*(?:\.\d+)?)\s*(k(?![a-z]))?"
_MONEY = rf"{_CURRENCY}?\s*{_AMOUNT}\s*{_CURRENCY}?"

_THOUSAND_MULTIPLIER = 1000

# Ceiling ("no more than X") cue words.
_MAX_CUE = (
    r"under|below|less\s+than|within|upto|up\s+to|at\s+most|max(?:imum)?"
    r"|cheaper\s+than|no\s+more\s+than|not\s+more\s+than|not\s+above"
)
# Floor ("at least X") cue words.
_MIN_CUE = (
    r"above|over|more\s+than|at\s+least|min(?:imum)?|starting\s+from"
    r"|costlier\s+than|not\s+less\s+than|not\s+below|not\s+under"
)
# Budget-context cue words: a number following these is a spending ceiling.
_BUDGET_CUE = r"budget|spend|spending|afford|price\s+range"

_BETWEEN_RE = re.compile(rf"(?:between|from)\s+{_MONEY}\s*(?:and|to|-)\s*{_MONEY}", re.IGNORECASE)
_MAX_RE = re.compile(rf"(?:{_MAX_CUE})\s*{_MONEY}", re.IGNORECASE)
_MIN_RE = re.compile(rf"(?:{_MIN_CUE})\s*{_MONEY}", re.IGNORECASE)
# "budget of/is/: 1500", "spend around 1500", "I have a budget of 1500".
_BUDGET_RE = re.compile(rf"(?:{_BUDGET_CUE})\s*(?:of|is|:|=|around|about)?\s*{_MONEY}", re.IGNORECASE)
# "1.5k budget", "1500 to spend" — the amount precedes the budget cue.
_BUDGET_TRAILING_RE = re.compile(rf"{_MONEY}\s*(?:to\s+)?(?:{_BUDGET_CUE})", re.IGNORECASE)
# Explicit wallet-size language. Plain counts such as "I have 2 phones" must not
# become a two-rupee budget.
_HAVE_BUDGET_RE = re.compile(
    rf"i\s+(?:only\s+)?(?:have|got)\s+(?:a\s+|an\s+|the\s+)?budget(?:\s+of|\s+is|\s*:)?\s*{_MONEY}",
    re.IGNORECASE,
)
_ONLY_HAVE_RE = re.compile(rf"i\s+only\s+(?:have|got)\s+{_MONEY}", re.IGNORECASE)
# "around 2500" is a ceiling, while "around 3 cameras" is a quantity and is
# rejected by the suffix guard below.
_APPROX_RE = re.compile(rf"(?:around|about|roughly|approx(?:imately)?)\s*{_MONEY}", re.IGNORECASE)
# Bare "1500 rupees" / "₹1500" — only trusted as a ceiling with budget context.
_BARE_MONEY_RE = re.compile(rf"(?:{_CURRENCY}\s*{_AMOUNT}|{_AMOUNT}\s*{_CURRENCY})", re.IGNORECASE)
_BUDGET_CONTEXT_WORDS = (
    "only", "just", "budget", "afford", "cheap", "save", "spend", "spending", "have", "got",
)

# Numeric specifications and quantities commonly follow the same cue words as
# prices ("under 2 kg", "at least 8 GB", "between 4 and 5 stars").
_NON_PRICE_SUFFIX_RE = re.compile(
    r"^\s*(?:"
    r"kg|kgs|kilograms?|g|grams?|mg|lb|lbs|pounds?|oz|ounces?|"
    r"mm|cm|m|metres?|meters?|km|kilometres?|kilometers?|"
    r"mah|wh|w|watts?|v|volts?|hz|khz|mhz|ghz|"
    r"kb|mb|gb|tb|bytes?|bits?|mp|megapixels?|"
    r"inch|inches|feet|ft|litres?|liters?|ml|"
    r"stars?|ratings?|reviews?|units?|pieces?|items?|products?|"
    r"phones?|cameras?|laptops?|tablets?|watches?|smartwatches?|chargers?"
    r")\b",
    re.IGNORECASE,
)


def _amount(number: str, multiplier: str | None) -> float:
    value = float(number.replace(",", ""))
    return value * _THOUSAND_MULTIPLIER if multiplier else value


def _is_non_price_measurement(text: str, match: re.Match[str]) -> bool:
    return bool(_NON_PRICE_SUFFIX_RE.match(text[match.end() :]))


def parse_budget(query: str) -> dict[str, float]:
    """Extract a price ceiling/floor from natural language.

    Returns a dict with optional ``min_price`` / ``max_price`` keys. Handles
    ₹/Rs/INR/rupees, thousands separators, "1.5k" shorthand, ranges, floors,
    and the many phrasings of a stated budget ("budget of 1500", "around 1500",
    "I can spend up to 1500", "within 1500"). A bare number is only treated as a
    price when the surrounding text carries an explicit budget cue.
    """
    text = (query or "").lower()
    constraints: dict[str, float] = {}

    range_match = _BETWEEN_RE.search(text)
    if range_match and not _is_non_price_measurement(text, range_match):
        low = _amount(range_match.group(1), range_match.group(2))
        high = _amount(range_match.group(3), range_match.group(4))
        return {"min_price": min(low, high), "max_price": max(low, high)}

    max_match = _MAX_RE.search(text)
    if max_match and not _is_non_price_measurement(text, max_match):
        constraints["max_price"] = _amount(max_match.group(1), max_match.group(2))

    min_match = _MIN_RE.search(text)
    if min_match and not _is_non_price_measurement(text, min_match):
        constraints["min_price"] = _amount(min_match.group(1), min_match.group(2))

    if "max_price" not in constraints:
        budget_match = (
            _BUDGET_RE.search(text)
            or _BUDGET_TRAILING_RE.search(text)
            or _HAVE_BUDGET_RE.search(text)
            or _ONLY_HAVE_RE.search(text)
        )
        if budget_match:
            constraints["max_price"] = _amount(budget_match.group(1), budget_match.group(2))

    if "max_price" not in constraints:
        approximate_match = _APPROX_RE.search(text)
        if approximate_match and not _is_non_price_measurement(text, approximate_match):
            constraints["max_price"] = _amount(approximate_match.group(1), approximate_match.group(2))

    if not constraints:
        bare_match = _BARE_MONEY_RE.search(text)
        if bare_match and any(word in text for word in _BUDGET_CONTEXT_WORDS):
            number = bare_match.group(1) or bare_match.group(3)
            multiplier = bare_match.group(2) or bare_match.group(4)
            constraints["max_price"] = _amount(number, multiplier)

    return constraints


# --- Recipient / occasion / ambiguity lexicons ------------------------------

# Ordered so multi-word recipients ("best friend") win over single words.
_RECIPIENTS = (
    "girlfriend", "boyfriend", "husband", "wife", "fiance", "fiancee", "partner",
    "mother", "father", "mom", "mum", "dad", "daughter", "son", "sister", "brother",
    "grandmother", "grandfather", "grandma", "grandpa", "best friend", "friend",
    "colleague", "boss", "teacher", "kids", "kid", "child", "baby", "parents",
)
_RECIPIENT_RE = re.compile(
    r"\bfor\s+(?:my|a|an|his|her|their|the)\s+(" + "|".join(re.escape(r) for r in _RECIPIENTS) + r")\b",
    re.IGNORECASE,
)
_OCCASIONS = (
    "birthday", "anniversary", "wedding", "valentine", "valentines", "diwali",
    "christmas", "rakhi", "raksha bandhan", "new year", "graduation", "housewarming",
)
_GIFT_RE = re.compile(r"\b(gift|present|gifting|surprise)\b", re.IGNORECASE)

# Undecided / "just browsing" phrasings that should trigger one clarification.
_UNDECIDED_RE = re.compile(
    r"\b(what should i (?:buy|get)|not decided|not sure|no idea|help me (?:choose|decide|pick)"
    r"|suggest something|recommend something|anything good|surprise me|just browsing|show me something)\b",
    re.IGNORECASE,
)
# Follow-up / correction markers ("No, ...", "actually", "instead", "that one").
_FOLLOWUP_RE = re.compile(
    r"^\s*(no|nope|actually|instead|wait|i meant|rather)\b"
    r"|\b(that one|this one|the (?:first|second|third|last|cheaper|other) one"
    r"|the \w+ (?:one|watch|phone|laptop))\b",
    re.IGNORECASE,
)

# Tokens that carry no product signal; used to detect malformed / empty intent.
_NOISE_WORDS = frozenset(
    {
        "i", "im", "i'm", "a", "an", "the", "is", "it", "its", "it's", "am", "are", "was",
        "do", "you", "me", "my", "for", "what", "should", "buy", "get", "want", "need",
        "looking", "interested", "just", "some", "something", "anything", "products",
        "product", "items", "item", "please", "can", "could", "would", "to", "in", "of",
        "and", "or", "not", "decided", "sure", "hello", "hi", "hey",
    }
)


@dataclass(frozen=True)
class QueryConstraints:
    """Typed, vertical-independent constraints extracted from one user turn."""

    raw_query: str
    brands: tuple[str, ...] = ()
    product_types: tuple[str, ...] = ()
    min_price: float | None = None
    max_price: float | None = None
    recipient: str | None = None
    occasion: str | None = None
    attributes: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    is_followup: bool = False
    is_ambiguous: bool = False
    ambiguity_reason: str = ""
    references: tuple[str, ...] = field(default_factory=tuple)

    def price_constraints(self) -> dict[str, float]:
        """Bridge to the legacy ``{'min_price', 'max_price'}`` dict shape."""
        out: dict[str, float] = {}
        if self.min_price is not None:
            out["min_price"] = self.min_price
        if self.max_price is not None:
            out["max_price"] = self.max_price
        return out

    def has_price_constraint(self) -> bool:
        return self.min_price is not None or self.max_price is not None

    def has_explicit_product_request(self) -> bool:
        """True when the user named a brand and/or a concrete product type."""
        return bool(self.brands or self.product_types)

    def requires_both_brand_and_type(self) -> bool:
        """True when the user named both a brand and a type (conjunctive match)."""
        return bool(self.brands and self.product_types)

    def should_ask_clarification(self) -> bool:
        """Ask exactly one clarification only for clearly under-determined asks.

        Fires for malformed/undecided requests ("what should I buy", nonsense) and
        recipient-only gifts. Mood/need queries (reason ``underspecified``) are left
        to normal retrieval so the "suggest something for a mood" flow is preserved.
        """
        return self.is_ambiguous and self.ambiguity_reason in {"no_product_signal", "gift_needs_detail"}


def clarification_question(constraints: QueryConstraints) -> str:
    """One useful, grounded clarification for an under-determined request."""
    if constraints.ambiguity_reason == "gift_needs_detail":
        recipient = constraints.recipient or "them"
        budget = f" within ₹{int(constraints.max_price)}" if constraints.max_price else ""
        return (
            f"I'd love to help you find a gift for {recipient}{budget}. "
            "What kind of product did you have in mind — a category or a brand?"
        )
    return (
        "I can definitely help — what kind of product are you looking for? "
        "A category, a brand, or a budget would let me narrow it down."
    )


def _matched_vocabulary(text: str, vocabulary: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Return whole-word matches from ``vocabulary`` in order of appearance."""
    matches: list[tuple[int, str]] = []
    for term in vocabulary:
        normalized = term.strip().lower()
        if not normalized:
            continue
        found = re.search(rf"(?:^|\W){re.escape(normalized)}(?:es|s)?(?:\W|$)", text)
        if found:
            matches.append((found.start(), normalized))
    ordered: list[str] = []
    seen: set[str] = set()
    for _position, term in sorted(matches):
        if term not in seen:
            seen.add(term)
            ordered.append(term)
    return tuple(ordered)


def _detect_recipient(text: str) -> str | None:
    match = _RECIPIENT_RE.search(text)
    if not match:
        return None
    recipient = match.group(1).lower()
    return {"mum": "mom"}.get(recipient, recipient)


def _detect_occasion(text: str) -> str | None:
    for occasion in _OCCASIONS:
        if re.search(rf"\b{re.escape(occasion)}\b", text):
            return occasion
    if _GIFT_RE.search(text):
        return "gift"
    return None


def _is_malformed(text: str, has_signal: bool) -> bool:
    """A query with no product signal and no meaningful content is malformed."""
    if has_signal:
        return False
    content_tokens = [tok for tok in re.findall(r"[a-z']+", text) if tok not in _NOISE_WORDS]
    return len(content_tokens) == 0 or bool(_UNDECIDED_RE.search(text))


def extract_ecommerce_constraints(
    query: str,
    *,
    catalog_brands: tuple[str, ...] | list[str] = (),
    catalog_types: tuple[str, ...] | list[str] = (),
) -> QueryConstraints:
    """Map an e-commerce query onto :class:`QueryConstraints`.

    ``catalog_brands`` / ``catalog_types`` are the tenant's real brand and
    product-type vocabularies (lower-cased). Passing them keeps brand/type
    detection grounded in what the store actually sells rather than a guess.
    """
    text = " " + (query or "").lower().strip() + " "
    budget = parse_budget(query)

    brands = _matched_vocabulary(text, tuple(catalog_brands))
    product_types = _matched_vocabulary(text, tuple(catalog_types))
    recipient = _detect_recipient(text)
    occasion = _detect_occasion(text)
    is_followup = bool(_FOLLOWUP_RE.search(query or ""))

    has_explicit = bool(brands or product_types)
    has_any_signal = has_explicit or bool(budget) or recipient is not None

    # Ambiguity: a gift with a named recipient but no product/brand/budget still
    # needs one clarifying question; a query with no product signal at all
    # (malformed, undecided, "what should I buy") is ambiguous by definition.
    ambiguity_reason = ""
    if not has_explicit:
        if _is_malformed(text, has_explicit):
            ambiguity_reason = "no_product_signal"
        elif recipient is not None or occasion is not None:
            ambiguity_reason = "gift_needs_detail"
        elif not budget:
            ambiguity_reason = "underspecified"
    # A follow-up correction is a continuation, not a fresh ambiguous request.
    is_ambiguous = bool(ambiguity_reason) and not is_followup

    return QueryConstraints(
        raw_query=query or "",
        brands=brands,
        product_types=product_types,
        min_price=budget.get("min_price"),
        max_price=budget.get("max_price"),
        recipient=recipient,
        occasion=occasion,
        is_followup=is_followup,
        is_ambiguous=is_ambiguous,
        ambiguity_reason=ambiguity_reason,
    )
