"""Streaming event formatting helpers for orchestrator responses."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any


def stream_final_result(result: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
    ui_actions = result.get("ui_actions", [])
    response_text = result.get("response_text", "")
    answer_scope = str(result.get("answer_scope") or "")
    latency_ms = result.get("latency_ms", {})
    retrieval_evidence = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    yield {"event": "actions", "data": {"ui_actions": ui_actions}}
    yield {"event": "response", "data": {"response_text": response_text, "answer_scope": answer_scope}}
    yield {
        "event": "audio",
        "data": {
            "response_text": response_text,
            "audio_b64": result.get("audio_b64", ""),
            "latency_ms": latency_ms,
            "retrieval": retrieval_evidence,
            "answer_scope": answer_scope,
        },
    }
    yield {"event": "metrics", "data": {"latency_ms": latency_ms, "retrieval": retrieval_evidence}}
