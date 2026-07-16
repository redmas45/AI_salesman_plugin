"""Assistant smoke-test result evaluation."""

from __future__ import annotations

from typing import Any

DISPLAY_ACTION_ID_PARAMS = {
    "SHOW_PRODUCTS": "product_ids",
    "SHOW_COMPARISON": "product_ids",
    "SHOW_ENTITIES": "entity_ids",
    "COMPARE_ENTITIES": "entity_ids",
}


def assistant_smoke_result(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    actions = [
        action
        for action in (result.get("ui_actions") or [])
        if isinstance(action, dict)
    ]
    action_names = [
        str(action.get("action") or "").upper()
        for action in actions
    ]
    expected_actions = [str(action).upper() for action in case.get("expected_actions") or []]
    expected_terms = [str(term).lower() for term in case.get("expected_response_terms_any") or [] if str(term).strip()]
    required_terms = [str(term).lower() for term in case.get("expected_response_terms_all") or [] if str(term).strip()]
    response_text = str(result.get("response_text") or "")
    retrieval_evidence = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    action_filter = result.get("action_filter") if isinstance(result.get("action_filter"), dict) else {}
    filtered_actions = action_filter.get("removed_actions") if isinstance(action_filter.get("removed_actions"), list) else []
    blocked_phrase = contains_blocked_smoke_phrase(response_text)
    matched_actions = sorted(set(action_names).intersection(expected_actions))
    matched_terms = [term for term in expected_terms if term in response_text.lower()]
    matched_required_terms = [term for term in required_terms if term in response_text.lower()]
    display_action_evidence = display_action_evidence_for(actions)
    display_payload_ok = display_payload_is_valid(matched_actions, display_action_evidence)
    passed = (
        bool(matched_actions)
        and not blocked_phrase
        and display_payload_ok
        and (not expected_terms or bool(matched_terms))
        and len(matched_required_terms) == len(required_terms)
    )
    failure_kind = "" if passed else smoke_failure_kind(
        action_names,
        matched_actions,
        blocked_phrase,
        expected_terms,
        matched_terms,
        required_terms,
        matched_required_terms,
        display_payload_ok,
        filtered_actions,
    )
    return {
        "name": case["name"],
        "prompt": case["prompt"],
        "status": "ok" if passed else "failed",
        "expected_actions": expected_actions,
        "expected_response_terms_any": expected_terms,
        "expected_response_terms_all": required_terms,
        "actual_actions": action_names,
        "matched_actions": matched_actions,
        "matched_response_terms": matched_terms,
        "matched_response_terms_all": matched_required_terms,
        "display_action_evidence": display_action_evidence,
        "filtered_actions": filtered_actions,
        "action_filter": action_filter,
        "retrieval_evidence": retrieval_evidence,
        "intent": str(result.get("intent") or ""),
        "response_excerpt": response_text[:320],
        "failure_kind": failure_kind,
        "reason": "" if passed else smoke_failure_reason(
            expected_actions,
            action_names,
            blocked_phrase,
            expected_terms,
            matched_terms,
            required_terms,
            matched_required_terms,
            display_payload_ok,
            filtered_actions,
        ),
        "recommended_fix": "" if passed else smoke_recommended_fix(
            failure_kind,
            expected_actions,
            retrieval_evidence,
            filtered_actions,
        ),
    }


def display_action_evidence_for(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for action in actions:
        action_name = str(action.get("action") or "").upper()
        id_param = DISPLAY_ACTION_ID_PARAMS.get(action_name)
        if not id_param:
            continue
        params = action.get("params") if isinstance(action.get("params"), dict) else action.get("parameters")
        params = params if isinstance(params, dict) else {}
        raw_ids = params.get(id_param)
        ids = [str(item) for item in raw_ids if str(item).strip()] if isinstance(raw_ids, list) else []
        evidence.append(
            {
                "action": action_name,
                "id_param": id_param,
                "id_count": len(ids),
                "ids": ids[:8],
            }
        )
    return evidence


def display_payload_is_valid(matched_actions: list[str], display_action_evidence: list[dict[str, Any]]) -> bool:
    required_actions = [action for action in matched_actions if action in DISPLAY_ACTION_ID_PARAMS]
    if not required_actions:
        return True
    return any(
        str(item.get("action") or "").upper() in required_actions and int(item.get("id_count") or 0) > 0
        for item in display_action_evidence
    )


def contains_blocked_smoke_phrase(response_text: str) -> bool:
    text = response_text.lower()
    blocked_phrases = [
        "no record found",
        "no records found",
        "currently don't have",
        "currently doesnt have",
        "currently doesn't have",
        "couldn't find",
        "could not find",
        "do not have enough",
    ]
    return any(phrase in text for phrase in blocked_phrases)


def smoke_failure_reason(
    expected_actions: list[str],
    action_names: list[str],
    blocked_phrase: bool,
    expected_terms: list[str] | None = None,
    matched_terms: list[str] | None = None,
    required_terms: list[str] | None = None,
    matched_required_terms: list[str] | None = None,
    display_payload_ok: bool = True,
    filtered_actions: list[Any] | None = None,
) -> str:
    filter_reason = primary_smoke_filter_reason(filtered_actions)
    if filter_reason == "missing_required_params":
        missing = filtered_missing_params(filtered_actions)
        return f"Runtime filter removed the action because required params were missing: {', '.join(missing) or 'unknown'}."
    if filter_reason in {"blocked_by_policy", "blocked_by_action_health"}:
        return "Runtime filter removed the action because the website flow is blocked by safety policy or recent browser health evidence."
    if filter_reason == "unsupported_action":
        return "Runtime filter removed an action that is not available for this client website."
    if blocked_phrase:
        return "Assistant response used a no-data or no-records fallback."
    if not display_payload_ok:
        return "Matched display action did not include product_ids or entity_ids, so the widget cannot render the records."
    missing_required = [term for term in (required_terms or []) if term not in (matched_required_terms or [])]
    if missing_required:
        return f"Expected response to mention all of {', '.join(required_terms or [])}; missing {', '.join(missing_required)}."
    if expected_terms and not matched_terms:
        return f"Expected response to mention one of {', '.join(expected_terms)}."
    return f"Expected one of {', '.join(expected_actions)} but got {', '.join(action_names) or 'no actions'}."


def smoke_failure_kind(
    action_names: list[str],
    matched_actions: list[str],
    blocked_phrase: bool,
    expected_terms: list[str] | None = None,
    matched_terms: list[str] | None = None,
    required_terms: list[str] | None = None,
    matched_required_terms: list[str] | None = None,
    display_payload_ok: bool = True,
    filtered_actions: list[Any] | None = None,
) -> str:
    filter_reason = primary_smoke_filter_reason(filtered_actions)
    if filter_reason == "missing_required_params":
        return "missing_required_action_params"
    if filter_reason in {"blocked_by_policy", "blocked_by_action_health"}:
        return "blocked_action_filtered"
    if filter_reason == "unsupported_action":
        return "unsupported_action_filtered"
    if blocked_phrase:
        return "no_data_fallback"
    if not action_names:
        return "no_ui_action"
    if not matched_actions:
        return "action_mismatch"
    if not display_payload_ok:
        return "missing_action_ids"
    if required_terms and len(matched_required_terms or []) < len(required_terms):
        return "missing_response_terms"
    if expected_terms and not matched_terms:
        return "missing_response_terms"
    return "unknown"


def smoke_recommended_fix(
    failure_kind: str,
    expected_actions: list[str],
    retrieval_evidence: dict[str, Any] | None = None,
    filtered_actions: list[Any] | None = None,
) -> str:
    expected = ", ".join(expected_actions) or "the expected action"
    if failure_kind == "no_data_fallback":
        issue = str((retrieval_evidence or {}).get("issue") or "")
        source = str((retrieval_evidence or {}).get("source") or "records")
        if issue == "no_active_records":
            return f"No active {source} are available for this client. Import/crawl the client's records, verify Data storage, then rerun prompt tests."
        if issue == "retrieval_returned_zero":
            return f"{source} exist, but retrieval returned zero records for this prompt. Check embeddings, query terms, prompt profile, and Data storage before rerunning prompt tests."
        if issue in {"all_vectors_missing", "some_vectors_missing"}:
            return f"{source} exist, but vector coverage is incomplete. Re-run vector sync or Setup run, then rerun prompt tests."
        return "Inspect Data storage and Crawl report, then rerun Setup run so retrieved records are available to the assistant."
    if failure_kind == "no_ui_action":
        return f"Inspect the Prompt profile and Adapter evidence; the assistant answered without emitting one of {expected}."
    if failure_kind == "action_mismatch":
        return f"Map this intent to one of {expected} in the prompt profile or generated adapter actions, then rerun prompt tests."
    if failure_kind == "missing_action_ids":
        return "Inspect retrieval evidence and action params; display actions must include product_ids or entity_ids from retrieved records before rerunning prompt tests."
    if failure_kind == "missing_response_terms":
        return "Tighten the prompt profile or recommendation logic so the response answers the requested recommendation detail, not only the record list."
    if failure_kind == "missing_required_action_params":
        missing = filtered_missing_params(filtered_actions)
        detail = f" ({', '.join(missing)})" if missing else ""
        return f"Teach field extraction or ask one short follow-up for missing required action params{detail}, then rerun prompt tests."
    if failure_kind == "blocked_action_filtered":
        return "The action is blocked by a managed website barrier or runtime health rule. Use the discovered handoff action/boundary instead of claiming autonomous completion."
    if failure_kind == "unsupported_action_filtered":
        return f"The prompt emitted an unavailable action. Map the intent to one of {expected} or repair generated adapter actions before rerunning prompt tests."
    return "Inspect the prompt profile, retrieved records, adapter actions, and runtime logs, then rerun prompt tests."


def primary_smoke_filter_reason(filtered_actions: list[Any] | None) -> str:
    reasons = [
        str(item.get("reason") or "").strip()
        for item in (filtered_actions or [])
        if isinstance(item, dict) and str(item.get("reason") or "").strip()
    ]
    priority = (
        "missing_required_params",
        "blocked_by_policy",
        "blocked_by_action_health",
        "unsupported_action",
    )
    for reason in priority:
        if reason in reasons:
            return reason
    return reasons[0] if reasons else ""


def filtered_missing_params(filtered_actions: list[Any] | None) -> list[str]:
    missing: list[str] = []
    for item in filtered_actions or []:
        if not isinstance(item, dict):
            continue
        raw_params = item.get("missing_params")
        if not isinstance(raw_params, (list, tuple)):
            continue
        for param in raw_params:
            clean = str(param or "").strip()
            if clean and clean not in missing:
                missing.append(clean)
    return missing
