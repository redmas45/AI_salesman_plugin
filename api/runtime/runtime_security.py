"""Tenant-origin enforcement for public AI runtime transports."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request, status

from api.runtime import cors_policy


ClientLoader = Callable[[str], dict[str, Any]]


def runtime_origin_is_allowed(site_id: str, raw_origin: str, client_loader: ClientLoader) -> bool:
    if not raw_origin:
        return True
    try:
        client = client_loader(site_id)
    except LookupError:
        return False
    return cors_policy.client_origin_is_allowed(raw_origin, client)


def require_runtime_origin(request: Request, site_id: str, client_loader: ClientLoader) -> None:
    if runtime_origin_is_allowed(site_id, request.headers.get("origin", ""), client_loader):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin is not allowed for this client.")
