import ipaddress
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from dotenv import set_key


PLUGIN_DIR = Path(__file__).parent.parent.resolve()
VERCEL_DIR = PLUGIN_DIR.parent / "Vercel_website"
ENV_FILE = PLUGIN_DIR / ".env"


def read_env_value(key: str) -> str:
    try:
        content = ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("'").strip('"')
    return ""


def normalize_url(raw: str) -> str:
    return (raw or "").strip().strip("'").strip('"').rstrip("/")


def is_public_https_url(raw: str) -> bool:
    url = normalize_url(raw)
    if not url:
        return False

    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme != "https" or not parsed.hostname:
        return False

    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True

    return not (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
    )


def active_ngrok_url() -> str:
    for port in range(4040, 4050):
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/tunnels", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue

        for tunnel in payload.get("tunnels", []):
            public_url = normalize_url(tunnel.get("public_url", ""))
            if tunnel.get("proto") == "https" and is_public_https_url(public_url):
                return public_url
    return ""


def site_id() -> str:
    return (
        read_env_value("CURRENT_SITE_ID")
        or read_env_value("AI_DEFAULT_SITE_ID")
        or read_env_value("DEFAULT_SITE_ID")
        or "site_1"
    )


def persist_public_url(api_url: str, current_site_id: str) -> None:
    script_src = f"{api_url}/shopbot.js?site={current_site_id}"
    script_tag = f'<script src="{script_src}"></script>'

    os.environ["PUBLIC_API_URL"] = api_url
    set_key(str(ENV_FILE), "PUBLIC_API_URL", api_url)
    set_key(str(ENV_FILE), "PUBLIC_WIDGET_SCRIPT_URL", script_src)
    set_key(str(ENV_FILE), "MANUAL_WIDGET_SCRIPT", script_tag)


def resolve_public_api_url() -> str:
    tunnel_url = active_ngrok_url()
    env_url = normalize_url(read_env_value("PUBLIC_API_URL"))

    if tunnel_url:
        if env_url and env_url != tunnel_url:
            print(f"[info] Replacing stale PUBLIC_API_URL ({env_url}) with active tunnel.")
        return tunnel_url

    if is_public_https_url(env_url):
        return env_url

    print("[error] No deployable public HTTPS URL found.")
    if env_url:
        print(f"[error] PUBLIC_API_URL is not deployable: {env_url}")
    print("[error] Start the backend and wait for a real https://...ngrok-free.app URL before deploying.")
    sys.exit(1)


def run_vercel_env_update(api_url: str) -> None:
    print("\nUpdating Vercel environment variable...")
    subprocess.run(
        ["npx.cmd", "-y", "vercel", "env", "rm", "SHOPBOT_API_URL", "production", "--yes"],
        cwd=str(VERCEL_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    result = subprocess.run(
        ["npx.cmd", "-y", "vercel", "env", "add", "SHOPBOT_API_URL", "production"],
        cwd=str(VERCEL_DIR),
        input=f"{api_url}\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print("[error] Failed to add SHOPBOT_API_URL:")
        print(result.stderr or result.stdout)
        sys.exit(1)

    print("[ok] Vercel SHOPBOT_API_URL updated.")


def deploy_vercel() -> str:
    print("\nDeploying Vercel production site...")
    result = subprocess.run(
        ["npx.cmd", "-y", "vercel", "deploy", "--prod", "--yes"],
        cwd=str(VERCEL_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        print("[error] Deployment failed:")
        print(result.stderr or result.stdout)
        sys.exit(1)

    deployment_url = ""
    for line in result.stderr.splitlines() + result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("https://"):
            deployment_url = stripped
            break

    print("[ok] Deployment successful.")
    if deployment_url:
        print(f"[ok] Deployment URL: {deployment_url}")
    return deployment_url


def main() -> None:
    print("AI Salesman Vercel Auto-Updater")
    print("-" * 40)

    if not VERCEL_DIR.exists():
        print(f"[error] Vercel website directory not found at {VERCEL_DIR}")
        sys.exit(1)

    if not ENV_FILE.exists():
        print(f"[error] .env file not found at {ENV_FILE}")
        sys.exit(1)

    api_url = resolve_public_api_url()
    if not is_public_https_url(api_url):
        print(f"[error] Refusing to deploy non-public URL: {api_url}")
        sys.exit(1)

    current_site_id = site_id()
    persist_public_url(api_url, current_site_id)
    print(f"[ok] Using public API URL: {api_url}")

    run_vercel_env_update(api_url)
    deploy_vercel()


if __name__ == "__main__":
    main()
