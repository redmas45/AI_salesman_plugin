"""Client identifier and URL boundary validation helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

SITE_ID_MAX_LENGTH = 80
SESSION_ID_MAX_LENGTH = 120


def site_id_from_name(name: str, store_url: str) -> str:
    candidate = name or urlparse(store_url).hostname or "client"
    return safe_site_id(candidate)


def safe_site_id(raw: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(raw or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        return "client"
    if text[0].isdigit():
        text = f"site_{text}"
    return text[:SITE_ID_MAX_LENGTH]


def safe_session_id(raw: str, site_id: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(raw or "").strip())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = f"{safe_site_id(site_id)}_server"
    return text[:SESSION_ID_MAX_LENGTH]


def validated_url(raw_url: str) -> str:
    value = required_text(raw_url, "Client URL is required.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Client URL must start with http:// or https://.")
    return value.rstrip("/")


def origin_from_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return raw_url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"


def required_text(value: str, message: str) -> str:
    clean_value = str(value or "").strip()
    if not clean_value:
        raise ValueError(message)
    return clean_value
