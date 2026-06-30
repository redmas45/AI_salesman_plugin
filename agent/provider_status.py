"""Provider usage and health status for CRM admin monitoring."""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx

import config
from db.quota import _usage_summary
from db.schema import _connect, init_admin_schema

logger = logging.getLogger(__name__)

OPENAI_COSTS_URL = "https://api.openai.com/v1/organization/costs"
RECENT_EVENT_LIMIT = 20
_RECENT_EVENTS: deque[dict[str, Any]] = deque(maxlen=RECENT_EVENT_LIMIT)
_COST_CACHE: tuple[float, dict[str, Any]] | None = None


def record_provider_failure(provider: str, exc: BaseException, *, category: str = "error") -> None:
    """Record a provider failure for the CRM health surface."""
    _record_provider_event(provider, category, _safe_error_message(exc))


def record_provider_success(provider: str) -> None:
    """Record provider recovery after a successful LLM call."""
    latest = _recent_provider_events(1)
    if latest and latest[0].get("provider") == provider and latest[0].get("category") == "ok":
        return
    _record_provider_event(provider, "ok", "LLM request completed successfully.")


def _record_provider_event(provider: str, category: str, message: str) -> None:
    event = {
        "provider": provider,
        "category": category,
        "message": message,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    _RECENT_EVENTS.appendleft(event)
    try:
        init_admin_schema()
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO hub_provider_events (provider, category, message)
                VALUES (%s, %s, %s)
                """,
                (provider[:80], category[:80], event["message"]),
            )
            conn.commit()
    except Exception as db_exc:
        logger.warning("Provider event persistence failed: %s", db_exc)


def provider_usage_status() -> dict[str, Any]:
    """Return admin-visible AI provider status and local token usage."""
    local_usage = _usage_summary()
    openai_costs = _openai_cost_status()
    recent_events = _recent_provider_events()
    status = _provider_status(recent_events, openai_costs)
    budget = _budget_status(openai_costs)
    return {
        "status": status,
        "provider": "openai",
        "llm_model": config.LLM_MODEL,
        "openai_api_key_configured": bool(config.OPENAI_API_KEY),
        "openai_admin_key_configured": bool(config.OPENAI_ADMIN_KEY),
        "local_tokens": {
            "estimated_total": local_usage["tokens_estimated"],
            "turns_total": local_usage["total_turns"],
            "turns_today": local_usage["turns_today"],
            "avg_latency_ms": local_usage["avg_latency_ms"],
        },
        "openai_costs": openai_costs,
        "budget": budget,
        "recent_events": recent_events,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _provider_status(recent_events: list[dict[str, Any]], openai_costs: dict[str, Any]) -> str:
    if not config.OPENAI_API_KEY:
        return "not_configured"
    if recent_events and recent_events[0].get("category") == "quota_exhausted":
        return "quota_exhausted"
    if openai_costs.get("status") == "error":
        return "usage_unavailable"
    return "ok"


def _recent_provider_events(limit: int = RECENT_EVENT_LIMIT) -> list[dict[str, Any]]:
    try:
        init_admin_schema()
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT provider, category, message, created_at
                FROM hub_provider_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "provider": str(row.get("provider") or ""),
                "category": str(row.get("category") or ""),
                "message": str(row.get("message") or ""),
                "occurred_at": str(row.get("created_at") or ""),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("Provider event lookup failed: %s", exc)
        return list(_RECENT_EVENTS)


def _budget_status(openai_costs: dict[str, Any]) -> dict[str, Any]:
    budget = float(config.OPENAI_MONTHLY_BUDGET_USD or 0)
    spent = float(openai_costs.get("month_to_date_usd") or 0)
    remaining = max(budget - spent, 0.0) if budget > 0 else 0.0
    percent_used = round((spent / budget) * 100, 1) if budget > 0 else 0.0
    return {
        "monthly_budget_usd": round(budget, 4),
        "month_to_date_usd": round(spent, 4),
        "remaining_budget_usd": round(remaining, 4),
        "percent_used": percent_used,
        "configured": budget > 0,
    }


def _openai_cost_status() -> dict[str, Any]:
    if not config.OPENAI_ADMIN_KEY:
        return {
            "status": "not_configured",
            "message": "Set OPENAI_ADMIN_KEY to enable OpenAI cost reporting.",
            "month_to_date_usd": 0.0,
            "currency": "usd",
        }

    global _COST_CACHE
    now = time.time()
    if _COST_CACHE and now - _COST_CACHE[0] < max(config.OPENAI_USAGE_REFRESH_SECONDS, 60):
        return dict(_COST_CACHE[1])

    started = _month_start_epoch()
    try:
        response = httpx.get(
            OPENAI_COSTS_URL,
            params={"start_time": started, "bucket_width": "1d"},
            headers={"Authorization": f"Bearer {config.OPENAI_ADMIN_KEY}"},
            timeout=8.0,
        )
        response.raise_for_status()
        payload = response.json()
        result = {
            "status": "ok",
            "message": "OpenAI month-to-date cost loaded.",
            "month_to_date_usd": _sum_cost_payload(payload),
            "currency": "usd",
            "period_start": datetime.fromtimestamp(started, timezone.utc).isoformat(),
        }
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        logger.warning("OpenAI cost status unavailable: %s", exc)
        result = {
            "status": "error",
            "message": _safe_error_message(exc),
            "month_to_date_usd": 0.0,
            "currency": "usd",
            "period_start": datetime.fromtimestamp(started, timezone.utc).isoformat(),
        }

    _COST_CACHE = (now, result)
    return dict(result)


def _sum_cost_payload(payload: dict[str, Any]) -> float:
    total = 0.0
    for bucket in payload.get("data", []) or []:
        if not isinstance(bucket, dict):
            continue
        for result in bucket.get("results", []) or []:
            if not isinstance(result, dict):
                continue
            amount = result.get("amount") if isinstance(result.get("amount"), dict) else {}
            value = amount.get("value", 0)
            try:
                total += float(value or 0)
            except (TypeError, ValueError):
                continue
    return round(total, 4)


def _month_start_epoch() -> int:
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    return int(start.timestamp())


def _safe_error_message(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    return text[:500]
