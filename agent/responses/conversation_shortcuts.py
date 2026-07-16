"""Short-circuit conversation responses before retrieval and LLM work."""

from __future__ import annotations

import re
from typing import Any, Callable


def is_simple_greeting(transcript: str) -> bool:
    text = re.sub(r"[^a-z\s]", " ", (transcript or "").lower())
    words = [word for word in text.split() if word]
    if not words or len(words) > 5:
        return False
    intent_words = {"buy", "find", "get", "looking", "need", "open", "purchase", "search", "show", "want"}
    if any(word in intent_words for word in words):
        return False
    greeting_words = {"hello", "hi", "hey", "namaste", "yo"}
    return any(word in greeting_words for word in words)


def needs_transcript_clarification(
    transcript: str,
    *,
    normalize_text: Callable[[Any], str],
) -> bool:
    text = normalize_text(transcript)
    if not text:
        return True

    filler_words = {
        "hello",
        "hi",
        "hey",
        "i",
        "im",
        "m",
        "um",
        "uh",
        "hmm",
        "like",
        "maybe",
        "think",
        "looking",
        "for",
        "want",
        "need",
        "something",
    }
    words = text.split()
    meaningful = [word for word in words if word not in filler_words]
    if len(words) <= 8 and not meaningful and re.search(r"\b(looking for|i think|maybe|something)\b", text):
        return True
    return bool(re.search(r"\b(looking for|need|want)\s*$", text))


def clarification_response(
    transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    synthesize_audio: Callable[[str, bool], tuple[str, float | None]],
    ai_log: Callable[[str, Any], None],
    elapsed_ms: Callable[[float], float],
) -> dict[str, Any]:
    response_text = "I did not catch what you want clearly. What should I help you find or do on this website?"
    ai_log("assistant", response_text)
    ai_log("actions", [])

    audio_b64, tts_ms = synthesize_audio(response_text, skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms
    timings["total_ms"] = elapsed_ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "clarify",
        "confidence": 1.0,
        "ui_actions": [],
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }
