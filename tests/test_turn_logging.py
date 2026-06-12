import re

from api.turn_logging import print_turn_summary, turn_timer


def test_turn_summary_prints_conversation_transport_and_timing(capsys):
    started_at = turn_timer()

    print_turn_summary(
        transport="websocket",
        site_id="ai_kart_main",
        started_at=started_at,
        transcript="show me caps",
        response_text="Here are two cap options.",
        ui_actions=[{"action": "SHOW_PRODUCTS"}],
        latency_ms={"total_ms": 1234},
    )

    output = capsys.readouterr().out
    assert "AI_CONVO | user: show me caps" in output
    assert "AI_CONVO | ai_reply: Here are two cap options." in output
    assert "AI_CONVO | method_used: websocket" in output
    assert "pipeline: 1234ms" in output
    assert "actions: 1" in output
    assert "[SHOPBOT TURN] transport=websocket status=ok site=ai_kart_main" in output
    assert re.search(r"time_taken: \d+ms", output)
    assert re.search(r"elapsed=\d+ms", output)
