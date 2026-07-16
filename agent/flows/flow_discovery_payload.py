"""Snapshot payload assembly for flow discovery."""

from __future__ import annotations

from typing import Any

from agent.flows.flow_html_snapshot import safe_element

MAX_FLOW_ELEMENTS = 100
MAX_FLOW_TEXT_CHARS = 2400


def combined_discovery_payload(snapshots: list[dict[str, Any]], site_id: str, site_url: str) -> dict[str, Any]:
    first = snapshots[0]
    return {
        "site_id": site_id,
        "origin": site_url,
        "url": first.get("url") or site_url,
        "title": first.get("title") or "",
        "text_sample": " ".join(str(snapshot.get("text_sample") or "") for snapshot in snapshots)[:MAX_FLOW_TEXT_CHARS],
        "buttons": merged_elements(snapshots, "buttons"),
        "links": merged_elements(snapshots, "links"),
        "forms": merged_elements(snapshots, "forms"),
        "platform_hints": merged_platform_hints(snapshots),
    }


def merged_elements(snapshots: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for snapshot in snapshots:
        for item in snapshot.get(key, []) or []:
            element = safe_element(item)
            identity = (element.get("label", ""), element.get("href", ""), element.get("selector", ""))
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(element)
    return merged[:MAX_FLOW_ELEMENTS]


def merged_platform_hints(snapshots: list[dict[str, Any]]) -> dict[str, bool]:
    hints: dict[str, bool] = {}
    for snapshot in snapshots:
        raw_hints = snapshot.get("platform_hints") if isinstance(snapshot.get("platform_hints"), dict) else {}
        for key, value in raw_hints.items():
            hints[key] = bool(hints.get(key) or value)
    return hints
