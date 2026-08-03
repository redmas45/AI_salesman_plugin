"""Prompt context budgeting helpers for Maya runtime turns."""

from __future__ import annotations

import re
from typing import Any

import config

MAX_RECENT_MESSAGES = 4
MAX_SUMMARY_CHARS = 1200
MAX_HISTORY_CONTENT_CHARS = 700

# Follow-up / correction markers that continue the current topic (never a reset).
_FOLLOWUP_RE = re.compile(
    r"^\s*(no|nope|actually|instead|wait|i meant|rather)\b"
    r"|\b(that one|this one|the other one|the cheaper one|the same|cheaper|under|below|budget)\b",
    re.IGNORECASE,
)


def build_context_messages(
    conversation_history: list[dict[str, Any]] | None,
    *,
    session_summary: str = "",
    max_recent_messages: int = MAX_RECENT_MESSAGES,
) -> list[dict[str, str]]:
    """Return a compact message window for the LLM prompt."""
    messages: list[dict[str, str]] = []
    summary = str(session_summary or "").strip()[:MAX_SUMMARY_CHARS]
    if summary:
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "Session memory summary for continuity. Use it as context, but obey the latest user "
                    f"message and retrieved website data first:\n{summary}"
                ),
            }
        )

    clean_history = _sanitize_history(conversation_history or [])
    messages.extend(clean_history[-max(0, int(max_recent_messages or 0)) :])
    return messages


def summarize_turns(
    existing_summary: str,
    history: list[dict[str, Any]] | None,
    transcript: str,
    response_text: str,
) -> str:
    """Create a deterministic rolling summary without another LLM call.

    Topic-aware: when the current turn switches to a clearly different product topic
    (and is not a follow-up/correction), prior context is dropped so stale products
    from an earlier topic cannot contaminate retrieval or bias the LLM.
    """
    lines: list[str] = []
    previous = str(existing_summary or "").strip()
    reset = _is_topic_shift(previous, transcript)

    if previous and not reset:
        lines.extend(_summary_lines(previous))

    history_window = [] if reset else _sanitize_history(history or [])[-6:]
    for msg in history_window:
        role = "User" if msg["role"] == "user" else "Maya"
        lines.append(f"{role}: {msg['content']}")

    clean_transcript = _short_text(transcript, config.MAX_TRANSCRIPT_CHARS)
    clean_response = _short_text(response_text, config.MAX_RESPONSE_CHARS)
    if clean_transcript:
        lines.append(f"User: {clean_transcript}")
    if clean_response:
        lines.append(f"Maya: {clean_response}")

    deduped: list[str] = []
    seen: set[str] = set()
    for line in lines:
        clean = " ".join(str(line or "").split())
        if not clean or clean in seen:
            continue
        seen.add(clean)
        deduped.append(clean)

    summary = "\n".join(deduped[-10:])
    return summary[-MAX_SUMMARY_CHARS:]


def _sanitize_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    sanitized: list[dict[str, str]] = []
    for msg in history:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "user")
        content = _short_text(msg.get("content"), MAX_HISTORY_CONTENT_CHARS)
        if role not in {"user", "assistant"} or not content:
            continue
        sanitized.append({"role": role, "content": content})
    return sanitized


def _summary_lines(summary: str) -> list[str]:
    return [line.strip() for line in str(summary or "").splitlines() if line.strip()]


def _dominant_topic(text: str) -> str:
    """The most recently mentioned normalized product type, or ``""``.

    Rolling summaries contain older turns first, so using the first noun keeps a
    stale topic forever. Plurals are normalized because natural turns usually say
    "phones", "laptops", and "smartwatches".
    """
    from agent.products.product_matching_lexical import BUILTIN_TYPE_NOUNS, canonical_type_token

    topics = [
        canonical_type_token(token)
        for token in re.findall(r"[a-z]+", str(text or "").lower())
    ]
    recognized = [topic for topic in topics if topic in BUILTIN_TYPE_NOUNS]
    return recognized[-1] if recognized else ""


def _is_topic_shift(previous_summary: str, transcript: str) -> bool:
    """True when the current turn names a different product topic and is not a
    follow-up/correction of the prior topic."""
    if not previous_summary or _FOLLOWUP_RE.search(str(transcript or "")):
        return False
    current_topic = _dominant_topic(transcript)
    previous_topic = _dominant_topic(previous_summary)
    return bool(current_topic and previous_topic and current_topic != previous_topic)


def _short_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[: max(1, int(limit or 1))]
