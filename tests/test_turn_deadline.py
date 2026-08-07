"""A single assistant turn is bounded: an absurd or degenerate request can never
leave the widget stuck on "Analyzing" forever.

Reported (2026-08-07): "Do you sell fresh bananas and a live elephant?" stayed in
Analyzing for over a minute and then returned to Ready with no answer rendered.
The pipeline had no turn-level deadline, and nested SDK+tenacity retries over a
stalled completion compounded well past a minute.

These drive the real `/v1/shop` endpoint with its collaborators stubbed, so the
deadline and the graceful fallback are exercised, not described.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from api.runtime import main_app, runtime_payloads


@pytest.fixture
def client(monkeypatch) -> TestClient:
    # Neutralise the auth/quota/telemetry collaborators so the test exercises the
    # turn lifecycle itself, not the database or origin policy.
    monkeypatch.setattr(main_app.runtime_payloads, "runtime_site_id", lambda site_id, db: site_id)
    monkeypatch.setattr(main_app.runtime_security, "require_runtime_origin", lambda *a, **k: None)
    monkeypatch.setattr(main_app.runtime_payloads, "raise_if_client_disabled", lambda *a, **k: None)
    monkeypatch.setattr(main_app.runtime_payloads, "raise_if_quota_exceeded", lambda *a, **k: None)
    monkeypatch.setattr(main_app, "get_session_summary", lambda site_id, session_id: "")
    monkeypatch.setattr(main_app.admin_db, "record_runtime_event_safely", lambda *a, **k: None)
    monkeypatch.setattr(main_app, "_record_usage_result", lambda **k: None)
    # TestClient without a `with` block does not run the lifespan, so no DB is touched.
    return TestClient(main_app.app)


def test_a_stalled_turn_returns_a_bounded_clarification(client, monkeypatch) -> None:
    # A short deadline plus an orchestrator that overruns it reproduces the hang.
    monkeypatch.setattr(main_app.config, "TURN_DEADLINE_SECONDS", 0.3)

    def _hang(**kwargs):
        time.sleep(5.0)  # still working long after the deadline
        return {"transcript": "hi", "response_text": "Late.", "intent": "x", "confidence": 1.0}

    monkeypatch.setattr(main_app.orchestrator, "run", _hang)

    started = time.monotonic()
    res = client.post("/v1/shop", data={"text": "fresh bananas and a live elephant", "site_id": "s"})
    elapsed = time.monotonic() - started

    assert res.status_code == 200, res.text
    body = res.json()
    # Exactly one useful response, and it is an honest clarification, not the late
    # answer, not an error banner, and not an empty busy state.
    assert body["intent"] == "turn_timeout"
    assert "Late." not in body["response_text"]
    assert body["response_text"].strip()
    assert body["ui_actions"] == []
    assert body["audio_b64"] == ""
    # The endpoint answered near the deadline, not after the 5s orchestrator work.
    assert elapsed < 3.0, elapsed


def test_a_healthy_turn_within_the_deadline_is_untouched(client, monkeypatch) -> None:
    monkeypatch.setattr(main_app.config, "TURN_DEADLINE_SECONDS", 5.0)

    def _quick(**kwargs):
        return {
            "transcript": "show me phones",
            "response_text": "Here are some phones.",
            "intent": "product_search",
            "confidence": 0.9,
            "ui_actions": [],
        }

    monkeypatch.setattr(main_app.orchestrator, "run", _quick)

    res = client.post("/v1/shop", data={"text": "show me phones", "site_id": "s"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["intent"] == "product_search"
    assert body["response_text"] == "Here are some phones."
