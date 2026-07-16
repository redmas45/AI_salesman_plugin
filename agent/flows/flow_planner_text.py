"""Text normalization helpers for universal flow planning."""

from __future__ import annotations

import re
from typing import Any

ORDINAL_INDEXES = {
    "first": 0,
    "1st": 0,
    "option one": 0,
    "second": 1,
    "2nd": 1,
    "option two": 1,
    "third": 2,
    "3rd": 2,
    "option three": 2,
    "fourth": 3,
    "4th": 3,
    "option four": 3,
}


def ordinal_index(text: str) -> int | None:
    for token, index in ORDINAL_INDEXES.items():
        if re.search(rf"\b{re.escape(token)}\b", text):
            return index
    match = re.search(r"\boption\s+([1-4])\b", text)
    if match:
        return int(match.group(1)) - 1
    return None


def normalize_text(value: Any) -> str:
    text = re.sub(r"[^a-z0-9\s_-]+", " ", str(value or "").lower())
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()
