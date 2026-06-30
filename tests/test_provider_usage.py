import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import llm
from agent import provider_status


def test_llm_quota_error_returns_customer_safe_provider_unavailable(monkeypatch):
    recorded = {}

    class QuotaError(RuntimeError):
        pass

    monkeypatch.setattr(
        llm,
        "_call_llm",
        lambda *args, **kwargs: (_ for _ in ()).throw(QuotaError("insufficient_quota: billing hard limit exceeded")),
    )
    monkeypatch.setattr(llm, "_runtime_vertical_key", lambda site_id: "ecommerce")
    monkeypatch.setattr(
        llm,
        "record_provider_failure",
        lambda provider, exc, category: recorded.update(
            {"provider": provider, "category": category, "message": str(exc)}
        ),
    )

    response = llm.generate_response(
        "ai_kart",
        "I am looking for a phone.",
        [],
        conversation_history=[],
    )

    assert response["intent"] == "llm_quota_exhausted"
    assert response["ui_actions"] == []
    assert "OpenAI" not in response["response_text"]
    assert recorded["provider"] == "openai"
    assert recorded["category"] == "quota_exhausted"


def test_llm_success_records_provider_recovery(monkeypatch):
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
        "ai_kart",
        "I am looking for a phone.",
        [],
        conversation_history=[],
    )

    assert response["response_text"] == "Sure."
    assert recorded == {"provider": "openai"}


def test_provider_usage_status_reports_quota_event(monkeypatch):
    provider_status._RECENT_EVENTS.clear()
    persisted: list[tuple[str, str, str]] = []

    class FakeConnection:
        rows = [
            {
                "provider": "openai",
                "category": "quota_exhausted",
                "message": "insufficient_quota: plan and billing details",
                "created_at": "2026-06-30 00:00:00+00",
            }
        ]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params=()):
            if str(query).lstrip().upper().startswith("INSERT"):
                persisted.append(tuple(params))
                return self
            return self

        def fetchall(self):
            return list(self.rows)

        def commit(self):
            return None

    monkeypatch.setattr(provider_status, "init_admin_schema", lambda: None)
    monkeypatch.setattr(provider_status, "_connect", lambda: FakeConnection())
    provider_status.record_provider_failure(
        "openai",
        RuntimeError("insufficient_quota: plan and billing details"),
        category="quota_exhausted",
    )

    monkeypatch.setattr(provider_status.config, "OPENAI_API_KEY", "test-runtime-key")
    monkeypatch.setattr(provider_status.config, "OPENAI_ADMIN_KEY", "")
    monkeypatch.setattr(provider_status.config, "OPENAI_MONTHLY_BUDGET_USD", 100.0)
    monkeypatch.setattr(
        provider_status,
        "_usage_summary",
        lambda: {
            "total_turns": 4,
            "turns_today": 2,
            "tokens_estimated": 1234,
            "avg_latency_ms": 500,
        },
    )

    status = provider_status.provider_usage_status()

    assert status["status"] == "quota_exhausted"
    assert status["local_tokens"]["estimated_total"] == 1234
    assert status["openai_costs"]["status"] == "not_configured"
    assert status["budget"]["monthly_budget_usd"] == 100.0
    assert status["recent_events"][0]["category"] == "quota_exhausted"
    assert persisted == [("openai", "quota_exhausted", "insufficient_quota: plan and billing details")]


def test_provider_success_clears_quota_status(monkeypatch):
    provider_status._RECENT_EVENTS.clear()
    persisted: list[tuple[str, str, str]] = []

    class FakeConnection:
        rows = [
            {
                "provider": "openai",
                "category": "quota_exhausted",
                "message": "insufficient_quota",
                "created_at": "2026-06-30 00:00:00+00",
            }
        ]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params=()):
            if str(query).lstrip().upper().startswith("INSERT"):
                persisted.append(tuple(params))
                self.rows.insert(
                    0,
                    {
                        "provider": params[0],
                        "category": params[1],
                        "message": params[2],
                        "created_at": "2026-06-30 00:01:00+00",
                    },
                )
            return self

        def fetchall(self):
            return list(self.rows)

        def commit(self):
            return None

    monkeypatch.setattr(provider_status, "init_admin_schema", lambda: None)
    monkeypatch.setattr(provider_status, "_connect", lambda: FakeConnection())
    monkeypatch.setattr(provider_status.config, "OPENAI_API_KEY", "test-runtime-key")
    monkeypatch.setattr(provider_status.config, "OPENAI_ADMIN_KEY", "")
    monkeypatch.setattr(
        provider_status,
        "_usage_summary",
        lambda: {
            "total_turns": 1,
            "turns_today": 1,
            "tokens_estimated": 50,
            "avg_latency_ms": 100,
        },
    )

    provider_status.record_provider_success("openai")
    status = provider_status.provider_usage_status()

    assert status["status"] == "ok"
    assert status["recent_events"][0]["category"] == "ok"
    assert persisted == [("openai", "ok", "LLM request completed successfully.")]
