"""Shared normalization primitives for catalog ingestion."""

from __future__ import annotations

import hashlib
import html
import re
from typing import Any

PRICE_RE = re.compile(r"(?:\u20b9|rs\.?|inr|\$)\s*([0-9]+(?:[.,][0-9]{1,2})?)", re.IGNORECASE)
SPACES_RE = re.compile(r"\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_site_id(raw: str) -> str:
    text = (raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        return "site"
    if text[0].isdigit():
        text = f"site_{text}"
    return text[:50]


def stable_id(*parts: str) -> int:
    seed = "|".join(parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return int(digest, 16) % (2**63 - 1) or 1


def clean_text(raw: Any) -> str:
    if raw is None:
        return ""
    return SPACES_RE.sub(" ", html.unescape(str(raw))).strip()


def strip_html(raw: Any) -> str:
    return clean_text(HTML_TAG_RE.sub(" ", str(raw or "")))


def first(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, tuple, dict)) and not value:
            continue
        return value
    return default


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return 0.0
    text = str(value).replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        return float(match.group(1)) if match else 0.0


def to_positive_int_id(value: Any) -> int | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"\d+", text):
        return None
    parsed = int(text)
    return parsed if parsed > 0 else None


def parse_price(text: str) -> float:
    match = PRICE_RE.search(clean_text(text))
    if not match:
        return 0.0
    return to_float(match.group(1))


def normalized_candidate_name(value: str) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"(?:\s+|^)(?:\u20b9|rs\.?|inr|\$)\s*[0-9]+(?:[.,][0-9]{1,2})?\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def looks_like_noise_name(value: str) -> bool:
    lowered = normalized_candidate_name(value)
    if not lowered:
        return True

    utility_tokens = {
        "relative",
        "block",
        "inline-block",
        "h-full",
        "w-full",
        "aspect-square",
        "sr-only",
        "pointer-events-none",
    }
    tokens = set(lowered.split())
    if len(tokens & utility_tokens) >= 2:
        return True

    if lowered.startswith(("relative ", "block ", "inline-block ")):
        return True

    if "," in lowered and float(parse_price(lowered)) <= 0:
        return True

    return False
