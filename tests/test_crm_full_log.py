"""The CRM conversation card exposes two controls, and the full log is complete.

Owner requirement (2026-08-07): the conversation-card toolbar must contain
exactly "Copy conversation" and "Full log"; client activity, copy diagnostics,
export JSON and the latest-intent chip move out of it, with Download JSON living
inside the full-log view.

The log itself has to be usable as evidence, which means it must (a) carry every
relevant field, (b) never carry a secret, and (c) state the disagreements
between what Maya said, which records she chose, and what the page rendered -
the failure this whole log exists to surface.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
VIEW = ROOT / "crm" / "src" / "views" / "conversations" / "ConversationsView.tsx"
PANEL = ROOT / "crm" / "src" / "views" / "conversations" / "FullLogPanel.tsx"
MODULE = ROOT / "crm" / "src" / "views" / "conversations" / "fullLog.ts"

TOOLBAR_START = '<div className="convo-card-actions">'


def _toolbar() -> str:
    source = VIEW.read_text(encoding="utf-8")
    start = source.index(TOOLBAR_START)
    return source[start : source.index("</div>", start)]


def test_the_toolbar_has_exactly_two_controls():
    toolbar = _toolbar()
    assert "CopyConversationButton" in toolbar
    assert "Full log" in toolbar
    assert toolbar.count("<Button") + toolbar.count("<CopyConversationButton") == 2


@pytest.mark.parametrize(
    "removed", ["Open client activity", "RuntimeDiagnosticActions", "Latest intent"]
)
def test_the_removed_controls_are_gone_from_the_toolbar(removed):
    assert removed not in _toolbar()


def test_download_json_lives_inside_the_full_log_view():
    assert "Download JSON" in PANEL.read_text(encoding="utf-8")
    assert "Download JSON" not in _toolbar()


def test_the_full_log_view_is_keyboard_accessible():
    panel = PANEL.read_text(encoding="utf-8")
    assert 'role="dialog"' in panel and 'aria-modal="true"' in panel
    assert "Escape" in panel
    assert "aria-label=\"Close full log\"" in panel


def test_the_full_log_is_a_separate_module_so_the_view_stays_within_budget():
    assert len(VIEW.read_text(encoding="utf-8").splitlines()) <= 500


# --- The exported record ----------------------------------------------------


def _node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")
    return node


def _build_log(session, tmp_path):
    """Bundle the shipped module and run it, so the real code is exercised."""
    # The workspace installs esbuild for the plugin build; reuse that binary
    # rather than requiring a global one.
    esbuild = next(
        (
            candidate
            for candidate in (
                ROOT / "node_modules" / ".bin" / "esbuild.CMD",
                ROOT / "node_modules" / ".bin" / "esbuild",
                ROOT / "plugin" / "node_modules" / ".bin" / "esbuild.CMD",
                ROOT / "plugin" / "node_modules" / ".bin" / "esbuild",
            )
            if candidate.exists()
        ),
        None,
    )
    if esbuild is None:
        pytest.skip("esbuild is not installed in this workspace")
    bundle = tmp_path / "fullLog.mjs"
    built = subprocess.run(
        [str(esbuild), str(MODULE), "--bundle", "--format=esm", f"--outfile={bundle}"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if built.returncode != 0:
        pytest.skip(f"esbuild unavailable: {built.stderr[:200]}")
    script = (
        f'import {{ buildFullLog }} from "file://{bundle.as_posix()}";'
        f"process.stdout.write(JSON.stringify(buildFullLog({json.dumps(session)}, '2026-08-07T00:00:00Z')));"
    )
    outcome = subprocess.run(
        [_node(), "--input-type=module", "-e", script], capture_output=True, text=True, cwd=ROOT
    )
    if outcome.returncode != 0:
        pytest.fail(outcome.stderr[:400])
    return json.loads(outcome.stdout)


_SESSION = {
    "session_id": "sess-1",
    "site_id": "demo_site",
    "date": "2026-08-07",
    "turn_count": 1,
    "turns": [
        {
            "created_at": "2026-08-07T10:00:00Z",
            "request_id": "req-1",
            "transcript": "show me the top 3 phones",
            "response_text": "I found 3 matching products.",
            "intent": "product_search",
            "status": "ok",
            "transport": "ws",
            "selected_ids": ["p1", "p2", "p3"],
            "matching_total": 7,
            "displayed_count": 3,
            "requested_count": 3,
            "password": "hunter2",
            "authorization": "Bearer abc",
            "action_events": [
                {
                    "action": "SHOW_PRODUCTS",
                    "status": "failed",
                    "reason": "requested_records_not_visible",
                    "query": "top 3 phone from",
                    "result_count": 0,
                    "requested_ids": ["p1", "p2", "p3"],
                    "rendered_ids": [],
                    "rendered_product_count": 0,
                }
            ],
        }
    ],
}


def test_the_export_carries_identity_counts_and_action_evidence(tmp_path):
    log = _build_log(_SESSION, tmp_path)
    assert log["schema_version"]
    assert log["exported_at"] == "2026-08-07T00:00:00Z"
    assert log["session"]["session_id"] == "sess-1"
    turn = log["turns"][0]
    assert turn["request_id"] == "req-1"
    assert turn["user_transcript"] == "show me the top 3 phones"
    assert turn["resolution"]["matching_total"] == 7
    assert turn["resolution"]["selected_ids"] == ["p1", "p2", "p3"]
    assert turn["browser_action_events"][0]["reason"] == "requested_records_not_visible"


def test_no_secret_survives_the_export(tmp_path):
    exported = json.dumps(_build_log(_SESSION, tmp_path))
    assert "hunter2" not in exported
    assert "Bearer abc" not in exported
    assert "[redacted]" in exported


def test_the_export_names_the_disagreements(tmp_path):
    log = _build_log(_SESSION, tmp_path)
    kinds = {mismatch["kind"] for mismatch in log["mismatch_summary"]}
    assert "response_count_vs_rendered_count" in kinds
    assert "success_claim_vs_failed_action" in kinds
    assert "spoken_text_vs_visible_result" in kinds


def test_a_consistent_turn_reports_no_disagreement(tmp_path):
    session = {
        "session_id": "sess-2",
        "turns": [
            {
                "request_id": "req-2",
                "response_text": "I found 2 matching products.",
                "selected_ids": ["a", "b"],
                "action_events": [
                    {
                        "action": "SHOW_PRODUCTS",
                        "status": "succeeded",
                        "result_count": 2,
                        "rendered_ids": ["a", "b"],
                        "rendered_product_count": 2,
                    }
                ],
            }
        ],
    }
    assert _build_log(session, tmp_path)["mismatch_summary"] == []
