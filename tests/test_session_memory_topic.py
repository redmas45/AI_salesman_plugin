"""Regression tests for slice 9: topic-aware session memory.

A new product topic must reset stale context so an earlier product cannot
contaminate retrieval, while explicit follow-ups/corrections keep the topic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.prompts.context_budget import summarize_turns  # noqa: E402

PRIOR = "User: I want a laptop\nMaya: I found 3 laptops: Dell, HP, Lenovo."


def test_topic_shift_drops_stale_products():
    summary = summarize_turns(PRIOR, [], "Show me a smartwatch", "Here are some smartwatches.")
    assert "laptop" not in summary.lower()
    assert "smartwatch" in summary.lower()


def test_followup_preserves_prior_topic():
    summary = summarize_turns(PRIOR, [], "the cheaper one", "This one is cheaper.")
    assert "laptop" in summary.lower()


def test_same_topic_accumulates():
    summary = summarize_turns(PRIOR, [], "a gaming laptop instead", "Here is a gaming laptop.")
    assert "laptop" in summary.lower()


def test_no_previous_summary_is_unaffected():
    summary = summarize_turns("", [], "Show me a smartwatch", "Here are smartwatches.")
    assert "smartwatch" in summary.lower()


def test_correction_marker_is_not_a_topic_shift():
    # "No, ..." is a correction of the same conversation, not a new topic.
    summary = summarize_turns(PRIOR, [], "No, I meant a laptop bag", "Here are laptop bags.")
    assert "laptop" in summary.lower()


def test_plural_topics_trigger_a_reset():
    summary = summarize_turns(PRIOR, [], "Show me smartwatches", "Here are smartwatches.")
    assert "laptop" not in summary.lower()
    assert "smartwatches" in summary.lower()


def test_latest_summary_topic_wins_over_older_topics():
    rolling = (
        "User: Show me phones\n"
        "Maya: Here are phones.\n"
        "User: Show me laptops\n"
        "Maya: Here are laptops."
    )
    summary = summarize_turns(rolling, [], "Show me phones", "Here are phones.")
    assert "laptops" not in summary.lower()
