"""The conversation payload the CRM actually receives.

The full log view was built against hand-written TypeScript objects, so every
field it asked for looked present. Against the real endpoint most of them were
`null`: the backend selected neither the turn's decisions nor the search
evidence, and paired a turn with its browser actions by guessing from
timestamps. These tests exercise `conversation_log()` itself - the function the
`/crm/conversations` route returns - with the database access faked at its
boundary, so the shape asserted here is the shape the CRM parses.
"""

from __future__ import annotations

from typing import Any

import pytest

from db.analytics import metrics
from db.analytics.turn_diagnostics import build_turn_diagnostics, sanitize, turn_id_of

TURN_AT = "2026-08-07T10:00:00+00:00"
NEIGHBOUR_AT = "2026-08-07T10:00:03+00:00"


def _usage_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "site_id": "site_a",
        "session_id": "session-1",
        "transport": "http",
        "status": "ok",
        "intent": "product_search",
        "action_count": 1,
        "input_tokens": 10,
        "output_tokens": 20,
        "latency_ms": 812.0,
        "transcript": "show me the top 3 phones from Alpha",
        "response_text": "I found 4 results. My top three are ...",
        "request_id": "req-1",
        "turn_id": "turn-1",
        "diagnostics": {
            "turn_id": "turn-1",
            "confidence": 0.91,
            "selected_ids": ["p1", "p2", "p3"],
            "matching_total": 4,
            "displayed_count": 3,
            "requested_count": 3,
            "planned_actions": [
                {"action": "SHOW_PRODUCTS", "request_id": "turn-1_1", "sequence": 1, "params": {"search_query": "alpha smartphones"}}
            ],
            "cache": {"hit": False, "match_type": "", "data_version": 3},
            "model": {"name": "test-model", "provider": "test"},
        },
        "created_at": TURN_AT,
    }
    row.update(overrides)
    return row


def _action_event(**overrides: Any) -> dict[str, Any]:
    event = {
        "occurred_at": TURN_AT,
        "request_id": "turn-1_1",
        "turn_id": "turn-1",
        "sequence": 1,
        "action": "SHOW_PRODUCTS",
        "status": "ok",
        "stage": "host_search",
        "reason": "",
        "duration_ms": 240,
        "requested_url": "https://shop.test/search?q=alpha+smartphones",
        "final_url": "https://shop.test/search?q=alpha+smartphones",
        "evidence": {
            "url_changed": True,
            "query": "alpha smartphones",
            "result_count": 4,
            "requested_ids": ["p1", "p2", "p3"],
            "rendered_ids": ["p1", "p2", "p3", "p4"],
            "rendered_product_count": 4,
            "visible_requested_count": 3,
            "authorization": "Bearer super-secret",
        },
    }
    event.update(overrides)
    return event


@pytest.fixture
def faked_store(monkeypatch: pytest.MonkeyPatch):
    """Fake only the database reads; everything else is the real code path."""

    state: dict[str, Any] = {"rows": [_usage_row()], "events": [_action_event()]}

    monkeypatch.setattr(metrics, "_usage_rows", lambda *a, **k: state["rows"])
    monkeypatch.setattr(metrics, "_safe_runtime_events", lambda *a, **k: [])
    monkeypatch.setattr(
        metrics,
        "_action_events_by_site",
        lambda site_ids: {
            site_id: [metrics._conversation_action_event(event) for event in state["events"]]
            for site_id in site_ids
            if site_id
        },
    )
    return state


def _only_turn(payload: dict[str, Any]) -> dict[str, Any]:
    sessions = [session for group in payload["groups"] for session in group["sessions"]]
    assert len(sessions) == 1
    return sessions[0]["turns"][0]


def test_turn_carries_its_own_identifiers(faked_store) -> None:
    turn = _only_turn(metrics.conversation_log())
    assert turn["request_id"] == "req-1"
    assert turn["turn_id"] == "turn-1"


def test_turn_carries_the_decisions_the_full_log_reports(faked_store) -> None:
    turn = _only_turn(metrics.conversation_log())
    assert turn["selected_ids"] == ["p1", "p2", "p3"]
    assert turn["matching_total"] == 4
    assert turn["displayed_count"] == 3
    assert turn["requested_count"] == 3
    assert turn["confidence"] == 0.91
    assert turn["planned_actions"][0]["params"]["search_query"] == "alpha smartphones"
    assert turn["model"]["name"] == "test-model"
    assert turn["cache"]["data_version"] == 3


