import io
import wave

import pytest


def test_azure_stt_uses_configured_speech_resource(monkeypatch):
    import config
    from agent import stt

    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"combinedPhrases": [{"text": "hello from azure"}]}

    def fake_post(url, **kwargs):
        calls.update({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(config, "AZURE_SPEECH_ENDPOINT", "https://speech.example.com")
    monkeypatch.setattr(config, "AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setattr(stt.httpx, "post", fake_post)

    transcript = stt.transcribe(b"fake audio", "audio.webm")

    assert transcript == "hello from azure"
    assert calls["url"].endswith("/speechtotext/transcriptions:transcribe?api-version=2025-10-15")
    assert calls["headers"]["Ocp-Apim-Subscription-Key"] == "speech-key"
    assert calls["files"]["audio"][0] == "audio.webm"


def test_azure_stt_reports_missing_deployment_as_voice_unavailable(monkeypatch):
    from agent import stt
    from agent import provider_status

    monkeypatch.setattr(
        stt,
        "_call_stt",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("404 DeploymentNotFound")),
    )
    monkeypatch.setattr(provider_status, "record_provider_failure", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="Voice transcription is unavailable"):
        stt.transcribe(b"fake audio", "audio.webm")


def test_azure_tts_uses_configured_speech_voice(monkeypatch):
    import config
    from agent import tts

    calls = {}

    class FakeResponse:
        content = b"fake-wav"

        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        calls.update({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(config, "AZURE_SPEECH_ENDPOINT", "https://speech.example.com")
    monkeypatch.setattr(config, "AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setattr(config, "AZURE_SPEECH_TTS_VOICE", "en-IN-NeerjaNeural")
    monkeypatch.setattr(config, "AZURE_SPEECH_TTS_STYLE", "empathetic")
    monkeypatch.setattr(tts.httpx, "post", fake_post)

    audio = tts.synthesize("hello")

    assert audio == b"fake-wav"
    assert calls["url"] == "https://speech.example.com/tts/cognitiveservices/v1"
    assert calls["headers"]["Ocp-Apim-Subscription-Key"] == "speech-key"
    assert b'en-IN-NeerjaNeural' in calls["content"]
    assert b'empathetic' in calls["content"]


def test_tts_splits_long_text_and_merges_wav_chunks(monkeypatch):
    import config
    from agent import tts

    calls = []

    def fake_azure_tts(text: str) -> bytes:
        calls.append(text)
        return _fake_wav_bytes(len(calls))

    monkeypatch.setattr(config, "TTS_CHUNK_CHARS", 300)
    monkeypatch.setattr(config, "TTS_MAX_INPUT_CHARS", 2000)
    monkeypatch.setattr(tts, "_call_tts", fake_azure_tts)

    audio = tts.synthesize("Sentence one has enough words. Sentence two has enough words. " * 20)

    assert len(calls) >= 2
    with wave.open(io.BytesIO(audio), "rb") as reader:
        assert reader.getnchannels() == 1
        assert reader.getframerate() == 8000
        assert reader.getnframes() > 0


def _fake_wav_bytes(multiplier: int) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(8000)
        writer.writeframes((b"\x00\x00" * 80) * multiplier)
    return output.getvalue()
