"""Runtime vertical config persistence for CRM clients."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClientConfigStore:
    safe_site_id: Callable[[str], str]
    json_object: Callable[[Any], dict[str, Any]]
    client_row: Callable[[str], dict[str, Any] | None]
    init_admin_schema: Callable[[], None]
    connect: Callable[[], Any]
    deleted_status: str


def client_vertical_config(site_id: str, store: ClientConfigStore) -> dict[str, Any]:
    client = store.client_row(site_id)
    if not client:
        raise LookupError(f"Client {site_id} was not found.")
    return store.json_object(client.get("vertical_config_json"))


def write_client_vertical_config(
    site_id: str,
    vertical_config: dict[str, Any],
    store: ClientConfigStore,
) -> None:
    store.init_admin_schema()
    clean_vertical_config = dict(vertical_config)
    clean_vertical_config.pop("action_events", None)
    clean_site_id = store.safe_site_id(site_id)
    with store.connect() as conn:
        cursor = conn.execute(
            """
            UPDATE hub_clients
            SET vertical_config_json = %s,
                updated_at = now()
            WHERE site_id = %s AND status <> %s
            """,
            (
                json.dumps(clean_vertical_config, ensure_ascii=False, default=str),
                clean_site_id,
                store.deleted_status,
            ),
        )
        conn.commit()
    if cursor.rowcount <= 0:
        raise LookupError(f"Client {site_id} was not found.")
    _bump_answer_cache_version(clean_site_id)


def _bump_answer_cache_version(site_id: str) -> None:
    try:
        from db.cache.answer_cache import bump_data_version

        bump_data_version(site_id, reason="client_runtime_config_changed")
    except Exception as exc:
        logger.warning("Answer cache invalidation skipped for %s: %s", site_id, exc)
