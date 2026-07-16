"""Client listing visibility and origin normalization helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from db.client_domain.core.client_identity import origin_from_url

CLIENT_STATUS_LIVE = "live"


def visible_client_rows(rows: Any) -> list[dict[str, Any]]:
    """Collapse duplicate universal auto-clients created from page paths on one origin.

    Explicit site IDs from installer tags are authoritative. If an explicit
    client and an auto-generated client point at the same origin, show only the
    explicit client so the operator does not see duplicate installs for one
    website.
    """
    row_list = list(rows)
    explicit_origins = {
        client_origin_key(row)
        for row in row_list
        if not str(row.get("site_id") or "").startswith("auto_") and client_origin_key(row)
    }
    visible: list[dict[str, Any]] = []
    auto_by_origin: dict[str, int] = {}
    for row in row_list:
        origin_key = auto_client_origin_key(row)
        if not origin_key:
            visible.append(row)
            continue
        if origin_key in explicit_origins:
            continue

        existing_index = auto_by_origin.get(origin_key)
        if existing_index is None:
            auto_by_origin[origin_key] = len(visible)
            visible.append(row)
            continue

        current = visible[existing_index]
        if auto_client_sort_key(row) < auto_client_sort_key(current):
            visible[existing_index] = row
    return visible


def auto_client_origin_key(row: dict[str, Any]) -> str:
    site_id = str(row.get("site_id") or "")
    if not site_id.startswith("auto_"):
        return ""
    return client_origin_key(row)


def client_origin_key(row: dict[str, Any]) -> str:
    return canonical_origin_key(str(row.get("allowed_origin") or row.get("store_url") or ""))


def canonical_origin_key(raw_url: str) -> str:
    origin = origin_from_url(raw_url)
    try:
        parsed = urlparse(origin)
    except ValueError:
        return origin.lower()
    if not parsed.scheme or not parsed.netloc:
        return origin.lower()

    hostname = (parsed.hostname or "").lower()
    if hostname in {"127.0.0.1", "localhost", "host.docker.internal"}:
        hostname = "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme.lower()}://{hostname}{port}"


def auto_client_sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    status_rank = 0 if row.get("status") == CLIENT_STATUS_LIVE else 1
    created_at = str(row.get("created_at") or "")
    return (status_rank, created_at, str(row.get("site_id") or ""))
