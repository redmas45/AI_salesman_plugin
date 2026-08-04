"""Deterministic resolved-turn context for multi-turn dialogue.

The clarification gate used to see only the current transcript, so a follow-up
("What should I buy? No budget issue") looked like a fresh, under-determined
request and was re-asked for a product category it had already been given.

This module resolves ONE turn against bounded recent context and returns the
constraints the rest of the pipeline should act on. Resolution rules:

* Current explicit facts always override historical facts.
* Corrections replace only the corrected constraint.
* A genuine topic change discards stale product/brand constraints.
* Follow-ups inherit only relevant recent facts (type, brands, recipient,
  occasion, budget, references).
* "No budget issue" means *no maximum*, never a missing intent and never zero.

Design constraints honoured here: no LLM call, no catalog load, no concatenating
history into the query, and no hard-coded brand, retailer, or product names --
brand/type vocabularies are supplied by the caller from tenant data, so the
module stays vertical-independent.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass

from agent.retrieval.query_constraints import QueryConstraints, extract_ecommerce_constraints

# Only a bounded window of recent user turns is considered, so resolution cost
# stays constant regardless of conversation length.
MAX_HISTORY_USER_TURNS = 6
MAX_SUMMARY_USER_LINES = 4

# "No budget issue" / "money is no object": an explicit statement that there is
# no upper bound. Distinct from "no budget mentioned".
_BUDGET_WAIVER_RE = re.compile(
    r"\bno\s+budget\s*(?:issue|limit|constraint|problem|bar|cap)?\b"
    r"|\bbudget\s+is\s+(?:not\s+(?:an?\s+)?(?:issue|problem|concern)|no\s+bar)\b"
    r"|\bmoney\s+is\s+no\s+object\b"
    r"|\bprice\s+is\s+not\s+(?:an?\s+)?(?:issue|problem|concern)\b"
    r"|\bany\s+budget\b|\bno\s+(?:maximum|max|upper\s+limit)\b",
    re.IGNORECASE,
)

# A correction: the customer is restating a value the assistant got wrong.
# "But I said 50,000" carries no budget cue word, so the bare number only makes
# sense as a correction of the constraint already under discussion.
_CORRECTION_RE = re.compile(
    r"^\s*but\b|\bi\s+said\b|\bi\s+meant\b|\bi\s+already\s+said\b|^\s*no,\s|\bactually\b",
    re.IGNORECASE,
)
_BARE_NUMBER_RE = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s*(k)?\b", re.IGNORECASE)

# A frustrated continuity marker: the user is asserting they already answered.
_CONTINUITY_RE = re.compile(
    r"\bi\s+(?:told|said)\s+(?:you|u)\b|\bi\s+already\s+(?:told|said|mentioned)\b"
    r"|\bas\s+i\s+(?:said|mentioned|told)\b|\blike\s+i\s+said\b|\bsame\s+as\s+before\b",
    re.IGNORECASE,
)

# The shopper is buying for themselves.
_SELF_RECIPIENT_RE = re.compile(
    r"\bfor\s+(?:myself|me)\b|\bfor\s+(?:him|her)self\b|\bit\s+is\s+for\s+me\b",
    re.IGNORECASE,
)

# A broad apparel need with no concrete garment named.
_APPAREL_NEED_RE = re.compile(
    r"\b(?:something|anything)\s+to\s+wear\b|\bto\s+wear\b|\bclothing\b|\bclothes\b|\boutfit\b|\bapparel\b",
    re.IGNORECASE,
)

# General-knowledge / small-talk questions that are not shopping requests.
_OFF_TOPIC_RE = re.compile(
    r"\b(?:prime\s+minister|president|capital\s+of|weather|temperature|forecast"
    r"|latest\s+news|who\s+won|what\s+time\s+is\s+it|tell\s+me\s+a\s+joke)\b",
    re.IGNORECASE,
)

# An explicit switch of subject. Type-level conflict is not enough on its own:
# "actually show me Home Kitchen" names a CATEGORY, which the constraint model
# does not carry, so the previous brand used to survive and silently emptied the
# results. A switch cue that also names a new subject resets the stale scope.
_TOPIC_SWITCH_RE = re.compile(
    r"^\s*(?:actually|instead|forget\s+(?:that|it|those)|never\s+mind|nevermind"
    r"|let'?s\s+(?:look\s+at|see|try)|how\s+about|what\s+about|switch\s+to|change\s+to)\b",
    re.IGNORECASE,
)
# Words that carry no subject of their own, so a turn made only of these plus a
# number is a correction ("actually 20000"), not a change of topic.
_SWITCH_FILLER_WORDS = frozenset({
    "a", "an", "the", "some", "any", "please", "show", "see", "look", "at", "for",
    "me", "us", "i", "you", "do", "have", "want", "need", "find", "get", "give",
    "something", "anything", "it", "them", "to", "of", "and", "or", "is", "are",
    "under", "over", "below", "above", "budget", "price", "rs", "inr", "rupees",
})


def _switches_subject(text: str) -> bool:
    """True when an explicit switch cue is followed by a genuinely new subject."""
    if not _TOPIC_SWITCH_RE.search(text or ""):
        return False
    remainder = _TOPIC_SWITCH_RE.sub(" ", text or "", count=1)
    words = [word for word in re.findall(r"[a-z']+", remainder.lower()) if word not in _SWITCH_FILLER_WORDS]
    return bool(words)


_COUNT_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "both": 2,
}
# A requested item count follows an explicit request verb ("suggest two ...").
_REQUESTED_COUNT_RE = re.compile(
    r"\b(?:suggest|show|give|compare|recommend|find|list|top|pick|shortlist)\s+(?:me\s+)?(?:the\s+)?"
    r"(one|two|three|four|five|six|seven|eight|nine|ten|both|\d{1,2})\b",
    re.IGNORECASE,
)

_SUMMARY_USER_LINE_RE = re.compile(r"^\s*user\s*:\s*(.+)$", re.IGNORECASE)


def _corrected_ceiling(text: str) -> float | None:
    """A bare number restated in a correction replaces the previous ceiling."""
    match = _BARE_NUMBER_RE.search(text or "")
    if not match:
        return None
    value = float(match.group(1).replace(",", ""))
    if match.group(2):
        value *= 1000
    return value or None


def _detect_self_recipient(text: str) -> str | None:
    return "self" if _SELF_RECIPIENT_RE.search(text or "") else None


def _requested_count(text: str) -> int | None:
    match = _REQUESTED_COUNT_RE.search(text or "")
    if not match:
        return None
    token = match.group(1).lower()
    if token in _COUNT_WORDS:
        return _COUNT_WORDS[token]
    try:
        value = int(token)
    except ValueError:
        return None
    return value if 1 <= value <= 10 else None


def _summary_user_lines(session_summary: str) -> list[str]:
    """Newest-first user lines from the rolling session summary."""
    lines: list[str] = []
    for line in reversed(str(session_summary or "").splitlines()):
        match = _SUMMARY_USER_LINE_RE.match(line)
        if match:
            lines.append(match.group(1).strip())
        if len(lines) >= MAX_SUMMARY_USER_LINES:
            break
    return lines


def _recent_user_texts(history: list[dict] | None, session_summary: str) -> list[str]:
    """Bounded, newest-first user utterances from history, else the summary."""
    texts: list[str] = []
    for message in reversed(list(history or [])):
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "").lower() != "user":
            continue
        content = str(message.get("content") or "").strip()
        if content:
            texts.append(content)
        if len(texts) >= MAX_HISTORY_USER_TURNS:
            break
    return texts or _summary_user_lines(session_summary)


@dataclass(frozen=True)
class ResolvedTurnContext:
    """One turn resolved against bounded recent conversation context."""

    constraints: QueryConstraints
    current: QueryConstraints
    inherited_fields: tuple[str, ...] = ()
    is_topic_change: bool = False
    is_greeting: bool = False
    is_off_topic: bool = False
    budget_waived: bool = False
    requested_count: int | None = None
    referenced_product_ids: tuple[str, ...] = ()
    clarification_topic: str = ""

    @property
    def is_followup(self) -> bool:
        return self.constraints.is_followup

    def inherited_product_context(self) -> bool:
        """True when a product type or brand came from earlier in the conversation."""
        return any(field in self.inherited_fields for field in ("product_types", "brands"))

    def should_ask_clarification(self) -> bool:
        """Ask exactly one question only when resolved context is still insufficient.

        Never re-asks for a category, brand, recipient, or budget already supplied
        in this conversation.
        """
        if self.is_greeting or self.is_off_topic:
            return False
        if self.clarification_topic:
            return True
        if self.constraints.has_explicit_product_request():
            return False
        if self.inherited_product_context():
            return False
        if self.constraints.is_followup:
            return False
        return self.constraints.should_ask_clarification()

    def clarification_question(self) -> str:
        """One focused question that never re-asks a known fact."""
        from agent.retrieval.query_constraints import clarification_question

        if self.clarification_topic == "apparel":
            return (
                "Happy to help you find something to wear. "
                "What kind of clothing are you after — a shirt, a jacket, or footwear?"
            )
        return clarification_question(self.constraints)

    def cache_identity(self) -> str:
        """Stable fingerprint of the resolved hard constraints for cache identity."""
        parts = [
            f"b={','.join(self.constraints.brands)}",
            f"t={','.join(self.constraints.product_types)}",
            f"min={self.constraints.min_price if self.constraints.min_price is not None else ''}",
            f"max={self.constraints.max_price if self.constraints.max_price is not None else ''}",
            f"waived={int(self.budget_waived)}",
            f"r={self.constraints.recipient or ''}",
            f"n={self.requested_count or ''}",
        ]
        return "|".join(parts)


def resolve_turn_context(
    query: str,
    *,
    history: list[dict] | None = None,
    session_summary: str = "",
    recent_product_ids: tuple[str, ...] = (),
    catalog_brands: tuple[str, ...] | list[str] = (),
    catalog_types: tuple[str, ...] | list[str] = (),
) -> ResolvedTurnContext:
    """Resolve one turn against bounded recent context. Pure and deterministic."""
    from agent.responses.conversation_shortcuts import is_simple_greeting

    text = str(query or "")
    brands = tuple(catalog_brands)
    types = tuple(catalog_types)

    current = extract_ecommerce_constraints(text, catalog_brands=brands, catalog_types=types)
    budget_waived = bool(_BUDGET_WAIVER_RE.search(text))
    is_greeting = is_simple_greeting(text)
    is_off_topic = bool(_OFF_TOPIC_RE.search(text))
    # A continuity complaint is a follow-up even without a leading "no"/"actually".
    is_correction = bool(_CORRECTION_RE.search(text))
    is_followup = current.is_followup or is_correction or bool(_CONTINUITY_RE.search(text))
    requested_count = _requested_count(text)

    # A greeting starts a clean slate: it must not drag product context forward.
    historical_texts = [] if is_greeting else _recent_user_texts(history, session_summary)
    historical = [
        extract_ecommerce_constraints(item, catalog_brands=brands, catalog_types=types)
        for item in historical_texts
    ]

    def newest(selector) -> object:
        for candidate in historical:
            value = selector(candidate)
            if value:
                return value
        return None

    inherited_types = tuple(newest(lambda item: item.product_types) or ())
    inherited_brands = tuple(newest(lambda item: item.brands) or ())
    inherited_recipient = newest(lambda item: item.recipient)
    if not inherited_recipient:
        for item in historical_texts:
            inherited_recipient = _detect_self_recipient(item)
            if inherited_recipient:
                break
    inherited_occasion = newest(lambda item: item.occasion)
    inherited_max = newest(lambda item: item.max_price)
    inherited_min = newest(lambda item: item.min_price)

    # A genuine topic change: this turn names a product type that shares nothing
    # with the active topic. Stale product and brand constraints are dropped.
    is_topic_change = bool(
        current.product_types
        and inherited_types
        and not set(current.product_types) & set(inherited_types)
    ) or _switches_subject(text)
    if is_topic_change:
        inherited_types = ()
        inherited_brands = ()

    inherited_fields: list[str] = []

    def resolve(current_value, inherited_value, field_name):
        if current_value:
            return current_value
        if inherited_value:
            inherited_fields.append(field_name)
            return inherited_value
        return current_value

    product_types = resolve(current.product_types, inherited_types, "product_types")
    # An explicit brand on this turn is authoritative: never widen it from history.
    resolved_brands = resolve(current.brands, inherited_brands, "brands")
    # Resolve the current turn's recipient (including "for myself", which the
    # per-utterance extractor does not model) BEFORE falling back to history, so a
    # stated recipient on this turn always wins.
    current_recipient = current.recipient or _detect_self_recipient(text)
    recipient = resolve(current_recipient, inherited_recipient, "recipient")
    occasion = resolve(current.occasion, inherited_occasion, "occasion")

    if budget_waived:
        # Explicitly unbounded: drop any inherited ceiling rather than inheriting it.
        max_price = None
    else:
        # "But I said 50,000" carries no budget cue word, so the bare number is
        # only meaningful as a correction of the ceiling already under discussion.
        # Without this the assistant keeps quoting the figure it got wrong.
        corrected = _corrected_ceiling(text) if (is_correction and inherited_max) else None
        max_price = corrected or resolve(current.max_price, inherited_max, "max_price")
    min_price = resolve(current.min_price, inherited_min, "min_price")

    # A broad apparel need with no garment named still deserves one focused question.
    clarification_topic = ""
    if not product_types and _APPAREL_NEED_RE.search(text):
        clarification_topic = "apparel"

    resolved = dataclasses.replace(
        current,
        brands=tuple(resolved_brands or ()),
        product_types=tuple(product_types or ()),
        recipient=recipient,
        occasion=occasion,
        min_price=min_price,
        max_price=max_price,
        is_followup=is_followup,
    )

    return ResolvedTurnContext(
        constraints=resolved,
        current=current,
        inherited_fields=tuple(inherited_fields),
        is_topic_change=is_topic_change,
        is_greeting=is_greeting,
        is_off_topic=is_off_topic,
        budget_waived=budget_waived,
        requested_count=requested_count,
        referenced_product_ids=() if (is_topic_change or is_greeting) else tuple(recent_product_ids),
        clarification_topic=clarification_topic,
    )
