"""Capability builders for generated adapter actions."""

from __future__ import annotations

from typing import Any

from agent.scanning.scanner_runtime_capabilities import CapabilityFactory


def adapter_action_capabilities(vertical_config: dict[str, Any], capability: CapabilityFactory) -> list[Any]:
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict) or not actions:
        return []

    validation = vertical_config.get("validation")
    validation_actions = validation.get("actions") if isinstance(validation, dict) else {}
    if not isinstance(validation_actions, dict):
        validation_actions = {}

    capabilities = [
        capability(
            name="adapter_action_map",
            supported=True,
            confidence=0.85,
            evidence=f"Generated adapter exposes {len(actions)} action(s).",
        )
    ]
    capabilities.extend(validated_action_caps(actions, validation_actions, capability))
    return capabilities


def validated_action_caps(
    actions: dict[str, Any],
    validation_actions: dict[str, Any],
    capability: CapabilityFactory,
) -> list[Any]:
    capabilities: list[Any] = []
    for action_name, action_config in actions.items():
        evidence = validation_actions.get(action_name)
        capabilities.append(action_capability(action_name, action_config, evidence, capability))
    return capabilities


def action_capability(
    action_name: str,
    action_config: Any,
    evidence: Any,
    capability: CapabilityFactory,
) -> Any:
    if isinstance(evidence, dict):
        supported = bool(evidence.get("supported") or evidence.get("repair"))
        confidence = float(evidence.get("confidence") or 0.55)
        note = str(evidence.get("evidence") or evidence.get("status") or "Browser validation evidence saved.")
        return capability(f"action:{action_name}", supported, min(max(confidence, 0.0), 1.0), note)

    action_type = action_config.get("type") if isinstance(action_config, dict) else "unknown"
    return capability(
        name=f"action:{action_name}",
        supported=True,
        confidence=0.6,
        evidence=f"Generated adapter config has a {action_type} target; browser validation is pending.",
    )
