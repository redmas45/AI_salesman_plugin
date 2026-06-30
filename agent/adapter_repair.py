"""Optional LLM-assisted repair for generated adapter action targets."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import config
from agent.actions.registry import is_supported_action, normalize_action_name

logger = logging.getLogger(__name__)

MAX_HTML_SAMPLE_CHARS = 6000
REPAIR_MAX_ACTIONS = 40
REPAIR_MIN_CONFIDENCE = 0.7
REPAIR_MAX_TOKENS = 700
MAX_REPAIR_PROPOSALS = 30
MAX_FLOW_REPAIR_PROPOSALS = 30
MAX_FLOW_REPAIR_CHANGES = 8
FLOW_REPAIR_CONTEXT_LIMIT = 8
FLOW_REPAIR_MAX_TOKENS = 900
FLOW_REPAIR_ROUTE_CONFIDENCE = 0.78
FLOW_REPAIR_ACTION_CONFIDENCE = 0.76
FLOW_REPAIR_REVIEW_CONFIDENCE = 0.45
LLM_FLOW_REPAIR_MIN_CONFIDENCE = 0.72
ACTION_TYPES = frozenset({"navigate", "click", "form"})
CSS_SELECTOR_PATTERN = re.compile(r'^[a-zA-Z#.\[\]:\-_\s>+~*="\'^$|,()0-9]+$')
ROUTE_REPAIR_KINDS = frozenset({"route_added", "route_changed"})
ACTION_REPAIR_KINDS = frozenset({"action_added", "action_changed", "action_recovered"})
MANUAL_REVIEW_KINDS = frozenset({
    "action_now_blocked",
    "new_action_blocked",
    "route_removed",
    "action_removed",
    "vertical_changed",
})

REPAIR_SYSTEM_PROMPT = (
    "You repair website adapter actions from HTML. Return only JSON. "
    "For each requested action, output a better target if visible in the HTML. "
    "Allowed action target types are navigate, click, and form. "
    "Never invent business facts. Never return external URLs."
)
FLOW_REPAIR_SYSTEM_PROMPT = (
    "You repair a discovered website flow graph. Return only JSON with a proposals array. "
    "Use only same-origin paths beginning with /. Use only action names already present in the payload. "
    "Allowed action target types are navigate, click, and form. "
    "Do not solve CAPTCHA, login, payment, or regulated final decisions; propose manual review for those."
)


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
    """Build CRM-reviewable repair plans from flow regression evidence."""
    regression = vertical_config.get("regression") if isinstance(vertical_config, dict) else {}
    changes = regression.get("changes") if isinstance(regression, dict) else []
    if not isinstance(changes, list):
        return []

    routes = vertical_config.get("routes") if isinstance(vertical_config.get("routes"), dict) else {}
    actions = vertical_config.get("actions") if isinstance(vertical_config.get("actions"), dict) else {}
    validation = vertical_config.get("validation") if isinstance(vertical_config.get("validation"), dict) else {}
    deterministic = [
        proposal
        for proposal in (
            _flow_repair_proposal(change, routes, actions, validation, vertical_key)
            for change in changes[:MAX_FLOW_REPAIR_PROPOSALS]
        )
        if proposal
    ]
    llm_proposals = _llm_flow_repair_proposals(
        vertical_config=vertical_config,
        vertical_key=vertical_key,
        changes=changes,
    )
    proposals = [*llm_proposals, *deterministic]
    return _dedupe_flow_proposals(proposals)[:MAX_FLOW_REPAIR_PROPOSALS]


def _repair_enabled(html_sample: str, actions: dict[str, Any]) -> bool:
    return bool(
        config.LLM_EXTRACTOR_ENABLED
        and config.OPENAI_API_KEY
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
        repair = _validated_repair(row.get("repair_candidate"))
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
        repair = _validated_repair(evidence.get("repair"))
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
    confidence = _confidence(candidate.get("confidence"))
    if confidence < REPAIR_MIN_CONFIDENCE:
        return {}
    config = _validated_repair(
        {
            "type": "navigate" if action_type == "navigate" else "click",
            "path": candidate.get("path"),
            "selector": candidate.get("selector"),
            "label": candidate.get("label"),
            "confidence": confidence,
        }
    )
    if not config:
        return {}
    return _proposal(
        action_name=action_name,
        kind="action_candidate",
        source=str(candidate.get("source") or "discovery"),
        confidence=confidence,
        reason="Discovered high-confidence browser action candidate.",
        config=config,
        candidate=candidate,
    )


def _flow_repair_proposal(
    raw_change: Any,
    routes: dict[str, Any],
    actions: dict[str, Any],
    validation: dict[str, Any],
    vertical_key: str,
) -> dict[str, Any]:
    change = raw_change if isinstance(raw_change, dict) else {}
    kind = str(change.get("kind") or "").strip()
    if kind in ROUTE_REPAIR_KINDS:
        return _route_flow_proposal(change, routes, vertical_key)
    if kind in ACTION_REPAIR_KINDS:
        return _action_flow_proposal(change, actions, validation, vertical_key)
    if kind in MANUAL_REVIEW_KINDS:
        return _manual_flow_proposal(change, vertical_key)
    return {}


def _route_flow_proposal(change: dict[str, Any], routes: dict[str, Any], vertical_key: str) -> dict[str, Any]:
    route_name = str(change.get("item") or "").strip()
    path = _clean_route_path(routes.get(route_name) or change.get("current"))
    if not route_name or not path:
        return {}
    return _flow_proposal(
        kind="route_repair",
        scope="route",
        item=route_name,
        vertical_key=vertical_key,
        confidence=FLOW_REPAIR_ROUTE_CONFIDENCE,
        reason="Flow regression found a changed route target.",
        changes=[change],
        patch={"routes": {route_name: path}},
    )


def _action_flow_proposal(
    change: dict[str, Any],
    actions: dict[str, Any],
    validation: dict[str, Any],
    vertical_key: str,
) -> dict[str, Any]:
    action_name = normalize_action_name(str(change.get("item") or ""))
    config = _flow_action_config(action_name, actions, validation)
    if not is_supported_action(action_name) or not config:
        return {}
    return _flow_proposal(
        kind="action_repair",
        scope="action",
        item=action_name,
        vertical_key=vertical_key,
        confidence=_flow_action_confidence(config),
        reason="Flow regression found a changed action target.",
        changes=[change],
        patch={"actions": {action_name: config}},
    )


def _manual_flow_proposal(change: dict[str, Any], vertical_key: str) -> dict[str, Any]:
    item = str(change.get("item") or "").strip()
    if not item:
        return {}
    return _flow_proposal(
        kind="manual_review",
        scope=_manual_flow_scope(change),
        item=item,
        vertical_key=vertical_key,
        confidence=FLOW_REPAIR_REVIEW_CONFIDENCE,
        reason=str(change.get("evidence") or "Flow changed and needs admin review."),
        changes=[change],
        patch={},
    )


def _llm_flow_repair_proposals(
    *,
    vertical_config: dict[str, Any],
    vertical_key: str,
    changes: list[Any],
) -> list[dict[str, Any]]:
    if not _flow_repair_llm_enabled(vertical_config, changes):
        return []
    payload = _flow_repair_payload(vertical_config, vertical_key, changes)
    raw_proposals = _request_flow_repairs(payload, site_id=str(payload.get("site_id") or ""))
    return [
        proposal
        for proposal in (
            _llm_flow_proposal(row, vertical_key)
            for row in _raw_flow_proposals(raw_proposals)
        )
        if proposal
    ]


def _flow_repair_llm_enabled(vertical_config: dict[str, Any], changes: list[Any]) -> bool:
    return bool(
        config.LLM_EXTRACTOR_ENABLED
        and config.OPENAI_API_KEY
        and isinstance(vertical_config, dict)
        and changes
    )


def _flow_repair_payload(
    vertical_config: dict[str, Any],
    vertical_key: str,
    changes: list[Any],
) -> dict[str, Any]:
    flow = vertical_config.get("flow") if isinstance(vertical_config.get("flow"), dict) else {}
    regression = vertical_config.get("regression") if isinstance(vertical_config.get("regression"), dict) else {}
    return {
        "site_id": str(flow.get("site_id") or regression.get("site_id") or ""),
        "vertical_key": vertical_key,
        "routes": _safe_route_payload(vertical_config.get("routes")),
        "actions": _repair_action_payload(vertical_config.get("actions") if isinstance(vertical_config.get("actions"), dict) else {}),
        "changes": [_safe_flow_change(change if isinstance(change, dict) else {}) for change in changes[:FLOW_REPAIR_CONTEXT_LIMIT]],
        "pages": _flow_page_payload(flow.get("pages")),
        "flow_actions": _flow_action_payload(flow.get("actions")),
    }


def _request_flow_repairs(payload: dict[str, Any], site_id: str) -> Any:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": FLOW_REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=FLOW_REPAIR_MAX_TOKENS,
        )
        return _json_response(completion.choices[0].message.content or "")
    except Exception as exc:
        logger.info("LLM flow repair skipped for %s: %s", site_id, exc)
        return {}


def _raw_flow_proposals(raw_response: Any) -> list[Any]:
    if isinstance(raw_response, list):
        return raw_response[:MAX_FLOW_REPAIR_PROPOSALS]
    if isinstance(raw_response, dict) and isinstance(raw_response.get("proposals"), list):
        return raw_response["proposals"][:MAX_FLOW_REPAIR_PROPOSALS]
    return []


def _llm_flow_proposal(raw_proposal: Any, vertical_key: str) -> dict[str, Any]:
    row = raw_proposal if isinstance(raw_proposal, dict) else {}
    confidence = _confidence(row.get("confidence"))
    if confidence < LLM_FLOW_REPAIR_MIN_CONFIDENCE:
        return {}
    scope = _clean_flow_scope(row.get("scope"))
    item = _clean_flow_item(row.get("item"))
    patch = _validated_llm_flow_patch(row.get("patch"))
    if not item or not _has_flow_patch(patch):
        return {}
    return _flow_proposal(
        kind=_llm_flow_kind(scope),
        scope=scope,
        item=item,
        vertical_key=vertical_key,
        confidence=confidence,
        reason=str(row.get("reason") or "LLM suggested a flow repair from current flow evidence."),
        changes=_safe_llm_changes(row.get("changes")),
        patch=patch,
        source="llm_flow_repair",
    )


def _validated_llm_flow_patch(raw_patch: Any) -> dict[str, Any]:
    patch = raw_patch if isinstance(raw_patch, dict) else {}
    route_patch = _safe_route_payload(patch.get("routes"))
    action_patch = _validated_llm_action_patch(patch.get("actions"))
    return {"routes": route_patch, "actions": action_patch}


def _validated_llm_action_patch(raw_actions: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_actions, dict):
        return {}
    clean_actions: dict[str, dict[str, Any]] = {}
    for raw_name, raw_config in list(raw_actions.items())[:MAX_FLOW_REPAIR_PROPOSALS]:
        action_name = normalize_action_name(str(raw_name or ""))
        repair = _validated_repair(raw_config)
        if is_supported_action(action_name) and repair:
            clean_actions[action_name] = {**repair, "source": "llm_flow_repair"}
    return clean_actions


def _flow_proposal(
    *,
    kind: str,
    scope: str,
    item: str,
    vertical_key: str,
    confidence: float,
    reason: str,
    changes: list[dict[str, Any]],
    patch: dict[str, Any],
    source: str = "flow_regression",
) -> dict[str, Any]:
    return {
        "key": f"{scope}:{item}",
        "kind": kind,
        "source": source,
        "scope": scope,
        "item": item,
        "vertical_key": vertical_key,
        "confidence": _confidence(confidence),
        "reason": reason[:300],
        "review_required": True,
        "changes": [_safe_flow_change(change) for change in changes[:MAX_FLOW_REPAIR_CHANGES]],
        "patch": patch,
    }


def _flow_action_config(action_name: str, actions: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    validation_config = _validation_action_repair(action_name, validation)
    if validation_config:
        return validation_config
    action_config = actions.get(action_name)
    return action_config if isinstance(action_config, dict) else {}


def _validation_action_repair(action_name: str, validation: dict[str, Any]) -> dict[str, Any]:
    actions = validation.get("actions") if isinstance(validation.get("actions"), dict) else {}
    evidence = actions.get(action_name)
    repair = evidence.get("repair") if isinstance(evidence, dict) else {}
    return _validated_repair(repair)


def _flow_action_confidence(config: dict[str, Any]) -> float:
    confidence = _confidence(config.get("confidence"))
    return confidence if confidence else FLOW_REPAIR_ACTION_CONFIDENCE


def _manual_flow_scope(change: dict[str, Any]) -> str:
    kind = str(change.get("kind") or "")
    if kind.startswith("route"):
        return "route"
    if kind.startswith("action") or kind.startswith("new_action"):
        return "action"
    return "flow"


def _safe_flow_change(change: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": str(change.get("kind") or "")[:80],
        "item": str(change.get("item") or "")[:120],
        "severity": str(change.get("severity") or "")[:40],
        "previous": _clean_target(change.get("previous"))[:240],
        "current": _clean_target(change.get("current"))[:240],
        "evidence": str(change.get("evidence") or "")[:300],
    }


def _safe_llm_changes(raw_changes: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_changes, list):
        return []
    return [_safe_flow_change(change if isinstance(change, dict) else {}) for change in raw_changes[:MAX_FLOW_REPAIR_CHANGES]]


def _clean_flow_scope(value: Any) -> str:
    scope = str(value or "").strip().lower()
    return scope if scope in {"route", "action", "flow"} else "flow"


def _clean_flow_item(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip()[:120]


def _llm_flow_kind(scope: str) -> str:
    if scope == "route":
        return "llm_route_repair"
    if scope == "action":
        return "llm_action_repair"
    return "llm_flow_repair"


def _safe_route_payload(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    routes: dict[str, str] = {}
    for raw_key, raw_path in list(value.items())[:MAX_FLOW_REPAIR_PROPOSALS]:
        route_key = re.sub(r"[^a-z0-9_]+", "_", str(raw_key or "").strip().lower()).strip("_")[:80]
        route_path = _clean_route_path(raw_path)
        if route_key and route_path:
            routes[route_key] = route_path
    return routes


def _flow_page_payload(raw_pages: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_pages, list):
        return []
    return [_safe_flow_page(page) for page in raw_pages[:FLOW_REPAIR_CONTEXT_LIMIT] if isinstance(page, dict)]


def _safe_flow_page(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": _clean_target(page.get("url"))[:240],
        "title": str(page.get("title") or "")[:160],
        "text_sample": str(page.get("text_sample") or "")[:600],
        "route_names": [str(name)[:80] for name in page.get("route_names", [])[:8]]
        if isinstance(page.get("route_names"), list)
        else [],
    }


def _flow_action_payload(raw_actions: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_actions, list):
        return []
    return [_safe_flow_action(action) for action in raw_actions[:FLOW_REPAIR_CONTEXT_LIMIT] if isinstance(action, dict)]


def _safe_flow_action(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_name": normalize_action_name(str(action.get("action_name") or "")),
        "action_type": str(action.get("action_type") or "")[:40],
        "label": str(action.get("label") or "")[:160],
        "selector": _clean_target(action.get("selector")),
        "path": _clean_route_path(action.get("path")),
        "evidence": str(action.get("evidence") or "")[:300],
    }


def _clean_route_path(value: Any) -> str:
    path = _clean_target(value)
    return path if path.startswith("/") else ""


def _has_flow_patch(patch: dict[str, Any]) -> bool:
    routes = patch.get("routes")
    actions = patch.get("actions")
    return bool(isinstance(routes, dict) and routes) or bool(isinstance(actions, dict) and actions)


def _dedupe_flow_proposals(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_key: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        key = str(proposal.get("key") or "")
        if not key:
            continue
        current = best_by_key.get(key)
        if not current or _flow_proposal_rank(proposal) > _flow_proposal_rank(current):
            best_by_key[key] = proposal
    return sorted(best_by_key.values(), key=lambda row: (-float(row.get("confidence") or 0), str(row.get("key") or "")))


def _flow_proposal_rank(proposal: dict[str, Any]) -> tuple[int, float]:
    patch = proposal.get("patch") if isinstance(proposal.get("patch"), dict) else {}
    return (1 if _has_flow_patch(patch) else 0, float(proposal.get("confidence") or 0))


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
        "confidence": _confidence(confidence),
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
        "selector": _clean_target(candidate.get("selector")),
        "path": _clean_target(candidate.get("path")),
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
        "actions": _repair_action_payload(actions),
        "html": html_sample[:MAX_HTML_SAMPLE_CHARS],
    }
    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=REPAIR_MAX_TOKENS,
        )
        raw_response = completion.choices[0].message.content or ""
        return _parse_repair_response(raw_response)
    except Exception as exc:
        logger.info("Adapter repair skipped for %s: %s", site_id, exc)
        return {}


def _repair_action_payload(actions: dict[str, Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for action_name, action_config in list(actions.items())[:REPAIR_MAX_ACTIONS]:
        payload.append({"action": action_name, "config": action_config})
    return payload


def _parse_repair_response(raw_response: str) -> dict[str, dict[str, Any]]:
    parsed = _json_response(raw_response)
    if not isinstance(parsed, dict):
        return {}
    raw_actions = parsed.get("actions", parsed)
    if not isinstance(raw_actions, dict):
        return {}
    repairs: dict[str, dict[str, Any]] = {}
    for action_name, raw_repair in raw_actions.items():
        normalized = normalize_action_name(action_name)
        repair = _validated_repair(raw_repair)
        if is_supported_action(normalized) and repair:
            repairs[normalized] = repair
    return repairs


def _json_response(raw_response: str) -> Any:
    cleaned = str(raw_response or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _validated_repair(raw_repair: Any) -> dict[str, Any]:
    repair = raw_repair if isinstance(raw_repair, dict) else {}
    confidence = _confidence(repair.get("confidence"))
    action_type = str(repair.get("type") or "").strip().lower()
    if confidence < REPAIR_MIN_CONFIDENCE or action_type not in ACTION_TYPES:
        return {}

    clean: dict[str, Any] = {"type": action_type, "confidence": confidence}
    for key in ("path", "selector", "form", "input", "submit", "label"):
        value = _clean_target(repair.get(key))
        if value:
            clean[key] = value
    if _has_required_target(clean):
        return clean
    return {}


def _has_required_target(repair: dict[str, Any]) -> bool:
    action_type = repair.get("type")
    if action_type == "navigate":
        return bool(str(repair.get("path") or "").startswith("/"))
    if action_type == "click":
        return _valid_selector(repair.get("selector"))
    if action_type == "form":
        return _valid_selector(repair.get("input"))
    return False


def _valid_selector(value: Any) -> bool:
    selector = str(value or "").strip()
    return bool(selector and len(selector) <= 240 and CSS_SELECTOR_PATTERN.match(selector))


def _clean_target(value: Any) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if text.lower().startswith(("javascript:", "data:", "http://", "https://")):
        return ""
    if any(key in text for key in ("<script", "</")):
        return ""
    return text[:500]


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(number, 1.0)), 2)
