"""Discovery merge and CRM review helpers for client vertical config."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import config
from agent.actions.registry import is_supported_action, normalize_action_name
from agent.action_helpers.sales_intake import sanitize_intake_questions
from db.client_domain.actions.client_action_configs import MAX_ADAPTER_ACTIONS, validated_action_config, validated_action_map
from db.client_domain.actions.client_action_health import has_crm_action_override, utc_timestamp
from db.client_domain.reports.client_reports import validated_barrier_report
from db.client_domain.core.client_serialization import (
    dict_config,
    safe_action_text,
    safe_confidence,
    safe_flow_list,
    safe_json_value,
    safe_route_map,
    safe_text_list,
)

DISCOVERY_PRESERVED_KEYS = frozenset({
    "action_health",
    "action_proposals",
    "action_proposal_reviews",
    "action_repairs",
    "action_reviews",
    "flow",
    "flow_repair_proposals",
    "flow_repair_reviews",
    "interaction_events",
    "policy_events",
    "regression",
    "rehearsal",
    "validation",
})
DISCOVERY_DIRECT_KEYS = frozenset({
    "discovery",
    "platform",
    "runtime_capabilities",
})


def merge_discovery_vertical_config(
    existing_config: dict[str, Any],
    fresh_config: dict[str, Any],
    *,
    vertical_changed: bool,
) -> dict[str, Any]:
    """Merge browser rediscovery without deleting learned/admin runtime state."""
    existing = dict_config(existing_config)
    fresh = dict_config(fresh_config)
    merged = dict(existing)

    for key in DISCOVERY_DIRECT_KEYS:
        if key in fresh:
            merged[key] = fresh[key]

    merged["routes"] = {
        **dict_config(existing.get("routes")),
        **dict_config(fresh.get("routes")),
    }
    merged["action_candidates"] = merge_discovery_rows(
        fresh.get("action_candidates"),
        existing.get("action_candidates"),
        ("kind", "action", "selector", "path", "label"),
    )
    merged["actions"] = merge_discovery_actions(existing, fresh, vertical_changed=vertical_changed)
    auto_approve_confidence = action_auto_approve_confidence()
    candidates = merged.get("action_candidates")
    if isinstance(candidates, list):
        actions = merged["actions"].copy()
        action_reviews = list(merged.get("action_reviews") or [])
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            confidence = 0.0
            try:
                confidence = float(candidate.get("confidence") or 0.0)
            except (ValueError, TypeError):
                pass

            review_status = str(candidate.get("review") or "").lower()
            action_name = str(candidate.get("action") or "")
            if confidence >= auto_approve_confidence and review_status != "reject" and action_name:
                candidate["review"] = "approve"
                try:
                    action_config = action_config_from_candidate(candidate, actions.get(action_name))
                    actions[action_name] = action_config

                    review = action_candidate_review(candidate, "approve", action_name=action_name)
                    action_reviews = merge_action_reviews(review, action_reviews)
                except Exception:
                    pass
        merged["actions"] = actions
        merged["action_reviews"] = action_reviews

    merged["prompt_suggestions"] = merge_discovery_texts(
        fresh.get("prompt_suggestions"),
        existing.get("prompt_suggestions"),
    )
    merged["intake_questions"] = merge_intake_questions(
        fresh.get("intake_questions"),
        existing.get("intake_questions"),
        vertical_changed=vertical_changed,
    )
    merged["barriers"] = merge_discovery_barriers(existing.get("barriers"), fresh.get("barriers"))

    for key, value in fresh.items():
        if key in merged or key in DISCOVERY_PRESERVED_KEYS:
            continue
        merged[key] = value
    return merged


def action_auto_approve_confidence() -> float:
    value = os.getenv("ACTION_AUTO_APPROVE_CONFIDENCE", config.ACTION_AUTO_APPROVE_CONFIDENCE)
    return max(0.0, min(safe_confidence(value, 0.75), 1.0))


def merge_discovery_actions(existing: dict[str, Any], fresh: dict[str, Any], *, vertical_changed: bool) -> dict[str, Any]:
    existing_actions = dict_config(existing.get("actions"))
    fresh_actions = dict_config(fresh.get("actions"))
    if has_crm_action_override(existing):
        return existing_actions
    if vertical_changed:
        return fresh_actions
    return {**existing_actions, **fresh_actions}


def merge_intake_questions(fresh_value: Any, existing_value: Any, *, vertical_changed: bool) -> list[dict[str, Any]]:
    fresh = sanitize_intake_questions(fresh_value)
    existing = sanitize_intake_questions(existing_value)
    if vertical_changed:
        return fresh
    return fresh or existing


def action_candidate_review(
    candidate: dict[str, Any],
    decision: str,
    *,
    action_name: str = "",
    note: str = "",
) -> dict[str, Any]:
    row = dict_config(candidate)
    action = normalize_action_name(action_name or safe_action_text(row.get("action")))
    if not is_supported_action(action):
        raise ValueError("Action candidate does not map to a supported action.")
    return {
        "key": action_candidate_key(row, action),
        "action": action,
        "decision": decision,
        "kind": safe_action_text(row.get("kind")),
        "type": safe_action_text(row.get("type")),
        "label": safe_action_text(row.get("label")),
        "selector": safe_action_text(row.get("selector")),
        "path": safe_action_text(row.get("path")),
        "confidence": safe_confidence(row.get("confidence"), 0.0),
        "note": safe_action_text(note),
        "reviewed_at": utc_timestamp(),
    }


def approve_action_candidate(vertical_config: dict[str, Any], candidate: dict[str, Any], action_name: str) -> None:
    actions = dict_config(vertical_config.get("actions")).copy()
    action_config = action_config_from_candidate(candidate, actions.get(action_name))
    actions[action_name] = action_config
    vertical_config["actions"] = actions
    vertical_config.setdefault("overrides", {})["actions"] = {
        "source": "crm",
        "updated": True,
        "approved_action": action_name,
    }


def action_config_from_candidate(candidate: dict[str, Any], existing_config: Any) -> dict[str, Any]:
    row = dict_config(candidate)
    action_type = safe_action_text(row.get("type")).lower()
    selector = safe_action_text(row.get("selector"))
    path = safe_candidate_path(row.get("path"))
    base = {
        "label": safe_action_text(row.get("label")),
        "source": "crm_approved_candidate",
        "confidence": max(safe_confidence(row.get("confidence"), 0.7), 0.7),
    }
    if action_type == "click" and selector:
        return validated_action_config({**base, "type": "click", "selector": selector})
    if action_type in {"navigate", "click"} and path:
        return validated_action_config({**base, "type": "navigate", "path": path})
    if action_type in {"form", "sequence"}:
        return existing_candidate_config(existing_config, base)
    raise ValueError("Approved action candidate has no safe executable target.")


def existing_candidate_config(existing_config: Any, base: dict[str, Any]) -> dict[str, Any]:
    existing = dict_config(existing_config)
    if not existing:
        raise ValueError("Form and sequence candidates require an existing generated action config.")
    return validated_action_config({**existing, **base})


def safe_candidate_path(value: Any) -> str:
    path = safe_action_text(value)
    if not path or path.lower().startswith(("http://", "https://", "javascript:", "data:")):
        return ""
    return path if path.startswith("/") else ""


def merge_action_reviews(review: dict[str, Any], existing_reviews: Any) -> list[dict[str, Any]]:
    rows = [review, *safe_flow_list(existing_reviews, MAX_ADAPTER_ACTIONS - 1)]
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = safe_action_text(row.get("key"))
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged[:MAX_ADAPTER_ACTIONS]


def action_proposal_review(proposal: dict[str, Any], decision: str, *, note: str = "") -> dict[str, Any]:
    row = dict_config(proposal)
    action = normalize_action_name(safe_action_text(row.get("action")))
    if not is_supported_action(action):
        raise ValueError("Action proposal does not map to a supported action.")
    action_config = validated_action_config(row.get("config"))
    return {
        "key": action_proposal_key(row, action, action_config),
        "action": action,
        "decision": decision,
        "kind": safe_action_text(row.get("kind")),
        "source": safe_action_text(row.get("source")),
        "type": safe_action_text(action_config.get("type")),
        "selector": safe_action_text(action_config.get("selector") or action_config.get("input")),
        "path": safe_action_text(action_config.get("path")),
        "confidence": safe_confidence(row.get("confidence"), 0.0),
        "note": safe_action_text(note),
        "reviewed_at": utc_timestamp(),
    }


def approve_action_proposal(vertical_config: dict[str, Any], proposal: dict[str, Any], action_name: str) -> None:
    actions = dict_config(vertical_config.get("actions")).copy()
    current = dict_config(actions.get(action_name))
    proposed = validated_action_config(dict_config(proposal).get("config"))
    actions[action_name] = validated_action_config(
        {
            **current,
            **proposed,
            "source": "crm_approved_proposal",
            "confidence": max(
                safe_confidence(current.get("confidence"), 0.0),
                safe_confidence(proposed.get("confidence"), 0.0),
            ),
        }
    )
    vertical_config["actions"] = actions
    vertical_config.setdefault("overrides", {})["actions"] = {
        "source": "crm",
        "updated": True,
        "approved_action": action_name,
    }


def flow_repair_review(proposal: dict[str, Any], decision: str, *, note: str = "") -> dict[str, Any]:
    row = dict_config(proposal)
    patch = validated_flow_repair_patch(row.get("patch"), require_patch=decision == "approve")
    return {
        "key": flow_repair_proposal_key(row, patch),
        "proposal_key": safe_action_text(row.get("key")),
        "decision": decision,
        "kind": safe_action_text(row.get("kind")),
        "scope": safe_action_text(row.get("scope")),
        "item": safe_action_text(row.get("item")),
        "confidence": safe_confidence(row.get("confidence"), 0.0),
        "note": safe_action_text(note),
        "patch": safe_json_value(patch),
        "reviewed_at": utc_timestamp(),
    }


def approve_flow_repair_proposal(vertical_config: dict[str, Any], proposal: dict[str, Any]) -> None:
    patch = validated_flow_repair_patch(dict_config(proposal).get("patch"), require_patch=True)
    route_patch = safe_route_map(patch.get("routes"))
    action_patch = validated_action_map(dict_config(patch.get("actions")))
    if route_patch:
        vertical_config["routes"] = {**dict_config(vertical_config.get("routes")), **route_patch}
    if action_patch:
        vertical_config["actions"] = {**dict_config(vertical_config.get("actions")), **action_patch}
    vertical_config.setdefault("overrides", {})["flow_repairs"] = {
        "source": "crm",
        "updated": True,
        "approved_item": safe_action_text(dict_config(proposal).get("item")),
    }


def validated_flow_repair_patch(raw_patch: Any, *, require_patch: bool) -> dict[str, Any]:
    patch = dict_config(raw_patch)
    route_patch = safe_route_map(patch.get("routes"))
    action_patch = validated_action_map(dict_config(patch.get("actions")))
    if require_patch and not route_patch and not action_patch:
        raise ValueError("Flow repair proposal has no safe route or action patch.")
    return {"routes": route_patch, "actions": action_patch}


def action_proposal_key(proposal: dict[str, Any], action_name: str, action_config: dict[str, Any]) -> str:
    parts = [
        action_name,
        safe_action_text(proposal.get("kind")),
        safe_action_text(proposal.get("source")),
        safe_action_text(action_config.get("type")),
        safe_action_text(action_config.get("selector") or action_config.get("input")),
        safe_action_text(action_config.get("path")),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def flow_repair_proposal_key(proposal: dict[str, Any], patch: dict[str, Any]) -> str:
    parts = [
        safe_action_text(proposal.get("key")),
        safe_action_text(proposal.get("kind")),
        safe_action_text(proposal.get("scope")),
        safe_action_text(proposal.get("item")),
        json.dumps(safe_json_value(patch), sort_keys=True),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def action_candidate_key(candidate: dict[str, Any], action_name: str) -> str:
    parts = [
        action_name,
        safe_action_text(candidate.get("kind")),
        safe_action_text(candidate.get("type")),
        safe_action_text(candidate.get("selector")),
        safe_action_text(candidate.get("path")),
        safe_action_text(candidate.get("label")),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def merge_discovery_rows(new_rows: Any, old_rows: Any, key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    rows = [*safe_flow_list(new_rows, MAX_ADAPTER_ACTIONS), *safe_flow_list(old_rows, MAX_ADAPTER_ACTIONS)]
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(safe_action_text(row.get(field)) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged[:MAX_ADAPTER_ACTIONS]


def merge_discovery_texts(new_values: Any, old_values: Any) -> list[str]:
    values = [*safe_text_list(new_values, 20), *safe_text_list(old_values, 20)]
    return list(dict.fromkeys(values))[:20]


def merge_discovery_barriers(existing_barriers: Any, fresh_barriers: Any) -> dict[str, Any]:
    existing = validated_barrier_report(existing_barriers)
    fresh = validated_barrier_report(fresh_barriers)
    findings = merge_discovery_rows(fresh.get("findings"), existing.get("findings"), ("key", "page_url", "evidence"))
    return {
        "site_id": safe_action_text(fresh.get("site_id") or existing.get("site_id")),
        "site_url": safe_action_text(fresh.get("site_url") or existing.get("site_url")),
        "summary": barrier_summary(findings),
        "findings": findings,
        "detected_at": safe_action_text(fresh.get("detected_at") or existing.get("detected_at")),
    }


def barrier_summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(findings),
        "high": barrier_severity_count(findings, "high"),
        "medium": barrier_severity_count(findings, "medium"),
        "low": barrier_severity_count(findings, "low"),
        "keys": sorted({safe_action_text(finding.get("key")) for finding in findings if safe_action_text(finding.get("key"))}),
    }


def barrier_severity_count(findings: list[dict[str, Any]], severity: str) -> int:
    return sum(1 for finding in findings if safe_action_text(finding.get("severity")).lower() == severity)
