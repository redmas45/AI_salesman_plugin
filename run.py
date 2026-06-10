from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from dotenv import load_dotenv, set_key

import config
from agent.ingestion import sanitize_site_id, sync_web_crawl

load_dotenv()

import sys
from datetime import datetime
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
log_filename = LOGS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

class TeeLogger:
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, data):
        self.original_stream.write(data)
        self.original_stream.flush()
        try:
            if isinstance(data, bytes):
                data = data.decode('utf-8', 'replace')
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(data)
        except Exception:
            pass

    def flush(self):
        self.original_stream.flush()

    def isatty(self):
        return getattr(self.original_stream, "isatty", lambda: False)()

sys.stdout = TeeLogger(sys.stdout, log_filename)
sys.stderr = TeeLogger(sys.stderr, log_filename)


PID_FILE = Path(__file__).resolve().parent / ".run.pid"


def _ask(prompt: str, default: str | None = None) -> str:
    label = f"{prompt} [{default}]: " if default is not None else f"{prompt}: "
    value = input(label).strip()
    return value if value else (default or "")


def _persist_env_value(key: str, value: str) -> None:
    os.environ[key] = value
    env_path = Path(__file__).resolve().parent / ".env"
    set_key(str(env_path), key, value)


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid_file() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _write_pid_file() -> None:
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid_file() -> None:
    current = _read_pid_file()
    if current not in {None, os.getpid()}:
        return
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


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
    
    if not _is_public_https_url(public_url):
        print(f"[warning] This is a LOCAL URL. Widget will only work from: {public_url}")
        print(f"[warning] For production, ensure ngrok is running and update PUBLIC_API_URL")
    else:
        print(f"Saved to .env as MANUAL_WIDGET_SCRIPT for CURRENT_URL={config.CURRENT_URL or 'current target'}")
        print(f"Allow this backend origin in target CSP: {public_url} (script-src, connect-src, frame-src)")


def _local_base_url(host: str, port: int) -> str:
    local_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{local_host}:{port}"


def _is_public_https_url(raw: str) -> bool:
    try:
        parsed = urlparse((raw or "").strip().strip("\"'"))
    except ValueError:
        return False
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    return parsed.hostname.lower() not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _port_is_in_use(host: str, port: int) -> bool:
    check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((check_host, port)) == 0


def _list_listening_pids(port: int) -> list[int]:
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    pids: set[int] = set()
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address = parts[1]
        pid_raw = parts[-1]
        if ":" not in local_address:
            continue
        local_port = local_address.rsplit(":", 1)[-1].strip("[]")
        if local_port != str(port):
            continue
        try:
            pid = int(pid_raw)
        except ValueError:
            continue
        if pid > 0 and pid != os.getpid():
            pids.add(pid)
    return sorted(pids)


def _kill_pid(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F", "/T"],
        capture_output=True,
        text=True,
        check=False,
    )


def _stop_previous_run_instance() -> None:
    existing_pid = _read_pid_file()
    if existing_pid is None or existing_pid == os.getpid():
        return
    if not _process_exists(existing_pid):
        _remove_pid_file()
        return

    print(f"[!] Stopping previous run.py instance PID {existing_pid}")
    _kill_pid(existing_pid)
    for _ in range(20):
        if not _process_exists(existing_pid):
            _remove_pid_file()
            return
        time.sleep(0.25)
    raise RuntimeError(f"Previous run.py instance PID {existing_pid} did not stop cleanly.")


def _ensure_port_free(host: str, port: int) -> None:
    if not _port_is_in_use(host, port):
        return

    pids = _list_listening_pids(port)
    if not pids:
        print(f"[!] Port {port} is busy but no listener PID could be resolved.")
        return

    print(f"[!] Freeing port {port} by stopping listener PID(s): {', '.join(str(pid) for pid in pids)}")
    for pid in pids:
        _kill_pid(pid)

    for _ in range(20):
        if not _port_is_in_use(host, port):
            print(f"[ok] Port {port} is now free.")
            return
        time.sleep(0.25)

    raise RuntimeError(f"Port {port} is still busy after attempting to stop existing listeners.")


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
        print("[warning] ngrok unavailable. Using localhost-only mode.")
        print("[warning] Widget will only work on localhost. To enable public access, fix ngrok.")
        return local_url
    except ImportError:
        print("\n[warning] pyngrok not installed. Cannot create public HTTPS widget URL.")
        print("[warning] Widget will only work on localhost. Install pyngrok for public access.")
        return local_url


def _cleanup_runtime() -> None:
    try:
        from pyngrok import ngrok

        ngrok.kill()
    except Exception:
        pass
    _remove_pid_file()


def _handle_exit_signal(signum, _frame) -> None:
    print(f"\n[!] Received signal {signum}. Shutting down run.py...")
    raise KeyboardInterrupt


def _run_server(host: str, port: int, site_id: str) -> None:
    _ensure_port_free(host, port)
    selected_port = _choose_server_port(host, port)
    public_url = _start_tunnel(host, selected_port)
    
    if not _is_public_https_url(public_url):
        print(f"[warning] Using local URL: {public_url}")
        print("[warning] Widget will only work locally. For public access, ensure ngrok is working.")
        # Still persist the URL but mark it as local-only
        _persist_launch_config(site_id, public_url)
    else:
        _persist_launch_config(site_id, public_url)
    
    local_url = _local_base_url(host, selected_port)
    if public_url == local_url:
        print("[warning] No public ngrok URL available. Manual script output is local-only.")
    _print_widget_install_instructions(site_id, public_url)

    print(f"\nStarting FastAPI server on {local_url}")
    print(f"Widget will be served from: {public_url}\n")
    try:
        uvicorn.run("api.main:app", host=host, port=selected_port, reload=False)
    except KeyboardInterrupt:
        print("\nShutting down Hub Server...")


if __name__ == "__main__":
    atexit.register(_cleanup_runtime)
    signal.signal(signal.SIGINT, _handle_exit_signal)
    signal.signal(signal.SIGTERM, _handle_exit_signal)

    print("\n" + "=" * 80)
    print(" AI SALESMAN HUB ".center(80, "="))
    print("=" * 80)

    _stop_previous_run_instance()
    _write_pid_file()

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
