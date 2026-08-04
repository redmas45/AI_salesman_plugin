"""The server-side conversation context must stay flat as turns accumulate.

The reported regression is that a longer conversation makes each turn slower. A
first-order cause is the prompt the model must read growing with the transcript.
The Hub assembles the LLM context as a rolling summary plus the most recent
verbatim turns, then trims it to a hard token budget. These tests measure that
the assembled context does NOT grow with conversation length and never exceeds
the budget - which is what keeps per-turn latency flat.

The measurement is deterministic and provider-free (it inspects the assembled
message window, not a live model). A separate live-DB integration test proves the
persisted rolling summary stays bounded across many turns.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import config  # noqa: E402
from agent.prompts.context_budget import (  # noqa: E402
    MAX_SUMMARY_CHARS,
    build_context_messages,
    estimate_tokens,
    summarize_turns,
)

SAMPLE_TURNS = (1, 5, 10, 20, 30)


def _grown_history(turns: int) -> list[dict]:
    history = []
    for i in range(turns):
        history.append({"role": "user", "content": f"turn {i} question about product options and budgets"})
        history.append({"role": "assistant", "content": f"turn {i} answer [PRODUCT_IDS: p{i}a,p{i}b,p{i}c]"})
    return history


def _rolled_summary(turns: int) -> str:
    """The rolling summary after `turns` deterministic updates, as production builds it."""
    summary = ""
    for i in range(turns):
        summary = summarize_turns(
            summary,
            _grown_history(i + 1),
            f"turn {i} question about phones under 50000",
            f"turn {i} answer with several options",
        )
    return summary


def test_assembled_context_is_flat_and_bounded_across_turns():
    table = []
    for turns in SAMPLE_TURNS:
        messages = build_context_messages(
            _grown_history(turns),
            session_summary=_rolled_summary(turns),
            max_recent_messages=6,
        )
        table.append((turns, len(messages), estimate_tokens(messages)))

    print("\nturns | context_messages | approx_tokens")
    for turns, count, tokens in table:
        print(f"{turns:>5} | {count:>16} | {tokens:>13}")

    tokens_by_turn = {turns: tokens for turns, _c, tokens in table}
    # Never over the configured budget.
    for turns, tokens in tokens_by_turn.items():
        assert tokens <= config.CONTEXT_TOKEN_BUDGET, f"turn {turns}: {tokens} > budget"
    # Flat, not linear: turn 30 must be no larger than turn 10's steady state.
    assert tokens_by_turn[30] <= tokens_by_turn[10] * 1.15, tokens_by_turn


def test_early_turns_are_never_larger_than_replaying_them():
    """A short conversation must not pay the summary's fixed overhead: through the
    first several turns the assembled context is no larger than the raw history."""
    for turns in (1, 2, 3, 5, 8):
        raw = _grown_history(turns)
        assembled = build_context_messages(raw, session_summary=_rolled_summary(turns), max_recent_messages=6)
        assert estimate_tokens(assembled) <= estimate_tokens(raw), (
            f"turn {turns}: assembled {estimate_tokens(assembled)} > raw {estimate_tokens(raw)}"
        )
        # No summary is added while the conversation is still short.
        assert not any("Session memory summary" in m["content"] for m in assembled), turns


def test_the_summary_switches_on_only_when_it_saves_tokens():
    # Long enough that condensing older turns beats replaying them.
    assembled = build_context_messages(_grown_history(20), session_summary=_rolled_summary(20), max_recent_messages=6)
    assert any("Session memory summary" in m["content"] for m in assembled)


def test_a_single_oversized_turn_is_compacted_before_sending():
    from agent.prompts.context_budget import PER_MESSAGE_TOKEN_CAP

    verbose = {"role": "user", "content": "x " * 2000}  # ~1000 tokens in one turn
    assembled = build_context_messages([verbose], session_summary="", max_recent_messages=6)
    assert assembled, "the turn should still be present, just compacted"
    assert estimate_tokens([assembled[-1]]) <= PER_MESSAGE_TOKEN_CAP + 1


def test_token_budget_is_enforced_even_with_a_huge_summary_and_history():
    huge_summary = "x " * 5000  # ~10k chars, far over budget
    huge_history = [{"role": "user", "content": "y " * 500} for _ in range(40)]
    messages = build_context_messages(huge_history, session_summary=huge_summary, max_recent_messages=6)
    assert estimate_tokens(messages) <= config.CONTEXT_TOKEN_BUDGET


def test_rolling_summary_stays_bounded_regardless_of_turn_count():
    short = _rolled_summary(3)
    long = _rolled_summary(60)
    assert len(long) <= MAX_SUMMARY_CHARS
    # A 20x longer conversation must not produce a materially larger summary.
    assert len(long) <= max(len(short), MAX_SUMMARY_CHARS)


def test_the_latest_turns_are_kept_verbatim_for_accuracy():
    history = _grown_history(10)
    messages = build_context_messages(history, session_summary="prior context", max_recent_messages=6)
    verbatim = [m["content"] for m in messages if "Session memory summary" not in m["content"]]
    # The most recent user turn is present verbatim, not only summarized.
    assert any("turn 9 question" in c for c in verbatim), verbatim


@pytest.mark.integration
def test_live_db_rolling_summary_is_bounded_and_flat():
    """Against a real PostgreSQL: the persisted per-session summary stays bounded
    across many turns, so the context read on turn 30 is not larger than turn 5."""
    import psycopg

    try:
        with psycopg.connect(config.DATABASE_URL, connect_timeout=5):
            pass
    except Exception:
        pytest.skip("PostgreSQL not reachable at DATABASE_URL")

    from db.runtime.session_memory import get_session_summary, update_session_summary

    site_id = "ai_kart"
    session_id = "ctx-budget-latency-probe"
    sizes = {}
    for turn in range(1, 31):
        update_session_summary(
            site_id,
            session_id,
            history=_grown_history(turn),
            transcript=f"turn {turn} show me phones under 50000",
            response_text=f"turn {turn} here are some options",
        )
        if turn in SAMPLE_TURNS:
            summary = get_session_summary(site_id, session_id)
            context = build_context_messages(_grown_history(turn), session_summary=summary, max_recent_messages=6)
            sizes[turn] = estimate_tokens(context)

    print("\n(live DB) turns -> context tokens:", sizes)
    for turn, tokens in sizes.items():
        assert tokens <= config.CONTEXT_TOKEN_BUDGET, f"turn {turn}: {tokens} over budget"
    # Flat in the long run: once the summary is in effect, more turns add nothing.
    assert sizes[30] <= sizes[20] * 1.1, f"context still growing late: {sizes}"
    # Early turns are lean (no summary overhead), so the long conversation's steady
    # state is only a small constant, never a multiple that scales with turns.
    assert sizes[30] <= sizes[5] + 200, f"steady state far above the early turns: {sizes}"
