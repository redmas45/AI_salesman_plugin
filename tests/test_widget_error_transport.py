"""Regressions for how widget-facing failures reach the browser.

Reported production defect: after recording, the widget shows "Connection issue"
no matter what actually failed.

Two Hub-side causes are pinned here:

1. An unhandled exception propagated past the public-widget CORS middleware, so
   the 500 arrived with no ``Access-Control-Allow-Origin``. The browser blocked
   it and ``fetch`` rejected exactly like an offline network, hiding the real
   status from both the customer and support.
2. The audio turn ran the fully synchronous orchestrator directly on the event
   loop, so one slow turn blocked the worker and later turns died at the reverse
   proxy instead of returning a real status.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

WIDGET_ORIGIN = "https://storefront.example.test"


@pytest.fixture
def client():
    from api.runtime.main_app import app

    return TestClient(app, raise_server_exceptions=False)


def _widget_paths() -> tuple[str, ...]:
    from api.runtime import cors_policy

    return tuple(cors_policy.PUBLIC_WIDGET_CORS_PATHS)


def test_shop_is_a_public_widget_cors_path():
    assert any(path.startswith("/v1/shop") for path in _widget_paths())


def test_unhandled_widget_error_keeps_cors_headers(client, monkeypatch):
    """A 500 must stay readable by the browser, not look like a network outage."""
    from api.runtime import main_app

    def explode(*args, **kwargs):
        raise RuntimeError("psycopg.OperationalError at 10.0.0.4:5432 token=sk-secret")

    monkeypatch.setattr(main_app.runtime_payloads, "runtime_site_id", explode)

    response = client.post(
        "/v1/shop",
        headers={"Origin": WIDGET_ORIGIN},
        data={"site_id": "site_1", "text": "hello"},
    )

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == WIDGET_ORIGIN


def test_unhandled_widget_error_returns_structured_safe_json(client, monkeypatch):
    from api.runtime import main_app

    def explode(*args, **kwargs):
        raise RuntimeError("psycopg.OperationalError at 10.0.0.4:5432 token=sk-secret")

    monkeypatch.setattr(main_app.runtime_payloads, "runtime_site_id", explode)

    response = client.post(
        "/v1/shop",
        headers={"Origin": WIDGET_ORIGIN},
        data={"site_id": "site_1", "text": "hello"},
    )

    body = response.json()
    assert body["code"] == "internal_error"
    assert "request_id" in body
    assert "X-Request-ID" in response.headers.get("access-control-expose-headers", "")

    serialized = response.text.lower()
    for leaked in ("traceback", "psycopg", "sk-secret", "10.0.0.4", "operationalerror"):
        assert leaked not in serialized, f"internal detail leaked to the widget: {leaked}"


def test_widget_preflight_is_answered_without_running_the_turn(client):
    response = client.options(
        "/v1/shop",
        headers={
            "Origin": WIDGET_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 204
    assert response.headers.get("access-control-allow-origin") == WIDGET_ORIGIN


def test_audio_turn_does_not_block_the_event_loop():
    """The blocking orchestrator must be dispatched to a worker thread.

    `shop` is declared `async def`, so calling the synchronous orchestrator
    inline would freeze every other request for the length of a voice turn.
    """
    from api.runtime import main_app

    source = inspect.getsource(main_app.shop)
    assert "run_in_threadpool" in source, "the synchronous orchestrator must not run on the event loop"
    assert "await run_in_threadpool(" in source
