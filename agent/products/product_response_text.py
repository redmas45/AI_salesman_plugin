"""Shared text normalization helpers for product response services."""

from __future__ import annotations

import html
import re
from typing import Any


def normalize_lookup_text(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("t-shirt", "t shirt").replace("tee-shirt", "tee shirt")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def plain_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def concise_text(value: str, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text if text.endswith((".", "!", "?")) else f"{text}."

    truncated = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    sentence_end = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if sentence_end >= 40:
        return truncated[: sentence_end + 1]
    return f"{truncated}."


def phrase_in_text(phrase: str, text: str) -> bool:
    return f" {phrase} " in f" {text} "


def numeric_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return number if number == number else None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None
