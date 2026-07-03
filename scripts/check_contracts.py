"""Fail fast when Python and TypeScript action contracts drift."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.actions.registry import list_action_names


CONTRACTS_SOURCE = ROOT / "packages/contracts/index.js"
ACTION_PATTERN = re.compile(r"\b[A-Z0-9_]+\s*:\s*\"([A-Z0-9_]+)\"")


def _contract_action_names() -> set[str]:
    source = CONTRACTS_SOURCE.read_text(encoding="utf-8")
    action_block = source.split("export const ACTION_PARAMS", 1)[0]
    return set(ACTION_PATTERN.findall(action_block))


def main() -> None:
    python_actions = list_action_names()
    ts_actions = _contract_action_names()
    missing_in_ts = sorted(python_actions - ts_actions)
    extra_in_ts = sorted(ts_actions - python_actions)
    if missing_in_ts or extra_in_ts:
        details = [
            f"missing_in_ts={missing_in_ts}",
            f"extra_in_ts={extra_in_ts}",
        ]
        raise SystemExit("Shared action contract drift detected: " + "; ".join(details))
    print(f"Shared action contracts match: {len(ts_actions)} actions.")


if __name__ == "__main__":
    main()
