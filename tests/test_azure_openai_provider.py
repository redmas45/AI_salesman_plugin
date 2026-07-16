import pytest

from agent.providers import azure_openai


def test_azure_client_uses_validated_v1_configuration(monkeypatch):
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(azure_openai.config, "AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        azure_openai.config,
        "AZURE_OPENAI_BASE_URL",
        "https://example.openai.azure.com/openai/v1/",
    )
    monkeypatch.setattr(azure_openai.config, "AZURE_OPENAI_TIMEOUT_SECONDS", 25.0)
    monkeypatch.setattr(azure_openai, "OpenAI", fake_openai)
    azure_openai.reset_azure_openai_client()

    azure_openai.get_azure_openai_client()

    assert captured == {
        "api_key": "test-key",
        "base_url": "https://example.openai.azure.com/openai/v1/",
        "timeout": 25.0,
    }
    azure_openai.reset_azure_openai_client()


@pytest.mark.parametrize(
    "base_url",
    [
        "http://example.openai.azure.com/openai/v1/",
        "https://example.com/openai/v1/",
        "https://example.openai.azure.com/openai/v1/chat/completions",
    ],
)
def test_azure_client_rejects_invalid_base_url(monkeypatch, base_url):
    monkeypatch.setattr(azure_openai.config, "AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(azure_openai.config, "AZURE_OPENAI_BASE_URL", base_url)
    azure_openai.reset_azure_openai_client()

    with pytest.raises(RuntimeError):
        azure_openai.get_azure_openai_client()


def test_chat_completion_uses_gpt5_parameters(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = type("Message", (), {"content": '{"status":"ok"}'})()
            return type("Completion", (), {"choices": [type("Choice", (), {"message": message})()]})()

    fake_client = type(
        "FakeClient",
        (),
        {"chat": type("Chat", (), {"completions": FakeCompletions()})()},
    )()
    monkeypatch.setattr(azure_openai.config, "AZURE_OPENAI_CHAT_DEPLOYMENT", "chat-deployment")
    monkeypatch.setattr(azure_openai.config, "AZURE_OPENAI_REASONING_EFFORT", "none")
    monkeypatch.setattr(azure_openai, "get_azure_openai_client", lambda: fake_client)

    content = azure_openai.create_chat_completion(
        [{"role": "user", "content": "hello"}],
        max_completion_tokens=64,
        json_response=True,
    )

    assert content == '{"status":"ok"}'
    assert captured["model"] == "chat-deployment"
    assert captured["max_completion_tokens"] == 64
    assert captured["reasoning_effort"] == "none"
    assert captured["response_format"] == {"type": "json_object"}
    assert "temperature" not in captured
    assert "max_tokens" not in captured
