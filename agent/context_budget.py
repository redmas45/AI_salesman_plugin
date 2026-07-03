"""Prompt context budgeting helpers for Maya runtime turns."""

from __future__ import annotations

from typing import Any

import config

MAX_RECENT_MESSAGES = 4
MAX_SUMMARY_CHARS = 1200
MAX_HISTORY_CONTENT_CHARS = 700


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
    """Create a deterministic rolling summary without another LLM call."""
    lines: list[str] = []
    previous = str(existing_summary or "").strip()
    if previous:
        lines.extend(_summary_lines(previous))

    for msg in _sanitize_history(history or [])[-6:]:
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


def _short_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[: max(1, int(limit or 1))]
