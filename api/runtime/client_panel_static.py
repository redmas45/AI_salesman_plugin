"""Static-file helpers for the public client panel SPA."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse

from api.runtime.static_files import SpaStaticFiles

CLIENT_PANEL_RESERVED_SLUGS = frozenset(
    {
        "assets",
        "client-panel",
        "client_panel",
        "crm",
        "docs",
        "health",
        "install.js",
        "mayabot-adapter.js",
        "mayabot-widget.js",
        "openapi.json",
        "redoc",
        "v1",
        "ws",
    }
)


def prefixed_url(request: Request, path: str) -> str:
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    return f"{prefix}{path}"


def is_client_panel_site_slug(site_id: str) -> bool:
    clean = str(site_id or "").strip().strip("/")
    if not clean or clean.lower() in CLIENT_PANEL_RESERVED_SLUGS:
        return False
    return "." not in clean and "/" not in clean


def client_panel_file_response(static_dir: Path, relative_path: str) -> FileResponse:
    base_dir = static_dir.resolve()
    target = (base_dir / relative_path).resolve()
    if not target.is_file() or base_dir not in (target, *target.parents):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client panel file not found.")
    return FileResponse(
        target,
        headers={
            "Cache-Control": "no-store, max-age=0, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def client_panel_spa_response(static_dir: Path, spa_path: str) -> FileResponse:
    if spa_path.startswith("assets/"):
        return client_panel_file_response(static_dir, spa_path)
    if spa_path:
        candidate = static_dir / spa_path
        if candidate.is_file():
            return client_panel_file_response(static_dir, spa_path)
        if "." in Path(spa_path).name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client panel file not found.")
    return client_panel_file_response(static_dir, "index.html")


def register_client_panel_static_routes(
    app: FastAPI,
    *,
    public_path: str,
    legacy_path: str,
    static_dir: Path,
) -> None:
    @app.get(public_path, include_in_schema=False)
    async def redirect_client_panel_root(request: Request) -> RedirectResponse:
        """Redirect the bare client_panel path to the static app root."""
        return RedirectResponse(url=prefixed_url(request, f"{public_path}/"))

    @app.get(f"{legacy_path}", include_in_schema=False)
    @app.get(f"{legacy_path}/{{spa_path:path}}", include_in_schema=False)
    async def redirect_legacy_client_panel_path(request: Request, spa_path: str = "") -> RedirectResponse:
        """Redirect old /client-panel links to the canonical /client_panel path."""
        suffix = f"/{spa_path}" if spa_path else "/"
        return RedirectResponse(url=prefixed_url(request, f"{public_path}{suffix}"))

    if static_dir.exists():
        app.mount(
            public_path,
            SpaStaticFiles(directory=static_dir, html=True),
            name="client_panel",
        )

    @app.get(f"{public_path}/assets/{{asset_path:path}}", include_in_schema=False)
    async def serve_root_client_panel_asset(asset_path: str) -> FileResponse:
        """Serve client-panel assets for public /aihub/client_panel/<site_id> panel URLs."""
        return client_panel_file_response(static_dir, f"assets/{asset_path}")

    @app.get(f"{public_path}/{{site_id}}", include_in_schema=False)
    async def redirect_clean_client_panel_url(request: Request, site_id: str) -> RedirectResponse:
        """Redirect /client_panel/<site_id> to /client_panel/<site_id>/ for SPA routing."""
        if not is_client_panel_site_slug(site_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        return RedirectResponse(url=prefixed_url(request, f"{public_path}/{site_id}/"))

    @app.get(f"{public_path}/{{site_id}}/{{spa_path:path}}", include_in_schema=False)
    async def serve_clean_client_panel_url(site_id: str, spa_path: str) -> FileResponse:
        """Serve the client panel at /client_panel/<site_id>/ for public /aihub/client_panel/<site_id>/ links."""
        if not is_client_panel_site_slug(site_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        return client_panel_spa_response(static_dir, spa_path)
