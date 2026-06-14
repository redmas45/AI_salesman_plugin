"""
Text-to-Speech module using OpenAI TTS API.
Returns WAV audio bytes that can be base64-encoded and sent to the frontend.
"""

import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from openai import OpenAI

import config

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
_groq_client: Any | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def _get_groq_client() -> Any:
    global _groq_client
    if _groq_client is None:
        if not config.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set.")
        from groq import Groq

        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _call_tts(text: str) -> bytes:
    if config.TTS_MODEL == "gTTS":
        import io

        from gtts import gTTS

        tts = gTTS(text=text, lang="en")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()

    models_to_try = [config.TTS_MODEL]
    if config.TTS_MODEL != "tts-1":
        models_to_try.append("tts-1")

    last_exc = None
    for model in models_to_try:
        try:
            response = _get_client().audio.speech.create(
                model=model,
                voice=config.TTS_VOICE,
                input=text,
                response_format="wav",
            )
            return response.content
        except Exception as exc:
            last_exc = exc
            logger.warning("TTS failed for model %s: %s", model, exc)
            if model == config.TTS_MODEL and len(models_to_try) > 1:
                config.TTS_MODEL = "tts-1"

    if last_exc:
        raise last_exc


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.25, min=0.25, max=1),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _call_groq_tts(text: str) -> bytes:
    response = _get_groq_client().audio.speech.create(
        model=config.GROQ_TTS_MODEL,
        voice=config.GROQ_TTS_VOICE,
        input=text,
        response_format=config.GROQ_TTS_RESPONSE_FORMAT,
    )
    return _binary_response_to_bytes(response)


def _binary_response_to_bytes(response: Any) -> bytes:
    content = getattr(response, "content", None)
    if isinstance(content, bytes):
        return content

    read = getattr(response, "read", None)
    if callable(read):
        data = read()
        if isinstance(data, bytes):
            return data

    write_to_file = getattr(response, "write_to_file", None)
    if callable(write_to_file):
        suffix = f".{config.GROQ_TTS_RESPONSE_FORMAT or 'wav'}"
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                temp_path = handle.name
            write_to_file(temp_path)
            return Path(temp_path).read_bytes()
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    raise RuntimeError("Groq TTS response did not contain audio bytes.")


def synthesize(text: str) -> bytes:
    """
    Convert text to speech using OpenAI TTS.

    This API path returns WAV only. If TTS fails, the orchestrator degrades to
    text-only instead of returning audio bytes with the wrong MIME type.
    """
    if len(text) > 4000:
        text = text[:3997] + "..."

    try:
        if config.TTS_PROVIDER == "groq":
            try:
                audio_bytes = _call_groq_tts(text)
                logger.info(
                    "TTS | Groq model=%s voice=%s bytes=%d chars=%d",
                    config.GROQ_TTS_MODEL,
                    config.GROQ_TTS_VOICE,
                    len(audio_bytes),
                    len(text),
                )
            except Exception:
                if not config.GROQ_FALLBACK_TO_OPENAI:
                    raise
                logger.exception("TTS | Groq failed; falling back to OpenAI")
                audio_bytes = _call_tts(text)
        else:
            audio_bytes = _call_tts(text)
    except Exception as exc:
        logger.error("TTS | synthesis failed: %s", exc)
        raise RuntimeError(f"Text-to-speech failed: {exc}") from exc

    logger.info("TTS | synthesized %d bytes for %d chars", len(audio_bytes), len(text))
    return audio_bytes


def synthesize_b64(text: str) -> str:
    """
    Convert text to speech and return base64-encoded WAV string.
    Convenient for embedding directly in JSON API responses.
    """
    audio_bytes = synthesize(text)
    return base64.b64encode(audio_bytes).decode("utf-8")

