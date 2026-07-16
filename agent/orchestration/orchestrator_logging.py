"""Logging and timing helpers for the orchestrator facade."""

from __future__ import annotations

import builtins
import json
import logging
import sys
import time
from typing import Any, Callable

import config


def safe_print(*args: Any, **kwargs: Any) -> None:
    """Print safely on consoles that cannot encode model output."""
    try:
        builtins.print(*args, **kwargs)
        return
    except UnicodeEncodeError:
        pass

    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)

    text = sep.join(str(arg) for arg in args)
    encoding = getattr(file, "encoding", "utf-8") or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding)

    file.write(safe_text + end)
    file.flush()


def ai_log(
    logger: logging.Logger,
    printer: Callable[..., None],
    label: str,
    value: Any,
) -> None:
    if not config.LOG_CONVERSATION_CONTENT:
        return
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(str(text).split())
    line = f"AI_CONVO | {label}: {text[:2000]}"
    logger.info(line)
    printer(line, flush=True)


def elapsed_ms(since: float) -> float:
    return round((time.perf_counter() - since) * 1000, 1)
