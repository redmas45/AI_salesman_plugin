import sys
import io
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_groq_stt_provider_uses_configured_model(monkeypatch):
    import config
    from agent import stt

    calls = {}

    class FakeTranscriptions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return "hello from groq"

    class FakeAudio:
        transcriptions = FakeTranscriptions()

    class FakeClient:
        audio = FakeAudio()

    monkeypatch.setattr(config, "STT_PROVIDER", "groq")
    monkeypatch.setattr(config, "GROQ_STT_MODEL", "whisper-large-v3-turbo")
    monkeypatch.setattr(stt, "_get_groq_client", lambda: FakeClient())

    transcript = stt.transcribe(b"fake audio", "audio.webm")

    assert transcript == "hello from groq"
    assert calls["model"] == "whisper-large-v3-turbo"
    assert calls["response_format"] == "text"
    assert calls["file"][0] == "audio.webm"


def test_groq_tts_provider_uses_configured_model_and_voice(monkeypatch):
    import config
    from agent import tts

    calls = {}

    class FakeSpeech:
        def create(self, **kwargs):
            calls.update(kwargs)

            class Response:
                content = b"fake-wav"

            return Response()

    class FakeAudio:
        speech = FakeSpeech()

    class FakeClient:
        audio = FakeAudio()

    monkeypatch.setattr(config, "TTS_PROVIDER", "groq")
    monkeypatch.setattr(config, "GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english")
    monkeypatch.setattr(config, "GROQ_TTS_VOICE", "troy")
    monkeypatch.setattr(config, "GROQ_TTS_RESPONSE_FORMAT", "wav")
    monkeypatch.setattr(tts, "_get_groq_client", lambda: FakeClient())

    audio = tts.synthesize("hello")

    assert audio == b"fake-wav"
    assert calls == {
        "model": "canopylabs/orpheus-v1-english",
        "voice": "troy",
        "input": "hello",
        "response_format": "wav",
    }


def test_tts_splits_long_text_and_merges_wav_chunks(monkeypatch):
    import config
    from agent import tts

    calls = []

    def fake_groq_tts(text: str) -> bytes:
        calls.append(text)
        return _fake_wav_bytes(len(calls))

    monkeypatch.setattr(config, "TTS_PROVIDER", "groq")
    monkeypatch.setattr(config, "TTS_CHUNK_CHARS", 300)
    monkeypatch.setattr(config, "TTS_MAX_INPUT_CHARS", 2000)
    monkeypatch.setattr(tts, "_call_groq_tts", fake_groq_tts)

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
