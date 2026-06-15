from __future__ import annotations

import atexit
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv, set_key

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
LOGS_DIR = ROOT / "logs"
PID_FILE = ROOT / ".run.pid"
BACKEND_PID_FILE = ROOT / ".static_ip_backend.pid"
STOREFRONT_PID_FILE = ROOT / ".static_ip_storefront.pid"
CADDY_PID_FILE = ROOT / ".caddy.pid"
DEFAULT_STOREFRONT_ROOT = ROOT.parent / "Vercel_website"

load_dotenv(ENV_FILE)
LOGS_DIR.mkdir(exist_ok=True)


class TeeLogger:
    """Write supervisor output to both the console and a timestamped log file."""

    def __init__(self, original_stream, log_file: Path):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, data):
        try:
            self.original_stream.write(data)
            self.original_stream.flush()
        except UnicodeEncodeError:
            encoding = getattr(self.original_stream, "encoding", "utf-8") or "utf-8"
            safe_data = str(data).encode(encoding, errors="replace").decode(encoding)
            self.original_stream.write(safe_data)
            self.original_stream.flush()

        try:
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(str(data))
        except OSError as exc:
            self.original_stream.write(f"[warning] Could not write tee log: {exc}\n")
            self.original_stream.flush()

    def flush(self):
        self.original_stream.flush()

    def isatty(self):
        return getattr(self.original_stream, "isatty", lambda: False)()


log_file = LOGS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
sys.stdout = TeeLogger(sys.stdout, log_file)
sys.stderr = TeeLogger(sys.stderr, log_file)


@dataclass
class Service:
    name: str
    command: list[str]
    cwd: Path
    env: dict[str, str]
    pid_file: Path
    log_file: Path
    process: subprocess.Popen | None = None
    stdout_handle: object | None = None
    stderr_handle: object | None = None

    def start(self) -> None:
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.stdout_handle = self.log_file.open("ab")
        self.stderr_handle = self.log_file.with_suffix(self.log_file.suffix + ".err").open("ab")
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        self.process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            env={**os.environ, **self.env},
            stdout=self.stdout_handle,
            stderr=self.stderr_handle,
            creationflags=creationflags,
        )
        self.pid_file.write_text(str(self.process.pid), encoding="utf-8")
        print(f"[ok] Started {self.name} PID {self.process.pid}")
        print(f"     log: {self.log_file}")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            stop_process_tree(self.process.pid)
        self.pid_file.unlink(missing_ok=True)
        for handle in (self.stdout_handle, self.stderr_handle):
            try:
                if handle:
                    handle.close()
            except OSError as exc:
                print(f"[warning] Could not close service log handle: {exc}")

    def exited(self) -> bool:
        return self.process is not None and self.process.poll() is not None


@dataclass(frozen=True)
class RuntimeOrigin:
    mode: str
    public_origin: str
    lan_ip: str
    public_ip: str


services: list[Service] = []
log_tail_stop = threading.Event()


