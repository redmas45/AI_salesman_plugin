"""
Runtime Capability Engine — filter AI actions by site readiness.

Reads the readiness report for a site and determines which UI actions
the AI is allowed to perform. Unsupported actions are filtered out
before being sent to the client widget.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

import config
from agent.actions.registry import get_action, list_action_names, list_actions, normalize_action_name
from agent.action_helpers.action_readiness import action_readiness_for, action_readiness_prompt_context
from agent.action_helpers.barrier_policy import apply_barrier_policy, barrier_policy_prompt_context, build_barrier_action_policy
from agent.action_helpers.capability_action_params import (
    adapter_action_field_context,
    clean_action_fields,
    missing_required_action_params,
)
from agent.verticals.registry import DEFAULT_VERTICAL_KEY, get_vertical
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)

# Actions that are always safe — they only show information or navigate
SAFE_ACTION_FAMILIES: frozenset[str] = frozenset({"discovery", "navigation", "session"})


def _always_allowed_actions() -> frozenset[str]:
    """Return actions that only show data, navigate, or manage the chat session."""
    return frozenset(
        action.name
        for action in list_actions()
        if action.family in SAFE_ACTION_FAMILIES
        and not action.requires_cart
        and not action.requires_checkout
    )


ALWAYS_ALLOWED_ACTIONS: frozenset[str] = _always_allowed_actions()

# Actions that require cart capability
CART_ACTIONS: frozenset[str] = frozenset({
    "ADD_TO_CART",
    "REMOVE_FROM_CART",
    "CLEAR_CART",
    "UPDATE_CART_QUANTITY",
})

# Actions that require checkout capability
CHECKOUT_ACTIONS: frozenset[str] = frozenset({
    "CHECKOUT",
})

ECOMMERCE_DISCOVERY_ACTIONS: frozenset[str] = frozenset({
    "SHOW_PRODUCTS",
    "SHOW_COMPARISON",
    "FILTER_PRODUCTS",
    "SORT_PRODUCTS",
    "SHOW_PRODUCT_DETAIL",
    "CLEAR_FILTERS",
})
FILTER_REASON_INVALID = "invalid_action_payload"
FILTER_REASON_UNSUPPORTED = "unsupported_action"
FILTER_REASON_BLOCKED = "blocked_by_policy"
FILTER_REASON_RUNTIME_BLOCKED = "blocked_by_action_health"
FILTER_REASON_MISSING_PARAMS = "missing_required_params"
FILTER_STATUS_UNCHANGED = "unchanged"
FILTER_STATUS_CHANGED = "changed"


@dataclass(frozen=True)
class FilteredActionNotice:
    """One action removed by capability filtering."""

    action: str
    reason: str
    message: str
    missing_params: tuple[str, ...] = ()
    question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_allowed_actions(site_id: str) -> set[str]:
    """Return the set of UI action types this site supports."""
    vertical_key = _client_vertical_key(site_id)
    configured_actions = _configured_adapter_actions(site_id)
    if configured_actions:
        return _allowed_configured_actions(site_id, vertical_key, configured_actions)

    if vertical_key != "ecommerce":
        return _allowed_vertical_actions(site_id)

    report = admin_db.get_readiness_report(site_id)
    if not report:
        # No scan yet — allow everything for backward compatibility
        return apply_barrier_policy(set(config.VALID_UI_ACTIONS), _client_vertical_config(site_id), vertical_key)

    capabilities = {
        cap["name"]: cap
        for cap in report.get("capabilities", [])
    }

    allowed: set[str] = set(ALWAYS_ALLOWED_ACTIONS)

    cart_cap = capabilities.get("cart", {})
    if cart_cap.get("supported", False):
        allowed |= CART_ACTIONS

    checkout_cap = capabilities.get("checkout", {})
    if checkout_cap.get("supported", False):
        allowed |= CHECKOUT_ACTIONS

    return apply_barrier_policy({action for action in allowed if get_action(action)}, _client_vertical_config(site_id), vertical_key)


def _allowed_configured_actions(site_id: str, vertical_key: str, configured_actions: set[str]) -> set[str]:
    allowed = set(ALWAYS_ALLOWED_ACTIONS)
    allowed.update(action for action in configured_actions if get_action(action))
    if vertical_key == "ecommerce":
        allowed.update(action for action in ECOMMERCE_DISCOVERY_ACTIONS if get_action(action))

    validation = _adapter_validation_actions(site_id)
    for action_name in list(configured_actions):
        evidence = validation.get(action_name)
        if evidence and not evidence.get("supported") and not evidence.get("repair"):
            allowed.discard(action_name)
    return apply_barrier_policy({action for action in allowed if get_action(action)}, _client_vertical_config(site_id), vertical_key)


def _client_vertical_key(site_id: str) -> str:
    try:
        client = admin_db._client_row(site_id)
    except Exception as exc:
        logger.warning("Capability lookup could not load client %s: %s", site_id, exc)
        client = None
    return str((client or {}).get("vertical_key") or DEFAULT_VERTICAL_KEY)


def _client_vertical_config(site_id: str) -> dict[str, Any]:
    try:
        client = admin_db._client_row(site_id)
    except Exception as exc:
        logger.warning("Adapter config lookup could not load client %s: %s", site_id, exc)
        return {}
    raw_config = (client or {}).get("vertical_config_json")
    if isinstance(raw_config, dict):
        return raw_config
    try:
        parsed = json.loads(str(raw_config or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _configured_adapter_actions(site_id: str) -> set[str]:
    return set(_configured_action_configs(_client_vertical_config(site_id)))


def _configured_action_configs(vertical_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict):
        return {}
    return {
        normalize_action_name(action): action_config
        for action, action_config in actions.items()
        if get_action(str(action)) and isinstance(action_config, dict)
    }


def _adapter_validation_actions(site_id: str) -> dict[str, Any]:
    validation = _client_vertical_config(site_id).get("validation")
    if not isinstance(validation, dict):
        return {}
    actions = validation.get("actions")
    if not isinstance(actions, dict):
        return {}
    return {
        normalize_action_name(action): evidence
        for action, evidence in actions.items()
        if str(action).strip() and isinstance(evidence, dict)
    }


def _readiness_by_action(vertical_config: dict[str, Any], vertical_key: str) -> dict[str, dict[str, Any]]:
    return {row["action"]: row for row in action_readiness_for(vertical_config, vertical_key)}


def _invalid_action_notice() -> FilteredActionNotice:
    return FilteredActionNotice(
        action="<invalid>",
        reason=FILTER_REASON_INVALID,
        message="The generated action payload was invalid, so it was not sent to the website.",
    )


def _unsupported_action_notice(action_name: str, action_policy: dict[str, Any]) -> FilteredActionNotice:
    clean_action = action_name or "<missing>"
    reason = _unsupported_reason(clean_action, action_policy)
    return FilteredActionNotice(
        action=clean_action,
        reason=reason,
        message=_unsupported_message(clean_action, reason),
    )


def _missing_params_notice(
    action_name: str,
    missing_params: list[str],
    readiness: dict[str, Any] | None,
) -> FilteredActionNotice:
    question = _missing_param_question(missing_params)
    return FilteredActionNotice(
        action=action_name,
        reason=FILTER_REASON_MISSING_PARAMS,
        message=f"{action_name} needs {', '.join(missing_params)} before it can run.",
        missing_params=tuple(missing_params),
        question=question,
    )


def _unsupported_reason(action_name: str, action_policy: dict[str, Any]) -> str:
    if action_name in set(action_policy.get("runtime_blocked_actions") or []):
        return FILTER_REASON_RUNTIME_BLOCKED
    if action_name in set(action_policy.get("blocked_actions") or []):
        return FILTER_REASON_BLOCKED
    return FILTER_REASON_UNSUPPORTED


def _unsupported_message(action_name: str, reason: str) -> str:
    if reason == FILTER_REASON_BLOCKED:
        return f"{action_name} is blocked by this site's safety policy and needs handoff or admin repair."
    if reason == FILTER_REASON_RUNTIME_BLOCKED:
        return f"{action_name} is paused because recent browser execution failed and needs adapter repair."
    return f"{action_name} is not currently available for this client website."


def _missing_param_question(missing_params: list[str]) -> str:
    labels = [_missing_param_label(param) for param in missing_params if str(param or "").strip()]
    if not labels:
        return "Please provide the missing detail."
    if labels == ["age of eldest member"]:
        return "What is the age of the eldest member?"
    if labels == ["city"]:
        return "Which city should I use?"
    if len(labels) == 1:
        return f"Please provide {labels[0]}."
    return f"Please provide {', '.join(labels[:-1])} and {labels[-1]}."


def _missing_param_label(param: str) -> str:
    key = str(param or "").strip().lower().replace("-", "_")
    labels = {
        "age_of_eldest_member": "age of eldest member",
        "coverage_type": "coverage type",
        "full_name": "full name",
        "phone_number": "phone number",
        "mobile_number": "phone number",
    }
    return labels.get(key, key.replace("_", " "))


def _allowed_vertical_actions(site_id: str) -> set[str]:
    vertical = _client_vertical(site_id)
    allowed = {action for action in vertical.action_types if get_action(action)}
    allowed.update(action for action in ALWAYS_ALLOWED_ACTIONS if get_action(action))
    allowed.update({"CLEAR_HISTORY", "UPDATE_PREFERENCES"})

    report = admin_db.get_readiness_report(site_id)
    if not report:
        return apply_barrier_policy(allowed or list_action_names(), _client_vertical_config(site_id), vertical.key)

    capabilities = {cap["name"]: cap for cap in report.get("capabilities", [])}
    if not capabilities.get("cart", {}).get("supported", False):
        allowed -= CART_ACTIONS
    if not capabilities.get("checkout", {}).get("supported", False):
        allowed -= CHECKOUT_ACTIONS
    return apply_barrier_policy(allowed, _client_vertical_config(site_id), vertical.key)


def _client_vertical(site_id: str):
    try:
        return get_vertical(_client_vertical_key(site_id))
    except ValueError:
        return get_vertical("generic")


def filter_actions(site_id: str, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove actions that the site does not support."""
    return filter_actions_with_diagnostics(site_id, actions)["actions"]


