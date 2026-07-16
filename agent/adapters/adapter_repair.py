"""Optional LLM-assisted repair for generated adapter action targets."""

from __future__ import annotations

import json
import logging
from typing import Any

import config
from agent.actions.registry import is_supported_action, normalize_action_name
from agent.adapters.adapter_flow_repair import (
    build_flow_repair_proposals as _build_flow_repair_proposals,
    request_flow_repairs_default as _default_request_flow_repairs,
)
from agent.adapters.adapter_repair_validation import (
    REPAIR_MIN_CONFIDENCE,
    clean_target,
    confidence as normalized_confidence,
    json_response,
    repair_action_payload,
    validated_repair,
)
from agent.providers.azure_openai import create_chat_completion

logger = logging.getLogger(__name__)

MAX_HTML_SAMPLE_CHARS = 6000
REPAIR_MAX_TOKENS = 700
MAX_REPAIR_PROPOSALS = 30

REPAIR_SYSTEM_PROMPT = (
    "You repair website adapter actions from HTML. Return only JSON. "
    "For each requested action, output a better target if visible in the HTML. "
    "Allowed action target types are navigate, click, and form. "
    "Never invent business facts. Never return external URLs."
)

_request_flow_repairs = _default_request_flow_repairs


def repair_actions_from_html(
    *,
    html_sample: str,
    vertical_key: str,
    actions: dict[str, Any],
    site_id: str,
) -> dict[str, Any]:
    """Return actions merged with high-confidence LLM selector repairs."""
    if not _repair_enabled(html_sample, actions):
        return actions

    repaired = _request_repairs(html_sample, vertical_key, actions, site_id)
    if not repaired:
        return actions

    merged = dict(actions)
    for action_name, repair in repaired.items():
        if action_name not in merged:
            continue
        merged[action_name] = {**merged[action_name], **repair, "source": "llm_repair"}
    return merged


def build_action_repair_proposals(
    *,
    vertical_config: dict[str, Any],
    vertical_key: str,
) -> list[dict[str, Any]]:
    """Build CRM-reviewable action repair proposals from runtime evidence."""
    proposals = [
        *_runtime_health_proposals(vertical_config),
        *_validation_repair_proposals(vertical_config),
        *_candidate_proposals(vertical_config),
    ]
    return _dedupe_proposals(proposals, vertical_key)[:MAX_REPAIR_PROPOSALS]


def build_flow_repair_proposals(
    *,
    vertical_config: dict[str, Any],
    vertical_key: str,
) -> list[dict[str, Any]]:
    return _build_flow_repair_proposals(
        vertical_config=vertical_config,
        vertical_key=vertical_key,
        request_flow_repairs=_request_flow_repairs,
    )


def _repair_enabled(html_sample: str, actions: dict[str, Any]) -> bool:
    return bool(
        config.LLM_EXTRACTOR_ENABLED
        and config.AZURE_OPENAI_API_KEY
        and html_sample.strip()
        and isinstance(actions, dict)
        and actions
    )


def _runtime_health_proposals(vertical_config: dict[str, Any]) -> list[dict[str, Any]]:
    health = vertical_config.get("action_health") if isinstance(vertical_config, dict) else {}
    rows = health.get("needs_repair") if isinstance(health, dict) else []
    if not isinstance(rows, list):
        return []
    proposals: list[dict[str, Any]] = []
    for row in rows[:MAX_REPAIR_PROPOSALS]:
        if not isinstance(row, dict):
            continue
        repair = validated_repair(row.get("repair_candidate"))
        action_name = normalize_action_name(str(row.get("action") or ""))
        if not is_supported_action(action_name) or not repair:
            continue
        proposals.append(
            _proposal(
                action_name=action_name,
                kind="runtime_repair",
                source="action_health",
                confidence=repair.get("confidence"),
                reason=str(row.get("last_reason") or "Runtime action failed and has a matching browser interaction."),
                config=repair,
            )
        )
    return proposals


def _validation_repair_proposals(vertical_config: dict[str, Any]) -> list[dict[str, Any]]:
    validation = vertical_config.get("validation") if isinstance(vertical_config, dict) else {}
    actions = validation.get("actions") if isinstance(validation, dict) else {}
    if not isinstance(actions, dict):
        return []
    proposals: list[dict[str, Any]] = []
    for action_name, evidence in list(actions.items())[:MAX_REPAIR_PROPOSALS]:
        if not isinstance(evidence, dict):
            continue
        repair = validated_repair(evidence.get("repair"))
        normalized = normalize_action_name(str(action_name or ""))
        if not is_supported_action(normalized) or not repair:
            continue
        proposals.append(
            _proposal(
                action_name=normalized,
                kind="validation_repair",
                source="browser_validation",
                confidence=repair.get("confidence"),
                reason=str(evidence.get("evidence") or "Browser validation found a replacement target."),
                config=repair,
            )
        )
    return proposals


