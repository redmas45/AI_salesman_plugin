"""Response wording helpers for filtered or pending UI actions."""

from __future__ import annotations

import re
from typing import Any, Callable

from api.contracts.models import (
    ACTION_COMPARE_ENTITIES,
    ACTION_NAVIGATE_TO,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_ENTITIES,
    ACTION_SHOW_PRODUCTS,
)


def apply_capability_filter_result(
    site_id: str,
    actions: list[dict[str, Any]],
    *,
    recoverable_errors: tuple[type[BaseException], ...],
    skipped_status: str,
    logger: Any,
) -> dict[str, Any]:
    try:
        from agent.action_helpers.capabilities import filter_actions_with_diagnostics

        return filter_actions_with_diagnostics(site_id, actions)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | capability filter skipped: %s", exc)
        return {"status": skipped_status, "actions": actions, "removed_actions": []}


def align_response_with_action_filter(
    response_text: str,
    filter_report: dict[str, Any],
    *,
    recoverable_errors: tuple[type[BaseException], ...],
    logger: Any,
) -> str:
    try:
        from agent.action_helpers.capabilities import action_filter_response_note

        note = action_filter_response_note(filter_report)
    except recoverable_errors as exc:
        logger.warning("PIPELINE | action filter response note skipped: %s", exc)
        note = ""
    if not note:
        return response_text
    return merged_action_filter_response(response_text, note, filter_report)


def align_response_with_enriched_action_params(
    response_text: str,
    actions: list[dict[str, Any]],
    *,
    action_param_has_value: Callable[[dict[str, Any], str], bool],
    lead_flow_fallback_text: Callable[[str], str],
    normalize_lookup_text: Callable[[Any], str],
) -> str:
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action") or "").upper()
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        known_params = [str(param) for param, _value in params.items() if action_param_has_value(params, str(param))]
        if not known_params:
            continue
        known_age = action_param_has_value(params, "age_of_eldest_member")
        known_city = action_param_has_value(params, "city")
        if not response_asks_for_known_action_param(response_text, known_params, normalize_lookup_text):
            continue
        if action_name == "START_QUOTE" and known_age and known_city:
            return "I have your age and city. Starting the quote flow now."
        if action_name == "START_QUOTE" and known_age:
            return "I have your age. Starting the quote flow now."
        if action_name == "START_QUOTE" and known_city:
            return "I have your city. Starting the quote flow now."
        return f"I have the required details. {lead_flow_fallback_text(action_name)}"
    return response_text


def neutralize_pending_action_claims(response_text: str, actions: list[dict[str, Any]]) -> str:
    if not actions or not response_text or not response_promises_website_action(response_text):
        return response_text

    verb_bases = {
        "opening": "open",
        "opened": "open",
        "taking": "take",
        "took": "take",
        "starting": "start",
        "started": "start",
        "showing": "show",
        "showed": "show",
        "switching": "switch",
        "switched": "switch",
        "navigating": "navigate",
        "navigated": "navigate",
        "redirecting": "redirect",
        "redirected": "redirect",
        "moving": "move",
        "moved": "move",
        "adding": "add",
        "added": "add",
        "submitting": "submit",
        "submitted": "submit",
        "sorting": "sort",
        "sorted": "sort",
        "booking": "book",
        "booked": "book",
        "checking": "check",
        "checked": "check",
    }
    pattern = re.compile(
        r"\b(?:i\s*(?:am|'m)\s+)?("
        + "|".join(re.escape(verb) for verb in verb_bases)
        + r")\b",
        re.IGNORECASE,
    )

    def replacement(match: re.Match[str]) -> str:
        return f"I'll try to {verb_bases[match.group(1).lower()]}"

    return pattern.sub(replacement, response_text, count=1)


def align_response_when_actions_removed(
    response: dict[str, Any],
    transcript: str,
    site_id: str,
    original_actions: list[str],
    page_context: dict[str, Any] | None,
    *,
    navigation_unavailable_text: Callable[[str, str, dict[str, Any] | None], str],
) -> None:
    if response.get("ui_actions") or not original_actions:
        return
    action_names = {str(action or "").upper() for action in original_actions}
    if ACTION_NAVIGATE_TO in action_names:
        response["intent"] = "navigation_unavailable"
        response["confidence"] = min(float(response.get("confidence") or 1.0), 0.7)
        response["response_text"] = navigation_unavailable_text(site_id, transcript, page_context)
        return
    if action_names & {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON}:
        response["intent"] = "display_unavailable"
        response["confidence"] = min(float(response.get("confidence") or 1.0), 0.7)
        response["response_text"] = "I could not verify matching products on this site right now."
        return
    if action_names & {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES, "OPEN_ENTITY_DETAIL"}:
        response["intent"] = "display_unavailable"
        response["confidence"] = min(float(response.get("confidence") or 1.0), 0.7)
        response["response_text"] = "I could not verify matching records on this site right now."
        return
    if response_promises_website_action(str(response.get("response_text") or "")):
        response["intent"] = "action_unavailable"
        response["confidence"] = min(float(response.get("confidence") or 1.0), 0.7)
        response["response_text"] = "I could not safely perform that website action from the controls I can see right now."


def suppress_lead_recovery_after_removed_navigation(
    response: dict[str, Any],
    transcript: str,
    original_actions: list[str],
    *,
    normalize_navigation_text: Callable[[str], str],
) -> bool:
    if response.get("ui_actions") or ACTION_NAVIGATE_TO not in {str(action or "").upper() for action in original_actions}:
        return False
    text = normalize_navigation_text(transcript)
    return bool(
        re.search(r"\b(page|tab|section|screen)\b", text)
        or re.search(r"\b(go|going|open|opening|navigate|navigating|take|taking|send|move|switch|switching|visit|show|showing)\b", text)
    )


def response_promises_website_action(response_text: str, normalize_lookup_text: Callable[[Any], str] | None = None) -> bool:
    text = normalize_lookup_text(response_text) if normalize_lookup_text else str(response_text or "").lower()
    return bool(
        re.search(
            r"\b(opening|opened|taking|took|starting|started|showing|showed|switching|switched|navigating|navigated|redirecting|redirected|moving|moved|adding|added|submitting|submitted|sorting|sorted|booking|booked|checking|checked)\b",
            text,
        )
    )


def response_asks_for_known_action_param(
    response_text: str,
    known_params: list[str],
    normalize_lookup_text: Callable[[Any], str],
) -> bool:
    text = normalize_lookup_text(response_text)
    if not text:
        return False
    asks_detail = bool(re.search(r"\b(need|confirm|provide|tell me|what|which|ask|share)\b", text))
    if not asks_detail:
        return False
    param_terms = {
        term
        for param in known_params
        for term in normalize_lookup_text(param).split()
        if len(term) >= 3
    }
    aliases = {
        "eldest": {"age", "eldest", "member"},
        "traveler": {"traveler", "travelers", "traveller", "travellers", "people", "guests"},
        "travellers": {"traveler", "travelers", "traveller", "travellers", "people", "guests"},
        "destination": {"destination", "where", "city", "location"},
        "origin": {"origin", "from", "departure"},
        "date": {"date", "when", "day"},
    }
    expanded_terms = set(param_terms)
    for term in list(param_terms):
        expanded_terms.update(aliases.get(term, set()))
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in expanded_terms)


def merged_action_filter_response(response_text: str, note: str, filter_report: dict[str, Any]) -> str:
    actions = filter_report.get("actions") if isinstance(filter_report, dict) else []
    if not actions:
        return note
    clean_response = str(response_text or "").strip()
    return f"{clean_response} {note}".strip() if clean_response else note
