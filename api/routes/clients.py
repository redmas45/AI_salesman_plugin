"""Client and widget serving routes for the Voice Shopping Agent API."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel, Field

import config
from agent.adapter_discovery import build_discovery, render_adapter_code
from agent.ingestion import sync_web_crawl
from db import admin as admin_db

logger = logging.getLogger(__name__)

CLIENT_DISABLED_MESSAGE = "AI assistant is disabled for this client."
DISABLED_WIDGET_DOM_ID = "shopbot-widget"
DISABLED_WIDGET_BOOT_FLAG = "__shopbotBooted"
DISABLED_WIDGET_FRAME_FLAG = "__shopbotFrameLoaded"
DISABLED_WIDGET_REGISTRY = "__shopbotDisabledSites"
INSTALL_REGISTRY_FLAG = "__aihubInstallLoadedSites"
ADAPTER_SCRIPT_NAME = "shopbot-adapter.js"
WIDGET_SCRIPT_NAME = "shopbot.js"
PLUGIN_DIR = Path(__file__).parent.parent.parent / "plugin"
RUNTIME_CONFIG_VERSION = 1
MAX_DISCOVERY_ELEMENTS = 80
MAX_DISCOVERY_TEXT_LENGTH = 3000

router = APIRouter(tags=["Plugin"])


class DiscoveryElement(BaseModel):
    label: str = Field(default="", max_length=160)
    selector: str = Field(default="", max_length=260)
    href: str = Field(default="", max_length=600)
    input_selector: str = Field(default="", max_length=260)
    submit_selector: str = Field(default="", max_length=260)


class WidgetRegisterRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    title: str = Field(default="", max_length=180)
    text_sample: str = Field(default="", max_length=MAX_DISCOVERY_TEXT_LENGTH)
    buttons: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    links: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    forms: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    platform_hints: dict[str, Any] = Field(default_factory=dict)


def _safe_site_id(raw: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", (raw or "").strip().lower())[:80] or "site_1"


def _safe_script_base_url(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip().strip("\"'")
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        return raw.rstrip("/")
    return ""


def _public_widget_base_url() -> str:
    return (
        _safe_script_base_url(os.environ.get("PUBLIC_API_URL", ""))
        or _safe_script_base_url(config.PUBLIC_API_URL)
        or _safe_script_base_url(config.VOICE_ORB_API_URL or "")
    )


def _load_plugin_script(script_name: str, *, site: str, api_base_url: str) -> str:
    plugin_path = PLUGIN_DIR / script_name
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail="Plugin script not found.")

    with open(plugin_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    js_code = js_code.replace('"__AI_PUBLIC_API_URL__"', json.dumps(api_base_url))
    js_code = js_code.replace('"__AI_DEFAULT_SITE_ID__"', json.dumps(site))
    return js_code


def _load_widget_script(*, site: str, api_base_url: str) -> str:
    return _load_plugin_script(WIDGET_SCRIPT_NAME, site=site, api_base_url=api_base_url)


def _load_adapter_script(*, site: str, api_base_url: str) -> str:
    return _load_plugin_script(ADAPTER_SCRIPT_NAME, site=site, api_base_url=api_base_url)


def _disabled_widget_script(*, site: str) -> str:
    return f"""
(function () {{
  var siteId = {json.dumps(site)};
  var widget = document.getElementById({json.dumps(DISABLED_WIDGET_DOM_ID)});
  if (widget) widget.remove();
  window[{json.dumps(DISABLED_WIDGET_BOOT_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_FRAME_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] = window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] || {{}};
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}][siteId] = true;
  console.info("[ShopBot] " + {json.dumps(CLIENT_DISABLED_MESSAGE)} + " Site: " + siteId);
}})();
"""


def _script_url(*, api_base_url: str, script_name: str, site: str) -> str:
    return f"{api_base_url}/{script_name}?site={site}"


def _render_install_script(*, site: str, api_base_url: str) -> str:
    adapter_url = _script_url(api_base_url=api_base_url, script_name=ADAPTER_SCRIPT_NAME, site=site)
    widget_url = _script_url(api_base_url=api_base_url, script_name=WIDGET_SCRIPT_NAME, site=site)
    return f"""