def main() -> None:
    print("\n" + "=" * 80)
    print(" AI-KART MODULAR HOST ".center(80, "="))
    print("=" * 80)

    stop_previous_supervisor()
    write_pid_file(PID_FILE, os.getpid())

    deployment_mode = current_deployment_mode()
    default_storefront_port = "8584" if deployment_mode == "intranet" else "8000"
    default_backend_port = "8585" if deployment_mode == "intranet" else "8011"
    default_https_port = "8484" if deployment_mode == "intranet" else "443"
    default_http_redirect_port = "0" if deployment_mode == "intranet" else "80"

    storefront_port = int(os.getenv("STOREFRONT_PORT", default_storefront_port))
    backend_port = int(os.getenv("BACKEND_PORT", os.getenv("SHOPBOT_BACKEND_PORT", default_backend_port)))
    https_port = int(os.getenv("HTTPS_PORT", default_https_port))
    http_redirect_port = int(os.getenv("HTTP_REDIRECT_PORT", default_http_redirect_port))
    site_id = safe_site_id(
        os.getenv("CURRENT_SITE_ID")
        or os.getenv("AI_DEFAULT_SITE_ID")
        or os.getenv("DEFAULT_SITE_ID")
        or "ai_kart_main"
    )
    storefront_root = Path(os.getenv("STOREFRONT_ROOT", str(DEFAULT_STOREFRONT_ROOT))).resolve()

    runtime_origin = resolve_runtime_origin(storefront_port, https_port)
    public_origin = runtime_origin.public_origin
    public_ip = runtime_origin.public_ip

    local_storefront_origin = f"http://127.0.0.1:{storefront_port}"
    backend_origin = f"http://127.0.0.1:{backend_port}"
    persist_runtime_env(
        site_id,
        public_origin,
        local_storefront_origin,
        runtime_origin.mode,
        storefront_port,
        backend_port,
        https_port,
        http_redirect_port,
    )
    ensure_firewall_rule(storefront_port)
    if http_redirect_port > 0:
        ensure_firewall_rule(http_redirect_port, "AI-KART HTTPS Redirect")
    ensure_firewall_rule(https_port, "AI-KART HTTPS Proxy")

    print("\nRuntime configuration:")
    print(f"- deployment mode: {runtime_origin.mode}")
    print(f"- storefront root: {storefront_root}")
    print(f"- site_id: {site_id}")
    print(f"- client storefront: 0.0.0.0:{storefront_port}")
    print(f"- backend/private: 127.0.0.1:{backend_port}")
    print(f"- https proxy: 0.0.0.0:{https_port}")
    print(f"- local URL: {local_storefront_origin}")
    print(f"- LAN IP: {runtime_origin.lan_ip}")
    if public_ip:
        print(f"- public IP: {public_ip}")
    print(f"- browser URL target: {public_origin}")
    if is_ip_https_origin(public_origin):
        print("[warning] IP-based HTTPS uses a local self-signed certificate. Browsers may warn on other devices.")

    caddy = build_caddy_service(
        public_origin,
        public_ip,
        https_port,
        http_redirect_port,
        storefront_port,
        backend_port,
    )
    stop_stale_runtime_processes(
        [port for port in [storefront_port, backend_port, http_redirect_port, https_port] if port > 0]
    )

    storefront = Service(
        name="AI-KART client storefront",
        command=[
            sys.executable,
            "-m",
            "uvicorn",
            "api.index:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(storefront_port),
        ],
        cwd=storefront_root,
        env={
            "LAB_INJECTION_HTML": client_embed_snippet(site_id, public_origin),
            "LAB_ALLOWED_SCRIPT_ORIGINS": public_origin,
            "SHOPBOT_BACKEND_ORIGIN": backend_origin,
            "AI_DEFAULT_SITE_ID": site_id,
            "PUBLIC_HTTPS_ORIGIN": os.getenv("PUBLIC_HTTPS_ORIGIN", "").strip(),
            "FORCE_HTTPS": os.getenv("FORCE_HTTPS", "").strip(),
        },
        pid_file=STOREFRONT_PID_FILE,
        log_file=LOGS_DIR / "static_ip_storefront.log",
    )

    backend = Service(
        name="AI Salesman backend",
        command=[
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(backend_port),
        ],
        cwd=ROOT,
        env={
            "PUBLIC_API_URL": public_origin,
            "CURRENT_URL": local_storefront_origin,
            "CURRENT_SITE_ID": site_id,
            "AI_DEFAULT_SITE_ID": site_id,
            "DEFAULT_SITE_ID": site_id,
            "CRAWL_ON_STARTUP": os.getenv("CRAWL_ON_STARTUP", "true"),
        },
        pid_file=BACKEND_PID_FILE,
        log_file=LOGS_DIR / "static_ip_backend.log",
    )

    services.extend([caddy, storefront, backend])
    caddy.start()
    wait_for_port("127.0.0.1", https_port, "Caddy HTTPS proxy", timeout=30)

    storefront.start()
    wait_for_http(f"{local_storefront_origin}/api/products.json", "storefront catalog", timeout=45)

    backend.start()
    start_ai_log_tail(backend.log_file)
    wait_for_http(f"{local_storefront_origin}/health", "backend health through storefront proxy", timeout=240)

    print("\nReady.")
    print(f"- Open storefront: {local_storefront_origin}")
    print(f"- Wi-Fi/LAN URL:   {public_origin}")
    print("\nPress Ctrl+C to stop all services.")

    monitor_services()


