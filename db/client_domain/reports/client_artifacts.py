"""Persistence helpers for client readiness, crawl, and selector artifacts."""

from __future__ import annotations

import json
from typing import Any

from db.client_domain.core.client_identity import safe_site_id
from db.core.database import get_db, init_tenant_schema
from db.core.schema import _connect, init_admin_schema


def save_readiness_report(site_id: str, report: dict[str, Any]) -> None:
    """Persist a readiness scan result for a client."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE hub_clients
            SET readiness_report = %s,
                updated_at = now()
            WHERE site_id = %s
            """,
            (json.dumps(report, ensure_ascii=False), safe_site_id(site_id)),
        )
        conn.commit()


def get_readiness_report(site_id: str) -> dict[str, Any] | None:
    """Return the saved readiness report for a client, or None."""
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT readiness_report FROM hub_clients WHERE site_id = %s",
            (safe_site_id(site_id),),
        ).fetchone()
    if not row:
        return None
    raw = row.get("readiness_report") or ""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def save_crawl_report(site_id: str, report: dict[str, Any]) -> None:
    """Persist a crawl coverage report for a client."""
    init_admin_schema()
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        conn.execute(
            """
            UPDATE catalog_sync_runs
            SET report_json = %s
            WHERE id = (
                SELECT id FROM catalog_sync_runs
                ORDER BY created_at DESC
                LIMIT 1
            )
            """,
            (json.dumps(report, ensure_ascii=False),),
        )
        conn.commit()


def get_latest_crawl_report(site_id: str) -> dict[str, Any] | None:
    """Return the latest crawl report for a client."""
    init_admin_schema()
    try:
        with get_db(site_id) as conn:
            row = conn.execute(
                """
                SELECT report_json
                FROM catalog_sync_runs
                WHERE report_json IS NOT NULL AND report_json <> ''
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    raw = row.get("report_json") or ""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def save_site_selectors(
    site_id: str,
    selectors: dict[str, Any],
    confidence: float,
    validated: bool,
) -> None:
    """Persist LLM-extracted CSS selectors for a client site."""
    init_admin_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO site_selectors
                (site_id, selectors_json, confidence, validated, updated_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (site_id) DO UPDATE SET
                selectors_json = EXCLUDED.selectors_json,
                confidence = EXCLUDED.confidence,
                validated = EXCLUDED.validated,
                updated_at = now()
            """,
            (
                safe_site_id(site_id),
                json.dumps(selectors, ensure_ascii=False),
                max(0.0, min(float(confidence), 1.0)),
                bool(validated),
            ),
        )
        conn.commit()


def get_site_selectors(site_id: str) -> dict[str, Any] | None:
    """Return saved LLM-extracted selectors for a client site."""
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM site_selectors WHERE site_id = %s",
            (safe_site_id(site_id),),
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    try:
        result["selectors"] = json.loads(result.pop("selectors_json", "{}"))
    except json.JSONDecodeError:
        result["selectors"] = {}
    return result