(function () {{
  var siteId = {json.dumps(site)};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var loadedSites = window[{json.dumps(INSTALL_REGISTRY_FLAG)}] || {{}};
  if (loadedSites[siteId]) return;
  loadedSites[siteId] = true;
  window[{json.dumps(INSTALL_REGISTRY_FLAG)}] = loadedSites;

  function loadScript(src, onload) {{
    var script = document.createElement("script");
    script.defer = true;
    script.src = src;
    script.setAttribute("data-site-id", siteId);
    script.setAttribute("data-api-url", apiBaseUrl);
    script.onload = onload || function () {{}};
    script.onerror = function () {{
      console.error("[AIHub] Failed to load " + src);
    }};
    (document.head || document.documentElement).appendChild(script);
  }}

  loadScript({json.dumps(adapter_url)}, function () {{
    loadScript({json.dumps(widget_url)});
  }});
}})();
"""


def _public_runtime_config(*, site: str, api_base_url: str) -> dict[str, Any]:
    client = _safe_client_detail(site)
    vertical = _safe_vertical_detail(client.get("vertical_key"))
    selectors = admin_db.get_site_selectors(site) or {}
    vertical_config = client.get("vertical_config")
    if not isinstance(vertical_config, dict):
        vertical_config = {}

    return {
        "version": RUNTIME_CONFIG_VERSION,
        "site_id": site,
        "enabled": admin_db.is_client_widget_enabled(site),
        "api_base_url": api_base_url,
        "install": _install_asset_config(site=site, api_base_url=api_base_url),
        "vertical": _runtime_vertical_config(vertical),
        "adapter": _runtime_adapter_config(client, vertical_config, selectors),
    }


def _safe_client_detail(site: str) -> dict[str, Any]:
    try:
        return admin_db.get_client_detail(site)
    except LookupError:
        return {
            "site_id": site,
            "name": site,
            "adapter_name": admin_db.DEFAULT_ADAPTER_NAME,
            "vertical_key": admin_db.DEFAULT_CLIENT_VERTICAL_KEY,
            "vertical_config": {},
        }


def _safe_vertical_detail(vertical_key: str | None) -> dict[str, Any]:
    try:
        return admin_db.get_vertical_detail(vertical_key or admin_db.DEFAULT_CLIENT_VERTICAL_KEY)
    except ValueError:
        return admin_db.get_vertical_detail(admin_db.DEFAULT_CLIENT_VERTICAL_KEY)


def _install_asset_config(*, site: str, api_base_url: str) -> dict[str, str]:
    return {
        "adapter_script": _script_url(api_base_url=api_base_url, script_name=ADAPTER_SCRIPT_NAME, site=site),
        "widget_script": _script_url(api_base_url=api_base_url, script_name=WIDGET_SCRIPT_NAME, site=site),
    }


def _runtime_vertical_config(vertical: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": vertical.get("key") or admin_db.DEFAULT_CLIENT_VERTICAL_KEY,
        "label": vertical.get("label") or "E-commerce",
        "risk_level": vertical.get("risk_level") or "low",
        "action_types": vertical.get("action_types") or [],
        "entity_types": vertical.get("entity_types") or [],
    }


def _runtime_adapter_config(
    client: dict[str, Any],
    vertical_config: dict[str, Any],
    selectors: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": client.get("adapter_name") or admin_db.DEFAULT_ADAPTER_NAME,
        "mode": "generated-runtime",
        "platform": vertical_config.get("platform") or "auto",
        "routes": _dict_value(vertical_config, "routes"),
        "actions": _dict_value(vertical_config, "actions"),
        "selectors": selectors.get("selectors") or _dict_value(vertical_config, "selectors"),
        "selector_confidence": float(selectors.get("confidence") or 0),
        "selector_validated": bool(selectors.get("validated")),
    }


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _process_widget_registration(req: WidgetRegisterRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    payload = req.model_dump()
    discovery = build_discovery(payload)
    safe_site = _safe_site_id(req.site_id)
    store_url = _safe_script_base_url(req.origin) or _safe_script_base_url(req.url)
    if not store_url:
        raise HTTPException(status_code=400, detail="Registration origin must be http or https.")

    client = _ensure_registration_client(safe_site, store_url, req.title, discovery.vertical_key)
    client = admin_db.update_client_discovery_config(
        safe_site,
        vertical_key=discovery.vertical_key,
        vertical_config=discovery.vertical_config,
        adapter_name="generated_adapter.js",
    )
    admin_db.save_site_selectors(
        safe_site,
        selectors=discovery.selectors,
        confidence=discovery.confidence,
        validated=discovery.confidence >= 0.65,
    )
    _seed_generated_prompt_once(safe_site, client, discovery)
    _schedule_auto_crawl_if_needed(background_tasks, safe_site, store_url, client)
    return {
        "site_id": safe_site,
        "vertical_key": discovery.vertical_key,
        "confidence": discovery.confidence,
        "actions": sorted(discovery.vertical_config.get("actions", {}).keys()),
        "crawl_scheduled": _should_auto_crawl(client),
    }


def _ensure_registration_client(site_id: str, store_url: str, title: str, vertical_key: str) -> dict[str, Any]:
    try:
        return admin_db.get_client_detail(site_id)
    except LookupError:
        name = str(title or site_id.replace("_", " ").title()).strip()[:120]
        return admin_db.create_client(
            name=name or site_id,
            store_url=store_url,
            site_id=site_id,
            deploy_mode=admin_db.DEFAULT_DEPLOY_MODE,
            plan=admin_db.DEFAULT_PLAN,
            adapter_name="generated_adapter.js",
            vertical_key=vertical_key,
        )


def _seed_generated_prompt_once(site_id: str, client: dict[str, Any], discovery: Any) -> None:
    try:
        profile = admin_db.get_client_prompt_profile(site_id)
    except LookupError:
        return
    if len(profile.get("versions") or []) > 1:
        return
    admin_db.save_client_prompt_profile(
        site_id,
        name=f"{client.get('name') or site_id} generated prompt",
        system_prompt=discovery.prompt,
        developer_rules=discovery.developer_rules,
        publish=False,
        changelog="Generated from one-line script discovery.",
    )


def _schedule_auto_crawl_if_needed(
    background_tasks: BackgroundTasks,
    site_id: str,
    store_url: str,
    client: dict[str, Any],
) -> None:
    if not _should_auto_crawl(client):
        return
    admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_RUNNING, "Auto crawl scheduled from widget install.")
    background_tasks.add_task(_run_auto_crawl, site_id, store_url)


def _should_auto_crawl(client: dict[str, Any]) -> bool:
    status_text = str(client.get("last_crawl_status") or admin_db.CRAWL_STATUS_NOT_STARTED)
    if status_text == admin_db.CRAWL_STATUS_RUNNING:
        return False
    catalog = client.get("catalog") if isinstance(client.get("catalog"), dict) else {}
    active_products = int(catalog.get("active_products") or 0)
    return status_text in {admin_db.CRAWL_STATUS_NOT_STARTED, admin_db.CRAWL_STATUS_ERROR} or active_products <= 0


def _run_auto_crawl(site_id: str, store_url: str) -> None:
    try:
        sync_web_crawl(
            store_url,
            max_pages=config.CRAWL_MAX_PAGES,
            max_depth=config.CRAWL_MAX_DEPTH,
            site_id=site_id,
            reconcile_missing=True,
            source_name="widget_auto_crawler",
        )
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_OK, "Auto crawler completed.")
    except Exception as exc:
        logger.error("Auto crawl failed for %s: %s", site_id, exc)
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_ERROR, str(exc))


def _render_embed_bootstrap(*, site: str, api_base_url: str) -> str:
    return f"""
