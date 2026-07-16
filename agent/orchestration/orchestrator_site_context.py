"""Site context helpers for the orchestrator facade."""

from __future__ import annotations

import logging
from typing import Callable

import psycopg

DEFAULT_AUDIO_FILENAME = "audio.wav"
GENERIC_BLOCKED_RESPONSE = (
    "I'm sorry, I can't respond to that safely. Tell me what you need and I will help from this website's information."
)
ECOMMERCE_BLOCKED_RESPONSE = "I had trouble with that shopping request. Tell me what you need and I will help you find it."
NON_ECOMMERCE_CART_CONTEXT = "No ecommerce cart context applies to this client."
CAPABILITY_FILTER_SKIPPED = "skipped"
PIPELINE_RECOVERABLE_ERRORS: tuple[type[BaseException], ...] = (
    KeyError,
    LookupError,
    RuntimeError,
    TypeError,
    ValueError,
    psycopg.Error,
)


def is_ecommerce_site(
    site_id: str,
    *,
    get_client_vertical_key: Callable[[str], str],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> bool:
    try:
        return get_client_vertical_key(site_id) == "ecommerce"
    except recoverable_errors as exc:
        logger.warning("PIPELINE | vertical lookup failed for %s: %s", site_id, exc)
        return False


def cart_context_for_site(
    site_id: str,
    ecommerce_runtime: bool,
    *,
    get_cart_items: Callable[[str], list[dict]],
    format_cart_for_prompt: Callable[[list[dict]], str],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> str:
    if not ecommerce_runtime:
        return NON_ECOMMERCE_CART_CONTEXT
    try:
        return format_cart_for_prompt(get_cart_items(site_id))
    except recoverable_errors as exc:
        logger.warning("PIPELINE | cart context unavailable for %s: %s", site_id, exc)
        return "The cart is unavailable."


def blocked_text_for_site(ecommerce_runtime: bool) -> str:
    return ECOMMERCE_BLOCKED_RESPONSE if ecommerce_runtime else GENERIC_BLOCKED_RESPONSE
