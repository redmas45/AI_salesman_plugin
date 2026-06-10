from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import uvicorn
from dotenv import load_dotenv, set_key

import config
from agent.ingestion import sanitize_site_id, sync_web_crawl

load_dotenv()


def _ask(prompt: str, default: str | None = None) -> str:
    label = f"{prompt} [{default}]: " if default is not None else f"{prompt}: "
    value = input(label).strip()
    return value if value else (default or "")


def _persist_env_value(key: str, value: str) -> None:
    os.environ[key] = value
    env_path = Path(__file__).resolve().parent / ".env"
    set_key(str(env_path), key, value)


def _configured_url() -> str:
    if config.CURRENT_URL:
        print(f"Using CURRENT_URL from .env: {config.CURRENT_URL}")
        return config.CURRENT_URL
    return _ask("Website URL to crawl")


def _configured_site_id() -> str:
    configured = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if configured:
        site_id = sanitize_site_id(configured.strip("\"'"))
        print(f"Using CURRENT_SITE_ID from .env: {site_id}")
        return site_id
    custom_site = _ask("Target site_id", "site_1")
    return sanitize_site_id(custom_site)


def _run_with_animation(message: str, fn, *args, **kwargs):
    result: dict[str, str] = {}
    error: dict[str, Exception] = {}

    def worker():
        try:
            result["value"] = fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover
            error["value"] = exc

    spinner = "|/-\\"
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    idx = 0
    while thread.is_alive():
        print(f"\r{spinner[idx % len(spinner)]} {message}", end="", flush=True)
        idx += 1
        time.sleep(0.12)
    thread.join()

    if "value" in result:
        print(f"\r[ok] {message} done", flush=True)
        return result["value"]

    exc = error.get("value")
    print(f"\r[x] {message} failed")
    if exc is None:
        raise RuntimeError(f"{message} failed unexpectedly.")
    raise exc


def _persist_launch_config(site_id: str, public_url: str) -> None:
    _persist_env_value("AI_DEFAULT_SITE_ID", site_id)
    _persist_env_value("DEFAULT_SITE_ID", site_id)
    _persist_env_value("CURRENT_SITE_ID", site_id)
    _persist_env_value("PUBLIC_API_URL", public_url)


def _build_widget_script_tag(site_id: str, public_url: str) -> str:
    return f'<script src="{public_url}/shopbot.js?site={site_id}"></script>'


def _persist_widget_script(site_id: str, public_url: str) -> str:
    script_tag = _build_widget_script_tag(site_id, public_url)
    _persist_env_value("MANUAL_WIDGET_SCRIPT", script_tag)
    _persist_env_value("PUBLIC_WIDGET_SCRIPT_URL", f"{public_url}/shopbot.js?site={site_id}")
    return script_tag


def _print_widget_install_instructions(site_id: str, public_url: str) -> None:
    script_tag = _persist_widget_script(site_id, public_url)
    print("\nManual widget injection:")
    print(script_tag)
    print(f"Saved to .env as MANUAL_WIDGET_SCRIPT for CURRENT_URL={config.CURRENT_URL or 'current target'}")
    print(f"Allow this backend origin in target CSP: {public_url} (script-src, connect-src, frame-src)")


def _local_base_url(host: str, port: int) -> str:
    local_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{local_host}:{port}"


def _port_is_in_use(host: str, port: int) -> bool:
    check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((check_host, port)) == 0


def _find_any_free_port(host: str) -> int:
    bind_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((bind_host, 0))
        return int(sock.getsockname()[1])


def _choose_server_port(host: str, preferred_port: int, max_port: int = 8010) -> int:
    last_port = max(preferred_port, max_port)
    for candidate in range(preferred_port, last_port + 1):
        if not _port_is_in_use(host, candidate):
            if candidate != preferred_port:
                print(f"\n[!] Port {preferred_port} is busy. Using port {candidate} instead.")
            return candidate
    fallback_port = _find_any_free_port(host)
    print(
        f"\n[!] Ports {preferred_port}-{last_port} are all busy. "
        f"Using fallback port {fallback_port} instead."
    )
    return fallback_port


def _connect_ngrok(port: int) -> str:
    from pyngrok import ngrok

    ngrok_domain = os.getenv("NGROK_HOSTNAME", "").strip() or os.getenv("NGROK_SUBDOMAIN", "").strip()
    if ngrok_domain:
        print(f"Using configured ngrok hostname: {ngrok_domain}")
        try:
            return ngrok.connect(port, hostname=ngrok_domain).public_url
        except TypeError:
            return ngrok.connect(port, subdomain=ngrok_domain).public_url
        except Exception:
            print("Configured ngrok hostname failed. Falling back to a random ngrok domain.")
    return ngrok.connect(port).public_url


def _start_tunnel(host: str, port: int) -> str:
    local_url = _local_base_url(host, port)

    try:
        from pyngrok import ngrok

        print("\n[+] Starting ngrok tunnel...")
        try:
            ngrok.kill()
        except Exception as exc:
            print(f"[!] ngrok.kill() failed before startup: {exc}")
        time.sleep(0.5)

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                public_url = _connect_ngrok(port)
                print(f"Ngrok public URL: {public_url}")
                return public_url
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    print(f"[!] ngrok connect failed: {exc}")
                    print("[!] Retrying once after clearing existing ngrok sessions...")
                    try:
                        ngrok.kill()
                    except Exception as kill_exc:
                        print(f"[!] ngrok.kill() retry failed: {kill_exc}")
                    time.sleep(1)
        print(f"[!] ngrok unavailable. Falling back to local URL: {local_url}")
        if last_error is not None:
            print(f"[!] ngrok error: {last_error}")
        return local_url
    except ImportError:
        print("\n[-] pyngrok not installed. Running locally only.")
        return local_url


def _run_server(host: str, port: int, site_id: str) -> None:
    selected_port = _choose_server_port(host, port)
    public_url = _start_tunnel(host, selected_port)
    _persist_launch_config(site_id, public_url)
    local_url = _local_base_url(host, selected_port)
    if public_url == local_url:
        print("[!] No public ngrok URL is available. Manual script output is local-only.")
    _print_widget_install_instructions(site_id, public_url)

    print(f"\nStarting FastAPI server on {local_url}")
    print(f"Widget will be served from: {public_url}\n")
    try:
        uvicorn.run("api.main:app", host=host, port=selected_port, reload=False)
    except KeyboardInterrupt:
        print("\nShutting down Hub Server...")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" AI SALESMAN HUB ".center(80, "="))
    print("=" * 80)

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8001"))

    start_url = _configured_url()
    site_id = _configured_site_id()
    max_pages = config.CRAWL_MAX_PAGES
    max_depth = config.CRAWL_MAX_DEPTH

    print("\nCurrent crawl target:")
    print(f"- url: {start_url}")
    print(f"- site_id: {site_id}")
    print(f"- max_pages: {max_pages}")
    print(f"- max_depth: {max_depth}")

    crawled_site_id = _run_with_animation(
        "Crawling website and building catalog",
        sync_web_crawl,
        start_url,
        max_pages=max_pages,
        max_depth=max_depth,
        site_id=site_id,
        reconcile_missing=True,
        source_name="custom_url_crawler",
    )

    print(f"\nUsing site_id: {crawled_site_id}")
    print("Starting API server now...")
    _run_server(host, port, crawled_site_id)
