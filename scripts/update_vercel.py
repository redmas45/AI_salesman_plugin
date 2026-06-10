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

def is_localhost_url(raw: str) -> bool:
    url = normalize_url(raw)
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    
    host = parsed.hostname.lower() if parsed.hostname else ""
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


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

    print("[warning] No deployable public HTTPS URL found.")
    print("[warning] This will deploy the site WITHOUT the voice orb widget.")
    print("[warning] To enable voice orb, start the backend with: python run.py")
    print("[warning] Then run this script again when ngrok tunnel is active.")
    
    # Return a placeholder URL that won't break the deployment
    return "https://placeholder.ngrok-free.app"


def run_vercel_env_update(api_url: str) -> None:
    print("\nUpdating Vercel environment variable...")
    subprocess.run(
        ["npx.cmd", "-y", "vercel", "env", "rm", "SHOPBOT_API_URL", "production", "--yes"],
        cwd=str(VERCEL_DIR),
        stdin=subprocess.DEVNULL,
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
    process = subprocess.Popen(
        ["npx.cmd", "-y", "vercel", "deploy", "--prod", "--yes"],
        cwd=str(VERCEL_DIR),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    deployment_url = ""
    # Stream the output live to console
    while True:
        line = process.stdout.readline()
        if not line:
            break
        # Safely write to console, replacing characters not supported by the terminal encoding (e.g. ▲ on Windows)
        enc = sys.stdout.encoding or "utf-8"
        sys.stdout.write(line.encode(enc, errors="replace").decode(enc))
        sys.stdout.flush()

        stripped = line.strip()
        if stripped.startswith("https://"):
            deployment_url = stripped

    process.wait()
    if process.returncode != 0:
        print("[error] Deployment failed.")
        sys.exit(1)

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
    current_site_id = site_id()
    
    # Handle placeholder URL case
    if api_url == "https://placeholder.ngrok-free.app":
        print(f"\n[warning] Using placeholder URL: {api_url}")
        print("[warning] Voice orb widget will NOT be functional on deployed site.")
        print("[warning] To enable voice orb, start backend with ngrok tunnel and run this script again.")
        
        # Don't try to fetch shopbot.js or update widget script when using placeholder
        # Just update Vercel env with placeholder
        persist_public_url(api_url, current_site_id)
        print(f"[info] Using placeholder API URL: {api_url}")
        
        # Deploy without widget functionality
        run_vercel_env_update(api_url)
        deploy_vercel()
        return
    
    # Handle localhost URL case
    if is_localhost_url(api_url):
        print(f"\n[warning] Using localhost URL: {api_url}")
        print("[warning] Voice orb widget will NOT work on deployed site (local-only).")
        print("[warning] To enable public voice orb, start backend with ngrok tunnel.")
        
        # Still update the env but with warning
        persist_public_url(api_url, current_site_id)
        print(f"[info] Using localhost API URL: {api_url}")
        
        # Deploy without widget functionality
        run_vercel_env_update(api_url)
        deploy_vercel()
        return
    
    # Valid ngrok URL case - proceed with full widget injection
    if not is_public_https_url(api_url):
        print(f"[error] Refusing to deploy non-public URL: {api_url}")
        sys.exit(1)

    persist_public_url(api_url, current_site_id)
    print(f"[ok] Using public API URL: {api_url}")

    run_vercel_env_update(api_url)
    deploy_vercel()


if __name__ == "__main__":
    main()
