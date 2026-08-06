"""Detecting when a turn refers back to records already shown.

A turn like "add this to the cart" or "the first one" carries no searchable
terms of its own. Its meaning lives entirely in the set of records the customer
was just shown, so the pipeline must resolve it against that ordered set rather
than run a fresh catalog search.

The detector previously recognised "this one", "that one" and "add it", but not
the two most common phrasings: a bare demonstrative used as an object ("add this
to the cart") and any ordinal at all ("the first one", "I'll take the second").
Both fell through to a fresh search for a query with no product terms, which is
how "add this to the cart" reached an unrelated earlier result set.

Two rules matter here:

* A demonstrative only counts as a reference when it is used as a *pronoun*.
  "Add this to the cart" refers back; "show me this week's deals" does not, and
  the difference is whether a noun follows.
* An ordinal only counts when it selects from a list. "The first one" selects;
  "first I want to browse" does not.

The vocabulary is ordinary English, so the same rules hold for a travel
itinerary, an insurance quote list, or any future vertical.
"""

from __future__ import annotations

import re

# The words a customer uses to point at something already on screen.
_DEMONSTRATIVE = r"(?:this|that|these|those|it|them)"

# Verbs that take an already-shown record as their object.
_SELECTION_VERB = (
    r"(?:add|buy|order|take|get|put|place|choose|pick|select|open|view|show|"
    r"compare|remove|delete)"
)

# A demonstrative is a pronoun when nothing it could modify follows it: the
# phrase ends, is punctuated, or continues with a preposition or filler.
_PRONOUN_TAIL = (
    r"(?=\s*$|\s*[.,;!?]|\s+(?:to|in|into|onto|from|for|please|now|instead|also|too|"
    r"as\s+well|then|and)\b|\s+(?:one|ones|option|product|item|record)\b)"
)

_ORDINAL_WORD = r"(?:first|second|third|fourth|fifth|last)"
_ORDINAL_SUFFIXED = r"(?:1st|2nd|3rd|4th|5th)"

_ORDINAL_REFERENCE_RE = re.compile(
    # "the first one", "the last option"
    rf"\b(?:the\s+)?(?:{_ORDINAL_WORD}|{_ORDINAL_SUFFIXED})\s+(?:one|option|item|product|record)\b"
    # "option 2", "number 3", "choice 1", "option two"
    rf"|\b(?:option|item|number|choice)\s*(?:[1-9]|one|two|three|four|five)\b"
    # "add the second", "I'll take the first"
    rf"|\b{_SELECTION_VERB}\s+(?:me\s+)?(?:the\s+)?(?:{_ORDINAL_WORD}|{_ORDINAL_SUFFIXED})\b"
    # A whole turn that is nothing but the choice: "The first one."
    rf"|^\s*(?:the\s+)?(?:{_ORDINAL_WORD}|{_ORDINAL_SUFFIXED})(?:\s+one)?\s*[.!]?\s*$",
    re.IGNORECASE,
)

_DEMONSTRATIVE_REFERENCE_RE = re.compile(
    rf"\b{_SELECTION_VERB}\s+(?:me\s+)?{_DEMONSTRATIVE}\b{_PRONOUN_TAIL}",
    re.IGNORECASE,
)

# Phrases that can only mean records already under discussion.
_SET_REFERENCE_RE = re.compile(
    r"\b(?:those|these|them|compared|shortlisted|best\s+one|best\s+option|"
    r"which\s+option|which\s+one|that\s+one|this\s+one|open\s+it|add\s+it|pick\s+it)\b",
    re.IGNORECASE,
)

# A superlative refers back only when the turn names nothing new. "The cheaper
# one" means one of the records just shown; "the cheapest item in the
# electronics section" names a new scope and must be searched, not inherited.
# Treating these alike is what let a jacket answer an explicit electronics
# question.
_SUPERLATIVE_REFERENCE_RE = re.compile(
    r"\b(?:the\s+other|the\s+cheaper|the\s+cheapest|the\s+better|better\s+value|"
    r"the\s+more\s+expensive|the\s+pricier)\b",
    re.IGNORECASE,
)

# Words that carry no subject of their own, so a turn built only from these plus
# a superlative is still a pure back-reference.
_SUBJECTLESS_WORDS = frozenset({
    "a", "add", "an", "and", "are", "as", "at", "back", "basket", "bag", "buy", "can", "cart",
    "choose", "do", "does", "for", "get", "give", "go", "i", "id", "ill", "in", "into", "is",
    "it", "just", "know", "let", "like", "me", "my", "of", "ok", "okay", "one", "ones", "open",
    "option", "options", "or", "order", "pick", "place", "please", "product", "products", "put",
    "record", "records", "s", "select", "show", "so", "take", "tell", "than", "that", "the",
    "them", "then", "these", "this", "those", "to", "us", "view", "want", "was", "we", "what",
    "which", "will", "with", "would", "you", "your",
})


def _names_a_new_subject(text: str, matched_phrase: str) -> bool:
    """True when words other than the reference phrase and filler remain."""
    remainder = text.replace(matched_phrase, " ")
    words = re.findall(r"[a-z]+", remainder.lower())
    return any(word not in _SUBJECTLESS_WORDS for word in words)


def _is_superlative_back_reference(text: str) -> bool:
    match = _SUPERLATIVE_REFERENCE_RE.search(text)
    if not match:
        return False
    return not _names_a_new_subject(text, match.group(0))

_TRAILING_DEMONSTRATIVE_RE = re.compile(
    rf"\b{_SELECTION_VERB}\s+(?:that|this)\s+[a-z][a-z0-9-]{{2,}}\b",
    re.IGNORECASE,
)


def refers_to_shown_records(text: str) -> bool:
    """True when this turn's subject is a record the customer was already shown."""
    clean_text = str(text or "")
    if not clean_text.strip():
        return False
    return bool(
        _SET_REFERENCE_RE.search(clean_text)
        or _is_superlative_back_reference(clean_text)
        or _ORDINAL_REFERENCE_RE.search(clean_text)
        or _DEMONSTRATIVE_REFERENCE_RE.search(clean_text)
        or _TRAILING_DEMONSTRATIVE_RE.search(clean_text)
    )


def ordinal_position(text: str) -> int | None:
    """Zero-based position selected by an ordinal, or ``None`` if none is used.

    Only the ordinal *reference* forms count, so "first I want to browse" does
    not silently select the first record.
    """
    clean_text = str(text or "")
    if not _ORDINAL_REFERENCE_RE.search(clean_text):
        return None
    numbered = re.search(
        r"\b(?:option|item|number|choice)\s*([1-9]|one|two|three|four|five)\b",
        clean_text,
        re.IGNORECASE,
    )
    if numbered:
        token = numbered.group(1).lower()
        spelled = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        return (spelled.get(token) or int(token)) - 1
    positions = {
        "first": 0, "1st": 0,
        "second": 1, "2nd": 1,
        "third": 2, "3rd": 2,
        "fourth": 3, "4th": 3,
        "fifth": 4, "5th": 4,
    }
    for word, index in positions.items():
        if re.search(rf"\b{word}\b", clean_text, re.IGNORECASE):
            return index
    if re.search(r"\blast\b", clean_text, re.IGNORECASE):
        return -1
    return None
