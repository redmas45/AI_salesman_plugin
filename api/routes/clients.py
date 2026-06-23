"""Client and widget serving routes for the Voice Shopping Agent API."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Response

import config
from db import admin as admin_db

logger = logging.getLogger(__name__)

CLIENT_DISABLED_MESSAGE = "AI assistant is disabled for this client."
DISABLED_WIDGET_DOM_ID = "shopbot-widget"
DISABLED_WIDGET_BOOT_FLAG = "__shopbotBooted"
DISABLED_WIDGET_FRAME_FLAG = "__shopbotFrameLoaded"
DISABLED_WIDGET_REGISTRY = "__shopbotDisabledSites"

router = APIRouter(tags=["Plugin"])


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


def _load_widget_script(*, site: str, api_base_url: str) -> str:
    plugin_path = Path(__file__).parent.parent.parent / "plugin" / "shopbot.js"
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail="Plugin script not found.")

    with open(plugin_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    js_code = js_code.replace('"__AI_PUBLIC_API_URL__"', json.dumps(api_base_url))
    js_code = js_code.replace('"__AI_DEFAULT_SITE_ID__"', json.dumps(site))
    return js_code


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
