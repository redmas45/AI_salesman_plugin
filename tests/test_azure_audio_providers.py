import io
import wave

import pytest


def test_azure_stt_uses_configured_deployment(monkeypatch):
    import config
    from agent import stt

    calls = {}

    class FakeTranscriptions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return "hello from azure"

    fake_client = type("FakeClient", (), {"audio": type("Audio", (), {"transcriptions": FakeTranscriptions()})()})()
    monkeypatch.setattr(config, "AZURE_OPENAI_STT_DEPLOYMENT", "stt-deployment")
    monkeypatch.setattr(stt, "get_azure_openai_client", lambda: fake_client)

    transcript = stt.transcribe(b"fake audio", "audio.webm")

    assert transcript == "hello from azure"
    assert calls["model"] == "stt-deployment"
    assert calls["response_format"] == "text"
    assert calls["file"][0] == "audio.webm"


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


def test_azure_tts_uses_configured_deployment_and_voice(monkeypatch):
    import config
    from agent import tts

    calls = {}

    class FakeSpeech:
        def create(self, **kwargs):
            calls.update(kwargs)
            return type("Response", (), {"content": b"fake-wav"})()

    fake_client = type("FakeClient", (), {"audio": type("Audio", (), {"speech": FakeSpeech()})()})()
    monkeypatch.setattr(config, "AZURE_OPENAI_TTS_DEPLOYMENT", "tts-deployment")
    monkeypatch.setattr(config, "AZURE_OPENAI_TTS_VOICE", "coral")
    monkeypatch.setattr(tts, "get_azure_openai_client", lambda: fake_client)

    audio = tts.synthesize("hello")

    assert audio == b"fake-wav"
    assert calls == {
        "model": "tts-deployment",
        "voice": "coral",
        "input": "hello",
        "response_format": "wav",
    }


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
