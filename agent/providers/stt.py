"""Azure OpenAI speech-to-text integration."""

import io
import logging
from pathlib import Path
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAIError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import config
from agent.providers.azure_openai import get_azure_openai_client

logger = logging.getLogger(__name__)
STT_TRANSIENT_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
STT_PROVIDER_ERRORS = (OpenAIError, RuntimeError, TypeError, ValueError)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception_type(STT_TRANSIENT_ERRORS),
    reraise=True,
)
def _call_stt(audio_file: tuple, language: str) -> str:
    request = {
        "model": config.AZURE_OPENAI_STT_DEPLOYMENT,
        "file": audio_file,
        "response_format": "text",
        "temperature": 0.0,
        "prompt": "The user is talking to an AI shopping assistant. Please transcribe their speech.",
    }
    if language:
        request["language"] = language

    response = get_azure_openai_client().audio.transcriptions.create(**request)
    if isinstance(response, str):
        return response.strip()
    return (getattr(response, "text", "") or "").strip()


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Transcribe audio bytes using the configured Azure OpenAI deployment.

    Args:
        audio_bytes: Raw audio data (WAV, MP3, WebM, OGG, M4A, FLAC).
        filename: Hint for the file extension so Azure selects the right decoder.

    Returns:
        Transcript string (stripped of leading/trailing whitespace).

    Raises:
        RuntimeError: On API failure.
    """
    try:
        transcript = _call_stt(_audio_file(audio_bytes, filename), config.STT_LANGUAGE)
        
        # Speech models can hallucinate these phrases on very short or silent audio.
        hallucinations = ["thank you.", "thank you", "thanks for watching.", "thanks for watching", "you"]
        if transcript.lower() in hallucinations:
            logger.info("STT | filtered hallucination: %s", transcript)
            return ""

        logger.info(
            "STT | Azure deployment=%s length=%d",
            config.AZURE_OPENAI_STT_DEPLOYMENT,
            len(transcript),
        )
        return transcript

    except STT_PROVIDER_ERRORS as exc:
        logger.exception("STT | transcription failed")
        from agent.providers.provider_status import record_provider_failure

        record_provider_failure("azure_openai", exc)
        if "deploymentnotfound" in str(exc).lower() or "404" in str(exc).lower():
            raise RuntimeError("Voice transcription is unavailable. Please try text chat.") from exc
        raise RuntimeError("I didn't catch that. Please try again.") from exc


def verify_runtime(audio_bytes: bytes) -> None:
    """Verify that the configured STT deployment accepts a valid audio request."""
    _call_stt(_audio_file(audio_bytes, "runtime-check.wav"), config.STT_LANGUAGE)


def _audio_file(audio_bytes: bytes, filename: str) -> tuple:
    return (filename, io.BytesIO(audio_bytes), _mime_type(filename))


def _mime_type(filename: str) -> str:
    """Return MIME type based on file extension."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".mp4": "audio/mp4",
    }
    return mapping.get(ext, "audio/wav")

