"""Contracts for privacy-safe frontend/backend voice diagnostics."""

from __future__ import annotations

from api.routes.client_widgets.client_models import WidgetRuntimeEventRequest
from api.routes.client_widgets.client_widget_events import process_runtime_event
from db.analytics import metrics
from db.runtime.runtime_diagnostics import validated_runtime_event


class FakeRuntimeEventStore:
    def __init__(self) -> None:
        self.event: tuple[str, dict] | None = None

    def get_client_detail(self, site_id: str) -> dict:
        return {"site_id": site_id, "allowed_origin": "https://shop.example.test"}

    def record_runtime_event(self, site_id: str, event: dict) -> None:
        self.event = (site_id, event)


def test_runtime_event_ingest_binds_origin_and_drops_sensitive_metadata() -> None:
    store = FakeRuntimeEventStore()
    request = WidgetRuntimeEventRequest(
        site_id="site_1",
        origin="https://shop.example.test",
        session_id="session-1",
        event_type="voice_turn_failed",
        severity="error",
        status="failed",
        metadata={
            "transport": "http",
            "http_status": 502,
            "transcript": "private customer words",
            "exception_message": "database host and secret",
            "nested": {"secret": "no"},
        },
    )

    response = process_runtime_event(
        request,
        client_store=store,
        safe_site_id=lambda value: value,
        safe_script_base_url=lambda value: value.rstrip("/"),
        safe_client_detail=store.get_client_detail,
    )

    assert response == {"site_id": "site_1", "status": "ok"}
    assert store.event is not None
    _, event = store.event
    assert event["metadata"] == {"transport": "http", "http_status": 502}


def test_runtime_event_validator_allowlists_source_status_and_severity() -> None:
    event = validated_runtime_event(
        {
            "source": "attacker",
            "severity": "critical",
            "status": "destroyed",
            "event_type": "Voice Turn Failed!",
            "metadata": {"category": "network"},
        }
    )
    assert event["source"] == "frontend"
    assert event["severity"] == "info"
    assert event["status"] == "ok"
    assert event["event_type"] == "voice_turn_failed"


def test_conversation_log_keeps_failed_session_without_usage_turn(monkeypatch) -> None:
    runtime_event = {
        "site_id": "site_1",
        "session_id": "failed-session",
        "request_id": "req-1",
        "source": "frontend",
        "component": "voice",
        "stage": "http_response",
        "event_type": "voice_turn_failed",
        "severity": "error",
        "status": "failed",
        "message_code": "provider_unavailable",
        "duration_ms": 1234,
        "metadata": {"http_status": 502},
        "occurred_at": "2026-08-03T10:00:00+00:00",
    }
    monkeypatch.setattr(metrics, "_usage_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(metrics, "_action_events_by_site", lambda _site_ids: {})
    monkeypatch.setattr(metrics, "_safe_runtime_events", lambda *_args: [runtime_event])

    payload = metrics.conversation_log("1d", "site_1")

    session = payload["groups"][0]["sessions"][0]
    assert session["session_id"] == "failed-session"
    assert session["turn_count"] == 0
    assert session["runtime_events"] == [runtime_event]
