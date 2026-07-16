"""Durable audit and browser action event persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agent.actions.registry import normalize_action_name
from db.client_domain.events.client_events import safe_action_status
from db.client_domain.core.client_identity import safe_site_id
from db.client_domain.core.client_serialization import (
    dict_config,
    json_list,
    json_object,
    safe_action_stage,
    safe_action_text,
    safe_audit_status,
    safe_duration_ms,
    safe_int,
    safe_json_value,
    safe_text_list,
)
from db.core.schema import _connect, init_admin_schema

logger = logging.getLogger(__name__)

MAX_DURABLE_ACTION_EVENT_ROWS = 1000


def record_audit_event(
    *,
    site_id: str = "",
    actor_type: str = "system",
    event_type: str,
    event_scope: str = "",
    status: str = "ok",
    request_id: str = "",
    action: str = "",
    message: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append one durable server-owned audit event."""
    clean_site_id = safe_site_id(site_id) if site_id else ""
    clean_metadata = safe_json_value(metadata or {})
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_audit_events
                (
                    site_id, actor_type, event_type, event_scope, status,
                    request_id, action, message, metadata_json
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                clean_site_id,
                safe_action_text(actor_type) or "system",
                safe_action_text(event_type) or "event",
                safe_action_text(event_scope),
                safe_audit_status(status),
                safe_action_text(request_id),
                normalize_action_name(safe_action_text(action)),
                safe_action_text(message),
                json.dumps(clean_metadata, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()


def record_audit_event_safely(**kwargs: Any) -> None:
    try:
        record_audit_event(**kwargs)
    except Exception as exc:
        logger.warning("Audit event write skipped: %s", exc)


def list_client_action_events(site_ids: list[str] | set[str], *, limit: int = 500) -> dict[str, list[dict[str, Any]]]:
    """Return durable browser action events grouped by site ID."""
    clean_site_ids = sorted({safe_site_id(site_id) for site_id in site_ids if str(site_id or "").strip()})
    if not clean_site_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(clean_site_ids))
    row_limit = max(1, min(int(limit or 500), MAX_DURABLE_ACTION_EVENT_ROWS))
    init_admin_schema()
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                site_id,
                request_id,
                turn_id,
                sequence,
                action,
                status,
                stage,
                reason,
                origin,
                url,
                requested_url,
                final_url,
                duration_ms,
                param_keys_json,
                evidence_json,
                occurred_at::TEXT AS occurred_at
            FROM hub_action_events
            WHERE site_id IN ({placeholders})
            ORDER BY occurred_at DESC, id DESC
            LIMIT %s
            """,
            (*clean_site_ids, row_limit),
        ).fetchall()
    events_by_site: dict[str, list[dict[str, Any]]] = {site_id: [] for site_id in clean_site_ids}
    for row in rows:
        event = action_event_row_to_dict(dict(row))
        events_by_site.setdefault(event["site_id"], []).append(event)
    return events_by_site


def insert_client_action_event(site_id: str, event: dict[str, Any]) -> None:
    """Store one normalized browser action event in durable Postgres rows."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_action_events
                (
                    site_id, request_id, turn_id, sequence, action, status, stage,
                    reason, origin, url, requested_url, final_url, duration_ms,
                    param_keys_json, evidence_json, occurred_at
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
            """,
            (
                site_id,
                event["request_id"],
                event["turn_id"],
                event["sequence"],
                event["action"],
                event["status"],
                event["stage"],
                event["reason"],
                event["origin"],
                event["url"],
                event["requested_url"],
                event["final_url"],
                event["duration_ms"],
                json.dumps(event["param_keys"], ensure_ascii=False, default=str),
                json.dumps(event["evidence"], ensure_ascii=False, default=str),
                event_datetime(event.get("occurred_at")),
            ),
        )
        conn.commit()


def action_event_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "site_id": safe_site_id(row.get("site_id")),
        "source": "server_durable",
        "origin": safe_action_text(row.get("origin")),
        "url": safe_action_text(row.get("url")),
        "occurred_at": safe_action_text(row.get("occurred_at")),
        "request_id": safe_action_text(row.get("request_id")),
        "turn_id": safe_action_text(row.get("turn_id")),
        "sequence": safe_int(row.get("sequence")),
        "action": normalize_action_name(safe_action_text(row.get("action"))),
        "status": safe_action_status(row.get("status")),
        "stage": safe_action_stage(row.get("stage")),
        "reason": safe_action_text(row.get("reason")),
        "duration_ms": safe_duration_ms(row.get("duration_ms")),
        "param_keys": safe_text_list(json_list(row.get("param_keys_json")), 20),
        "requested_url": safe_action_text(row.get("requested_url")),
        "final_url": safe_action_text(row.get("final_url")),
        "evidence": safe_json_value(dict_config(json_object(row.get("evidence_json")))),
    }


def event_datetime(value: Any) -> datetime | None:
    text = safe_action_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
