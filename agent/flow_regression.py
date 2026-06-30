"""Regression comparison for discovered website flows.

This module compares the last saved flow evidence to a newly discovered and
rehearsed flow. It does not repair anything; it records what changed so CRM and
readiness checks can stop trusting stale adapter targets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent.actions.registry import normalize_action_name

MAX_REGRESSION_CHANGES = 80
HIGH_SEVERITY = "high"
MEDIUM_SEVERITY = "medium"
LOW_SEVERITY = "low"
BASELINE_STATUS = "baseline"
STABLE_STATUS = "stable"
CHANGED_STATUS = "changed"


@dataclass(frozen=True)
class FlowRegressionChange:
    """One detected flow drift item."""

    kind: str
    item: str
    severity: str
    previous: str = ""
    current: str = ""
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FlowRegressionReport:
    """Comparison between previous and current flow evidence."""

    site_id: str
    site_url: str
    status: str
    summary: dict[str, Any] = field(default_factory=dict)
    changes: tuple[FlowRegressionChange, ...] = ()
    compared_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "site_url": self.site_url,
            "status": self.status,
            "summary": self.summary,
            "changes": [change.to_dict() for change in self.changes],
            "compared_at": self.compared_at,
        }


def build_flow_regression_report(
    previous_flow: dict[str, Any] | None,
    current_flow: dict[str, Any] | None,
    *,
    previous_rehearsal: dict[str, Any] | None = None,
    current_rehearsal: dict[str, Any] | None = None,
    site_id: str = "",
    site_url: str = "",
) -> FlowRegressionReport:
    """Compare previous and current website flow evidence."""
    previous = previous_flow if isinstance(previous_flow, dict) else {}
    current = current_flow if isinstance(current_flow, dict) else {}
    if not previous:
        return _baseline_report(current, site_id, site_url)

    changes = [
        *_vertical_changes(previous, current),
        *_route_changes(previous.get("routes"), current.get("routes")),
        *_action_changes(previous.get("adapter_actions"), current.get("adapter_actions")),
        *_rehearsal_changes(previous_rehearsal, current_rehearsal),
    ][:MAX_REGRESSION_CHANGES]
    summary = _summary(previous, current, changes)
    
    if changes and site_id:
        from db import admin as admin_db
        try:
            admin_db.update_client_setup_status(site_id, needs_setup=True)
        except Exception:
            pass

    return FlowRegressionReport(
        site_id=str(site_id or current.get("site_id") or previous.get("site_id") or ""),
        site_url=str(site_url or current.get("site_url") or previous.get("site_url") or ""),
        status=CHANGED_STATUS if changes else STABLE_STATUS,
        summary=summary,
        changes=tuple(changes),
        compared_at=datetime.now(timezone.utc).isoformat(),
    )


def _baseline_report(current_flow: dict[str, Any], site_id: str, site_url: str) -> FlowRegressionReport:
    actions = _action_targets(current_flow.get("adapter_actions"))
    routes = _route_map(current_flow.get("routes"))
    summary = {
        "baseline": True,
        "previous_actions": 0,
        "current_actions": len(actions),
        "previous_routes": 0,
        "current_routes": len(routes),
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    return FlowRegressionReport(
        site_id=str(site_id or current_flow.get("site_id") or ""),
        site_url=str(site_url or current_flow.get("site_url") or ""),
        status=BASELINE_STATUS,
        summary=summary,
        compared_at=datetime.now(timezone.utc).isoformat(),
    )


def _vertical_changes(previous: dict[str, Any], current: dict[str, Any]) -> list[FlowRegressionChange]:
    previous_key = str(previous.get("vertical_key") or "")
    current_key = str(current.get("vertical_key") or "")
    if not previous_key or not current_key or previous_key == current_key:
        return []
    return [
        FlowRegressionChange(
            kind="vertical_changed",
            item="vertical_key",
            severity=HIGH_SEVERITY,
            previous=previous_key,
            current=current_key,
            evidence="Detected website vertical changed between flow discovery runs.",
        )
    ]


def _route_changes(previous_routes: Any, current_routes: Any) -> list[FlowRegressionChange]:
    previous = _route_map(previous_routes)
    current = _route_map(current_routes)
    changes: list[FlowRegressionChange] = []
    for name in sorted(previous.keys() - current.keys()):
        changes.append(_change("route_removed", name, HIGH_SEVERITY, previous[name], "", "Route disappeared."))
    for name in sorted(current.keys() - previous.keys()):
        changes.append(_change("route_added", name, LOW_SEVERITY, "", current[name], "New route discovered."))
    for name in sorted(previous.keys() & current.keys()):
        if previous[name] != current[name]:
            changes.append(_change("route_changed", name, MEDIUM_SEVERITY, previous[name], current[name], "Route target changed."))
    return changes


def _action_changes(previous_actions: Any, current_actions: Any) -> list[FlowRegressionChange]:
    previous = _action_targets(previous_actions)
    current = _action_targets(current_actions)
    changes: list[FlowRegressionChange] = []
    for name in sorted(previous.keys() - current.keys()):
        changes.append(_change("action_removed", name, HIGH_SEVERITY, previous[name], "", "Adapter action disappeared."))
    for name in sorted(current.keys() - previous.keys()):
        changes.append(_change("action_added", name, LOW_SEVERITY, "", current[name], "New adapter action discovered."))
    for name in sorted(previous.keys() & current.keys()):
        if previous[name] != current[name]:
            changes.append(_change("action_changed", name, MEDIUM_SEVERITY, previous[name], current[name], "Adapter target changed."))
    return changes


def _rehearsal_changes(previous_rehearsal: Any, current_rehearsal: Any) -> list[FlowRegressionChange]:
    previous = _rehearsal_status(previous_rehearsal)
    current = _rehearsal_status(current_rehearsal)
    changes: list[FlowRegressionChange] = []
    for name in sorted(previous.keys() & current.keys()):
        if previous[name] and not current[name]:
            changes.append(_change("action_now_blocked", name, HIGH_SEVERITY, "supported", "blocked", "Previously rehearsed action is now blocked."))
        if not previous[name] and current[name]:
            changes.append(_change("action_recovered", name, LOW_SEVERITY, "blocked", "supported", "Previously blocked action now rehearses successfully."))
    for name in sorted(current.keys() - previous.keys()):
        if not current[name]:
            changes.append(_change("new_action_blocked", name, MEDIUM_SEVERITY, "", "blocked", "New rehearsed action is blocked."))
    return changes


def _change(kind: str, item: str, severity: str, previous: str, current: str, evidence: str) -> FlowRegressionChange:
    return FlowRegressionChange(kind=kind, item=item, severity=severity, previous=previous, current=current, evidence=evidence)


def _summary(previous: dict[str, Any], current: dict[str, Any], changes: list[FlowRegressionChange]) -> dict[str, Any]:
    previous_actions = _action_targets(previous.get("adapter_actions"))
    current_actions = _action_targets(current.get("adapter_actions"))
    previous_routes = _route_map(previous.get("routes"))
    current_routes = _route_map(current.get("routes"))
    return {
        "baseline": False,
        "previous_actions": len(previous_actions),
        "current_actions": len(current_actions),
        "previous_routes": len(previous_routes),
        "current_routes": len(current_routes),
        "changes": len(changes),
        "high": _severity_count(changes, HIGH_SEVERITY),
        "medium": _severity_count(changes, MEDIUM_SEVERITY),
        "low": _severity_count(changes, LOW_SEVERITY),
    }


def _severity_count(changes: list[FlowRegressionChange], severity: str) -> int:
    return sum(1 for change in changes if change.severity == severity)


def _route_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if str(key).strip() and str(item).strip()}


def _action_targets(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    targets: dict[str, str] = {}
    for raw_name, raw_config in value.items():
        name = normalize_action_name(str(raw_name or ""))
        target = _action_target(raw_config)
        if name and target:
            targets[name] = target
    return targets


def _action_target(raw_config: Any) -> str:
    if not isinstance(raw_config, dict):
        return ""
    action_type = str(raw_config.get("type") or "").strip().lower()
    parts = [
        action_type,
        str(raw_config.get("path") or ""),
        str(raw_config.get("selector") or ""),
        str(raw_config.get("form") or ""),
        str(raw_config.get("input") or ""),
        str(raw_config.get("submit") or ""),
        str(raw_config.get("submit_mode") or ""),
    ]
    return "|".join(parts)


def _rehearsal_status(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict) or not isinstance(value.get("steps"), list):
        return {}
    status: dict[str, bool] = {}
    for step in value.get("steps", []):
        if not isinstance(step, dict):
            continue
        name = normalize_action_name(str(step.get("action_name") or ""))
        if name:
            status[name] = bool(step.get("supported"))
    return status
