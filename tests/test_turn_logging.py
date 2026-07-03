import re

from db import analytics_math
from api.turn_logging import print_turn_summary, turn_timer


def test_turn_summary_prints_conversation_transport_and_timing(capsys):
    started_at = turn_timer()

    print_turn_summary(
        transport="websocket",
        site_id="ai_kart",
        started_at=started_at,
        transcript="show me caps",
        response_text="Here are two cap options.",
        ui_actions=[{"action": "SHOW_PRODUCTS"}],
        latency_ms={"total_ms": 1234, "stt_ms": 100, "llm_ms": 800, "tts_ms": 300},
    )

    output = capsys.readouterr().out
    assert "AI_CONVO | user: show me caps" in output
    assert "AI_CONVO | ai_reply: Here are two cap options." in output
    assert "AI_CONVO | method_used: websocket" in output
    assert "pipeline: 1234ms" in output
    assert "stages: stt=100ms llm=800ms tts=300ms" in output
    assert "actions: 1" in output
    assert "[MAYABOT TURN] transport=websocket status=ok site=ai_kart" in output
    assert "stt=100ms llm=800ms tts=300ms" in output
    assert re.search(r"time_taken: \d+ms", output)
    assert re.search(r"elapsed=\d+ms", output)


def test_conversation_log_includes_matching_action_events(monkeypatch):
    monkeypatch.setattr(
        analytics_math,
        "_usage_rows",
        lambda range_key, site_id="", limit=500: [
            {
                "site_id": "policy_site",
                "session_id": "session_1",
                "transport": "websocket",
                "status": "ok",
                "intent": "navigate",
                "action_count": 1,
                "input_tokens": 10,
                "output_tokens": 12,
                "latency_ms": 1234,
                "transcript": "open travel insurance",
                "response_text": "Opening travel insurance.",
                "created_at": "2026-07-02T10:00:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        analytics_math,
        "_action_events_by_site",
        lambda site_ids: {
            "policy_site": [
                {
                    "occurred_at": "2026-07-02T10:00:02+00:00",
                    "request_id": "turn_demo_1",
                    "turn_id": "turn_demo",
                    "sequence": 1,
                    "action": "NAVIGATE_TO",
                    "status": "succeeded",
                    "stage": "navigation",
                    "duration_ms": 40,
                    "requested_url": "https://policy.example.com/",
                    "final_url": "https://policy.example.com/insurance/travel",
                    "url_changed": True,
                    "evidence": {"url_changed": True, "target_page": "travel"},
                }
            ]
        },
    )

    log = analytics_math.conversation_log("7d", "policy_site")
    turn = log["groups"][0]["sessions"][0]["turns"][0]

    assert turn["action_events"][0]["request_id"] == "turn_demo_1"
    assert turn["action_events"][0]["status"] == "succeeded"
    assert turn["action_events"][0]["final_url"] == "https://policy.example.com/insurance/travel"
    assert turn["action_events"][0]["url_changed"] is True