(function () {{
  if (window.__shopbotFrameLoaded) return;
  window.__shopbotFrameLoaded = true;

  var currentScript = document.currentScript;
  var scriptUrl = currentScript && currentScript.src ? new URL(currentScript.src, window.location.href) : null;
  var siteId = {json.dumps(site)};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var parentOrigin = window.location.origin;
  var frameUrl = new URL(apiBaseUrl + "/shopbot-frame");
  frameUrl.searchParams.set("site", siteId);
  frameUrl.searchParams.set("parent_origin", parentOrigin);

  var frame = document.createElement("iframe");
  frame.src = frameUrl.toString();
  frame.title = "ShopBot Voice Orb";
  frame.setAttribute("allow", "microphone");
  frame.setAttribute("aria-label", "ShopBot Voice Orb");
  frame.style.position = "fixed";
  frame.style.left = "50%";
  frame.style.bottom = "12px";
  frame.style.transform = "translateX(-50%)";
  frame.style.width = "360px";
  frame.style.height = "180px";
  frame.style.maxWidth = "calc(100vw - 24px)";
  frame.style.maxHeight = "calc(100vh - 24px)";
  frame.style.border = "0";
  frame.style.background = "transparent";
  frame.style.zIndex = "2147483647";
  frame.style.overflow = "hidden";
  frame.style.colorScheme = "light";

  function clamp(value, fallback, maxCss) {{
    var numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric <= 0) return fallback;
    return Math.min(numeric, maxCss);
  }}

  window.addEventListener("message", function (event) {{
    if (event.origin !== new URL(apiBaseUrl).origin) return;
    var data = event.data || {{}};
    if (data.source !== "shopbot-frame") return;

    if (data.type === "shopbot:frame-size") {{
      var width = clamp(data.width, 360, Math.max(320, window.innerWidth - 24));
      var height = clamp(data.height, 180, Math.max(180, window.innerHeight - 24));
      frame.style.width = width + "px";
      frame.style.height = height + "px";
      return;
    }}

    if (data.type === "shopbot:navigate" && data.path) {{
      try {{
        var targetUrl = new URL(data.path, window.location.href);
        if (targetUrl.origin === window.location.origin) {{
          window.location.href = targetUrl.pathname + targetUrl.search + targetUrl.hash;
        }}
      }} catch (_err) {{}}
    }}
  }});

  function mountFrame(retries) {{
    if (document.body) {{
      document.body.appendChild(frame);
      return;
    }}
    if (retries > 100) {{
      return;
    }}
    setTimeout(function () {{ mountFrame(retries + 1); }}, 50);
  }}

  mountFrame(0);
}})();
"""


@router.get("/v1/widget/config")
async def widget_config(
    site_id: str = config.DEFAULT_SITE_ID,
    site: Optional[str] = None,
    shop: Optional[str] = None,
) -> dict[str, Any]:
    """Return public adapter/runtime config for one tenant."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    return _public_runtime_config(site=safe_site, api_base_url=_public_widget_base_url())


