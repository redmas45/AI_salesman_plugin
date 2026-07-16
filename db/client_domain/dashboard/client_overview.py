"""CRM client overview payload helpers."""

from __future__ import annotations

from typing import Any, Callable


def overview(
    *,
    list_clients: Callable[[], list[dict[str, Any]]],
    live_status: str,
    available_status: str,
    health_snapshot: Callable[[], dict[str, str]],
    recent_usage_events: Callable[[], list[dict[str, Any]]],
) -> dict[str, Any]:
    clients = list_clients()
    current_clients = [client for client in clients if client["status"] != available_status]

    from agent.providers.provider_status import provider_usage_status
    from db.runtime.quota import _usage_summary

    usage = _usage_summary()
    products_indexed = sum(int(client["catalog"]["active_products"]) for client in current_clients)
    cache_hits = sum(int((client.get("answer_cache") or {}).get("hits") or 0) for client in current_clients)
    cache_fresh = sum(int((client.get("answer_cache") or {}).get("fresh") or 0) for client in current_clients)
    tokens_saved = sum(
        int((client.get("answer_cache") or {}).get("estimated_tokens_saved") or 0)
        for client in current_clients
    )
    return {
        "health": health_snapshot(),
        "provider_usage": provider_usage_status(),
        "metrics": {
            "active_clients": len([item for item in clients if item["status"] == live_status]),
            "voice_turns_today": usage["turns_today"],
            "total_voice_turns": usage["total_turns"],
            "products_indexed": products_indexed,
            "avg_latency_ms": usage["avg_latency_ms"],
            "tokens_estimated": usage["tokens_estimated"],
            "answer_cache_hits": cache_hits,
            "answer_cache_fresh": cache_fresh,
            "answer_cache_tokens_saved": tokens_saved,
        },
        "clients": clients,
        "recent_activity": recent_usage_events(),
    }


def script_tag_for_site(
    site_id: str,
    *,
    safe_site_id: Callable[[str], str],
    public_hub_origin: Callable[[], str],
) -> str:
    clean_site_id = safe_site_id(site_id)
    origin = public_hub_origin()
    return (
        f'<script defer src="{origin}/install.js?site={clean_site_id}" '
        f'data-site-id="{clean_site_id}"></script>'
    )
