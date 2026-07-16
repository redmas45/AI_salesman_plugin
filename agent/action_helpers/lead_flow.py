"""Lead-flow intent recovery helpers for orchestrator responses."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

from agent.action_helpers.action_params import action_param_specs
from agent.products.product_response import normalize_lookup_text, phrase_in_text

LEAD_FLOW_INTENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("REQUEST_TEST_DRIVE", (r"\btest drive\b",)),
    ("REQUEST_SITE_VISIT", (r"\bsite visit\b", r"\bvisit\b.{0,30}\bsite\b")),
    ("REQUEST_VIEWING", (r"\bviewing\b", r"\bproperty tour\b", r"\bhome tour\b", r"\bsee\b.{0,30}\b(property|home|flat|apartment)\b")),
    ("BOOK_APPOINTMENT_REQUEST", (r"\bbook\b.{0,25}\bappointment\b", r"\bappointment\b.{0,25}\bbook\b")),
    ("REQUEST_APPOINTMENT", (r"\bappointment\b", r"\bbook\b.{0,25}\b(doctor|clinic|consult)\b")),
    ("REQUEST_COUNSELOR_CALLBACK", (r"\bcounsell?or\b", r"\badvisor\b.{0,30}\b(call|callback|contact)\b")),
    ("REQUEST_CONSULTATION", (r"\bconsultation\b", r"\bconsult\b.{0,30}\b(expert|lawyer|advisor|doctor|specialist)\b")),
    ("START_TICKET_PURCHASE", (r"\bticket(s)?\b", r"\bbuy\b.{0,30}\bpass(es)?\b")),
    ("START_ENROLLMENT", (r"\benroll\b", r"\benrolment\b", r"\benrollment\b", r"\badmission\b", r"\bregister\b.{0,30}\b(course|program|class)\b")),
    ("START_APPLICATION", (r"\bapply\b", r"\bapplication\b", r"\bstart\b.{0,30}\bapplication\b")),
    (
        "START_QUOTE",
        (
            r"\bquote(s)?\b",
            r"\bget\b.{0,30}\brate(s)?\b",
            r"\bpremium\b",
            r"\bshow\b.{0,30}\bquote(s)?\b",
        ),
    ),
    ("REQUEST_ESTIMATE", (r"\bestimate\b", r"\bquote\b", r"\bproject cost\b", r"\brenovation cost\b")),
    ("START_BOOKING", (r"\bbook\b", r"\bbooking\b", r"\breserve\b", r"\breservation\b")),
    ("REQUEST_CALLBACK", (r"\bcall me\b", r"\bcallback\b", r"\bcall back\b", r"\bphone call\b")),
    ("CONTACT_AGENT", (r"\bagent\b", r"\brealtor\b", r"\bsales person\b", r"\bsalesperson\b")),
    ("CAPTURE_LEAD", (r"\bcontact me\b", r"\bsend my details\b", r"\bleave my details\b")),
)

LEAD_FLOW_FALLBACK_LABELS = {
    "START_QUOTE": "I can start the quote flow now.",
    "START_BOOKING": "I can start the booking flow now.",
    "START_APPLICATION": "I can start the application flow now.",
    "REQUEST_APPOINTMENT": "I can start the appointment request now.",
    "BOOK_APPOINTMENT_REQUEST": "I can start the appointment request now.",
    "REQUEST_TEST_DRIVE": "I can start the test-drive request now.",
    "REQUEST_VIEWING": "I can start the viewing request now.",
    "REQUEST_CONSULTATION": "I can start the consultation request now.",
    "REQUEST_ESTIMATE": "I can start the estimate request now.",
    "REQUEST_SITE_VISIT": "I can start the site-visit request now.",
    "START_TICKET_PURCHASE": "I can start the ticket flow now.",
    "START_ENROLLMENT": "I can start the enrollment flow now.",
    "REQUEST_COUNSELOR_CALLBACK": "I can request a counselor callback now.",
    "REQUEST_CALLBACK": "I can request a callback now.",
    "CONTACT_AGENT": "I can connect you with an agent now.",
    "CAPTURE_LEAD": "I can open the contact flow now.",
}


def ensure_lead_flow_response(
    response: dict[str, Any],
    transcript: str,
    site_id: str,
    *,
    action_for_transcript: Callable[[str, str], str],
) -> None:
    if response.get("ui_actions"):
        return
    action_name = action_for_transcript(transcript, site_id)
    if not action_name:
        return

    response["intent"] = "lead_flow"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    response["ui_actions"] = [{"action": action_name, "params": {}}]
    response["response_text"] = lead_flow_fallback_text(action_name)


def lead_flow_action_from_transcript(
    transcript: str,
    site_id: str,
    *,
    allowed_actions_for_site: Callable[[str], set[str]],
    action_configs_for_site: Callable[[str], dict[str, dict[str, Any]]],
) -> str:
    normalized = normalize_lookup_text(transcript)
    if not normalized:
        return ""

    allowed_actions = allowed_actions_for_site(site_id)
    if not allowed_actions:
        return ""

    for action_name, patterns in LEAD_FLOW_INTENT_PATTERNS:
        if action_name not in allowed_actions:
            continue
        if any(re.search(pattern, normalized) for pattern in patterns):
            return action_name
    return lead_flow_action_from_site_contract(
        normalized,
        site_id,
        allowed_actions,
        action_configs_for_site=action_configs_for_site,
    )


def lead_flow_action_from_site_contract(
    normalized_text: str,
    site_id: str,
    allowed_actions: set[str],
    *,
    action_configs_for_site: Callable[[str], dict[str, dict[str, Any]]],
) -> str:
    if not looks_like_supported_flow_request(normalized_text):
        return ""
    candidates = [action for action in sorted(allowed_actions) if not action.startswith("HANDOFF_")]
    if not candidates:
        return ""

    action_configs = action_configs_for_site(site_id)
    scored: list[tuple[int, str]] = []
    for action_name in candidates:
        score = lead_flow_contract_match_score(normalized_text, action_name, action_configs.get(action_name) or {})
        if score:
            scored.append((score, action_name))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored[0][1]
    if len(candidates) == 1:
        return candidates[0]
    return ""


def looks_like_supported_flow_request(text: str) -> bool:
    return bool(
        re.search(
            r"\b("
            r"buy|get|need|want|looking for|start|apply|book|reserve|request|schedule|enroll|register|"
            r"purchase|take|help me|show me|find|check"
            r")\b",
            text,
        )
    )


def lead_flow_contract_match_score(normalized_text: str, action_name: str, action_config: dict[str, Any]) -> int:
    terms = lead_flow_contract_terms(action_name, action_config)
    score = 0
    for term in terms:
        if phrase_in_text(term, normalized_text):
            score += 2 if len(term.split()) > 1 else 1
    return score


def lead_flow_contract_terms(action_name: str, action_config: dict[str, Any]) -> set[str]:
    raw_parts: list[str] = [action_name.replace("_", " ")]
    for key in ("label", "title", "button_label", "form_label", "path", "page", "page_path"):
        value = action_config.get(key)
        if value:
            raw_parts.append(str(value))
    for spec in action_param_specs(action_config):
        for key in ("param", "label", "placeholder", "type"):
            value = spec.get(key)
            if value:
                raw_parts.append(str(value))
    terms: set[str] = set()
    for part in raw_parts:
        normalized = normalize_lookup_text(part)
        for term in normalized.split():
            if len(term) >= 4 and term not in {"start", "request", "flow", "field", "form"}:
                terms.add(term)
        if normalized and len(normalized) >= 4:
            terms.add(normalized)
    return terms


def lead_flow_actions_for_site(
    site_id: str,
    *,
    vertical_key_for_site: Callable[[str], str],
    recoverable_errors: tuple[type[BaseException], ...],
    logger: logging.Logger,
) -> set[str]:
    candidates: set[str] = set()
    try:
        from agent.action_helpers.capabilities import get_allowed_actions

        candidates.update(get_allowed_actions(site_id))
    except recoverable_errors as exc:
        logger.warning("PIPELINE | lead fallback capability lookup skipped: %s", exc)

    try:
        from agent.actions.registry import get_action
    except ImportError as exc:
        logger.warning("PIPELINE | lead fallback action registry skipped: %s", exc)
        return set()

    try:
        from agent.verticals.registry import get_vertical
        vertical = get_vertical(vertical_key_for_site(site_id))
        candidates.update(vertical.action_types)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | lead fallback vertical lookup skipped: %s", exc)
    return {
        action_name
        for action_name in candidates
        if (definition := get_action(action_name)) and definition.family == "lead"
    }


def lead_flow_fallback_text(action_name: str) -> str:
    return LEAD_FLOW_FALLBACK_LABELS.get(action_name, "I can start that website flow now.")