def html_attr(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def client_embed_snippet(site_id: str, api_url: str) -> str:
    site_id_attr = html_attr(site_id)
    api_url_attr = html_attr(api_url)
    return (
        f'<script defer src="{api_url_attr}/shopbot.js?site={site_id_attr}" '
        f'data-site-id="{site_id_attr}" data-brand="AI-KART"></script>'
    )


def detect_public_ip() -> str:
    try:
        with urlopen("https://api.ipify.org?format=json", timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return str(data["ip"])
    except Exception as exc:
        print(f"[warning] Could not detect public IP: {exc}")
        print("[warning] Falling back to 127.0.0.1 for public-origin config.")
        return "127.0.0.1"


def detect_lan_ip() -> str:
    configured = clean_env_value(os.getenv("LAN_IP") or os.getenv("INTRANET_IP"))
    if configured:
        return configured

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            detected = sock.getsockname()[0]
            if detected and not detected.startswith("127."):
                return detected
    except OSError:
        detected = ""

    try:
        detected = socket.gethostbyname(socket.gethostname())
        if detected and not detected.startswith("127."):
            return detected
    except OSError:
        detected = ""

    return "127.0.0.1"


def current_deployment_mode() -> str:
    return normalize_deployment_mode(clean_env_value(
        os.getenv("DEPLOYMENT_MODE")
        or os.getenv("AI_KART_DEPLOYMENT_MODE")
        or os.getenv("HOSTING_MODE")
        or "intranet"
    ).lower())


def resolve_runtime_origin(storefront_port: int, https_port: int) -> RuntimeOrigin:
    mode = current_deployment_mode()

    lan_ip = detect_lan_ip()
    public_ip = clean_env_value(os.getenv("STATIC_PUBLIC_IP") or os.getenv("PUBLIC_IP"))
    public_origin = ""

    if mode == "intranet":
        public_origin = first_env_value("INTRANET_ORIGIN", "LAN_ORIGIN")
        if not public_origin:
            public_origin = origin_with_port(f"https://{lan_ip}", https_port)
    elif mode == "public-ip":
        public_ip = public_ip or detect_public_ip()
        public_origin = first_env_value("PUBLIC_STOREFRONT_ORIGIN", "PUBLIC_API_URL")
        if not public_origin:
            public_origin = f"https://{public_ip}"
    elif mode == "domain":
        public_origin = first_env_value("PUBLIC_STOREFRONT_ORIGIN", "PUBLIC_API_URL")
        public_domain = clean_env_value(os.getenv("PUBLIC_DOMAIN") or os.getenv("DOMAIN"))
        if not public_origin and public_domain:
            public_origin = f"https://{public_domain}"
        if not public_origin:
            raise RuntimeError(
                "DEPLOYMENT_MODE=domain requires PUBLIC_DOMAIN or PUBLIC_STOREFRONT_ORIGIN in .env."
            )
        public_ip = public_ip or detect_public_ip()
    elif mode == "custom":
        public_origin = first_env_value(
            "PUBLIC_STOREFRONT_ORIGIN",
            "PUBLIC_API_URL",
            "TUNNEL_ORIGIN",
            "CLOUDFLARE_TUNNEL_ORIGIN",
        )
        if not public_origin:
            raise RuntimeError(
                "DEPLOYMENT_MODE=custom requires PUBLIC_STOREFRONT_ORIGIN, PUBLIC_API_URL, "
                "TUNNEL_ORIGIN, or CLOUDFLARE_TUNNEL_ORIGIN in .env."
            )
        public_ip = public_ip or ""

    return RuntimeOrigin(
        mode=mode,
        public_origin=normalize_origin(public_origin),
        lan_ip=lan_ip,
        public_ip=public_ip,
    )


def normalize_deployment_mode(raw_mode: str) -> str:
    aliases = {
        "lan": "intranet",
        "wifi": "intranet",
        "local-network": "intranet",
        "local_network": "intranet",
        "static-ip": "public-ip",
        "static_ip": "public-ip",
        "public_ip": "public-ip",
        "public": "public-ip",
        "dns": "domain",
        "cloudflare": "custom",
        "cloudflare-tunnel": "custom",
        "cloudflare_tunnel": "custom",
        "tunnel": "custom",
        "ngrok": "custom",
    }
    normalized = aliases.get(raw_mode, raw_mode)
    if normalized not in {"intranet", "public-ip", "domain", "custom"}:
        raise RuntimeError(
            "Invalid DEPLOYMENT_MODE. Use one of: intranet, public-ip, domain, custom."
        )
    return normalized


def normalize_origin(raw_origin: str) -> str:
    origin = clean_env_value(raw_origin).rstrip("/")
    if not origin:
        raise RuntimeError("Browser URL target is empty.")
    if not re.match(r"^https?://", origin, flags=re.IGNORECASE):
        origin = f"https://{origin}"
    return origin.rstrip("/")


def origin_with_port(origin: str, port: int) -> str:
    normalized = normalize_origin(origin)
    if port in {0, 80, 443}:
        return normalized
    if re.search(r":\d+$", normalized.rsplit("@", 1)[-1]):
        return normalized
    return f"{normalized}:{port}"


def first_env_value(*keys: str) -> str:
    for key in keys:
        value = clean_env_value(os.getenv(key))
        if value:
            return value
    return ""


def clean_env_value(value: str | None) -> str:
    return (value or "").strip().strip("\"'")


def build_caddy_service(
    public_origin: str,
    public_ip: str,
    https_port: int,
    http_redirect_port: int,
    storefront_port: int,
    backend_port: int,
) -> Service:
    caddy_exe = find_caddy_executable()
    caddyfile = write_caddyfile(
        public_origin,
        public_ip,
        https_port,
        http_redirect_port,
        storefront_port,
        backend_port,
    )
    return Service(
        name="Caddy HTTPS proxy",
        command=[
            str(caddy_exe),
            "run",
            "--config",
            str(caddyfile),
            "--adapter",
            "caddyfile",
        ],
        cwd=ROOT,
        env={},
        pid_file=CADDY_PID_FILE,
        log_file=LOGS_DIR / "caddy.log",
    )


def find_caddy_executable() -> Path:
    configured = os.getenv("CADDY_EXE", "").strip().strip("\"'")
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))

    path_match = find_executable_on_path("caddy.exe" if os.name == "nt" else "caddy")
    if path_match:
        candidates.append(path_match)

    if os.name == "nt":
        winget_dir = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        if winget_dir.is_dir():
            candidates.extend(winget_dir.rglob("caddy.exe"))

    candidates.append(ROOT / ".local" / "caddy" / ("caddy.exe" if os.name == "nt" else "caddy"))

    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()

    raise RuntimeError(
        "Caddy executable not found. Install with: "
        "winget install --id CaddyServer.Caddy --accept-source-agreements --accept-package-agreements"
    )


