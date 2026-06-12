"""Terminal logging helpers for completed voice turns."""

from __future__ import annotations

from time import perf_counter
from typing import Any


def turn_timer() -> float:
    return perf_counter()


def print_turn_summary(
    *,
    transport: str,
    site_id: str,
    started_at: float,
    transcript: str = "",
    response_text: str = "",
    ui_actions: list[Any] | None = None,
    latency_ms: dict[str, Any] | None = None,
    status: str = "ok",
) -> None:
    elapsed_ms = (perf_counter() - started_at) * 1000
    pipeline_total = _number(latency_ms.get("total_ms") if latency_ms else None)
    pipeline_part = f" pipeline={pipeline_total:.0f}ms" if pipeline_total is not None else ""
    pipeline_value = f"{pipeline_total:.0f}ms" if pipeline_total is not None else "n/a"
    action_count = len(ui_actions or [])
    print(f"AI_CONVO | user: {_clip(transcript, 600)}", flush=True)
    print(f"AI_CONVO | ai_reply: {_clip(response_text, 600)}", flush=True)
    print(
        "AI_CONVO | "
        f"method_used: {transport} | "
        f"status: {status} | "
        f"time_taken: {elapsed_ms:.0f}ms | "
        f"pipeline: {pipeline_value} | "
        f"actions: {action_count}",
        flush=True,
    )
    print(
        "[SHOPBOT TURN] "
        f"transport={transport} "
        f"status={status} "
        f"site={site_id} "
        f"elapsed={elapsed_ms:.0f}ms"
        f"{pipeline_part} "
        f"actions={action_count} "
        f'transcript="{_clip(transcript, 90)}" '
        f'response="{_clip(response_text, 120)}"',
        flush=True,
    )


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clip(value: Any, limit: int) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 3)]}..."
