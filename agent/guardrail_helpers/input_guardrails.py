"""Input-side safety checks for raw user transcripts."""

from __future__ import annotations

import logging
import re
from typing import Type

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(everything|all|your\s+instructions?)",
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"act\s+as\s+(if\s+you\s+are|a|an)",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    r"developer\s+mode",
    r"override\s+(system|instructions?|prompt)",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"print\s+(your\s+)?(system\s+)?prompt",
    r"show\s+(me\s+)?(your\s+)?(instructions?|prompt|rules)",
    r"disregard\s+(all\s+)?(previous|prior)",
]

_COMPILED_INJECTION = [re.compile(pattern, re.IGNORECASE) for pattern in _INJECTION_PATTERNS]

_OFFENSIVE_WORDS = [
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "dick",
    "pussy",
    "cunt",
    "nigger",
    "faggot",
    "retard",
]

_OFFENSIVE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in _OFFENSIVE_WORDS) + r")\b",
    re.IGNORECASE,
)

_PII_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "[PHONE]"),
    (re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"), "[EMAIL]"),
]


def validate_input(
    transcript: str,
    *,
    max_transcript_chars: int,
    error_type: Type[Exception],
    logger: logging.Logger,
) -> str:
    if not transcript or not transcript.strip():
        raise error_type("Empty transcript received.")

    if len(transcript) > max_transcript_chars:
        logger.warning(
            "Guardrail | Transcript too long (%d chars), truncating.",
            len(transcript),
        )
        transcript = transcript[:max_transcript_chars]

    for pattern in _COMPILED_INJECTION:
        if pattern.search(transcript):
            logger.warning("Guardrail | Prompt injection detected: %r", transcript[:100])
            raise error_type(
                "Whoops! I'm just a simple sales assistant, so I can't do that. But I can definitely help you find some amazing deals on our store!"
            )

    if _OFFENSIVE_PATTERN.search(transcript):
        logger.warning("Guardrail | Offensive input detected.")
        raise error_type(
            "Let's keep things family-friendly while we shop! ðŸ˜Š What were you looking to buy today?"
        )

    for pattern, replacement in _PII_PATTERNS:
        transcript = pattern.sub(replacement, transcript)

    return transcript


def contains_offensive_content(value: str) -> bool:
    return bool(_OFFENSIVE_PATTERN.search(value))
