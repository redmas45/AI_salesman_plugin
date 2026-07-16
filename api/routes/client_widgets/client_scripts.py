"""Public widget script URL and installer helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, Request

import config
from db.admin_domain import admin_facade as admin_db

CLIENT_DISABLED_MESSAGE = "AI assistant is disabled for this client."
DISABLED_WIDGET_DOM_ID = "mayabot-widget"
DISABLED_WIDGET_BOOT_FLAG = "__mayabotBooted"
DISABLED_WIDGET_FRAME_FLAG = "__mayabotFrameLoaded"
DISABLED_WIDGET_REGISTRY = "__mayabotDisabledSites"
INSTALL_REGISTRY_FLAG = "__aihubInstallLoadedSites"
ADAPTER_SCRIPT_NAME = "mayabot-adapter.js"
WIDGET_SCRIPT_NAME = "mayabot.js"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = PROJECT_ROOT / "plugin"


def safe_script_base_url(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip().strip("\"'")
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        return raw.rstrip("/")
    return ""


def public_script_base_url(raw: str) -> str:
    safe_url = safe_script_base_url(raw)
    if not safe_url:
        return ""
    parsed_url = urlparse(safe_url)
    hostname = (parsed_url.hostname or "").lower()
    if parsed_url.scheme == "http" and not is_local_script_host(hostname):
        return f"https://{safe_url[len('http://'):]}"
    return safe_url


def is_local_script_host(hostname: str) -> bool:
    return (
        hostname == "localhost"
        or hostname.startswith("127.")
        or hostname.startswith("10.")
        or hostname.startswith("192.168.")
        or hostname in {"0.0.0.0", "::1"}
        or hostname.startswith("172.16.")
        or hostname.startswith("172.17.")
        or hostname.startswith("172.18.")
        or hostname.startswith("172.19.")
        or hostname.startswith("172.2")
        or hostname.startswith("172.30.")
        or hostname.startswith("172.31.")
    )


def request_public_base_url(request: Request | None = None) -> str:
    if request is None:
        return ""

    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip()
    forwarded_prefix = request.headers.get("x-forwarded-prefix", "").strip().rstrip("/")
    scheme = forwarded_proto or request.url.scheme
    host = forwarded_host or request.headers.get("host", "") or request.url.netloc
    return public_script_base_url(f"{scheme}://{host}{forwarded_prefix}") if scheme and host else ""


def public_widget_base_url(request: Request | None = None) -> str:
    return (
        request_public_base_url(request)
        or public_script_base_url(os.environ.get("HUB_PUBLIC_URL", ""))
        or public_script_base_url(os.environ.get("PUBLIC_API_URL", ""))
        or public_script_base_url(config.PUBLIC_API_URL)
        or public_script_base_url(config.HUB_PUBLIC_URL)
        or public_script_base_url(config.VOICE_ORB_API_URL or "")
    )


def load_plugin_script(script_name: str, *, site: str, api_base_url: str) -> str:
    plugin_path = PLUGIN_DIR / script_name
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail="Plugin script not found.")

    with open(plugin_path, "r", encoding="utf-8") as script_file:
        js_code = script_file.read()

    js_code = js_code.replace('"__AI_PUBLIC_API_URL__"', json.dumps(api_base_url))
    js_code = js_code.replace('"__AI_DEFAULT_SITE_ID__"', json.dumps(site))
    return js_code


def load_widget_script(*, site: str, api_base_url: str) -> str:
    return load_plugin_script(WIDGET_SCRIPT_NAME, site=site, api_base_url=api_base_url)


def load_adapter_script(*, site: str, api_base_url: str) -> str:
    return load_plugin_script(ADAPTER_SCRIPT_NAME, site=site, api_base_url=api_base_url)


def disabled_widget_script(*, site: str) -> str:
    return f"""
(function () {{
  var siteId = {json.dumps(site)};
  var widget = document.getElementById({json.dumps(DISABLED_WIDGET_DOM_ID)});
  if (widget) widget.remove();
  window[{json.dumps(DISABLED_WIDGET_BOOT_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_FRAME_FLAG)}] = false;
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] = window[{json.dumps(DISABLED_WIDGET_REGISTRY)}] || {{}};
  window[{json.dumps(DISABLED_WIDGET_REGISTRY)}][siteId] = true;
  console.info("[AI Hub Widget] " + {json.dumps(CLIENT_DISABLED_MESSAGE)} + " Site: " + siteId);
}})();
"""


def client_scripts_can_load(site: str, *, client_store: Any = admin_db) -> bool:
    if not site:
        return True
    try:
        client = client_store.get_client_detail(site)
    except LookupError:
        return True
    return str(client.get("status") or "").strip().lower() != client_store.CLIENT_STATUS_DISABLED


def script_url(*, api_base_url: str, script_name: str, site: str | None = None) -> str:
    if site:
        return f"{api_base_url}/{script_name}?site={site}"
    return f"{api_base_url}/{script_name}"


def render_install_script(*, site: str | None = None, api_base_url: str) -> str:
    adapter_url = script_url(api_base_url=api_base_url, script_name=ADAPTER_SCRIPT_NAME, site=site)
    widget_url = script_url(api_base_url=api_base_url, script_name=WIDGET_SCRIPT_NAME, site=site)
    return f"""
(function () {{
  var siteId = {json.dumps(site or "")};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var loadedSites = window[{json.dumps(INSTALL_REGISTRY_FLAG)}] || {{}};
  var installKey = siteId || "auto:" + window.location.origin + ":" + window.location.pathname.split("/").slice(0, 2).join("/");
  if (loadedSites[installKey]) return;
  loadedSites[installKey] = true;
  window[{json.dumps(INSTALL_REGISTRY_FLAG)}] = loadedSites;

  function loadScript(src, onload) {{
    var script = document.createElement("script");
    script.defer = true;
    script.src = src;
    if (siteId) script.setAttribute("data-site-id", siteId);
    script.setAttribute("data-aihub-universal", siteId ? "false" : "true");
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


def render_embed_bootstrap(*, site: str, api_base_url: str) -> str:
    return f"""
(function () {{
  if (window.__mayabotFrameLoaded) return;
  window.__mayabotFrameLoaded = true;

  var currentScript = document.currentScript;
  var scriptUrl = currentScript && currentScript.src ? new URL(currentScript.src, window.location.href) : null;
  var siteId = {json.dumps(site)};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var parentOrigin = window.location.origin;
  var frameUrl = new URL(apiBaseUrl + "/mayabot-frame");
  frameUrl.searchParams.set("site", siteId);
  frameUrl.searchParams.set("parent_origin", parentOrigin);

  var frame = document.createElement("iframe");
  frame.src = frameUrl.toString();
  frame.title = "AI Hub Voice Widget";
  frame.setAttribute("allow", "microphone");
  frame.setAttribute("aria-label", "AI Hub Voice Widget");
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
    if (data.source !== "mayabot-frame") return;

    if (data.type === "mayabot:frame-size") {{
      var width = clamp(data.width, 360, Math.max(320, window.innerWidth - 24));
      var height = clamp(data.height, 180, Math.max(180, window.innerHeight - 24));
      frame.style.width = width + "px";
      frame.style.height = height + "px";
      return;
    }}

    if (data.type === "mayabot:navigate" && data.path) {{
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


def universal_install_script_tag(*, api_base_url: str | None = None) -> str:
    safe_api = (api_base_url or public_widget_base_url()).rstrip("/")
    return f'<script defer src="{safe_api}/install.js"></script>'
