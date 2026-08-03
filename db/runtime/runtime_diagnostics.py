"""Privacy-safe runtime diagnostics for widget and server voice turns."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from db.client_domain.core.client_identity import safe_site_id
from db.client_domain.core.client_serialization import safe_duration_ms, safe_json_value
from db.core.schema import _connect, init_admin_schema

logger = logging.getLogger(__name__)

MAX_RUNTIME_EVENT_ROWS = 2000
RUNTIME_RANGE_DAYS = {
    "1d": 1,
    "3d": 3,
    "7d": 7,
    "15d": 15,
    "30d": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "all": None,
}
RUNTIME_SOURCES = frozenset({"frontend", "backend"})
RUNTIME_SEVERITIES = frozenset({"debug", "info", "warning", "error"})
RUNTIME_STATUSES = frozenset({"started", "ok", "cancelled", "failed"})
SAFE_TOKEN_PATTERN = re.compile(r"[^a-z0-9_.:-]+")


def safe_runtime_token(value: Any, *, fallback: str = "", limit: int = 80) -> str:
    token = SAFE_TOKEN_PATTERN.sub("_", str(value or "").strip().lower()).strip("_")
    return (token or fallback)[:limit]


def validated_runtime_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    event = raw_event if isinstance(raw_event, dict) else {}
    source = safe_runtime_token(event.get("source"), fallback="frontend")
    severity = safe_runtime_token(event.get("severity"), fallback="info")
    status = safe_runtime_token(event.get("status"), fallback="ok")
    return {
        "session_id": str(event.get("session_id") or "").strip()[:120],
        "request_id": str(event.get("request_id") or "").strip()[:80],
        "source": source if source in RUNTIME_SOURCES else "frontend",
        "component": safe_runtime_token(event.get("component"), fallback="voice", limit=60),
        "stage": safe_runtime_token(event.get("stage"), limit=80),
        "event_type": safe_runtime_token(event.get("event_type"), fallback="runtime_event", limit=80),
        "severity": severity if severity in RUNTIME_SEVERITIES else "info",
        "status": status if status in RUNTIME_STATUSES else "ok",
        "message_code": safe_runtime_token(event.get("message_code"), limit=80),
        "duration_ms": safe_duration_ms(event.get("duration_ms")),
        "metadata": safe_json_value(event.get("metadata") if isinstance(event.get("metadata"), dict) else {}),
        "occurred_at": _event_datetime(event.get("occurred_at")),
    }


def record_runtime_event(site_id: str, event: dict[str, Any]) -> None:
    """Persist one bounded event. Callers must authenticate/bind the site first."""
    clean_site_id = safe_site_id(site_id)
    clean = validated_runtime_event(event)
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_runtime_events
                (site_id, session_id, request_id, source, component, stage,
                 event_type, severity, status, message_code, duration_ms,
                 metadata_json, occurred_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
            """,
            (
                clean_site_id,
                clean["session_id"],
                clean["request_id"],
                clean["source"],
                clean["component"],
                clean["stage"],
                clean["event_type"],
                clean["severity"],
                clean["status"],
                clean["message_code"],
                clean["duration_ms"],
                json.dumps(clean["metadata"], ensure_ascii=True, default=str),
                clean["occurred_at"],
            ),
        )
        conn.commit()


def record_runtime_event_safely(site_id: str, event: dict[str, Any]) -> None:
    try:
        record_runtime_event(site_id, event)
    except Exception as exc:
        logger.warning("Runtime diagnostic write skipped for %s: %s", site_id, type(exc).__name__)


def list_runtime_events(range_key: str = "7d", site_id: str = "", *, limit: int = 1000) -> list[dict[str, Any]]:
    """Return newest events for CRM; caller is the authenticated admin route."""
    days = RUNTIME_RANGE_DAYS.get(str(range_key or "").lower(), 7)
    row_limit = max(1, min(int(limit or 1000), MAX_RUNTIME_EVENT_ROWS))
    params: list[Any] = []
    time_clause = "TRUE"
    if days is not None:
        time_clause = "occurred_at >= now() - (%s * interval '1 day')"
        params.append(days)
    site_clause = ""
    if str(site_id or "").strip():
        site_clause = "AND site_id = %s"
        params.append(safe_site_id(site_id))
    params.append(row_limit)
    init_admin_schema()
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT site_id, session_id, request_id, source, component, stage,
                   event_type, severity, status, message_code, duration_ms,
                   metadata_json, occurred_at::TEXT AS occurred_at
            FROM hub_runtime_events
            WHERE {time_clause}
              {site_clause}
            ORDER BY occurred_at DESC, id DESC
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()
    return [_runtime_event_row(dict(row)) for row in rows]


def _runtime_event_row(row: dict[str, Any]) -> dict[str, Any]:
    try:
        metadata = json.loads(str(row.get("metadata_json") or "{}"))
    except json.JSONDecodeError:
        metadata = {}
    return {
        "site_id": safe_site_id(row.get("site_id")),
        "session_id": str(row.get("session_id") or "")[:120],
        "request_id": str(row.get("request_id") or "")[:80],
        "source": safe_runtime_token(row.get("source"), fallback="backend"),
        "component": safe_runtime_token(row.get("component"), fallback="voice"),
        "stage": safe_runtime_token(row.get("stage")),
        "event_type": safe_runtime_token(row.get("event_type"), fallback="runtime_event"),
        "severity": safe_runtime_token(row.get("severity"), fallback="info"),
        "status": safe_runtime_token(row.get("status"), fallback="ok"),
        "message_code": safe_runtime_token(row.get("message_code")),
        "duration_ms": safe_duration_ms(row.get("duration_ms")),
        "metadata": safe_json_value(metadata if isinstance(metadata, dict) else {}),
        "occurred_at": str(row.get("occurred_at") or ""),
    }


def _event_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()[:80]
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
