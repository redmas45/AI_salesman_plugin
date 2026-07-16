"""Transcript, audio, and simple response helpers for orchestrator turns."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable


def resolve_transcript(
    *,
    audio_bytes: bytes | None,
    text_input: str | None,
    audio_filename: str,
    timings: dict[str, float],
    transcribe: Callable[[bytes, str], str],
    elapsed_ms: Callable[[float], float],
) -> tuple[str | None, str | None]:
    if text_input:
        timings["stt_ms"] = 0
        return text_input, None
    if not audio_bytes:
        return None, "No audio or text input provided."

    started_at = time.perf_counter()
    try:
        transcript = transcribe(audio_bytes, audio_filename)
    except RuntimeError as exc:
        return None, str(exc)
    timings["stt_ms"] = elapsed_ms(started_at)
    return transcript, None


def synthesize_audio_b64(
    response_text: str,
    skip_tts: bool,
    *,
    synthesize_b64: Callable[[str], str],
    elapsed_ms: Callable[[float], float],
    logger: logging.Logger,
) -> tuple[str, float | None]:
    if skip_tts:
        return "", None
    started_at = time.perf_counter()
    try:
        return synthesize_b64(response_text), elapsed_ms(started_at)
    except RuntimeError as exc:
        logger.error("PIPELINE | TTS failed: %s - continuing without audio.", exc)
        return "", elapsed_ms(started_at)


def policy_boundary_response(
    transcript: str,
    response_text: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    retrieval: dict[str, Any] | None,
    synthesize_audio: Callable[[str, bool], tuple[str, float | None]],
    elapsed_ms: Callable[[float], float],
    ai_log: Callable[[str, Any], None],
) -> dict[str, Any]:
    audio_b64, tts_ms = synthesize_audio(response_text, skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms
    timings["total_ms"] = elapsed_ms(start_time)
    evidence = dict(retrieval or {})
    evidence["answer_scope"] = "unsupported_or_offsite"
    evidence["issue"] = "unsupported_or_offsite"
    ai_log("assistant", response_text)
    ai_log("actions", [])
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "unsupported_or_offsite",
        "confidence": 1.0,
        "answer_scope": "unsupported_or_offsite",
        "ui_actions": [],
        "audio_b64": audio_b64,
        "latency_ms": timings,
        "retrieval": evidence,
    }


def blocked_response(response_text: str) -> dict[str, Any]:
    return {
        "response_text": response_text,
        "intent": "blocked",
        "confidence": 1.0,
        "ui_actions": [],
    }


def guardrail_audio_b64(
    message: str,
    skip_tts: bool,
    *,
    synthesize_audio: Callable[[str, bool], tuple[str, float | None]],
) -> str:
    audio_b64, _duration_ms = synthesize_audio(message, skip_tts)
    return audio_b64


def error_response(message: str, timings: dict) -> dict[str, Any]:
    return {
        "transcript": "",
        "response_text": message,
        "intent": "error",
        "confidence": 0.0,
        "ui_actions": [],
        "audio_b64": "",
        "latency_ms": timings,
    }


def guardrail_response(
    message: str,
    transcript: str,
    skip_tts: bool,
    timings: dict,
    *,
    guardrail_audio: Callable[[str, bool], str],
) -> dict[str, Any]:
    audio_b64 = guardrail_audio(message, skip_tts)
    return {
        "transcript": transcript,
        "response_text": message,
        "intent": "blocked",
        "confidence": 1.0,
        "ui_actions": [],
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }
