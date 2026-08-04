"""Derive a concise spoken version of a rich response.

The model's full answer stays on screen (and remains available to read aloud in
full on request). But synthesizing every word of a long answer is the single
largest per-turn latency: text-to-speech time scales with length, so a long
comparison took ~13s just to speak. The customer does not need every fact read
out - those facts are already visible in the placard - they need a quick spoken
lead-in while they look at the screen.

`concise_spoken_text` keeps short answers exactly as they are and, for long ones,
speaks the first sentence or two plus a pointer to the on-screen detail. It is
deterministic, adds no model call and no latency, and is vertical-independent -
it reasons about sentence length and whether the turn rendered something visual,
never about any particular domain.
"""

from __future__ import annotations

import re
from typing import Any

# Below this an answer is spoken as written; above it, only a short lead-in is
# spoken and the rest is left on screen. ~160 characters is one or two sentences.
SPOKEN_MAX_CHARS = 160
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# Where a rich answer stops being narrative and becomes an on-screen list of facts
# (bullets, "- ", or a newline). The spoken lead-in stops here - those facts are
# what the placard shows, and reading them aloud is the slow part.
_LIST_MARKER_RE = re.compile(r"(:\s*[-•*]|\s[-•*]\s|\n|\s{2,}[-•*])")
# Actions that put detail on screen, so "the details are on your screen" is true.
_VISUAL_ACTIONS = frozenset(
    {"SHOW_PRODUCTS", "SHOW_COMPARISON", "SHOW_ENTITIES", "COMPARE_ENTITIES", "SHOW_PRODUCT_DETAIL"}
)
_ON_SCREEN_POINTER = "The full details are on your screen."


def _has_visual_action(ui_actions: Any) -> bool:
    for action in ui_actions or []:
        if isinstance(action, dict) and str(action.get("action") or "").upper() in _VISUAL_ACTIONS:
            return True
    return False


def concise_spoken_text(response_text: str, ui_actions: Any = None) -> str:
    """A short spoken lead-in for a rich answer; short answers pass through."""
    text = " ".join(str(response_text or "").split())
    if not text:
        return ""
    if len(text) <= SPOKEN_MAX_CHARS and not _LIST_MARKER_RE.search(text):
        return text

    # The narrative lead ends where the on-screen fact list begins.
    marker = _LIST_MARKER_RE.search(text)
    lead = text[: marker.start()] if marker else text
    lead = lead[:SPOKEN_MAX_CHARS] if len(lead) > SPOKEN_MAX_CHARS else lead

    # Prefer to end on a whole sentence within the lead.
    sentences = _SENTENCE_SPLIT_RE.split(lead)
    spoken = ""
    for sentence in sentences:
        candidate = f"{spoken} {sentence}".strip() if spoken else sentence.strip()
        if spoken and len(candidate) > SPOKEN_MAX_CHARS:
            break
        spoken = candidate
    spoken = (spoken or lead[:SPOKEN_MAX_CHARS]).rstrip(" ,;:-")
    if spoken and not spoken.endswith((".", "!", "?")):
        spoken += "."

    # Point to the screen when the turn actually rendered something, or when the
    # spoken lead is only part of a longer written answer.
    if _has_visual_action(ui_actions) or len(spoken) < len(text):
        return f"{spoken} {_ON_SCREEN_POINTER}".strip()
    return spoken
