"""Azure Speech fast-transcription integration."""

import json
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

import config

logger = logging.getLogger(__name__)
AZURE_SPEECH_TRANSCRIBE_PATH = (
    "/speechtotext/transcriptions:transcribe?api-version=2025-10-15"
)
STT_TRANSIENT_ERRORS = (httpx.TimeoutException, httpx.TransportError)
STT_PROVIDER_ERRORS = (httpx.HTTPError, RuntimeError, TypeError, ValueError)
STT_HALLUCINATIONS = frozenset(
    {"thank you.", "thank you", "thanks for watching.", "thanks for watching", "you"}
)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception_type(STT_TRANSIENT_ERRORS),
    reraise=True,
)
def _call_stt(audio_file: tuple[str, bytes, str], language: str) -> str:
    response = httpx.post(
        _speech_url(AZURE_SPEECH_TRANSCRIBE_PATH),
        headers={"Ocp-Apim-Subscription-Key": _speech_key()},
        data={"definition": json.dumps({"locales": [_speech_locale(language)]})},
        files={"audio": audio_file},
        timeout=config.AZURE_SPEECH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return _transcript_from_response(response.json())


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Transcribe supported audio bytes with Azure Speech."""
    if not audio_bytes:
        return ""
    try:
        transcript = _call_stt(_audio_file(audio_bytes, filename), config.STT_LANGUAGE)
        if transcript.lower() in STT_HALLUCINATIONS:
            logger.info("STT | filtered hallucination: %s", transcript)
            return ""
        logger.info("STT | Azure Speech locale=%s length=%d", _speech_locale(config.STT_LANGUAGE), len(transcript))
        return transcript
    except STT_PROVIDER_ERRORS as exc:
        logger.exception("STT | transcription failed")
        from agent.providers.provider_status import record_provider_failure

        record_provider_failure("azure_openai", exc)
        if _configuration_error(exc):
            raise RuntimeError("Voice transcription is unavailable. Please try text chat.") from exc
        raise RuntimeError("I didn't catch that. Please try again.") from exc


def verify_runtime(audio_bytes: bytes) -> None:
    """Verify that Azure Speech accepts a valid audio request."""
    _call_stt(_audio_file(audio_bytes, "runtime-check.wav"), config.STT_LANGUAGE)


def _audio_file(audio_bytes: bytes, filename: str) -> tuple[str, bytes, str]:
    return (filename, audio_bytes, _mime_type(filename))


def _mime_type(filename: str) -> str:
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


def _speech_url(path: str) -> str:
    endpoint = str(config.AZURE_SPEECH_ENDPOINT or "").strip().rstrip("/")
    if not endpoint.startswith("https://"):
        raise RuntimeError("AZURE_SPEECH_ENDPOINT must be a configured HTTPS URL.")
    return f"{endpoint}{path}"


def _speech_key() -> str:
    key = str(config.AZURE_SPEECH_KEY or "").strip()
    if not key:
        raise RuntimeError("AZURE_SPEECH_KEY is not configured.")
    return key


def _speech_locale(language: str) -> str:
    locale = str(language or "").strip()
    return "en-IN" if locale.lower() in {"", "en"} else locale


def _transcript_from_response(payload: object) -> str:
    if not isinstance(payload, dict):
        raise RuntimeError("Azure Speech returned an invalid transcription response.")
    phrases = payload.get("combinedPhrases", [])
    if not isinstance(phrases, list):
        raise RuntimeError("Azure Speech returned an invalid transcription response.")
    return " ".join(
        str(phrase.get("text") or "").strip()
        for phrase in phrases
        if isinstance(phrase, dict) and phrase.get("text")
    ).strip()


def _configuration_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(code in text for code in ("401", "403", "404", "not configured"))