def find_executable_on_path(name: str) -> Path | None:
    for raw_dir in os.getenv("PATH", "").split(os.pathsep):
        if not raw_dir:
            continue
        candidate = Path(raw_dir) / name
        if candidate.is_file():
            return candidate
    return None


def write_caddyfile(
    public_origin: str,
    public_ip: str,
    https_port: int,
    http_redirect_port: int,
    storefront_port: int,
    backend_port: int,
) -> Path:
    deploy_dir = ROOT / "deploy"
    deploy_dir.mkdir(exist_ok=True)
    caddyfile = deploy_dir / "Caddyfile"

    host = origin_host(public_origin)
    redirect_block = []
    if http_redirect_port > 0:
        target = "https://{host}{uri}" if https_port == 443 else f"https://{{host}}:{https_port}" + "{uri}"
        redirect_block = [
            f"http://:{http_redirect_port} {{",
            f"\tredir {target} 308",
            "}",
            "",
        ]

    if is_ip_address(host):
        cert_path, key_path = ensure_ip_certificate(host)
        global_options = ["{", f"\tdefault_sni {host}"]
        if http_redirect_port <= 0:
            global_options.append("\tauto_https disable_redirects")
        global_options.append("}")
        route_block = backend_route_block(backend_port, storefront_port)
        caddyfile.write_text(
            "\n".join(
                [
                    *global_options,
                    "",
                    *redirect_block,
                    f"https://:{https_port} {{",
                    "\tencode gzip zstd",
                    f"\ttls {to_caddy_path(cert_path)} {to_caddy_path(key_path)}",
                    "",
                    *route_block,
                    "}",
                    "",
                ]
            ),
            encoding="ascii",
        )
    else:
        site_label = host if https_port == 443 else f"https://{host}:{https_port}"
        route_block = backend_route_block(backend_port, storefront_port)
        caddyfile.write_text(
            "\n".join(
                [
                    *redirect_block,
                    f"{site_label} {{",
                    "\tencode gzip zstd",
                    "",
                    *route_block,
                    "}",
                    "",
                ]
            ),
            encoding="ascii",
        )

    return caddyfile


