"""WebSocket voice transport contract tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


def test_ws_config_and_empty_audio_are_safe():
    from api.main import app

    client = TestClient(app)
    with client.websocket_connect("/v1/ws/shop?site_id=site_1") as ws:
        assert ws.receive_json()["type"] == "ready"

        ws.send_json({"type": "config", "history": []})
        configured = ws.receive_json()
        assert configured["type"] == "configured"
        assert configured["history_size"] == 0

        ws.send_json({"type": "audio_end"})
        error = ws.receive_json()
        assert error["type"] == "error"
        assert "No audio or text" in error["message"]


def test_ws_text_turn_streams_pipeline_events(monkeypatch):
    from api.main import app
    from api import ws_shop

    def fake_run_stream(**kwargs):
        assert kwargs["site_id"] == "site_1"
        assert kwargs["text_input"] == "hello"
        assert kwargs["page_context"]["path"] == "/quote"
        assert kwargs["page_context"]["forms"][0]["fields"][0]["name"] == "Phone"
        yield {"event": "transcript", "data": {"transcript": "hello"}}
        yield {"event": "actions", "data": {"ui_actions": []}}
        yield {
            "event": "audio",
            "data": {"response_text": "Welcome to AI-KART.", "audio_b64": "UklGRg=="},
        }

    monkeypatch.setattr(ws_shop.orchestrator, "run_stream", fake_run_stream)

    client = TestClient(app)
    with client.websocket_connect("/v1/ws/shop?site_id=site_1") as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({
            "type": "config",
            "history": [],
            "page_context": {
                "path": "/quote",
                "controls": {
                    "forms": [
                        {
                            "selector": "form.quote",
                            "fields": [
                                {"selector": "input.phone", "name": "Phone", "type": "tel", "value": "secret"}
                            ],
                        }
                    ]
                },
            },
        })
        assert ws.receive_json()["type"] == "configured"

        ws.send_json({"type": "text", "text": "hello"})
        assert ws.receive_json() == {"type": "transcript", "text": "hello"}
        assert ws.receive_json() == {"type": "text_chunk", "text": "Welcome to AI-KART."}
        assert ws.receive_json() == {"type": "audio_chunk", "audio_b64": "UklGRg=="}

        done = ws.receive_json()
        assert done["type"] == "done"
        assert done["response_text"] == "Welcome to AI-KART."
        assert done["ui_actions"] == []
        assert done["history"][-2:] == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Welcome to AI-KART."},
        ]


def test_ws_text_turn_adds_action_request_ids(monkeypatch):
    from api.main import app
    from api import ws_shop

    def fake_run_stream(**kwargs):
        yield {"event": "transcript", "data": {"transcript": "open plans"}}
        yield {"event": "actions", "data": {"ui_actions": [{"action": "NAVIGATE_TO", "params": {"page": "plans"}}]}}
        yield {"event": "response", "data": {"response_text": "Opening plans."}}

    monkeypatch.setattr(ws_shop.orchestrator, "run_stream", fake_run_stream)

    client = TestClient(app)
    with client.websocket_connect("/v1/ws/shop?site_id=site_1") as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "text", "text": "open plans"})
        assert ws.receive_json() == {"type": "transcript", "text": "open plans"}
        assert ws.receive_json() == {"type": "text_chunk", "text": "Opening plans."}

        done = ws.receive_json()
        action = done["ui_actions"][0]
        assert action["action"] == "NAVIGATE_TO"
        assert action["params"] == {"page": "plans"}
        assert action["request_id"].startswith(action["turn_id"])
        assert action["sequence"] == 1
