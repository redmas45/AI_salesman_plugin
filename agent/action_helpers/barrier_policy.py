"""Barrier-aware action policy for dynamic website control."""

from __future__ import annotations

from typing import Any

from agent.actions.registry import get_action, list_actions, normalize_action_name
from agent.site_helpers.provider_handoff import handoff_playbook_for

HIGH_RISK_BARRIERS = frozenset({"auth_required", "captcha", "payment_handoff"})
CONFIRMATION_BARRIERS = frozenset({"embedded_iframe", "calendar_widget", "file_upload", "external_handoff"})
NO_BLOCK_BARRIERS = frozenset({"map_widget"})
DEFAULT_HANDOFF_ACTION = "HANDOFF_TO_HUMAN"
PAYMENT_HANDOFF_ACTION = "CHECKOUT_HANDOFF"

BARRIER_TITLES: dict[str, str] = {
    "auth_required": "Login or account gate",
    "captcha": "CAPTCHA or bot challenge",
    "payment_handoff": "Secure payment handoff",
    "calendar_widget": "Calendar or slot picker",
    "file_upload": "User file upload",
    "embedded_iframe": "Embedded provider widget",
    "external_handoff": "External provider handoff",
    "map_widget": "Map or location widget",
}
BARRIER_KIND_BY_KEY: dict[str, str] = {
    "auth_required": "auth",
    "captcha": "captcha",
    "payment_handoff": "payment",
    "calendar_widget": "calendar",
    "file_upload": "file_upload",
    "embedded_iframe": "iframe",
    "external_handoff": "external",
    "map_widget": "map",
}
PROVIDER_EVIDENCE_PREFIXES: dict[str, str] = {
    "captcha": "CAPTCHA provider(s):",
    "payment_handoff": "Payment provider(s):",
    "calendar_widget": "Calendar provider(s):",
    "map_widget": "Map provider(s):",
    "embedded_iframe": "iframe(s) detected:",
    "external_handoff": "Action links leave site:",
}

CHECKOUT_BLOCKED_ACTIONS = frozenset({
    "CHECKOUT",
    "CHECKOUT_HANDOFF",
    "SCHEDULE_ORDER",
})
BOOKING_BLOCKED_ACTIONS = frozenset({
    "START_BOOKING",
    "START_TICKET_PURCHASE",
    "REQUEST_APPOINTMENT",
    "BOOK_APPOINTMENT_REQUEST",
    "REQUEST_VIEWING",
    "REQUEST_SITE_VISIT",
})
APPLICATION_BLOCKED_ACTIONS = frozenset({
    "START_APPLICATION",
    "START_ENROLLMENT",
    "START_INTAKE",
    "MATCH_JOBS",
})
QUOTE_BLOCKED_ACTIONS = frozenset({
    "START_QUOTE",
    "REQUEST_ESTIMATE",
    "REQUEST_CONSULTATION",
    "CAPTURE_LEAD",
    "CAPTURE_PATIENT_LEAD",
})
AUTH_BLOCKED_ACTIONS = frozenset(
    CHECKOUT_BLOCKED_ACTIONS
    | BOOKING_BLOCKED_ACTIONS
    | APPLICATION_BLOCKED_ACTIONS
    | QUOTE_BLOCKED_ACTIONS
)
HUMAN_HANDOFF_ACTIONS = frozenset({
    "HANDOFF_TO_HUMAN",
    "HANDOFF_TO_AGENT",
    "HANDOFF_TO_LICENSED_AGENT",
    "HANDOFF_TO_ADVISOR",
    "HANDOFF_TO_CLINIC",
    "HANDOFF_TO_LAWYER",
    "HANDOFF_TO_RECRUITER",
})
VERTICAL_HANDOFF_ACTIONS: dict[str, tuple[str, ...]] = {
    "insurance": ("HANDOFF_TO_LICENSED_AGENT", "HANDOFF_TO_AGENT"),
    "finance_broker": ("HANDOFF_TO_ADVISOR", "HANDOFF_TO_HUMAN"),
    "healthcare": ("HANDOFF_TO_CLINIC", "HANDOFF_TO_HUMAN"),
    "legal_services": ("HANDOFF_TO_LAWYER", "HANDOFF_TO_HUMAN"),
    "jobs_recruiting": ("HANDOFF_TO_RECRUITER", "HANDOFF_TO_HUMAN"),
    "real_estate": ("HANDOFF_TO_AGENT", "HANDOFF_TO_HUMAN"),
    "ecommerce": ("CHECKOUT_HANDOFF", "HANDOFF_TO_HUMAN"),
}