def backend_route_block(backend_port: int, storefront_port: int) -> list[str]:
    """Route HUB API/widget traffic to backend and page traffic to storefront."""
    return [
        f"\thandle /shopbot.js {{",
        f"\t\treverse_proxy 127.0.0.1:{backend_port}",
        "\t}",
        f"\thandle /shopbot-widget.js {{",
        f"\t\treverse_proxy 127.0.0.1:{backend_port}",
        "\t}",
        f"\thandle /shopbot-frame {{",
        f"\t\treverse_proxy 127.0.0.1:{backend_port}",
        "\t}",
        f"\thandle /v1/* {{",
        f"\t\treverse_proxy 127.0.0.1:{backend_port}",
        "\t}",
        f"\thandle /health {{",
        f"\t\treverse_proxy 127.0.0.1:{backend_port}",
        "\t}",
        "\thandle {",
        f"\t\treverse_proxy 127.0.0.1:{storefront_port}",
        "\t}",
    ]


def origin_host(origin: str) -> str:
    text = origin.strip().rstrip("/")
    text = re.sub(r"^https?://", "", text, flags=re.IGNORECASE)
    return text.rsplit(":", 1)[0].strip("[]")


def is_ip_https_origin(origin: str) -> bool:
    return origin.lower().startswith("https://") and is_ip_address(origin_host(origin))


def is_ip_address(value: str) -> bool:
    try:
        ip_address(value)
        return True
    except ValueError:
        return False


def ensure_ip_certificate(raw_ip: str) -> tuple[Path, Path]:
    cert_dir = ROOT / "deploy" / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    parsed_ip = ip_address(raw_ip)
    safe_ip = str(parsed_ip).replace(":", "_").replace(".", "_")
    cert_path = cert_dir / f"ip-{safe_ip}.crt"
    key_path = cert_dir / f"ip-{safe_ip}.key"

    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, str(parsed_ip)),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AI-KART POC"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=int(os.getenv("IP_CERT_DAYS", "30"))))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(parsed_ip)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    print(f"[ok] Generated IP HTTPS certificate: {cert_path}")
    return cert_path, key_path


