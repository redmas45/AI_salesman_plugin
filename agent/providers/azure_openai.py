"""Shared Azure OpenAI client and chat-completion helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from openai import OpenAI, OpenAIError

import config

AZURE_OPENAI_ERRORS = (OpenAIError, RuntimeError, TypeError, ValueError)
AZURE_OPENAI_HOST_SUFFIXES = (".openai.azure.com", ".services.ai.azure.com")
AZURE_OPENAI_V1_PATH = "/openai/v1/"
AZURE_OPENAI_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh"})

_client: OpenAI | None = None


def azure_openai_is_configured() -> bool:
    """Return whether the Azure runtime has the minimum chat configuration."""
    return bool(
        config.AZURE_OPENAI_API_KEY
        and config.AZURE_OPENAI_BASE_URL
        and config.AZURE_OPENAI_CHAT_DEPLOYMENT
    )


def get_azure_openai_client() -> OpenAI:
    """Return the process-wide Azure OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=_required_setting("AZURE_OPENAI_API_KEY", config.AZURE_OPENAI_API_KEY),
            base_url=validate_azure_openai_base_url(config.AZURE_OPENAI_BASE_URL),
            timeout=config.AZURE_OPENAI_TIMEOUT_SECONDS,
        )
    return _client


def create_chat_completion(
    messages: list[dict[str, Any]],
    *,
    max_completion_tokens: int,
    json_response: bool = False,
) -> str:
    """Run one GPT-5-compatible Azure chat completion and return its text."""
    request: dict[str, Any] = {
        "model": _required_setting(
            "AZURE_OPENAI_CHAT_DEPLOYMENT",
            config.AZURE_OPENAI_CHAT_DEPLOYMENT,
        ),
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
        "reasoning_effort": validate_reasoning_effort(config.AZURE_OPENAI_REASONING_EFFORT),
    }
    if json_response:
        request["response_format"] = {"type": "json_object"}
    completion = get_azure_openai_client().chat.completions.create(**request)
    return completion.choices[0].message.content or ""


def reset_azure_openai_client() -> None:
    """Clear the cached client after runtime settings change or in tests."""
    global _client
    _client = None


def validate_azure_openai_base_url(value: str) -> str:
    base_url = _required_setting("AZURE_OPENAI_BASE_URL", value).rstrip("/") + "/"
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError("AZURE_OPENAI_BASE_URL must be an HTTPS URL.")
    if not parsed.hostname.endswith(AZURE_OPENAI_HOST_SUFFIXES):
        raise RuntimeError("AZURE_OPENAI_BASE_URL must use an Azure OpenAI hostname.")
    if parsed.path != AZURE_OPENAI_V1_PATH:
        raise RuntimeError("AZURE_OPENAI_BASE_URL must end with /openai/v1/.")
    if parsed.query or parsed.fragment:
        raise RuntimeError("AZURE_OPENAI_BASE_URL cannot include a query or fragment.")
    return base_url


def validate_reasoning_effort(value: str) -> str:
    """Return a supported GPT-5 reasoning effort value."""
    reasoning_effort = str(value or "").strip().lower()
    if reasoning_effort not in AZURE_OPENAI_REASONING_EFFORTS:
        allowed = ", ".join(sorted(AZURE_OPENAI_REASONING_EFFORTS))
        raise RuntimeError(f"AZURE_OPENAI_REASONING_EFFORT must be one of: {allowed}.")
    return reasoning_effort


def _required_setting(name: str, value: str) -> str:
    clean_value = str(value or "").strip()
    if not clean_value:
        raise RuntimeError(f"{name} is not configured.")
    return clean_value
