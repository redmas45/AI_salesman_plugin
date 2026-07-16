"""Runtime adapter config merge and repair helpers."""

from __future__ import annotations

import logging
from typing import Any, Callable

from agent.actions.registry import is_supported_action, normalize_action_name
from agent.adapters.adapter_repair import build_flow_repair_proposals
from agent.adapters.adapter_interaction_learning import candidate_from_interaction
from db.client_domain.actions.client_action_configs import (
    MAX_ADAPTER_ACTIONS,
    validated_action_config,
)
from db.client_domain.actions.client_action_health import VALIDATION_REPAIR_THRESHOLD
from db.client_domain.core.client_serialization import (
    dict_config,
    safe_action_text,
    safe_confidence,
    safe_flow_list,
)

logger = logging.getLogger(__name__)


def refresh_flow_repair_proposals(
    site_id: str,
    vertical_config: dict[str, Any],
    *,
    vertical_key_for_site: Callable[[str], str],
) -> None:
    vertical_config["flow_repair_proposals"] = build_flow_repair_proposals(
        vertical_config=vertical_config,
        vertical_key=vertical_key_for_site(site_id),
    )


def merge_interaction_candidate(raw_candidates: Any, event: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = raw_candidates if isinstance(raw_candidates, list) else []
    candidate = candidate_from_interaction(event)
    if not candidate:
        return safe_flow_list(candidates, MAX_ADAPTER_ACTIONS)

    rows = [candidate, *safe_flow_list(candidates, MAX_ADAPTER_ACTIONS - 1)]
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            safe_action_text(row.get("kind")),
            safe_action_text(row.get("selector")),
            safe_action_text(row.get("path")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:MAX_ADAPTER_ACTIONS]


def merge_learned_action(raw_actions: Any, action_name: str, raw_config: dict[str, Any]) -> dict[str, Any]:
    actions = dict_config(raw_actions).copy()
    normalized = normalize_action_name(action_name)
    if not is_supported_action(normalized):
        return actions
    try:
        clean_config = validated_action_config(raw_config)
    except ValueError as exc:
        logger.info("Ignoring learned adapter action %s: %s", normalized, exc)
        return actions

    existing = dict_config(actions.get(normalized))
    if not existing:
        actions[normalized] = clean_config
        return actions
    if safe_action_text(existing.get("source")) != "browser_interaction":
        return actions
    if safe_confidence(existing.get("confidence"), 0.0) >= safe_confidence(clean_config.get("confidence"), 0.0):
        return actions
    actions[normalized] = clean_config
    return actions


def apply_validation_repairs(vertical_config: dict[str, Any], validation: dict[str, Any]) -> None:
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict):
        return
    for action_name, evidence in validation.get("actions", {}).items():
        repair = evidence.get("repair")
        if not should_apply_repair(evidence, repair) or action_name not in actions:
            continue
        actions[action_name] = validated_action_config({
            **actions[action_name],
            **repair,
            "source": "browser_repair",
            "confidence": max(
                safe_confidence(actions[action_name].get("confidence"), 0.0),
                safe_confidence(repair.get("confidence"), 0.0),
            ),
        })


def should_apply_repair(evidence: dict[str, Any], repair: Any) -> bool:
    if bool(evidence.get("supported")):
        return False
    if not isinstance(repair, dict):
        return False
    return safe_confidence(repair.get("confidence"), 0.0) >= VALIDATION_REPAIR_THRESHOLD
