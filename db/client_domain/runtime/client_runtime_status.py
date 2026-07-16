"""Read-only website reachability probes for CRM client summaries."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

import config

RUNTIME_STATUS_TIMEOUT_SECONDS = 0.6
RUNTIME_STATUS_CACHE_SECONDS = 8.0
RUNTIME_STATUS_ONLINE = "online"
RUNTIME_STATUS_OFFLINE = "offline"
RUNTIME_STATUS_UNKNOWN = "unknown"

_runtime_status_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def runtime_status(raw_url: Any) -> dict[str, Any]:
    """Return a short-lived read-only website reachability snapshot for CRM display."""
    target_urls = runtime_status_urls(raw_url)
    if not target_urls:
        return {
            "status": RUNTIME_STATUS_UNKNOWN,
            "label": "No URL",
            "checked_url": "",
            "message": "Client URL is not configured.",
        }

    candidates = []
    for target_url in target_urls:
        candidates.extend(runtime_status_candidates(target_url))
    candidates = list(dict.fromkeys(candidates))
    cache_key = "|".join(candidates)
    cached = _runtime_status_cache.get(cache_key)
    now = time.monotonic()
    if cached and now - cached[0] < RUNTIME_STATUS_CACHE_SECONDS:
        return dict(cached[1])

    status = probe_runtime_status(candidates)
    _runtime_status_cache[cache_key] = (now, status)
    return dict(status)


def runtime_status_source_urls(client: dict[str, Any]) -> list[str]:
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    runtime = vertical_config.get("runtime_capabilities") if isinstance(vertical_config.get("runtime_capabilities"), dict) else {}
    discovery = vertical_config.get("discovery") if isinstance(vertical_config.get("discovery"), dict) else {}
    return [
        runtime.get("url"),
        runtime.get("origin"),
        discovery.get("url"),
        client.get("store_url"),
        client.get("allowed_origin"),
    ]


def runtime_status_urls(raw_url: Any) -> list[str]:
    if isinstance(raw_url, (list, tuple)):
        values = raw_url
    else:
        values = [raw_url]
    urls = [runtime_status_url(value) for value in values]
    return list(dict.fromkeys(url for url in urls if url))


def runtime_status_url(raw_url: Any) -> str:
    text = str(raw_url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return text
    return ""


def runtime_status_candidates(target_url: str) -> list[str]:
    parsed = urlparse(target_url)
    candidates = [target_url]
    if parsed.hostname in {"127.0.0.1", "localhost"}:
        port = f":{parsed.port}" if parsed.port else ""
        candidates.append(parsed._replace(netloc=f"host.docker.internal{port}").geturl())
    return list(dict.fromkeys(candidates))


def probe_runtime_status(target_urls: list[str]) -> dict[str, Any]:
    last_error = ""
    for target_url in target_urls:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=RUNTIME_STATUS_TIMEOUT_SECONDS,
                verify=config.CLIENT_TLS_VERIFY,
            ) as client:
                response = client.head(target_url)
                if response.status_code in {405, 501}:
                    response = client.get(target_url)
        except (httpx.HTTPError, OSError, ValueError) as exc:
            last_error = str(exc)
            continue

        online = response.status_code < 500
        return {
            "status": RUNTIME_STATUS_ONLINE if online else RUNTIME_STATUS_OFFLINE,
            "label": "Online" if online else "Offline",
            "checked_url": target_url,
            "status_code": response.status_code,
            "message": f"HTTP {response.status_code}",
        }

    return {
        "status": RUNTIME_STATUS_OFFLINE,
        "label": "Offline",
        "checked_url": target_urls[0] if target_urls else "",
        "message": last_error or "Website did not respond.",
    }
