"""Azure Speech text-to-speech integration returning WAV audio."""

import base64
import io
import logging
import re
import wave
from typing import Any
from xml.sax.saxutils import escape, quoteattr

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

import config

logger = logging.getLogger(__name__)
AZURE_SPEECH_TTS_PATH = "/tts/cognitiveservices/v1"
AZURE_SPEECH_OUTPUT_FORMAT = "riff-24khz-16bit-mono-pcm"
TTS_TRANSIENT_ERRORS = (httpx.TimeoutException, httpx.TransportError)
TTS_PROVIDER_ERRORS = (httpx.HTTPError, RuntimeError, TypeError, ValueError)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception_type(TTS_TRANSIENT_ERRORS),
    reraise=True,
)
def _call_tts(text: str) -> bytes:
    response = httpx.post(
        _speech_url(AZURE_SPEECH_TTS_PATH),
        headers={
            "Ocp-Apim-Subscription-Key": _speech_key(),
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": AZURE_SPEECH_OUTPUT_FORMAT,
            "User-Agent": "AI-Hub-Maya",
        },
        content=_ssml(text).encode("utf-8"),
        timeout=config.AZURE_SPEECH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.content


def _synthesize_single(text: str) -> bytes:
    try:
        audio_bytes = _call_tts(text)
        logger.info(
            "TTS | Azure Speech voice=%s bytes=%d chars=%d",
            config.AZURE_SPEECH_TTS_VOICE,
            len(audio_bytes),
            len(text),
        )
        return audio_bytes
    except TTS_PROVIDER_ERRORS as exc:
        logger.error("TTS | synthesis failed: %s", exc)
        from agent.providers.provider_status import record_provider_failure

        record_provider_failure("azure_openai", exc)
        raise RuntimeError(f"Text-to-speech failed: {exc}") from exc


def synthesize(text: str) -> bytes:
    """Convert text to speech, chunking long responses into one WAV payload."""
    clean_text = _clean_tts_text(text)
    if not clean_text:
        return b""
    clean_text = _limit_tts_text(clean_text)
    chunk_limit = _safe_int(config.TTS_CHUNK_CHARS, 1200, minimum=300, maximum=4000)
    audio_chunks = _synthesize_chunks(_split_text_for_tts(clean_text, chunk_limit))
    audio_bytes = _join_audio_chunks(audio_chunks)
    logger.info("TTS | synthesized %d bytes for %d chars", len(audio_bytes), len(clean_text))
    return audio_bytes


def verify_runtime() -> None:
    """Verify that Azure Speech accepts a minimal synthesis request."""
    _call_tts("Maya audio check.")


def _limit_tts_text(text: str) -> str:
    max_chars = _safe_int(config.TTS_MAX_INPUT_CHARS, 12000, minimum=2000, maximum=50000)
    if len(text) <= max_chars:
        return text
    truncated = _truncate_at_word(text, max_chars - 3) + "..."
    logger.warning("TTS | input truncated to %d chars before chunking", len(truncated))
    return truncated


def _synthesize_chunks(chunks: list[str]) -> list[bytes]:
    audio_chunks: list[bytes] = []
    for index, chunk in enumerate(chunks, start=1):
        try:
            audio_chunks.append(_synthesize_single(chunk))
        except RuntimeError:
            if not audio_chunks:
                raise
            logger.exception("TTS | chunk %d/%d failed; returning partial audio", index, len(chunks))
            break
    return audio_chunks


def _ssml(text: str) -> str:
    voice = str(config.AZURE_SPEECH_TTS_VOICE or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9:-]+", voice):
        raise RuntimeError("AZURE_SPEECH_TTS_VOICE is invalid.")
    locale = "-".join(voice.split("-")[:2]) or "en-IN"
    speech = escape(text)
    style = str(config.AZURE_SPEECH_TTS_STYLE or "").strip()
    if style:
        if not re.fullmatch(r"[A-Za-z0-9-]+", style):
            raise RuntimeError("AZURE_SPEECH_TTS_STYLE is invalid.")
        speech = f"<mstts:express-as style={quoteattr(style)}>{speech}</mstts:express-as>"
    return (
        f'<speak version="1.0" xml:lang={quoteattr(locale)} '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts">'
        f'<voice name={quoteattr(voice)}>{speech}</voice></speak>'
    )


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


def _clean_tts_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _split_text_for_tts(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_sentence(sentence, limit))
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


def _split_long_sentence(sentence: str, limit: int) -> list[str]:
    chunks: list[str] = []
    current_words: list[str] = []
    current_len = 0
    for word in sentence.split():
        next_len = current_len + len(word) + (1 if current_words else 0)
        if current_words and next_len > limit:
            chunks.append(" ".join(current_words))
            current_words = [word]
            current_len = len(word)
        else:
            current_words.append(word)
            current_len = next_len
    if current_words:
        chunks.append(" ".join(current_words))
    return chunks


def _join_audio_chunks(chunks: list[bytes]) -> bytes:
    clean_chunks = [chunk for chunk in chunks if chunk]
    if not clean_chunks:
        return b""
    if len(clean_chunks) == 1:
        return clean_chunks[0]
    wav_bytes = _join_wav_chunks(clean_chunks)
    if wav_bytes:
        return wav_bytes
    logger.warning("TTS | audio chunks were not mergeable WAV; concatenating raw chunks")
    return b"".join(clean_chunks)


def _join_wav_chunks(chunks: list[bytes]) -> bytes:
    params = None
    frames: list[bytes] = []
    try:
        for chunk in chunks:
            with wave.open(io.BytesIO(chunk), "rb") as reader:
                chunk_params = reader.getparams()
                comparable = (
                    chunk_params.nchannels,
                    chunk_params.sampwidth,
                    chunk_params.framerate,
                    chunk_params.comptype,
                    chunk_params.compname,
                )
                if params is None:
                    params = comparable
                elif comparable != params:
                    return b""
                frames.append(reader.readframes(chunk_params.nframes))
    except (wave.Error, EOFError):
        return b""
    if params is None:
        return b""
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(params[0])
        writer.setsampwidth(params[1])
        writer.setframerate(params[2])
        writer.writeframes(b"".join(frames))
    return output.getvalue()


def _safe_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def _truncate_at_word(text: str, limit: int) -> str:
    truncated = text[:limit].rsplit(" ", 1)[0].strip()
    return truncated or text[:limit].strip()


def synthesize_b64(text: str) -> str:
    """Convert text to speech and return base64-encoded WAV."""
    return base64.b64encode(synthesize(text)).decode("utf-8")
