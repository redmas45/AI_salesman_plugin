"""
LLM client using OpenAI chat completions.
Sends the assembled prompt and returns a parsed structured response.
Supports multi-turn conversation history.
"""

import json
import logging
import re
from typing import Any

from openai import OpenAI, OpenAIError

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import config
from agent.context_budget import build_context_messages
from agent.prompt import build_system_prompt, format_products_for_prompt
from agent.page_context import format_page_context, sanitize_page_context
from agent.prompts.generic import build_generic_system_prompt, format_knowledge_for_prompt
from agent.provider_status import record_provider_failure, record_provider_success
from agent.verticals.registry import DEFAULT_VERTICAL_KEY
from db.clients import get_client_vertical_key

logger = logging.getLogger(__name__)
LLM_RETRY_ERRORS = (OpenAIError, RuntimeError, ValueError, TypeError, KeyError, IndexError)
MAX_HISTORY_TURNS = 6

# --- ACTIVE CLIENT ---
_openai_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _openai_client

    if _openai_client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

    return _openai_client

# Response schema

DEFAULT_RESPONSE: dict[str, Any] = {
    "response_text": "I'm sorry, I couldn't process that request. Please try again.",
    "intent": "unknown",
    "confidence": 0.0,
    "answer_scope": "",
    "ui_actions": [],
}
QUOTA_EXHAUSTED_RESPONSE: dict[str, Any] = {
    "response_text": (
        "Maya is temporarily unavailable because the AI service is out of capacity. "
        "Please try again later."
    ),
    "intent": "llm_quota_exhausted",
    "confidence": 1.0,
    "answer_scope": "unsupported_or_offsite",
    "ui_actions": [],
}


# LLM call with retry

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(LLM_RETRY_ERRORS),
    reraise=True,
)
def _call_llm(system_prompt: str, messages: list[dict[str, Any]]) -> str:

    full_messages = [
        {"role": "system", "content": system_prompt},
        *messages,
    ]

    # ------------------------
    # OpenAI Chat Completions with lightweight model fallback
    # ------------------------
    preferred_models = [config.LLM_MODEL, "gpt-4.1", "gpt-4o"]
    seen = set()
    model_chain = [m for m in preferred_models if m and not (m in seen or seen.add(m))]
    last_error: BaseException | None = None

    for model in model_chain:
        try:
            logger.info("LLM | OpenAI model=%s", model)
            completion = _get_client().chat.completions.create(
                model=model,
                messages=full_messages,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            return completion.choices[0].message.content or ""
        except LLM_RETRY_ERRORS as exc:
            last_error = exc
            logger.warning("LLM model %s failed: %s", model, exc)
            continue

    logger.error("All OpenAI LLM model attempts failed.")
    if last_error:
        raise last_error
    raise RuntimeError("LLM failed for all configured models.")


# Public API

def generate_response(
    site_id: str,
    user_message: str,
    retrieved_products: list[dict],
    conversation_history: list[dict] | None = None,
    price_constraints: dict | None = None,
    cart_context: str = "",
    profile_context: str = "",
    page_context: dict[str, Any] | None = None,
    session_summary: str = "",
) -> dict[str, Any]:
    """
    Generate the next AI response, JSON-formatted, including UI actions.

    Args:
        site_id:                The ID of the tenant website.
        user_message:           Transcript from STT (already sanitised).
        retrieved_products:     Product dicts from RAG retrieval.
        conversation_history:   List of previous turns.
        price_constraints:      Optional price filter dict.
        cart_context:           Formatted string of current cart items.
        profile_context:        Formatted string of user profile data.
        session_summary:        Compact rolling memory for this browser session.

    Returns:
        Parsed dict with keys: response_text, intent, confidence, answer_scope, ui_actions.
    """
    vertical_key = _runtime_vertical_key(site_id)
    safe_page_context = sanitize_page_context(page_context)
    page_context_text = format_page_context(safe_page_context)
    if vertical_key == "ecommerce":
        product_context = format_products_for_prompt(retrieved_products, price_constraints)
        system_prompt = build_system_prompt(
            site_id,
            product_context,
            cart_context,
            profile_context,
            page_context_text,
        )
    else:
        knowledge_context = format_knowledge_for_prompt(retrieved_products)
        system_prompt = build_generic_system_prompt(
            site_id=site_id,
            vertical_key=vertical_key,
            knowledge_context=knowledge_context,
            profile_context=profile_context,
            page_context=page_context_text,
        )

    logger.info(
        "LLM | model=%s | user=%r | products=%d | history=%d",
        config.LLM_MODEL,
        user_message[:80],
        len(retrieved_products),
        len(conversation_history) if conversation_history else 0,
    )

    messages = build_context_messages(
        conversation_history or [],
        session_summary=session_summary,
        max_recent_messages=MAX_HISTORY_TURNS,
    )
    messages.append({"role": "user", "content": user_message})

    try:
        raw = _call_llm(system_prompt, messages)
        logger.debug("LLM | raw response: %s", raw[:300])
        result = _parse_response(raw)
        record_provider_success("openai")
        logger.info(
            "LLM | intent=%s confidence=%.2f actions=%d",
            result.get("intent"),
            result.get("confidence", 0),
            len(result.get("ui_actions", [])),
        )
        return result

    except LLM_RETRY_ERRORS as exc:
        logger.error("LLM | Failed after retries: %s", exc)
        if _is_quota_exhausted_error(exc):
            record_provider_failure("openai", exc, category="quota_exhausted")
            return QUOTA_EXHAUSTED_RESPONSE.copy()
        record_provider_failure("openai", exc, category="error")
        return DEFAULT_RESPONSE.copy()


# Response parsing

def _parse_response(raw: str) -> dict[str, Any]:
    """
    Parse the LLM's JSON response into a clean dict.
    Handles common LLM quirks like wrapping in markdown code blocks.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return {
            "response_text": data.get("response_text", DEFAULT_RESPONSE["response_text"]),
            "intent": data.get("intent", DEFAULT_RESPONSE["intent"]),
            "confidence": data.get("confidence", DEFAULT_RESPONSE["confidence"]),
            "answer_scope": data.get("answer_scope", DEFAULT_RESPONSE["answer_scope"]),
            "ui_actions": data.get("ui_actions", DEFAULT_RESPONSE["ui_actions"])
        }
    except json.JSONDecodeError as exc:
        logger.error("LLM | Failed to parse JSON: %s", exc)
        return DEFAULT_RESPONSE.copy()


def _is_quota_exhausted_error(exc: BaseException) -> bool:
    """Detect provider quota/billing exhaustion without depending on one SDK shape."""
    fields = [
        getattr(exc, "code", ""),
        getattr(exc, "type", ""),
        getattr(exc, "status_code", ""),
        getattr(exc, "body", ""),
        str(exc),
    ]
    text = " ".join(str(field or "") for field in fields).lower()
    return bool(
        "insufficient_quota" in text
        or "quota" in text and "exceeded" in text
        or "billing" in text and ("quota" in text or "plan" in text)
    )

def _sanitize_history(history: list[dict]) -> list[dict[str, str]]:
    """Ensure history messages only have allowed keys."""
    sanitized: list[dict[str, str]] = []
    for msg in history:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "user")
        content = str(msg.get("content") or "")
        if role not in {"user", "assistant"} or not content:
            continue
        sanitized.append({"role": role, "content": content[: config.MAX_TRANSCRIPT_CHARS]})
    return sanitized


def _runtime_vertical_key(site_id: str) -> str:
    try:
        return get_client_vertical_key(site_id)
    except (LookupError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        logger.warning("LLM | vertical lookup failed for %s: %s", site_id, exc)
        return DEFAULT_VERTICAL_KEY
