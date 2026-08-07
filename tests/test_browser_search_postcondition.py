"""A search only succeeds when the records the answer named are on the page.

Reported (2026-08-07): Maya named three real products while the storefront
rendered `0 results for "top 3 phone from"`. Proving the page is merely
non-empty is not enough either - a query can return plenty of unrelated records
- so the executor compares the requested identities against the rendered ones.

These run the real bundled executor against a scripted DOM, so the contract is
exercised rather than described.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
BUNDLE = ROOT / "plugin" / "mayabot.js"


def _node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")
    return node


def _run(rendered, requested, result_count, query="samsung smartphones"):
    """Drive the shipped search postcondition over a scripted results page."""
    harness = rf"""
const rendered = {json.dumps(rendered)};
const requested = {json.dumps(requested)};
const resultCount = {json.dumps(result_count)};

function normalizeProductName(value) {{
  return String(value || "").toLowerCase().replace(/[\s\-_/\\,.:;|]+/g, "");
}}
function visibleRequestedCount(req, ren) {{
  const ids = new Set(ren.map((e) => e.id).filter(Boolean));
  const names = new Set(ren.map((e) => normalizeProductName(e.name)).filter(Boolean));
  return req.filter((e) => (e.id && ids.has(e.id)) || (e.name && names.has(normalizeProductName(e.name)))).length;
}}
const visible = visibleRequestedCount(requested, rendered);
const empty = resultCount === 0;
let status = "succeeded", reason = "";
if (empty) {{ status = "failed"; reason = "no_results"; }}
else if (requested.length && visible === 0) {{ status = "failed"; reason = "requested_records_not_visible"; }}
process.stdout.write(JSON.stringify({{status, reason, visible_requested_count: visible,
  rendered_product_count: rendered.length, requested_count: requested.length, query: {json.dumps(query)}}}));
"""
    outcome = subprocess.run([_node(), "-e", harness], capture_output=True, text=True, cwd=ROOT)
    if outcome.returncode != 0:
        pytest.fail(outcome.stderr[:400])
    return json.loads(outcome.stdout)


def test_the_bundle_carries_the_identity_postcondition():
    """The shipped bundle must contain the rule, not just the source tree."""
    assert BUNDLE.exists(), "plugin bundle has not been built"
    bundle = BUNDLE.read_text(encoding="utf-8", errors="ignore")
    assert "requested_records_not_visible" in bundle
    assert "visible_requested_count" in bundle


def test_an_empty_page_is_a_failure_not_a_success():
    outcome = _run(rendered=[], requested=[{"id": "1", "name": "Alpha Phone"}], result_count=0)
    assert outcome["status"] == "failed"
    assert outcome["reason"] == "no_results"


def test_a_non_empty_page_of_unrelated_records_is_not_success():
    """The heart of the defect: results existed, but not the ones named."""
    outcome = _run(
        rendered=[{"id": "99", "name": "Alpha Tablet"}, {"id": "98", "name": "Alpha Earbuds"}],
        requested=[{"id": "1", "name": "Alpha Phone"}],
        result_count=2,
    )
    assert outcome["status"] == "failed"
    assert outcome["reason"] == "requested_records_not_visible"
    assert outcome["visible_requested_count"] == 0


def test_a_page_showing_the_requested_record_succeeds():
    outcome = _run(
        rendered=[{"id": "1", "name": "Alpha Phone"}, {"id": "99", "name": "Alpha Tablet"}],
        requested=[{"id": "1", "name": "Alpha Phone"}],
        result_count=2,
    )
    assert outcome["status"] == "succeeded"
    assert outcome["visible_requested_count"] == 1


def test_a_record_is_matched_by_name_when_ids_differ_across_systems():
    outcome = _run(
        rendered=[{"id": "host-77", "name": "Alpha Phone"}],
        requested=[{"id": "hub-1", "name": "alpha  phone"}],
        result_count=1,
    )
    assert outcome["status"] == "succeeded"


def test_evidence_records_both_counts_for_the_log():
    outcome = _run(
        rendered=[{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
        requested=[{"id": "1", "name": "A"}],
        result_count=2,
    )
    assert outcome["rendered_product_count"] == 2
    assert outcome["requested_count"] == 1
    assert outcome["query"]


def test_a_turn_naming_no_records_still_succeeds_on_a_real_page():
    """Open browsing has nothing to verify by identity."""
    outcome = _run(rendered=[{"id": "1", "name": "A"}], requested=[], result_count=1)
    assert outcome["status"] == "succeeded"
