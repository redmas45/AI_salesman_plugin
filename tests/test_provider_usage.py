from datetime import datetime, timedelta, timezone

from agent import llm
from agent import provider_status


def test_llm_quota_error_returns_customer_safe_provider_unavailable(monkeypatch):
    recorded = {}

    class QuotaError(RuntimeError):
        code = "insufficient_quota"

    monkeypatch.setattr(llm, "_call_llm", lambda *args, **kwargs: (_ for _ in ()).throw(QuotaError("quota exceeded")))
    monkeypatch.setattr(llm, "_runtime_vertical_key", lambda site_id: "ecommerce")
    monkeypatch.setattr(
        llm,
        "record_provider_failure",
        lambda provider, exc, category: recorded.update(
            {"provider": provider, "category": category, "message": str(exc)}
        ),
    )

    response = llm.generate_response(
        site_id="site_1",
        user_message="show phones",
        retrieved_products=[],
    )

    assert response["intent"] == "llm_quota_exhausted"
    assert "Azure" not in response["response_text"]
    assert recorded["provider"] == "azure_openai"
    assert recorded["category"] == "quota_exhausted"


def test_llm_success_records_azure_provider_recovery(monkeypatch):
    recorded = {}
    monkeypatch.setattr(
        llm,
        "_call_llm",
        lambda *args, **kwargs: '{"response_text":"Sure.","intent":"product_search","confidence":0.9,"ui_actions":[]}',
    )
    monkeypatch.setattr(llm, "_runtime_vertical_key", lambda site_id: "ecommerce")
    monkeypatch.setattr(
        llm,
        "record_provider_success",
        lambda provider: recorded.update({"provider": provider}),
    )

    response = llm.generate_response(
        site_id="site_1",
        user_message="show phones",
        retrieved_products=[],
    )

    assert response["intent"] == "product_search"
    assert recorded == {"provider": "azure_openai"}


def test_provider_usage_status_reports_azure_deployments(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(provider_status, "azure_openai_is_configured", lambda: True)
    monkeypatch.setattr(
        provider_status,
        "_recent_provider_events",
        lambda limit=provider_status.RECENT_EVENT_LIMIT: [
            {
                "provider": "azure_openai",
                "category": "ok",
                "message": "verified",
                "occurred_at": now,
            }
        ],
    )
    monkeypatch.setattr(
        provider_status,
        "_usage_summary",
        lambda: {
            "tokens_estimated": 120,
            "total_turns": 4,
            "turns_today": 2,
            "avg_latency_ms": 1250,
        },
    )
    monkeypatch.setattr(provider_status.config, "AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(provider_status.config, "AZURE_OPENAI_CHAT_DEPLOYMENT", "chat")
    monkeypatch.setattr(provider_status.config, "AZURE_OPENAI_STT_DEPLOYMENT", "stt")
    monkeypatch.setattr(provider_status.config, "AZURE_OPENAI_TTS_DEPLOYMENT", "tts")

    status = provider_status.provider_usage_status()

    assert status["status"] == "ok"
    assert status["provider"] == "azure_openai"
    assert status["llm_model"] == "chat"
    assert status["stt_model"] == "stt"
    assert status["tts_model"] == "tts"
    assert status["local_tokens"]["estimated_total"] == 120
    assert status["billing"]["status"] == "azure_portal"


def test_manual_azure_runtime_check_records_success(monkeypatch):
    events = []
    monkeypatch.setattr(provider_status, "azure_openai_is_configured", lambda: True)
    monkeypatch.setattr(provider_status, "create_chat_completion", lambda *args, **kwargs: '{"status":"ok"}')
    monkeypatch.setattr(
        provider_status,
        "_record_provider_event",
        lambda provider, category, message: events.insert(
            0,
            {
                "provider": provider,
                "category": category,
                "message": message,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        ),
    )
    monkeypatch.setattr(provider_status, "_recent_provider_events", lambda limit=20: events[:limit])
    monkeypatch.setattr(provider_status, "_usage_summary", _empty_usage)
    monkeypatch.setattr(provider_status.config, "AZURE_OPENAI_API_KEY", "test-key")

    status = provider_status.check_azure_openai_runtime()

    assert status["status"] == "ok"
    assert events[0]["provider"] == "azure_openai"
    assert events[0]["category"] == "ok"


def test_manual_azure_runtime_check_categorizes_quota(monkeypatch):
    events = []
    monkeypatch.setattr(provider_status, "azure_openai_is_configured", lambda: True)
    monkeypatch.setattr(
        provider_status,
        "create_chat_completion",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("429 insufficient_quota")),
    )
    monkeypatch.setattr(
        provider_status,
        "_record_provider_event",
        lambda provider, category, message: events.insert(
            0,
            {
                "provider": provider,
                "category": category,
                "message": message,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        ),
    )
    monkeypatch.setattr(provider_status, "_recent_provider_events", lambda limit=20: events[:limit])
    monkeypatch.setattr(provider_status, "_usage_summary", _empty_usage)
    monkeypatch.setattr(provider_status.config, "AZURE_OPENAI_API_KEY", "test-key")

    status = provider_status.check_azure_openai_runtime()

    assert status["status"] == "quota_exhausted"
    assert events[0]["category"] == "quota_exhausted"


def test_stale_provider_success_requires_verification(monkeypatch):
    monkeypatch.setattr(provider_status, "azure_openai_is_configured", lambda: True)
    stale = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    status = provider_status._provider_status(
        [
            {
                "provider": "azure_openai",
                "category": "ok",
                "message": "old success",
                "occurred_at": stale,
            }
        ]
    )

    assert status == "unverified"


def test_latest_provider_error_is_not_ready(monkeypatch):
    monkeypatch.setattr(provider_status, "azure_openai_is_configured", lambda: True)

    status = provider_status._provider_status(
        [
            {
                "provider": "azure_openai",
                "category": "auth_error",
                "message": "invalid key",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    assert status == "error"


def _empty_usage():
    return {
        "tokens_estimated": 0,
        "total_turns": 0,
        "turns_today": 0,
        "avg_latency_ms": 0,
    }
