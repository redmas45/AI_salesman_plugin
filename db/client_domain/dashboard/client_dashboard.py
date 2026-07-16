"""Read-only dashboard summary helpers for client CRM views."""

from __future__ import annotations

from typing import Any

import psycopg

from db.core.database import (
    catalog_source_stats,
    catalog_sync_history,
    get_db,
    init_tenant_schema,
    tenant_catalog_preview,
    tenant_catalog_stats,
)
from db.core.schema import _connect, init_admin_schema

DEFAULT_USAGE_LIMIT = 200


def safe_catalog_summary(site_id: str) -> dict[str, Any]:
    try:
        stats = tenant_catalog_stats(site_id)
        stats["categories"] = category_count(site_id)
        stats["sources"] = catalog_source_stats(site_id)
        stats["last_sync"] = latest_sync(site_id)
        return stats
    except psycopg.Error as exc:
        return empty_catalog_summary(str(exc))


def safe_answer_cache_summary(site_id: str) -> dict[str, Any]:
    try:
        from db.cache.answer_cache import answer_cache_summary

        return answer_cache_summary(site_id, limit=5)
    except Exception as exc:
        return {
            "site_id": site_id,
            "data_version": 0,
            "total": 0,
            "fresh": 0,
            "stale": 0,
            "hits": 0,
            "estimated_tokens_saved": 0,
            "items": [],
            "error": str(exc),
        }


def empty_catalog_summary(message: str = "") -> dict[str, Any]:
    return {
        "total_products": 0,
        "active_products": 0,
        "missing_embeddings": 0,
        "categories": 0,
        "sources": [],
        "last_sync": None,
        "error": message,
    }


def safe_catalog_preview(site_id: str) -> list[dict[str, Any]]:
    try:
        return tenant_catalog_preview(site_id, limit=12)
    except psycopg.Error:
        return []


def safe_sync_history(site_id: str) -> list[dict[str, Any]]:
    try:
        return catalog_sync_history(site_id, limit=8)
    except psycopg.Error:
        return []


def latest_sync(site_id: str) -> dict[str, Any] | None:
    runs = safe_sync_history(site_id)
    return runs[0] if runs else None


def category_count(site_id: str) -> int:
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM categories").fetchone()
    return int(row["total"] if row else 0)


def recent_usage_events(limit: int = DEFAULT_USAGE_LIMIT) -> list[dict[str, Any]]:
    init_admin_schema()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                site_id, session_id, transport, status, intent, action_count,
                latency_ms, input_tokens, output_tokens, transcript, response_text,
                created_at::TEXT AS created_at
            FROM hub_usage_events
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def health_snapshot() -> dict[str, str]:
    return {
        "fastapi": "up",
        "postgres": postgres_health(),
        "pgvector": "up",
        "crawler": "ready",
    }


def postgres_health() -> str:
    try:
        with _connect() as conn:
            conn.execute("SELECT 1")
        return "up"
    except psycopg.Error:
        return "down"