def to_caddy_path(path: Path) -> str:
    return path.resolve().as_posix()


def safe_site_id(raw: str) -> str:
    text = (raw or "").strip().strip("\"'").lower()
    text = re.sub(r"[^a-z0-9_:-]+", "_", text)
    text = text.replace(":", "_")
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80] or "ai_kart_main"


def persist_runtime_env(
    site_id: str,
    public_origin: str,
    local_storefront_origin: str,
    deployment_mode: str,
    storefront_port: int,
    backend_port: int,
    https_port: int,
    http_redirect_port: int,
) -> None:
    values = {
        "DEPLOYMENT_MODE": deployment_mode,
        "STOREFRONT_PORT": str(storefront_port),
        "BACKEND_PORT": str(backend_port),
        "HTTPS_PORT": str(https_port),
        "HTTP_REDIRECT_PORT": str(http_redirect_port),
        "AI_DEFAULT_SITE_ID": site_id,
        "DEFAULT_SITE_ID": site_id,
        "CURRENT_SITE_ID": site_id,
        "CURRENT_URL": local_storefront_origin,
        "PUBLIC_STOREFRONT_ORIGIN": public_origin,
        "PUBLIC_API_URL": public_origin,
        "PUBLIC_HTTPS_ORIGIN": public_origin,
        "FORCE_HTTPS": "true",
        "MANUAL_WIDGET_SCRIPT": f'<script defer src="{public_origin}/shopbot.js?site={site_id}" data-site-id="{site_id}"></script>',
        "PUBLIC_WIDGET_SCRIPT_URL": f"{public_origin}/shopbot.js?site={site_id}",
    }
    for key, value in values.items():
        os.environ[key] = value
        set_key(str(ENV_FILE), key, value)


def ensure_firewall_rule(port: int, label: str | None = None) -> None:
    if os.name != "nt":
        return
    if os.getenv("CONFIGURE_FIREWALL", "true").strip().lower() in {"0", "false", "no", "off"}:
        return

    display_name = f"{label or 'AI-KART Self Host Storefront'} {port}"
    command = (
        "if (-not (Get-NetFirewallRule -DisplayName "
        f"'{display_name}' -ErrorAction SilentlyContinue)) "
        "{ New-NetFirewallRule "
        f"-DisplayName '{display_name}' "
        "-Direction Inbound -Action Allow -Protocol TCP "
        f"-LocalPort {port} | Out-Null "
        "}"
    )

    if not is_windows_admin():
        print("\n[warning] Firewall rule was not created because this terminal is not elevated.")
        print("Run PowerShell as Administrator and execute:")
        print(
            f"New-NetFirewallRule -DisplayName '{display_name}' "
            f"-Direction Inbound -Action Allow -Protocol TCP -LocalPort {port}"
        )
        return

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        print(f"[ok] Windows Firewall allows inbound TCP {port}.")
    else:
        print(f"[warning] Firewall rule creation failed: {result.stderr.strip() or result.stdout.strip()}")


def is_windows_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def wait_for_http(url: str, label: str, timeout: int) -> None:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        fail_if_service_exited()
        try:
            with urlopen(url, timeout=5) as response:
                if 200 <= response.status < 400:
                    print(f"[ok] {label} ready.")
                    return
        except URLError as exc:
            last_error = str(exc)
        except Exception as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {label}: {last_error}")


def wait_for_port(host: str, port: int, label: str, timeout: int) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        fail_if_service_exited()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            if sock.connect_ex((host, port)) == 0:
                print(f"[ok] {label} ready.")
                return
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {label} on {host}:{port}.")


def monitor_services() -> None:
    try:
        while True:
            fail_if_service_exited()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        cleanup_runtime()


