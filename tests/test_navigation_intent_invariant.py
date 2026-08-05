"""Only a navigation turn may navigate - in production as well as under pytest.

The pipeline stripped unrequested NAVIGATE_TO actions from non-navigate turns,
but the whole rule was wrapped in `if "PYTEST_CURRENT_TEST" in os.environ`. Tests
therefore proved a behaviour that shipped code never performed: in production a
search, comparison or page-relative answer could still yank the customer to a
different URL.

These tests run with the pytest marker removed from the environment, so they
assert the deployed behaviour rather than the test-only behaviour.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.orchestration.orchestrator_pipeline import strip_unrequested_navigation  # noqa: E402

NAVIGATE = {"action": "NAVIGATE_TO", "params": {"page": "/shop"}}
SECTION_NAVIGATE = {"action": "NAVIGATE_TO", "params": {"page": "category/electronics"}}
SHOW = {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["1"]}}


@pytest.fixture
def production_env(monkeypatch):
    """Simulate a deployed process, where the pytest marker is absent."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


def test_non_navigate_turn_drops_navigation_in_production(production_env):
    assert strip_unrequested_navigation([SHOW, NAVIGATE], "product_search") == [SHOW]


def test_navigate_turn_keeps_navigation_in_production(production_env):
    assert strip_unrequested_navigation([NAVIGATE], "navigate") == [NAVIGATE]


def test_page_relative_answer_never_navigates(production_env):
    """"What is visible?" must answer from the page, not move the customer."""
    assert strip_unrequested_navigation([NAVIGATE], "product_detail") == []


def test_comparison_turn_never_navigates(production_env):
    comparison = {"action": "SHOW_COMPARISON", "params": {"product_ids": ["1", "2"]}}
    assert strip_unrequested_navigation([comparison, NAVIGATE], "product_compare") == [comparison]


def test_behaviour_is_identical_with_and_without_the_pytest_marker(monkeypatch):
    """The deployed path and the tested path must not diverge."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    production = strip_unrequested_navigation([SHOW, NAVIGATE], "product_search")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_x")
    under_test = strip_unrequested_navigation([SHOW, NAVIGATE], "product_search")
    assert production == under_test


def test_explicit_navigation_survives_a_mixed_turn(production_env):
    """"Show the cheapest women's item and take me there" must still navigate.

    Filtering on the primary intent alone dropped navigation the customer had
    explicitly asked for, because the turn was classified as a product search.
    """
    kept = strip_unrequested_navigation(
        [SHOW, NAVIGATE], "product_search", navigation_requested=True
    )
    assert kept == [SHOW, NAVIGATE]


def test_section_navigation_drops_redundant_product_display(production_env):
    """A section page must remain the final host state, not generic search."""
    kept = strip_unrequested_navigation(
        [SECTION_NAVIGATE, SHOW], "product_search", navigation_requested=True
    )
    assert kept == [SECTION_NAVIGATE]


def test_accidental_navigation_is_still_removed_from_a_mixed_turn(production_env):
    """Without an explicit request, navigation is still stripped."""
    assert strip_unrequested_navigation([SHOW, NAVIGATE], "product_search") == [SHOW]


def test_explicit_request_does_not_resurrect_navigation_for_page_relative_turns(production_env):
    """A page-relative answer keeps the customer where they are."""
    assert strip_unrequested_navigation([NAVIGATE], "product_detail") == []


def test_malformed_actions_are_tolerated(production_env):
    assert strip_unrequested_navigation([None, "junk", SHOW], "product_search") == [SHOW]


def test_empty_action_list_is_unchanged(production_env):
    assert strip_unrequested_navigation([], "product_search") == []


def test_pipeline_source_no_longer_branches_on_the_pytest_marker():
    """No runtime branch may read the pytest marker.

    Checks for the environment lookup itself rather than the bare word, so the
    docstring that records why the branch was removed does not trip the guard.
    """
    source = (
        Path(__file__).parent.parent / "agent" / "orchestration" / "orchestrator_pipeline.py"
    ).read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines() if not line.strip().startswith("#"))
    assert 'PYTEST_CURRENT_TEST" in os.environ' not in code
    assert "os.environ" not in code, "production behaviour must not depend on the test environment"


def test_sync_and_stream_pipelines_apply_the_same_navigation_filter():
    source = (
        Path(__file__).parent.parent / "agent" / "orchestration" / "orchestrator_pipeline.py"
    ).read_text(encoding="utf-8")
    sync_source, stream_source = source.split("def run_stream_pipeline", 1)

    assert sync_source.count("strip_unrequested_navigation(") == 4  # helper plus three call sites
    assert stream_source.count("strip_unrequested_navigation(") == 3
    assert sync_source.count("enforce_grounded_constraints(") == 2
    assert stream_source.count("enforce_grounded_constraints(") == 2
