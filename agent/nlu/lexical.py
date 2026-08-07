"""Scored lexical alignment between what a customer said and what a tenant publishes.

Matching a spoken word to a catalog term is an alignment problem, not a string
test, and it has to answer with a *degree of confidence* so the dialogue policy
can decide whether to act or to ask. Three mechanisms, in decreasing confidence:

1. **Morphological equality.** "phones" and "phone" are the same word. Snowball
   stemming (Porter2) reduces both to one form.

2. **Head-final compound match.** English compound nouns are head-final: the
   rightmost element names the category, so a "smartphone" *is* a phone. A
   spoken term therefore matches a published compound when it aligns with that
   compound's head.

   This rule needs a guard, and the guard is why it is safe. "tripod" also ends
   with the letters "ipod", and matching those cost a shopper five camera lenses
   when they asked for an iPod. The difference is that "smart|phone" splits at a
   real morpheme boundary - the remainder is itself a word the catalog uses -
   whereas "tr|ipod" leaves "tr", which is not a word anywhere. The modifier is
   therefore checked against the tenant's own vocabulary rather than assumed.

3. **Fuzzy similarity**, for speech-recognition damage ("samsang"). Held to a
   high threshold and computed over whole tokens; partial substring ratios are
   deliberately not used, because those are what score "ipod" against "tripod"
   at 100.

Nothing here knows a vendor, a category, or a vertical: every vocabulary is
supplied by the caller from tenant data.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import snowballstemmer
from rapidfuzz import fuzz

# Confidence attached to each mechanism above. They are ordered, not tuned: an
# exact morphological match is certain, a compound head is near-certain, and a
# fuzzy hit is a plausible guess that the dialogue policy may want to confirm.
EXACT_MATCH_SCORE = 1.0
COMPOUND_HEAD_SCORE = 0.9
FUZZY_MATCH_SCORE = 0.75

# Below this whole-token similarity a fuzzy hit is noise rather than a typo.
FUZZY_SIMILARITY_FLOOR = 85.0

# A head shorter than this carries too little signal to identify a category.
MIN_COMPOUND_HEAD_LENGTH = 4
# A modifier shorter than this is an artefact of spelling, not a word. "tr" in
# "tr|ipod" is the case this length bound exists to reject.
MIN_COMPOUND_MODIFIER_LENGTH = 4
# A modifier that is not itself a published word may still be a real morpheme if
# the catalogue uses it productively - "smart" heads both "smartphones" and
# "smartwatches" even where no record is called just "smart".
MIN_PRODUCTIVE_MODIFIER_USES = 2

# A published label of several words may be identified by one of them, but
# less confidently than a full match, because the part the customer omitted
# may be the distinguishing one.
PARTIAL_LABEL_CONFIDENCE = 0.85

_STEMMER = snowballstemmer.stemmer("english")
_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize(value: object) -> str:
    """Casefolded, accent-folded, punctuation-free text."""
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(_WORD_RE.findall(text))


def tokens(value: object) -> tuple[str, ...]:
    return tuple(normalize(value).split())


@lru_cache(maxsize=8192)
def stem(word: str) -> str:
    """One canonical form per word, so "phones" and "phone" compare equal."""
    return _STEMMER.stemWord(word) or word


def stem_tokens(value: object) -> tuple[str, ...]:
    return tuple(stem(word) for word in tokens(value))


@lru_cache(maxsize=8192)
def word_forms(word: str) -> frozenset[str]:
    """The surface forms one word can legitimately take.

    Stemming alone is not enough in both directions: Snowball maps "lenses" to
    "lens" but "lens" to "len", so two forms of one word stop comparing equal.
    Carrying the surface form and a plain plural alongside the stem keeps the
    comparison symmetric.
    """
    clean = normalize(word).replace(" ", "")
    if not clean:
        return frozenset()
    forms = {clean, stem(clean)}
    if clean.endswith("es"):
        forms.add(clean[:-2])
    if clean.endswith("s"):
        forms.add(clean[:-1])
    else:
        forms.add(f"{clean}s")
    return frozenset(form for form in forms if form)


def _is_head_final_compound(spoken: str, published: str, vocabulary: frozenset[str]) -> bool:
    """True when the published word is a compound whose head is the spoken word.

    The modifier left over must be a word the tenant actually uses, which is what
    separates "smart|phone" from "tr|ipod".
    """
    for head in sorted(word_forms(spoken), key=len, reverse=True):
        if len(head) < MIN_COMPOUND_HEAD_LENGTH:
            continue
        for whole in word_forms(published):
            if whole == head or not whole.endswith(head):
                continue
            modifier = whole[: -len(head)]
            if len(modifier) < MIN_COMPOUND_MODIFIER_LENGTH:
                continue
            if word_forms(modifier) & vocabulary:
                return True
            # Not a standalone word here, but a morpheme the catalogue reuses.
            uses = sum(1 for term in vocabulary if term.startswith(modifier))
            if uses >= MIN_PRODUCTIVE_MODIFIER_USES:
                return True
    return False


def word_alignment(spoken: str, published: str, vocabulary: frozenset[str] = frozenset()) -> float:
    """Confidence that one spoken word names the same thing as one published word."""
    spoken_forms, published_forms = word_forms(spoken), word_forms(published)
    if not spoken_forms or not published_forms:
        return 0.0
    if spoken_forms & published_forms:
        return EXACT_MATCH_SCORE
    if _is_head_final_compound(spoken, published, vocabulary):
        return COMPOUND_HEAD_SCORE
    if fuzz.ratio(stem(normalize(spoken)), stem(normalize(published))) >= FUZZY_SIMILARITY_FLOOR:
        return FUZZY_MATCH_SCORE
    return 0.0


def label_alignment(
    spoken: str,
    published: str,
    vocabulary: frozenset[str] = frozenset(),
) -> tuple[float, tuple[str, ...]]:
    """Confidence that a spoken phrase names a published label, and which of the
    label's own words carried the match.

    The matched words matter downstream: a customer who says "books" has named
    part of "Books Stationery", and searching the storefront for the part they
    said finds more than searching for a label they never used.
    """
    spoken_words = tokens(spoken)
    published_words = tokens(published)
    if not spoken_words or not published_words:
        return 0.0, ()
    scores = [
        max(
            (word_alignment(spoken_word, published_word, vocabulary) for spoken_word in spoken_words),
            default=0.0,
        )
        for published_word in published_words
    ]
    if all(score > 0.0 for score in scores):
        return min(scores), tuple(published_words)
    # The customer may name only part of a published label. Those labels are as
    # often conjunctions ("Books Stationery", "Lenses & Tripods") as they are
    # modifier-plus-head ("Health Policies"), so any constituent identifies the
    # value - less certainly than naming it in full, because the part they left
    # out may be the distinguishing one.
    best_part = max(scores)
    if best_part <= 0.0:
        return 0.0, ()
    matched = tuple(word for word, score in zip(published_words, scores) if score > 0.0)
    return best_part * PARTIAL_LABEL_CONFIDENCE, matched


def phrase_alignment(spoken: str, published: str, vocabulary: frozenset[str] = frozenset()) -> float:
    """Confidence alone, for callers that do not need the matched words."""
    return label_alignment(spoken, published, vocabulary)[0]


def build_vocabulary(values: object) -> frozenset[str]:
    """Every stemmed word a tenant publishes, used to validate compound splits."""
    collected: set[str] = set()
    for value in values or ():
        for word in tokens(value):
            collected.update(word_forms(word))
    return frozenset(collected)


def contains_alignment(
    spoken: str,
    published: str,
    vocabulary: frozenset[str] = frozenset(),
) -> tuple[float, tuple[str, ...]]:
    """Best confidence for a published value appearing anywhere in spoken text,
    with the published words that carried it."""
    return label_alignment(spoken, published, vocabulary)
