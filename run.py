from __future__ import annotations

import os
import threading
import time
from pathlib import Path
import json
from urllib.parse import urlparse

import httpx
import uvicorn
from dotenv import load_dotenv, set_key
import config

from agent.ingestion import sanitize_site_id, sync_shopify_api, sync_web_crawl, sync_website_api
from db.database import tenant_catalog_stats

load_dotenv()


def _ask(prompt: str, default: str | None = None) -> str:
    """Prompt and fall back to default when user leaves input empty."""
    label = f"{prompt} [{default}]: " if default is not None else f"{prompt}: "
    value = input(label).strip()
    return value if value else (default or "")


def _ask_int(prompt: str, default: int) -> int:
    value = _ask(prompt, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def _configured_or_ask(label: str, value: str, *, secret: bool = False) -> str:
    """Use configured .env value when present; ask only when it is missing."""
    if value:
        display = "***configured***" if secret else value
        print(f"Using {label} from .env: {display}")
        return value
    return _ask(label)


def _configured_int(label: str, value: int) -> int:
    print(f"Using {label} from .env: {value}")
    return value


def _configured_site_id() -> str | None:
    site_id = (
        config.VOICE_ORB_SITE_ID
        or config.DEFAULT_SITE_ID
        or os.getenv("AI_DEFAULT_SITE_ID", "").strip()
    )
    if site_id:
        print(f"Using target site_id from .env: {site_id}")
        return sanitize_site_id(site_id)
    custom_site = _ask("Target site_id (optional)", "").strip()
    return sanitize_site_id(custom_site) if custom_site else None


def _shopify_base_domain(value: str) -> str:
    raw = (value or "").strip()
    parsed = urlparse(raw if raw.startswith(("http://", "https://")) else f"https://{raw}")
    return (parsed.netloc or raw).rstrip("/")


def _shopify_site_url() -> str:
    if config.SHOPIFY_SITE_URL:
        print(f"Using Shopify site URL from .env: {config.SHOPIFY_SITE_URL}")
        return config.SHOPIFY_SITE_URL
    if config.SHOPIFY_CRAWL_FALLBACK_URL:
        print(f"Using Shopify crawl URL from .env: {config.SHOPIFY_CRAWL_FALLBACK_URL}")
        return config.SHOPIFY_CRAWL_FALLBACK_URL
    if config.SHOPIFY_STORE_DOMAIN:
        url = f"https://{_shopify_base_domain(config.SHOPIFY_STORE_DOMAIN)}/?pb=0"
        print(f"Using Shopify site URL from shop domain: {url}")
        return url
    return _ask("Shopify storefront URL to crawl")


def _shopify_site_id(source: str) -> str:
    if config.SHOPIFY_SITE_ID:
        print(f"Using Shopify site_id from .env: {config.SHOPIFY_SITE_ID}")
        return sanitize_site_id(config.SHOPIFY_SITE_ID)

    domain = _shopify_base_domain(source or config.SHOPIFY_STORE_DOMAIN)
    if domain.endswith(".myshopify.com"):
        domain = domain.removesuffix(".myshopify.com")
    site_id = sanitize_site_id(domain)
    print(f"Using Shopify site_id: {site_id}")
    return site_id


def _shopify_token_url(store_domain: str) -> str:
    domain = store_domain.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    return f"https://{domain}/admin/oauth/access_token"


def _persist_env_value(key: str, value: str) -> None:
    os.environ[key] = value
    env_path = Path(__file__).resolve().parent / ".env"
    set_key(str(env_path), key, value)


def _generate_shopify_access_token(store_domain: str) -> str:
    if not config.SHOPIFY_CLIENT_ID or not config.SHOPIFY_CLIENT_SECRET:
        return ""

    print("Generating fresh Shopify access token from client credentials...")
    response = httpx.post(
        _shopify_token_url(store_domain),
        json={
            "client_id": config.SHOPIFY_CLIENT_ID,
            "client_secret": config.SHOPIFY_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    token = str(data.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Shopify did not return an access_token.")

    _persist_env_value("SHOPIFY_ACCESS_TOKEN", token)
    print("Fresh Shopify access token stored in .env.")
    return token


def _resolve_shopify_access_token(store_domain: str) -> str:
    if config.SHOPIFY_ACCESS_TOKEN:
        return _configured_or_ask("Shop access token", config.SHOPIFY_ACCESS_TOKEN, secret=True)
    if config.SHOPIFY_CLIENT_ID and config.SHOPIFY_CLIENT_SECRET:
        return _generate_shopify_access_token(store_domain)
    return _ask("Shop access token")


def _parse_headers(raw: str | None) -> dict[str, str] | None:
    if not raw:
        return None

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Headers JSON must be an object.")

    headers: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str):
            raise ValueError("Header keys must be strings.")
        if not isinstance(value, str):
            raise ValueError("Header values must be strings.")
        headers[key.strip()] = value.strip()
    return headers or None


def _run_with_animation(message: str, fn, *args, **kwargs):
    """Run a blocking function while printing a terminal spinner."""
    result: dict[str, str] = {}
    error: dict[str, Exception] = {}

    def worker():
        try:
            result["value"] = fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover
            error["value"] = exc

    spinner = "|/-\\"
    stop_event = threading.Event()
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    idx = 0
    while thread.is_alive():
        print(f"\r{spinner[idx % len(spinner)]} {message}", end="", flush=True)
        idx += 1
        time.sleep(0.12)
        if stop_event.is_set():
            break
    thread.join()
    stop_event.set()

    if thread.is_alive():
        print()
        raise RuntimeError("background task did not stop as expected")

    if "value" in result:
        print(f"\r✓ {message} done", flush=True)
        return result["value"]
    exc = error.get("value")
    if exc is None:
        print(f"\r✗ {message} failed")
        raise RuntimeError(f"{message} failed unexpectedly.")
    print(f"\r✗ {message} failed")
    raise exc


def _persist_launch_config(site_id: str, public_url: str) -> None:
    os.environ["AI_DEFAULT_SITE_ID"] = site_id
    os.environ["DEFAULT_SITE_ID"] = site_id
    os.environ["PUBLIC_API_URL"] = public_url
    os.environ["AI_PLUGIN_SCRIPT_URL"] = f"{public_url}/shopbot.js"

    env_path = Path(__file__).resolve().parent / ".env"
    set_key(str(env_path), "AI_DEFAULT_SITE_ID", site_id)
    set_key(str(env_path), "DEFAULT_SITE_ID", site_id)
    set_key(str(env_path), "PUBLIC_API_URL", public_url)
    set_key(str(env_path), "AI_PLUGIN_SCRIPT_URL", f"{public_url}/shopbot.js")


def _env_public_url() -> str | None:
    configured = (
        os.getenv("STATIC_PUBLIC_URL", "").strip()
        or os.getenv("FORCE_PUBLIC_URL", "").strip()
        or os.getenv("PUBLIC_BASE_URL", "").strip()
    )
    if configured and configured.lower().startswith(("http://", "https://")):
        return configured.rstrip("/")
    return None


def _start_tunnel(host: str, port: int) -> str:
    """Start ngrok when available and persist PUBLIC_API_URL."""
    local_url = f"http://{host}:{port}"

    forced_public_url = _env_public_url()
    if forced_public_url:
        print("\n[+] Using configured public API URL from environment.")
        print(f"Your public API URL is: {forced_public_url}")
        return forced_public_url

    try:
        from pyngrok import ngrok
        print("\n[+] Starting Ngrok tunnel...")
        ngrok_domain = os.getenv("NGROK_HOSTNAME", "").strip() or os.getenv("NGROK_SUBDOMAIN", "").strip()

        if ngrok_domain:
            print(f"Using configured ngrok hostname: {ngrok_domain}")
            try:
                public_url = ngrok.connect(port, hostname=ngrok_domain).public_url
            except TypeError:
                # Older pyngrok versions may support `subdomain` instead of `hostname`.
                public_url = ngrok.connect(port, subdomain=ngrok_domain).public_url
            except Exception:
                print("Falling back to random ngrok domain.")
                public_url = ngrok.connect(port).public_url
        else:
            public_url = ngrok.connect(port).public_url

        print("\n" + "!" * 60)
        print(" ACTION REQUIRED ".center(60))
        print("!" * 60)
        print(f"Your public API URL is: {public_url}")
        print("Update Shopify callback URLs if you're using OAuth.")
        print("!" * 60 + "\n")
        return public_url
    except ImportError:
        print("\n[-] pyngrok not installed. Running locally only.")
        _persist_launch_config("site_1", local_url)
        return local_url


def _run_server(host: str, port: int, site_id: str) -> None:
    """Set runtime config and run FastAPI server."""
    public_url = _start_tunnel(host, port)
    _persist_launch_config(site_id, public_url)

    print(f"\nStarting Hub Server on {public_url} ...\n")
    try:
        uvicorn.run("api.main:app", host=host, port=port, reload=False)
    except KeyboardInterrupt:
        print("\nShutting down Hub Server...")


def _use_existing_catalog(site_id: str) -> str:
    stats = tenant_catalog_stats(site_id)
    active = int(stats.get("active_products") or 0)
    total = int(stats.get("total_products") or 0)
    if total == 0:
        print(f"No existing catalog found for site_id={site_id}. Use an update/sync option first.")
        return ""
    print(f"Catalog ready for {site_id}: {active} products.")
    return site_id


def _run_shopify_existing_mode() -> str:
    return _use_existing_catalog(_shopify_site_id(config.SHOPIFY_STORE_DOMAIN or config.SHOPIFY_SITE_URL))


def _run_shopify_api_mode() -> str:
    domain = _configured_or_ask("Shop domain", config.SHOPIFY_STORE_DOMAIN)
    site_id = _shopify_site_id(domain)
    existing = _use_existing_catalog(site_id)
    if existing:
        return existing

    token = _resolve_shopify_access_token(domain)
    if not domain or not token:
        raise ValueError("Both domain and access token are required for Shopify API mode.")
    return _run_with_animation(
        "Ingesting products from Shopify API",
        sync_shopify_api,
        domain,
        token,
        site_id=site_id,
        reconcile_missing=True,
    )


def _run_shopify_crawl_mode() -> str:
    start_url = _shopify_site_url()
    if not start_url:
        raise ValueError("Website URL is required.")
    site_id = _shopify_site_id(start_url)
    existing = _use_existing_catalog(site_id)
    if existing:
        return existing

    max_pages = _configured_int("Max pages to crawl", config.WEBSITE_CRAWL_MAX_PAGES)
    max_depth = _configured_int("Max crawl depth", config.WEBSITE_CRAWL_MAX_DEPTH)
    return _run_with_animation(
        "Crawling and ingesting website content",
        sync_web_crawl,
        start_url,
        max_pages=max_pages,
        max_depth=max_depth,
        site_id=site_id,
        reconcile_missing=True,
    )


def _run_api_mode() -> str:
    endpoint = _configured_or_ask("Product API endpoint URL", config.WEBSITE_API_URL)
    if not endpoint:
        raise ValueError("WEBSITE_API_URL is empty. Use option 2b for crawler-only update.")

    method = _configured_or_ask("HTTP method", config.WEBSITE_API_METHOD or "GET").upper()
    if method not in {"GET", "POST"}:
        raise ValueError("Method must be GET or POST.")

    headers = None
    headers_json = config.WEBSITE_API_HEADERS_JSON
    if headers_json:
        print("Using optional headers JSON from .env.")
    if headers_json:
        try:
            headers = _parse_headers(headers_json)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid headers JSON: {exc}") from exc
    site_id = _configured_site_id()
    return _run_with_animation(
        "Ingesting products from external API",
        sync_website_api,
        endpoint,
        method=method,
        headers=headers,
        site_id=site_id,
        reconcile_missing=True,
    )


def _run_existing_generic_mode() -> str:
    site_id = _configured_site_id()
    if not site_id:
        raise ValueError("No generic site_id configured.")
    return _use_existing_catalog(site_id)


def _run_crawler_mode() -> str:
    start_url = _configured_or_ask("Website URL to crawl", config.WEBSITE_CRAWL_URL)
    max_pages = _configured_int("Max pages to crawl", config.WEBSITE_CRAWL_MAX_PAGES)
    max_depth = _configured_int("Max crawl depth", config.WEBSITE_CRAWL_MAX_DEPTH)
    site_id = _configured_site_id()
    return _run_with_animation(
        "Crawling website and building catalog",
        sync_web_crawl,
        start_url,
        max_pages=max_pages,
        max_depth=max_depth,
        site_id=site_id,
        reconcile_missing=True,
    )


def _print_menu() -> None:
    print("\n" + "=" * 54)
    print(" AI SALESMAN HUB RUN OPTIONS ".center(54, "="))
    print("=" * 54)
    print("1) Shopify")
    print("   a) Shopify API")
    print("   b) Shopify crawler")
    print("2) Website API")
    print("3) Website crawler")
    print("0) Exit")
    print("=" * 54)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" AI SALESMAN HUB ".center(80, "="))
    print("=" * 80)

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8001"))

    selected_site_id: str | None = None
    while selected_site_id is None:
        _print_menu()
        choice = _ask("Choose an option", "0").lower().strip()
        if choice in {"0", "q", "quit", "exit"}:
            print("Exiting without starting server.")
            raise SystemExit(0)
        try:
            if choice == "1":
                subtype = _ask("Choose Shopify mode", "a").lower().strip()
                if subtype in {"a", "1a"}:
                    selected_site_id = _run_shopify_api_mode()
                elif subtype in {"b", "1b"}:
                    selected_site_id = _run_shopify_crawl_mode()
                else:
                    print("Invalid Shopify option.")
            elif choice == "1a":
                selected_site_id = _run_shopify_api_mode()
            elif choice == "1b":
                selected_site_id = _run_shopify_crawl_mode()
            elif choice == "2":
                selected_site_id = _run_existing_generic_mode()
            elif choice == "2a":
                selected_site_id = _run_api_mode()
            elif choice in {"2b", "3"}:
                selected_site_id = _run_crawler_mode()
            else:
                print("Invalid option.")
        except Exception as exc:
            print(f"Error in selected option: {exc}")

    if not selected_site_id:
        print("No ingestion mode completed. Exiting.")
        raise SystemExit(1)

    print(f"\nUsing site_id: {selected_site_id}")
    print("Starting API server now...")
    _run_server(host, port, selected_site_id)