def build_barrier_action_policy(vertical_config: dict[str, Any], vertical_key: str = "") -> dict[str, Any]:
    """Convert saved barrier evidence into blocked actions and handoff guidance."""
    barriers = vertical_config.get("barriers") if isinstance(vertical_config, dict) else {}
    findings = barriers.get("findings") if isinstance(barriers, dict) else []
    if not isinstance(findings, list):
        findings = []

    runtime_blocked = _runtime_blocked_actions(vertical_config)
    blocked: set[str] = set()
    confirmation: set[str] = set()
    notes: list[dict[str, str]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        key = str(finding.get("key") or "").strip()
        blocked.update(_blocked_actions_for_barrier(key))
        confirmation.update(_confirmation_actions_for_barrier(key))
        notes.append(_policy_note(finding))

    handoffs = _handoff_actions(vertical_key, findings)
    handoff_flows = _handoff_flows(vertical_key, findings, handoffs)
    blocked.update(runtime_blocked)
    notes.extend(_runtime_health_notes(vertical_config))
    blocked -= handoffs
    return {
        "blocked_actions": sorted(action for action in blocked if get_action(action)),
        "runtime_blocked_actions": sorted(action for action in runtime_blocked if get_action(action)),
        "handoff_actions": sorted(action for action in handoffs if get_action(action)),
        "handoff_flows": handoff_flows,
        "confirmation_required_actions": sorted(action for action in confirmation if get_action(action)),
        "has_high_risk_barrier": any(str(item.get("key") or "") in HIGH_RISK_BARRIERS for item in findings if isinstance(item, dict)),
        "notes": notes[:20],
    }


def apply_barrier_policy(allowed_actions: set[str], vertical_config: dict[str, Any], vertical_key: str = "") -> set[str]:
    """Remove blocked actions and add allowed handoff actions."""
    policy = build_barrier_action_policy(vertical_config, vertical_key)
    allowed = {normalize_action_name(action) for action in allowed_actions if get_action(action)}
    allowed -= set(policy["blocked_actions"])
    allowed |= set(policy["handoff_actions"])
    return {action for action in allowed if get_action(action)}


def barrier_policy_prompt_context(site_id: str, vertical_config: dict[str, Any], vertical_key: str = "") -> str:
    """Return prompt instructions derived from hard-flow barriers."""
    policy = build_barrier_action_policy(vertical_config, vertical_key)
    blocked = policy["blocked_actions"]
    notes = policy["notes"]
    if not blocked and not notes:
        return ""
    lines = ["Hard-flow barrier policy for this client:"]
    if blocked:
        lines.append(f"Blocked UI actions until admin/integration repair: {', '.join(blocked)}.")
    handoffs = policy["handoff_actions"]
    if handoffs:
        lines.append(f"Use handoff actions for blocked flows: {', '.join(handoffs)}.")
    for flow in policy["handoff_flows"][:4]:
        lines.append(f"Handoff flow {flow['key']} uses {flow['action']}: {flow['handling']}")
        if flow.get("automation_boundary"):
            lines.append(f"Boundary for {flow['key']}: {flow['automation_boundary']}")
        if flow.get("admin_action"):
            lines.append(f"Admin action for {flow['key']}: {flow['admin_action']}")
    for note in notes[:6]:
        lines.append(f"{note['key']}: {note['handling']}")
    return " ".join(lines)


def _blocked_actions_for_barrier(key: str) -> set[str]:
    if key == "auth_required":
        return set(AUTH_BLOCKED_ACTIONS)
    if key == "captcha":
        return _all_finalization_actions()
    if key == "payment_handoff":
        return set(CHECKOUT_BLOCKED_ACTIONS)
    if key == "calendar_widget":
        return set(BOOKING_BLOCKED_ACTIONS)
    if key == "file_upload":
        return set(APPLICATION_BLOCKED_ACTIONS)
    if key == "embedded_iframe":
        return set(BOOKING_BLOCKED_ACTIONS | CHECKOUT_BLOCKED_ACTIONS)
    if key == "external_handoff":
        return set(BOOKING_BLOCKED_ACTIONS | CHECKOUT_BLOCKED_ACTIONS | APPLICATION_BLOCKED_ACTIONS | QUOTE_BLOCKED_ACTIONS)
    return set()


def _confirmation_actions_for_barrier(key: str) -> set[str]:
    if key in NO_BLOCK_BARRIERS:
        return set()
    if key in CONFIRMATION_BARRIERS | HIGH_RISK_BARRIERS:
        return _blocked_actions_for_barrier(key)
    return set()


def _all_finalization_actions() -> set[str]:
    actions: set[str] = set()
    for action in list_actions():
        if action.family in {"lead", "commerce"} and not _is_handoff_action(action.name):
            actions.add(action.name)
    actions.update(CHECKOUT_BLOCKED_ACTIONS | BOOKING_BLOCKED_ACTIONS | APPLICATION_BLOCKED_ACTIONS | QUOTE_BLOCKED_ACTIONS)
    return actions


def _handoff_actions(vertical_key: str, findings: list[Any]) -> set[str]:
    if not findings:
        return set()
    handoffs = set(VERTICAL_HANDOFF_ACTIONS.get(str(vertical_key or ""), (DEFAULT_HANDOFF_ACTION,)))
    if any(isinstance(item, dict) and str(item.get("key") or "") == "payment_handoff" for item in findings):
        handoffs.add(PAYMENT_HANDOFF_ACTION)
    return {action for action in handoffs if get_action(action)}


def _handoff_flows(vertical_key: str, findings: list[Any], handoff_actions: set[str]) -> list[dict[str, Any]]:
    flows = [_handoff_flow(vertical_key, finding, handoff_actions) for finding in findings if isinstance(finding, dict)]
    return [flow for flow in flows if flow]


def _handoff_flow(vertical_key: str, finding: dict[str, Any], handoff_actions: set[str]) -> dict[str, Any]:
    key = str(finding.get("key") or "").strip()
    if key in NO_BLOCK_BARRIERS:
        return {}
    if not _blocked_actions_for_barrier(key):
        return {}
    action = _handoff_action_for_barrier(vertical_key, key, handoff_actions)
    if not get_action(action):
        action = DEFAULT_HANDOFF_ACTION
    evidence = str(finding.get("evidence") or "")
    provider = _provider_from_evidence(key, evidence)
    playbook = handoff_playbook_for(key, provider, vertical_key)
    return {
        "key": key or "unknown",
        "kind": BARRIER_KIND_BY_KEY.get(key, "handoff"),
        "title": BARRIER_TITLES.get(key, "Human handoff required"),
        "severity": str(finding.get("severity") or "unknown"),
        "provider": provider,
        "action": action,
        "page_url": str(finding.get("page_url") or ""),
        "evidence": evidence,
        "handling": str(playbook.get("user_message") or finding.get("handling") or "Use admin review or human handoff before continuing."),
        **playbook,
    }


def _handoff_action_for_barrier(vertical_key: str, key: str, handoff_actions: set[str]) -> str:
    if key == "payment_handoff" and PAYMENT_HANDOFF_ACTION in handoff_actions:
        return PAYMENT_HANDOFF_ACTION
    for action in VERTICAL_HANDOFF_ACTIONS.get(str(vertical_key or ""), (DEFAULT_HANDOFF_ACTION,)):
        if action in handoff_actions:
            return action
    return next(iter(sorted(handoff_actions)), DEFAULT_HANDOFF_ACTION)


def _provider_from_evidence(key: str, evidence: str) -> str:
    prefix = PROVIDER_EVIDENCE_PREFIXES.get(key)
    if not prefix or prefix not in evidence:
        return ""
    provider_text = evidence.split(prefix, 1)[1].strip()
    provider = provider_text.split(",", 1)[0].strip()
    return provider[:80]


def _policy_note(finding: dict[str, Any]) -> dict[str, str]:
    return {
        "key": str(finding.get("key") or "unknown"),
        "severity": str(finding.get("severity") or "unknown"),
        "evidence": str(finding.get("evidence") or ""),
        "handling": str(finding.get("handling") or "Use admin review or human handoff before continuing."),
    }


def _runtime_blocked_actions(vertical_config: dict[str, Any]) -> set[str]:
    health = vertical_config.get("action_health") if isinstance(vertical_config, dict) else {}
    blocked = health.get("blocked_actions") if isinstance(health, dict) else []
    if not isinstance(blocked, list):
        return set()
    return {normalize_action_name(action) for action in blocked if get_action(normalize_action_name(action))}


def _runtime_health_notes(vertical_config: dict[str, Any]) -> list[dict[str, str]]:
    health = vertical_config.get("action_health") if isinstance(vertical_config, dict) else {}
    rows = health.get("needs_repair") if isinstance(health, dict) else []
    if not isinstance(rows, list):
        return []
    return [_runtime_health_note(row) for row in rows[:6] if isinstance(row, dict)]


def _runtime_health_note(row: dict[str, Any]) -> dict[str, str]:
    action = normalize_action_name(str(row.get("action") or ""))
    status = str(row.get("status") or "needs_repair")
    reason = str(row.get("last_reason") or row.get("last_stage") or "runtime action failure")
    severity = "high" if status == "blocked" else "medium"
    return {
        "key": f"action_health:{action}",
        "severity": severity,
        "evidence": reason,
        "handling": f"{action} needs adapter repair before automatic execution.",
    }


def _is_handoff_action(action_name: str) -> bool:
    name = normalize_action_name(action_name)
    return name in HUMAN_HANDOFF_ACTIONS or name.endswith("_HANDOFF")