def filter_actions_with_diagnostics(site_id: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Remove unsupported actions and explain every removal."""
    allowed = get_allowed_actions(site_id)
    vertical_config = _client_vertical_config(site_id)
    vertical_key = _client_vertical_key(site_id)
    action_configs = _configured_action_configs(vertical_config)
    action_policy = build_barrier_action_policy(vertical_config, vertical_key)
    readiness = _readiness_by_action(vertical_config, vertical_key)
    filtered: list[dict[str, Any]] = []
    notices: list[FilteredActionNotice] = []

    for action in actions:
        if not isinstance(action, dict):
            notices.append(_invalid_action_notice())
            continue

        action_name = normalize_action_name(action.get("action"))
        if action_name not in allowed:
            notices.append(_unsupported_action_notice(action_name, action_policy))
            continue

        missing_params = missing_required_action_params(action, action_configs.get(action_name))
        if missing_params:
            notices.append(_missing_params_notice(action_name, missing_params, readiness.get(action_name)))
            continue

        filtered.append(action)

    if notices:
        logger.info(
            "Capability filter removed %d action(s) for %s: %s",
            len(notices),
            site_id,
            [notice.to_dict() for notice in notices],
        )

    return {
        "status": FILTER_STATUS_CHANGED if notices else FILTER_STATUS_UNCHANGED,
        "actions": filtered,
        "removed_actions": [notice.to_dict() for notice in notices],
    }


def capability_summary(site_id: str) -> dict[str, Any]:
    """Return a human-readable capability summary for the CRM."""
    report = admin_db.get_readiness_report(site_id)
    if not report:
        return {
            "scanned": False,
            "platform": "unknown",
            "platform_confidence": 0.0,
            "supported": [],
            "unsupported": [],
        }

    capabilities = report.get("capabilities", [])
    supported = [
        cap["name"] for cap in capabilities
        if cap.get("supported", False)
    ]
    unsupported = [
        cap["name"] for cap in capabilities
        if not cap.get("supported", False) and cap.get("blocking", True) is not False
    ]

    return {
        "scanned": True,
        "platform": report.get("platform", "unknown"),
        "platform_confidence": report.get("platform_confidence", 0.0),
        "supported": supported,
        "unsupported": unsupported,
        "action_policy": build_barrier_action_policy(_client_vertical_config(site_id), _client_vertical_key(site_id)),
        "scanned_at": report.get("scanned_at", ""),
    }


def action_filter_response_note(filter_report: dict[str, Any]) -> str:
    """Return a user-facing correction when generated actions were removed."""
    notices = filter_report.get("removed_actions") if isinstance(filter_report, dict) else []
    if not isinstance(notices, list) or not notices:
        return ""
    first_notice = next((notice for notice in notices if isinstance(notice, dict)), {})
    if not first_notice:
        return ""
    if _safe_notice_reason(first_notice) == FILTER_REASON_MISSING_PARAMS:
        return _missing_params_response_note(first_notice)
    return _blocked_response_note(first_notice)


def _missing_params_response_note(notice: dict[str, Any]) -> str:
    question = str(notice.get("question") or "").strip()
    missing = clean_action_fields(notice.get("missing_params"))
    if question:
        return f"I need one more detail before I can do that: {question}"
    if missing:
        return f"I need {', '.join(missing)} before I can do that."
    return "I need one more detail before I can do that."


def _blocked_response_note(notice: dict[str, Any]) -> str:
    message = str(notice.get("message") or "").strip()
    if message:
        return message
    return "That website action is not available right now, so I can guide you instead."


def _safe_notice_reason(notice: dict[str, Any]) -> str:
    return str(notice.get("reason") or "").strip()


def capability_prompt_context(site_id: str) -> str:
    """
    Return a prompt fragment describing the site's capabilities.

    Injected into the LLM system prompt to prevent the AI from suggesting
    actions the website does not support.
    """
    vertical_config = _client_vertical_config(site_id)
    vertical_key = _client_vertical_key(site_id)
    report = admin_db.get_readiness_report(site_id)
    barrier_context = barrier_policy_prompt_context(site_id, vertical_config, vertical_key)
    action_field_context = adapter_action_field_context(vertical_config)
    action_readiness_context = action_readiness_prompt_context(vertical_config, vertical_key)
    if not report:
        return " ".join(part for part in (action_field_context, action_readiness_context, barrier_context) if part)

    capabilities = report.get("capabilities", [])
    supported = [cap["name"] for cap in capabilities if cap.get("supported")]
    unsupported = [cap["name"] for cap in capabilities if not cap.get("supported")]
    platform = report.get("platform", "unknown")

    lines: list[str] = []
    lines.append(f"Client website platform: {platform}.")
    if supported:
        lines.append(f"Supported capabilities: {', '.join(supported)}.")
    if unsupported:
        lines.append(f"Unsupported capabilities: {', '.join(unsupported)}.")
    if "cart" not in supported:
        lines.append("Do NOT suggest adding items to cart or cart operations.")
    if "checkout" not in supported:
        lines.append("Do NOT suggest checkout or order placement.")
    if "variants" not in supported:
        lines.append("Do NOT ask about product sizes or color variants.")
    if action_field_context:
        lines.append(action_field_context)
    if action_readiness_context:
        lines.append(action_readiness_context)
    if barrier_context:
        lines.append(barrier_context)

    return " ".join(lines)