@router.post("/v1/widget/register")
async def widget_register(req: WidgetRegisterRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Register one script-installed page and generate adapter config."""
    return _process_widget_registration(req, background_tasks)


@router.get("/v1/widget/status")
async def widget_status(
    site_id: str = config.DEFAULT_SITE_ID,
    site: Optional[str] = None,
    shop: Optional[str] = None,
) -> dict[str, Any]:
    """Return the public widget availability state for one tenant."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    return {
        "site_id": safe_site,
        "enabled": admin_db.is_client_widget_enabled(safe_site),
    }


@router.get("/shopbot-frame")
async def serve_plugin_frame(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
    parent_origin: Optional[str] = None,
) -> Response:
    """Serve a standalone orb frame for external website modes."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    script_path = f"{_public_widget_base_url()}/shopbot-widget.js?site={safe_site}"
    if parent_origin:
        script_path += f"&parent_origin={parent_origin}"

    if not admin_db.is_client_widget_enabled(safe_site):
        return Response(
            content="<!doctype html><html><body></body></html>",
            media_type="text/html",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ShopBot</title>
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: transparent;
      }}
      body {{
        position: relative;
      }}
    </style>
  </head>
  <body>
    <script src="{script_path}"></script>
  </body>
</html>"""

    return Response(
        content=html_doc,
        media_type="text/html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/shopbot-widget.js")
async def serve_plugin_widget(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the full widget app for direct use or inside the external embed frame."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = (
        _load_widget_script(site=safe_site, api_base_url=safe_api)
        if admin_db.is_client_widget_enabled(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/shopbot-adapter.js")
async def serve_plugin_adapter(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the client-side adapter runtime used by the one-line installer."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = (
        _load_adapter_script(site=safe_site, api_base_url=safe_api)
        if admin_db.is_client_widget_enabled(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/shopbot.js")
async def serve_plugin(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the public widget loader — inlined directly (no iframe).

    The iframe-based bootstrap (_render_embed_bootstrap) fails with free-tier
    ngrok because the interstitial "Visit Site" page blocks iframe loading.
    Serving the full widget JS directly avoids this issue entirely.
    """
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = (
        _load_widget_script(site=safe_site, api_base_url=safe_api)
        if admin_db.is_client_widget_enabled(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/install.js")
async def serve_install_script(
    site: Optional[str] = None,
    site_id: Optional[str] = None,
    shop: Optional[str] = None,
) -> Response:
    """Serve the single script clients paste into their website."""
    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = (
        _render_install_script(site=safe_site, api_base_url=safe_api)
        if admin_db.is_client_widget_enabled(safe_site)
        else _disabled_widget_script(site=safe_site)
    )

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )
