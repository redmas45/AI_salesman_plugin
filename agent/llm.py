"""
LLM client using OpenAI chat completions.
Sends the assembled prompt and returns a parsed structured response.
Supports multi-turn conversation history.
"""

import json
import logging
import re
from typing import Any

from openai import OpenAI

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import config
from agent.prompt import build_system_prompt, format_products_for_prompt

logger = logging.getLogger(__name__)

# --- ACTIVE CLIENT ---
_openai_client = None


def _get_client():
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
    "ui_actions": [],
}


# LLM call with retry

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _call_llm(system_prompt: str, messages: list[dict]) -> str:

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
    last_error = None

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
        except Exception as exc:
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

    Returns:
        Parsed dict with keys: response_text, intent, confidence, ui_actions.
    """
    product_context = format_products_for_prompt(retrieved_products, price_constraints)
    system_prompt = build_system_prompt(site_id, product_context, cart_context, profile_context)

    logger.info(
        "LLM | model=%s | user=%r | products=%d | history=%d",
        config.LLM_MODEL,
        user_message[:80],
        len(retrieved_products),
        len(conversation_history) if conversation_history else 0,
    )

    # Build messages array with history + current user message
    messages: list[dict] = []

    if conversation_history:
        # Keep last N turns to avoid token overflow (each turn = 2 messages)
        max_history_turns = 6
        history_to_use = _sanitize_history(conversation_history)[
            -(max_history_turns * 2) :
        ]
        messages.extend(history_to_use)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    try:
        raw = _call_llm(system_prompt, messages)
        logger.debug("LLM | raw response: %s", raw[:300])
        result = _parse_response(raw)
        logger.info(
            "LLM | intent=%s confidence=%.2f actions=%d",
            result.get("intent"),
            result.get("confidence", 0),
            len(result.get("ui_actions", [])),
        )
        return result

    except Exception as exc:
        logger.error("LLM | Failed after retries: %s", exc)
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
            "ui_actions": data.get("ui_actions", DEFAULT_RESPONSE["ui_actions"])
        }
    except json.JSONDecodeError as exc:
        logger.error("LLM | Failed to parse JSON: %s", exc)
        return DEFAULT_RESPONSE.copy()

def _sanitize_history(history: list[dict]) -> list[dict]:
    """Ensure history messages only have allowed keys."""
    sanitized = []
    for msg in history:
        sanitized.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    return sanitized
