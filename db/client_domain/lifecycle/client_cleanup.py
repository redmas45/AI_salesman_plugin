"""Client cleanup workflows."""

from __future__ import annotations

from typing import Any, Callable


ConnectFactory = Callable[[], Any]


def cleanup_synthetic_demo_clients(
    *,
    init_schema: Callable[[], None],
    connect: ConnectFactory,
    deleted_status: str,
    available_status: str,
    url_pattern: str,
) -> int:
    init_schema()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET status = %s, updated_at = now()
            WHERE status = %s
              AND (
                COALESCE(store_url, '') ~* %s
                OR COALESCE(allowed_origin, '') ~* %s
              )
            """,
            (
                deleted_status,
                available_status,
                url_pattern,
                url_pattern,
            ),
        )
        conn.commit()
        return max(0, int(cursor.rowcount or 0))
