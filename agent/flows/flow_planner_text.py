"""Text normalization helpers for universal flow planning."""

from __future__ import annotations

import re
from typing import Any

from agent.retrieval.referent_reference import ordinal_position


def ordinal_index(text: str) -> int | None:
    """Which displayed record an ordinal selects, if the turn selects one.

    Delegates to the shared referent rules so "the first one" and "first I want
    to browse" are told apart the same way in every part of the pipeline.
    """
    return ordinal_position(text)


def normalize_text(value: Any) -> str:
    text = re.sub(r"[^a-z0-9\s_-]+", " ", str(value or "").lower())
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()