def _candidate_proposals(vertical_config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = vertical_config.get("action_candidates") if isinstance(vertical_config, dict) else []
    if not isinstance(rows, list):
        return []
    proposals: list[dict[str, Any]] = []
    for row in rows[:MAX_REPAIR_PROPOSALS]:
        proposal = _candidate_proposal(row)
        if proposal:
            proposals.append(proposal)
    return proposals


def _candidate_proposal(row: Any) -> dict[str, Any]:
    candidate = row if isinstance(row, dict) else {}
    action_name = normalize_action_name(str(candidate.get("action") or ""))
    if not is_supported_action(action_name):
        return {}
    action_type = str(candidate.get("type") or "").strip().lower()
    proposal_confidence = normalized_confidence(candidate.get("confidence"))
    if proposal_confidence < REPAIR_MIN_CONFIDENCE:
        return {}
    config = validated_repair(
        {
            "type": "navigate" if action_type == "navigate" else "click",
            "path": candidate.get("path"),
            "selector": candidate.get("selector"),
            "label": candidate.get("label"),
            "confidence": proposal_confidence,
        }
    )
    if not config:
        return {}
    return _proposal(
        action_name=action_name,
        kind="action_candidate",
        source=str(candidate.get("source") or "discovery"),
        confidence=proposal_confidence,
        reason="Discovered high-confidence browser action candidate.",
        config=config,
        candidate=candidate,
    )


def _proposal(
    *,
    action_name: str,
    kind: str,
    source: str,
    confidence: Any,
    reason: str,
    config: dict[str, Any],
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "action": action_name,
        "kind": kind,
        "source": source,
        "confidence": normalized_confidence(confidence),
        "reason": reason[:300],
        "config": config,
    }
    if candidate:
        row["candidate"] = _safe_candidate(candidate)
    return row


def _dedupe_proposals(proposals: list[dict[str, Any]], vertical_key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for proposal in proposals:
        config = proposal.get("config") if isinstance(proposal.get("config"), dict) else {}
        key = (
            normalize_action_name(str(proposal.get("action") or "")),
            str(config.get("type") or ""),
            str(config.get("selector") or config.get("path") or config.get("input") or ""),
        )
        if not key[0] or key in seen:
            continue
        seen.add(key)
        rows.append({**proposal, "vertical_key": vertical_key})
    return sorted(rows, key=lambda row: (-float(row.get("confidence") or 0), str(row.get("action") or "")))


def _safe_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": str(candidate.get("kind") or "")[:80],
        "action": normalize_action_name(str(candidate.get("action") or "")),
        "type": str(candidate.get("type") or "")[:40],
        "label": str(candidate.get("label") or "")[:160],
        "selector": clean_target(candidate.get("selector")),
        "path": clean_target(candidate.get("path")),
        "source": str(candidate.get("source") or "")[:80],
    }


def _request_repairs(
    html_sample: str,
    vertical_key: str,
    actions: dict[str, Any],
    site_id: str,
) -> dict[str, dict[str, Any]]:
    payload = {
        "vertical": vertical_key,
        "actions": repair_action_payload(actions),
        "html": html_sample[:MAX_HTML_SAMPLE_CHARS],
    }
    try:
        raw_response = create_chat_completion(
            [
                {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_completion_tokens=REPAIR_MAX_TOKENS,
            json_response=True,
        )
        return _parse_repair_response(raw_response)
    except Exception as exc:
        logger.info("Adapter repair skipped for %s: %s", site_id, exc)
        return {}


def _parse_repair_response(raw_response: str) -> dict[str, dict[str, Any]]:
    parsed = json_response(raw_response)
    if not isinstance(parsed, dict):
        return {}
    raw_actions = parsed.get("actions", parsed)
    if not isinstance(raw_actions, dict):
        return {}
    repairs: dict[str, dict[str, Any]] = {}
    for action_name, raw_repair in raw_actions.items():
        normalized = normalize_action_name(action_name)
        repair = validated_repair(raw_repair)
        if is_supported_action(normalized) and repair:
            repairs[normalized] = repair
    return repairs