def start_ai_log_tail(log_file: Path) -> None:
    if os.getenv("STREAM_AI_LOGS", "true").strip().lower() in {"0", "false", "no", "off"}:
        return

    def _tail() -> None:
        try:
            while not log_file.exists() and not log_tail_stop.is_set():
                time.sleep(0.2)
            with log_file.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(0, os.SEEK_END)
                while not log_tail_stop.is_set():
                    line = handle.readline()
                    if not line:
                        time.sleep(0.25)
                        continue
                    if is_ai_turn_log_line(line):
                        print(line.rstrip())
        except OSError:
            return

    thread = threading.Thread(target=_tail, name="ai-log-tail", daemon=True)
    thread.start()


def is_ai_turn_log_line(line: str) -> bool:
    return "AI_CONVO |" in line or "[SHOPBOT TURN]" in line


def fail_if_service_exited() -> None:
    for service in services:
        if service.exited():
            code = service.process.returncode if service.process else "unknown"
            raise RuntimeError(f"{service.name} exited early with code {code}. Check {service.log_file}.")


def write_pid_file(path: Path, pid: int) -> None:
    path.write_text(str(pid), encoding="utf-8")


def read_pid_file(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def stop_previous_supervisor() -> None:
    pid = read_pid_file(PID_FILE)
    if not pid or pid == os.getpid():
        return
    if process_exists(pid):
        print(f"[!] Stopping previous run.py supervisor PID {pid}")
        stop_process_tree(pid)
    PID_FILE.unlink(missing_ok=True)


def stop_stale_runtime_processes(ports: list[int]) -> None:
    stale_pids = set()
    for pid_file in (BACKEND_PID_FILE, STOREFRONT_PID_FILE, CADDY_PID_FILE):
        pid = read_pid_file(pid_file)
        if pid:
            stale_pids.add(pid)
        pid_file.unlink(missing_ok=True)

    stale_pids.update(listening_pids(ports))
    stale_pids.discard(os.getpid())

    if not stale_pids:
        return

    print(f"[!] Stopping stale runtime PID(s): {', '.join(str(pid) for pid in sorted(stale_pids))}")
    for pid in sorted(stale_pids):
        stop_process_tree(pid)

    for _ in range(30):
        if not any(is_port_in_use(port) for port in ports):
            return
        time.sleep(0.25)
    blocking = listening_pids(ports)
    detail = f" Blocking PID(s): {', '.join(str(pid) for pid in sorted(blocking))}." if blocking else ""
    raise RuntimeError(
        "One or more runtime ports are still busy after cleanup."
        f"{detail} If Windows reports Access is denied, close the old elevated run.py/Caddy terminal "
        "or restart this command from an elevated PowerShell."
    )


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True, text=True, check=False)
        return
    subprocess.run(["kill", "-TERM", str(pid)], capture_output=True, text=True, check=False)


def listening_pids(ports: list[int]) -> set[int]:
    if os.name == "nt":
        result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=False)
        pids: set[int] = set()
        wanted = {str(port) for port in ports}
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line or "LISTENING" not in line.upper():
                continue
            parts = line.split()
            if len(parts) < 5 or ":" not in parts[1]:
                continue
            local_port = parts[1].rsplit(":", 1)[-1].strip("[]")
            if local_port not in wanted:
                continue
            try:
                pids.add(int(parts[-1]))
            except ValueError:
                continue
        return pids
    return set()


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def cleanup_runtime() -> None:
    log_tail_stop.set()
    for service in reversed(services):
        service.stop()
    PID_FILE.unlink(missing_ok=True)


def handle_exit_signal(signum, _frame) -> None:
    print(f"\n[!] Received signal {signum}. Shutting down...")
    cleanup_runtime()
    raise SystemExit(0)


if __name__ == "__main__":
    atexit.register(cleanup_runtime)
    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)
    try:
        main()
    except Exception as exc:
        print(f"\n[x] Startup failed: {exc}")
        cleanup_runtime()
        raise SystemExit(1)
