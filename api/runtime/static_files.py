"""Static-file helpers for mounted SPA frontends."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Response, status
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


class SpaStaticFiles(NoCacheStaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND and "." not in Path(path).name:
                return await super().get_response("index.html", scope)
            raise
