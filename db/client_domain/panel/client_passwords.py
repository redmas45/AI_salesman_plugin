"""Client-panel password hashing and status helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

PANEL_PASSWORD_DISABLED: str = "disabled"
MIN_CLIENT_PANEL_PASSWORD_LENGTH = 12
GENERATED_PANEL_PASSWORD_BYTES = 24
PANEL_PASSWORD_ITERATIONS = 210_000
PANEL_PASSWORD_SALT_BYTES = 16


def generate_panel_password(byte_count: int = GENERATED_PANEL_PASSWORD_BYTES) -> str:
    """Generate a strong one-time client-panel password for CRM operators."""
    return secrets.token_urlsafe(byte_count)


def default_panel_password_hash(
    password: str,
    *,
    minimum_length: int = MIN_CLIENT_PANEL_PASSWORD_LENGTH,
    salt_bytes: int = PANEL_PASSWORD_SALT_BYTES,
    iterations: int = PANEL_PASSWORD_ITERATIONS,
) -> str:
    """Return a default password hash only when the configured default is strong enough."""
    if len(str(password or "")) < minimum_length:
        return ""
    return hash_panel_password(password, salt_bytes=salt_bytes, iterations=iterations)


def hash_panel_password(
    password: str,
    *,
    salt_bytes: int = PANEL_PASSWORD_SALT_BYTES,
    iterations: int = PANEL_PASSWORD_ITERATIONS,
) -> str:
    clean_password = str(password or "")
    if len(clean_password) < 6:
        raise ValueError("Client panel password must be at least 6 characters.")
    salt = secrets.token_bytes(salt_bytes)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        clean_password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${b64(salt)}${b64(digest)}"


def verify_panel_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = str(password_hash or "").split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = unb64(salt_text)
    expected = unb64(digest_text)
    actual = hashlib.pbkdf2_hmac("sha256", str(password or "").encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def panel_password_configured(password_hash: str, *, disabled_marker: str = PANEL_PASSWORD_DISABLED) -> bool:
    return bool(password_hash and password_hash != disabled_marker)


def panel_password_status(password_hash: str, *, disabled_marker: str = PANEL_PASSWORD_DISABLED) -> str:
    if password_hash == disabled_marker:
        return "revoked"
    if password_hash:
        return "configured"
    return "not_configured"


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
