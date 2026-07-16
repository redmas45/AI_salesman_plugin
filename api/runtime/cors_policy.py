"""CORS policy helpers for runtime and public widget endpoints."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Request

import config


PUBLIC_WIDGET_CORS_PATHS = {
    "/install.js",
    "/mayabot.js",
    "/mayabot-widget.js",
    "/mayabot-adapter.js",
    "/mayabot-frame",
    "/v1/shop",
    "/v1/shop/stream",
    "/v1/ws/shop",
    "/v1/products",
    "/v1/products/by-ids",
    "/v1/knowledge/by-ids",
    "/ws/chat",
}


def origin_from_url(value: str) -> str:
    raw = str(value or "").strip().strip("\"'")
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def allowed_cors_origins() -> list[str]:
    configured = [origin.strip().strip("\"'") for origin in config.CORS_ORIGINS if origin.strip()]
    if configured and configured != ["*"]:
        return list(dict.fromkeys(configured))

    candidates = [
        config.PUBLIC_STOREFRONT_ORIGIN,
        config.CLIENT_STORE_URL,
        config.CURRENT_URL,
        config.HUB_PUBLIC_URL,
        config.PUBLIC_API_URL,
        config.VOICE_ORB_API_URL,
    ]
    if config.DEPLOYMENT_MODE in {"local", "dev", "development"}:
        candidates.extend(
            [
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:5176",
                "http://127.0.0.1:8585",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://localhost:5176",
                "http://localhost:8585",
            ]
        )

    return list(dict.fromkeys(origin for origin in (origin_from_url(value) for value in candidates) if origin))


def is_public_widget_cors_path(path: str) -> bool:
    clean_path = "/" + str(path or "").strip("/")
    return clean_path in PUBLIC_WIDGET_CORS_PATHS or clean_path.startswith("/v1/widget/")


def public_widget_cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin", "")
    requested_headers = request.headers.get("access-control-request-headers", "Accept, Content-Type")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": requested_headers,
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }


def client_origin_is_allowed(raw_origin: str, client: dict[str, object]) -> bool:
    """Check a browser Origin against one client's configured website origin."""
    request_origin = origin_from_url(raw_origin)
    if not request_origin:
        return True
    allowed_origin = origin_from_url(str(client.get("allowed_origin") or client.get("store_url") or ""))
    return not allowed_origin or request_origin == allowed_origin
