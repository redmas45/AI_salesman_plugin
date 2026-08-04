"""Prompt context budgeting helpers for Maya runtime turns."""

from __future__ import annotations

import re
from typing import Any

import config

MAX_RECENT_MESSAGES = 4
MAX_SUMMARY_CHARS = 1200
# Rough token estimate: ~4 characters per token. Used only to keep the assembled
# context under a hard budget; the provider does the authoritative tokenization.
CHARS_PER_TOKEN = 4
# A single turn longer than this is compacted before it is sent, so one verbose
# message cannot inflate the prompt on every subsequent turn.
PER_MESSAGE_TOKEN_CAP = 200
MAX_HISTORY_CONTENT_CHARS = PER_MESSAGE_TOKEN_CAP * CHARS_PER_TOKEN  # 800 chars
_SUMMARY_PREFIX = "Session memory summary"


def estimate_tokens(messages: list[dict[str, str]]) -> int:
    """A cheap, deterministic token estimate for a message list."""
    chars = sum(len(str(msg.get("content") or "")) for msg in messages or [])
    return (chars + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN

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
    token_budget: int | None = None,
) -> list[dict[str, str]]:
    """Return a compact message window for the LLM prompt.

    The window is the rolling session summary plus the most recent verbatim turns.
    It is then trimmed to a hard token budget so the assembled context - and the
    per-turn latency - stay flat as the conversation grows, regardless of how long
    the transcript becomes.
    """
    clean_history = _sanitize_history(conversation_history or [])
    window = max(0, int(max_recent_messages or 0))
    recent = clean_history[-window:] if window else []
    older = clean_history[: len(clean_history) - len(recent)]
    summary_message = _summary_message(session_summary)

    # Lazy summary. A short conversation has no older turns, so nothing is
    # summarized and the context costs no more than replaying those turns - early
    # turns never pay the summary's fixed overhead. The summary is introduced only
    # once condensing the older turns actually costs FEWER tokens than replaying
    # them (which happens once the conversation is long enough to matter), after
    # which the context stays flat regardless of how much longer it runs.
    if older and summary_message and estimate_tokens([summary_message]) < estimate_tokens(older):
        messages = [summary_message, *recent]
    else:
        messages = [*older, *recent]
    return _enforce_token_budget(messages, token_budget)


def _summary_message(session_summary: str) -> dict[str, str] | None:
    summary = str(session_summary or "").strip()[:MAX_SUMMARY_CHARS]
    if not summary:
        return None
    return {
        "role": "assistant",
        "content": (
            f"{_SUMMARY_PREFIX} for continuity. Use it as context, but obey the latest user "
            f"message and retrieved website data first:\n{summary}"
        ),
    }


def _enforce_token_budget(messages: list[dict[str, str]], token_budget: int | None) -> list[dict[str, str]]:
    """Keep the assembled context under the budget: drop the oldest recent turns
    first, then, only if a lone summary still overflows, truncate the summary."""
    budget = int(config.CONTEXT_TOKEN_BUDGET if token_budget is None else token_budget)
    if budget <= 0 or estimate_tokens(messages) <= budget:
        return messages
    # Index 0 is the summary (when present); drop the oldest of the recent turns.
    has_summary = bool(messages) and _SUMMARY_PREFIX in messages[0]["content"]
    floor = 1 if has_summary else 0
    trimmed = list(messages)
    while len(trimmed) > floor and estimate_tokens(trimmed) > budget:
        trimmed.pop(floor)  # remove the oldest recent turn, keep the summary
    if estimate_tokens(trimmed) > budget and has_summary:
        keep_chars = max(0, budget * CHARS_PER_TOKEN)
        trimmed[0] = {**trimmed[0], "content": trimmed[0]["content"][:keep_chars]}
    return trimmed


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
