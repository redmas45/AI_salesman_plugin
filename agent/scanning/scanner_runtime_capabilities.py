"""Capability builders for discovered flow runtime data."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class CapabilityFactory(Protocol):
    def __call__(
        self,
        name: str,
        supported: bool,
        confidence: float,
        evidence: str,
        blocking: bool = True,
    ) -> Any: ...


BarrierPolicyBuilder = Callable[[dict[str, Any], str], dict[str, Any]]


def flow_capabilities(vertical_config: dict[str, Any], capability: CapabilityFactory) -> list[Any]:
    flow = vertical_config.get("flow")
    if not isinstance(flow, dict):
        return []
    summary = flow.get("summary") if isinstance(flow.get("summary"), dict) else {}
    pages = int(summary.get("pages") or 0)
    actions = int(summary.get("actions") or 0)
    prompts = len(flow.get("prompt_suggestions") or [])
    engine = str(flow.get("engine") or "unknown")
    adapter_actions = adapter_action_count(vertical_config)
    graph_supported = pages > 0 and (actions > 0 or adapter_actions > 0)
    graph_confidence = 0.85 if pages > 0 and actions > 0 else 0.75 if graph_supported else 0.35
    if pages > 0 and actions == 0 and adapter_actions > 0:
        graph_evidence = (
            f"{engine} discovery mapped {pages} page(s) and 0 static action candidate(s); "
            f"generated adapter exposes {adapter_actions} runtime action(s) for the JS app."
        )
    else:
        graph_evidence = f"{engine} discovery mapped {pages} page(s) and {actions} action candidate(s)."
    return [
        capability(
            "flow_graph",
            graph_supported,
            graph_confidence,
            graph_evidence,
        ),
        capability(
            "flow_prompt_suggestions",
            prompts > 0,
            0.8 if prompts > 0 else 0.25,
            f"Flow discovery generated {prompts} customer prompt suggestion(s).",
        ),
    ]


def rehearsal_capabilities(vertical_config: dict[str, Any], capability: CapabilityFactory) -> list[Any]:
    rehearsal = vertical_config.get("rehearsal")
    if not isinstance(rehearsal, dict):
        return []
    summary = rehearsal.get("summary") if isinstance(rehearsal.get("summary"), dict) else {}
    total = int(summary.get("total") or 0)
    supported = int(summary.get("supported") or 0)
    blocked = int(summary.get("blocked") or 0)
    needs_confirmation = int(summary.get("needs_confirmation") or 0)
    engine = str(rehearsal.get("engine") or "unknown")
    adapter_actions = adapter_action_count(vertical_config)
    validated_actions = validated_adapter_action_count(vertical_config)
    fallback_supported = total == 0 and adapter_actions > 0 and validated_actions > 0
    if fallback_supported:
        rehearsal_supported = True
        rehearsal_confidence = 0.75
        rehearsal_evidence = (
            f"{engine} rehearsal had no generated flow targets; "
            f"browser validation supports {validated_actions}/{adapter_actions} adapter action(s)."
        )
        confirmation_supported = True
        confirmation_confidence = 0.6
        confirmation_evidence = (
            "No generated flow targets required confirmation; runtime adapter actions remain governed by action policy."
        )
    else:
        rehearsal_supported = total > 0 and supported > 0 and supported >= max(1, total - blocked)
        rehearsal_confidence = 0.9 if total > 0 and blocked == 0 else 0.7 if supported > 0 else 0.25
        rehearsal_evidence = f"{engine} rehearsal verified {supported}/{total} generated flow target(s); {blocked} blocked."
        confirmation_supported = total > 0
        confirmation_confidence = 0.8 if total > 0 else 0.2
        confirmation_evidence = f"{needs_confirmation} rehearsed action(s) require user confirmation before final completion."
    return [
        capability(
            "flow_rehearsal",
            rehearsal_supported,
            rehearsal_confidence,
            rehearsal_evidence,
        ),
        capability(
            "flow_confirmation_policy",
            confirmation_supported,
            confirmation_confidence,
            confirmation_evidence,
        ),
    ]


def adapter_action_count(vertical_config: dict[str, Any]) -> int:
    actions = vertical_config.get("actions")
    return len(actions) if isinstance(actions, dict) else 0


def validated_adapter_action_count(vertical_config: dict[str, Any]) -> int:
    validation = vertical_config.get("validation")
    validation_actions = validation.get("actions") if isinstance(validation, dict) else {}
    if not isinstance(validation_actions, dict):
        return 0
    return sum(
        1
        for evidence in validation_actions.values()
        if isinstance(evidence, dict) and (evidence.get("supported") or evidence.get("repair"))
    )


def regression_capabilities(vertical_config: dict[str, Any], capability: CapabilityFactory) -> list[Any]:
    regression = vertical_config.get("regression")
    if not isinstance(regression, dict):
        return []
    summary = regression.get("summary") if isinstance(regression.get("summary"), dict) else {}
    status = str(regression.get("status") or "unknown")
    high = int(summary.get("high") or 0)
    medium = int(summary.get("medium") or 0)
    changes = int(summary.get("changes") or 0)
    supported = status in {"baseline", "stable"} or high == 0
    confidence = 0.9 if status in {"baseline", "stable"} else 0.65 if high == 0 else 0.25
    return [
        capability(
            "flow_regression",
            supported,
            confidence,
            f"Flow regression status is {status}; {changes} change(s), {high} high severity, {medium} medium severity.",
        )
    ]


def barrier_capabilities(
    vertical_config: dict[str, Any],
    vertical_key: str,
    capability: CapabilityFactory,
    build_barrier_policy: BarrierPolicyBuilder,
) -> list[Any]:
    barriers = vertical_config.get("barriers")
    if not isinstance(barriers, dict):
        return []
    summary = barriers.get("summary") if isinstance(barriers.get("summary"), dict) else {}
    total = int(summary.get("total") or 0)
    high = int(summary.get("high") or 0)
    medium = int(summary.get("medium") or 0)
    keys = summary.get("keys") if isinstance(summary.get("keys"), list) else []
    action_policy = build_barrier_policy(vertical_config, vertical_key)
    managed = high > 0 and bool(action_policy.get("handoff_flows"))
    supported = high == 0 or managed
    confidence = 0.9 if total == 0 else 0.75 if managed else 0.65 if high == 0 else 0.2
    handoffs = action_policy.get("handoff_actions") if isinstance(action_policy.get("handoff_actions"), list) else []
    suffix = f" Managed by handoff policy: {', '.join(handoffs[:4])}." if managed and handoffs else ""
    return [
        capability(
            "flow_barriers",
            supported,
            confidence,
            f"Discovery detected {total} hard-flow barrier(s): {high} high, {medium} medium. {', '.join(str(key) for key in keys[:6])}.{suffix}",
            blocking=not managed,
        )
    ]