def test_action_evidence_keeps_what_was_searched_and_what_appeared(faked_store) -> None:
    event = _only_turn(metrics.conversation_log())["action_events"][0]
    assert event["query"] == "alpha smartphones"
    assert event["result_count"] == 4
    assert event["requested_ids"] == ["p1", "p2", "p3"]
    assert event["rendered_ids"] == ["p1", "p2", "p3", "p4"]
    assert event["evidence"]["rendered_product_count"] == 4
    assert event["evidence"]["visible_requested_count"] == 3


def test_credentials_in_evidence_never_reach_the_crm(faked_store) -> None:
    event = _only_turn(metrics.conversation_log())["action_events"][0]
    assert "authorization" not in event["evidence"]
    assert "super-secret" not in str(event)


def test_actions_are_paired_with_their_turn_by_id_not_by_clock(faked_store) -> None:
    """A neighbouring turn seconds later must not adopt these actions."""
    faked_store["rows"] = [
        _usage_row(),
        _usage_row(turn_id="turn-2", request_id="req-2", created_at=NEIGHBOUR_AT, diagnostics={}),
    ]
    payload = metrics.conversation_log()
    sessions = [session for group in payload["groups"] for session in group["sessions"]]
    by_turn = {turn["turn_id"]: turn for turn in sessions[0]["turns"]}
    assert [event["action"] for event in by_turn["turn-1"]["action_events"]] == ["SHOW_PRODUCTS"]
    assert by_turn["turn-2"]["action_events"] == []
    assert by_turn["turn-1"]["action_events"][0]["correlation"] == "turn_id"


def test_rows_written_before_ids_existed_are_labelled_as_guesses(faked_store) -> None:
    """Legacy rows still get their actions, but never claim certainty."""
    faked_store["rows"] = [_usage_row(turn_id="", request_id="", diagnostics=None)]
    event = _only_turn(metrics.conversation_log())["action_events"][0]
    assert event["correlation"] == "time_window"


def test_a_legacy_row_reports_absent_fields_rather_than_inventing_them(faked_store) -> None:
    faked_store["rows"] = [_usage_row(turn_id="", request_id="", diagnostics=None)]
    turn = _only_turn(metrics.conversation_log())
    assert "selected_ids" not in turn
    assert turn["transcript"] and turn["response_text"]


def test_diagnostics_are_built_from_the_turn_result() -> None:
    result = {
        "response_text": "Here are three.",
        "spoken_text": "Here are three.",
        "confidence": 0.8,
        "ui_actions": [
            {"action": "SHOW_PRODUCTS", "turn_id": "turn-9", "request_id": "turn-9_1", "sequence": 1, "params": {"search_query": "kayaks"}}
        ],
        "retrieval": {"selected_ids": ["a", "b"], "matching_total": 7, "cache_hit": True},
    }
    diagnostics = build_turn_diagnostics(result)
    assert turn_id_of(result) == "turn-9"
    assert diagnostics["selected_ids"] == ["a", "b"]
    assert diagnostics["matching_total"] == 7
    assert diagnostics["cache"]["hit"] is True
    # Identical spoken and written text is not worth storing twice.
    assert "spoken_text" not in diagnostics


def test_spoken_text_is_kept_when_it_differs_from_the_written_answer() -> None:
    diagnostics = build_turn_diagnostics(
        {"response_text": "Rs 1,299", "spoken_text": "one thousand two hundred ninety nine rupees"}
    )
    assert diagnostics["spoken_text"].startswith("one thousand")


def test_sanitize_drops_credentials_and_bounds_size() -> None:
    cleaned = sanitize({"api_key": "abc", "nested": {"cookie": "x", "keep": 1}, "big": "y" * 5000})
    assert cleaned["api_key"] == "[redacted]"
    assert cleaned["nested"]["cookie"] == "[redacted]"
    assert cleaned["nested"]["keep"] == 1
    assert cleaned["big"].endswith("...[truncated]")
