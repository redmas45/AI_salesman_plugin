"""Browser-origin checks for public widget routes."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request

from api.runtime import cors_policy


OriginSanitizer = Callable[[str], str]
ClientLoader = Callable[[str], dict[str, Any]]


def require_claimed_browser_origin(
    request: Request,
    claimed_origin: str,
    sanitize_origin: OriginSanitizer,
) -> None:
    request_origin = sanitize_origin(request.headers.get("origin", ""))
    if request_origin and request_origin != sanitize_origin(claimed_origin):
        raise HTTPException(status_code=403, detail="Widget request origin does not match the payload origin.")


def require_allowed_widget_origin(
    request: Request,
    site_id: str,
    client_loader: ClientLoader,
) -> None:
    request_origin = request.headers.get("origin", "")
    if not request_origin:
        return
    client = client_loader(site_id)
    if not cors_policy.client_origin_is_allowed(request_origin, client):
        raise HTTPException(status_code=403, detail="Widget request origin is not allowed for this client.")
