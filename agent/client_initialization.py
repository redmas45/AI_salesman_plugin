"""Automatic one-script client initialization jobs."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import config
from agent.flow_discovery import DEFAULT_FLOW_MAX_PAGES, discover_site_flows
from agent.flow_regression import build_flow_regression_report
from agent.flow_rehearsal import DEFAULT_REHEARSAL_MAX_STEPS, rehearse_site_flows
from agent.ingestion import sync_web_crawl
from db import admin as admin_db

logger = logging.getLogger(__name__)

INITIALIZATION_SOURCE = "widget_registration"
DISPLAY_ACTION_ID_PARAMS = {
    "SHOW_PRODUCTS": "product_ids",
    "SHOW_COMPARISON": "product_ids",
    "SHOW_ENTITIES": "entity_ids",
    "COMPARE_ENTITIES": "entity_ids",
}


def run_widget_initialization(
    site_id: str,
    site_url: str,
    *,
    vertical_key: str,
    run_crawl: bool,
    run_flow: bool,
    run_rehearsal: bool,
    crawl_max_pages: int,
    crawl_max_depth: int,
    flow_max_pages: int = DEFAULT_FLOW_MAX_PAGES,
    rehearsal_max_steps: int = DEFAULT_REHEARSAL_MAX_STEPS,
    run_readiness: bool = True,
    run_smoke_tests: bool = False,
) -> dict[str, Any]:
    """Run automatic onboarding after the universal script registers."""
    started = time.monotonic()
    started_at = _utc_now()
    stages: list[dict[str, Any]] = []

    def save_running() -> None:
        _save_report(site_id, _report(site_id, site_url, vertical_key, "running", stages, started_at, started))

    save_running()

    previous_client = _client_detail(site_id)
    flow_report: dict[str, Any] = {}
    rehearsal_report: dict[str, Any] = {}

    if run_crawl:
        _start_stage(stages, "crawl", "Content crawl is running.")
        save_running()
        stages[-1] = _crawl_stage(site_id, site_url, crawl_max_pages, crawl_max_depth)
        save_running()
    if run_flow:
        _start_stage(stages, "flow_discovery", "Adapter flow discovery is running.")
        save_running()
        flow_report, flow_stage = _flow_stage(site_id, site_url, vertical_key, flow_max_pages)
        stages[-1] = flow_stage
        save_running()
    rehearsal_flow_report = flow_report or _existing_flow_report(site_id)
    if run_rehearsal and rehearsal_flow_report:
        _start_stage(stages, "flow_rehearsal", "Safe action rehearsal is running.")
        save_running()
        rehearsal_report, rehearsal_stage = _rehearsal_stage(site_id, site_url, rehearsal_flow_report, rehearsal_max_steps)
        stages[-1] = rehearsal_stage
        save_running()
    elif run_rehearsal:
        stages.append(_stage("flow_rehearsal", "skipped", "No flow report is available to rehearse."))
        save_running()
    if flow_report:
        _start_stage(stages, "flow_regression", "Flow regression comparison is running.")
        save_running()
        stages[-1] = _regression_stage(site_id, site_url, previous_client, flow_report, rehearsal_report)
        save_running()
    if run_readiness:
        _start_stage(stages, "readiness_scan", "Readiness scan is running.")
        save_running()
        stages[-1] = _readiness_stage(site_id, site_url, vertical_key)
        save_running()
    if run_smoke_tests:
        _start_stage(stages, "assistant_smoke_tests", "Assistant prompt smoke tests are running.")
        save_running()
        stages[-1] = _assistant_smoke_stage(site_id, vertical_key)
        save_running()

    status = _overall_status(stages)
    final_report = _report(site_id, site_url, vertical_key, status, stages, started_at, started)
    _save_report(site_id, final_report)
    
    if status == "ok":
        admin_db.update_client_setup_status(site_id, needs_setup=False, last_setup_at=_utc_now())
        
    return final_report


def _crawl_stage(site_id: str, site_url: str, max_pages: int, max_depth: int) -> dict[str, Any]:
    try:
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_RUNNING, "Auto initialization crawl started.")
        sync_web_crawl(
            site_url,
            max_pages=max_pages,
            max_depth=max_depth,
            site_id=site_id,
            reconcile_missing=True,
            source_name="widget_initialization_crawler",
        )
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_OK, "Auto initialization crawl completed.")
        return _stage("crawl", "ok", "Content crawl completed.")
    except Exception as exc:
        logger.error("Auto initialization crawl failed for %s: %s", site_id, exc)
        admin_db.update_client_crawl_status(site_id, admin_db.CRAWL_STATUS_ERROR, str(exc))
        return _stage("crawl", "failed", str(exc))


def _flow_stage(site_id: str, site_url: str, vertical_key: str, max_pages: int) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        flow_report = asyncio.run(
            discover_site_flows(site_url, site_id, vertical_key=vertical_key, max_pages=max_pages)
        ).to_dict()
        admin_db.save_client_flow_report(site_id, flow_report)
        summary = flow_report.get("summary") if isinstance(flow_report.get("summary"), dict) else {}
        return flow_report, _stage("flow_discovery", "ok", "Flow discovery completed.", summary=summary)
    except Exception as exc:
        logger.error("Auto flow discovery failed for %s: %s", site_id, exc)
        return {}, _stage("flow_discovery", "failed", str(exc))


def _rehearsal_stage(
    site_id: str,
    site_url: str,
    flow_report: dict[str, Any],
    max_steps: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        rehearsal_report = asyncio.run(
            rehearse_site_flows(site_url, site_id, flow_report, max_steps=max_steps)
        ).to_dict()
        admin_db.save_client_rehearsal_report(site_id, rehearsal_report)
        summary = rehearsal_report.get("summary") if isinstance(rehearsal_report.get("summary"), dict) else {}
        return rehearsal_report, _stage("flow_rehearsal", "ok", "Flow rehearsal completed.", summary=summary)
    except Exception as exc:
        logger.error("Auto flow rehearsal failed for %s: %s", site_id, exc)
        return {}, _stage("flow_rehearsal", "failed", str(exc))


def _regression_stage(
    site_id: str,
    site_url: str,
    previous_client: dict[str, Any],
    flow_report: dict[str, Any],
    rehearsal_report: dict[str, Any],
) -> dict[str, Any]:
    try:
        previous_config = previous_client.get("vertical_config") if isinstance(previous_client.get("vertical_config"), dict) else {}
        regression = build_flow_regression_report(
            previous_config.get("flow") if isinstance(previous_config.get("flow"), dict) else {},
            flow_report,
            previous_rehearsal=previous_config.get("rehearsal") if isinstance(previous_config.get("rehearsal"), dict) else {},
            current_rehearsal=rehearsal_report,
            site_id=site_id,
            site_url=site_url,
        ).to_dict()
        admin_db.save_client_regression_report(site_id, regression)
        return _stage(
            "flow_regression",
            "ok",
            "Flow regression snapshot saved.",
            regression_status=regression.get("status"),
        )
    except Exception as exc:
        logger.error("Auto flow regression failed for %s: %s", site_id, exc)
        return _stage("flow_regression", "failed", str(exc))


def _readiness_stage(site_id: str, site_url: str, vertical_key: str) -> dict[str, Any]:
    try:
        client = _client_detail(site_id)
        vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
        from agent.scanner import scan_site

        report = asyncio.run(
            scan_site(
                site_url,
                site_id,
                adapter_name=str(client.get("adapter_name") or ""),
                vertical_key=str(client.get("vertical_key") or vertical_key),
                vertical_config=vertical_config,
            )
        ).to_dict()
        admin_db.save_readiness_report(site_id, report)
        supported = sum(1 for capability in report.get("capabilities", []) if capability.get("supported"))
        total = len(report.get("capabilities", []))
        return _stage(
            "readiness_scan",
            "ok",
            "Readiness scan completed.",
            supported=supported,
            total=total,
            platform=report.get("platform"),
            platform_confidence=report.get("platform_confidence"),
        )
    except Exception as exc:
        logger.error("Auto readiness scan failed for %s: %s", site_id, exc)
        return _stage("readiness_scan", "failed", str(exc))


def _assistant_smoke_stage(site_id: str, vertical_key: str) -> dict[str, Any]:
    tests: list[dict[str, Any]] = []
    for case in _assistant_smoke_cases(site_id, vertical_key):
        attempts = 0
        success = False
        last_result = None
        while attempts < 3 and not success:
            attempts += 1
            try:
                result = _run_assistant_turn(site_id, case["prompt"])
                test_result = _assistant_smoke_result(case, result)
                last_result = test_result
                if test_result["status"] == "ok":
                    success = True
                else:
                    if attempts < 3:
                        logger.warning("Smoke test failed (attempt %d). Auto-repairing: %s", attempts, test_result.get("failure_kind"))
                        _auto_repair_smoke_failure(site_id, case, test_result)
            except Exception as exc:
                logger.error("Assistant smoke test failed for %s/%s: %s", site_id, case["name"], exc)
                last_result = {
                    "name": case["name"],
                    "prompt": case["prompt"],
                    "status": "failed",
                    "expected_actions": [str(action).upper() for action in case.get("expected_actions") or []],
                    "expected_response_terms_any": [str(term).lower() for term in case.get("expected_response_terms_any") or [] if str(term).strip()],
                    "expected_response_terms_all": [str(term).lower() for term in case.get("expected_response_terms_all") or [] if str(term).strip()],
                    "actual_actions": [],
                    "matched_actions": [],
                    "matched_response_terms": [],
                    "matched_response_terms_all": [],
                    "display_action_evidence": [],
                    "retrieval_evidence": {},
                    "intent": "",
                    "response_excerpt": "",
                    "failure_kind": "exception",
                    "reason": str(exc),
                    "recommended_fix": "Check the assistant runtime error, API keys, model provider, and client prompt profile before rerunning prompt tests.",
                }
                break

        if last_result:
            tests.append(last_result)

    passed = sum(1 for item in tests if item["status"] == "ok")
    failed = len(tests) - passed
    status = "ok" if failed == 0 else "failed"
    return _stage(
        "assistant_smoke_tests",
        status,
        f"{passed}/{len(tests)} assistant smoke tests passed.",
        total=len(tests),
        passed=passed,
        failed=failed,
        tests=tests,
    )

def _auto_repair_smoke_failure(site_id: str, case: dict[str, Any], test_result: dict[str, Any]) -> None:
    if not _external_smoke_llm_enabled():
        logger.info("Skipping smoke auto-repair because external LLM calls are disabled.")
        return

    from db.prompts import get_client_prompt_profile, save_client_prompt_profile
    from agent.llm import _get_client
    
    prompt = f"""
    The automated smoke test for a chatbot failed. 
    User Prompt: "{case['prompt']}"
    Expected Actions: {case.get('expected_actions')}
    Actual Actions: {test_result.get('actual_actions')}
    Failure Kind: {test_result.get('failure_kind')}
    Assistant Response: {test_result.get('response_excerpt')}
    
    Write a 1-sentence developer rule to add to the assistant's prompt profile to fix this issue.
    For example: 'If the user asks for FAQ, always trigger the OPEN_POLICY action.'
    Just return the single sentence, nothing else.
    """
    
    try:
        openai_client = _get_client()
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100
        )
        rule = completion.choices[0].message.content.strip().strip('"').strip("'")
        profile_data = get_client_prompt_profile(site_id)
        if profile_data and rule:
            active_version = profile_data.get("active_version")
            if active_version:
                existing_rules = active_version.get("developer_rules") or ""
                new_rules = existing_rules.strip()
                if new_rules:
                    new_rules += "\n"
                new_rules += f"- [CRITICAL OVERRIDE RULE] {rule}"
                
                save_client_prompt_profile(
                    site_id,
                    name=profile_data["profile"]["name"],
                    system_prompt=active_version.get("system_prompt", ""),
                    developer_rules=new_rules,
                    publish=True,
                    changelog="Auto-repair from smoke test failure"
                )
                logger.info("Auto-repaired prompt profile with rule: %s", rule)
    except Exception as e:
        logger.error("Auto repair LLM generation failed: %s", e)


def run_assistant_smoke_tests(site_id: str, vertical_key: str) -> dict[str, Any]:
    """Run source-backed assistant prompt checks without crawling or replacing the setup report."""
    started = time.monotonic()
    started_at = _utc_now()
    stage = _assistant_smoke_stage(site_id, vertical_key)
    return {
        "source": "crm_assistant_smoke_tests",
        "status": stage["status"],
        "site_id": site_id,
        "vertical_key": vertical_key,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "duration_ms": (time.monotonic() - started) * 1000,
        "message": stage.get("message", ""),
        "total": stage.get("total", 0),
        "passed": stage.get("passed", 0),
        "failed": stage.get("failed", 0),
        "tests": stage.get("tests", []),
    }


def _assistant_smoke_cases(site_id: str, vertical_key: str | None = None) -> list[dict[str, Any]]:
    if vertical_key is None:
        return _fallback_assistant_smoke_cases(site_id)

    client = _client_detail(site_id)
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    domain = client.get("domain") or client.get("store_url") or client.get("allowed_origin") or site_id

    if not _external_smoke_llm_enabled():
        return _fallback_assistant_smoke_cases(vertical_key)

    prompt = f"""
    You are generating 2-3 smoke test queries for an AI agent on the domain {domain}.
    The agent belongs to vertical: {vertical_key}.
    The vertical config context: {vertical_config}
    
    Please return a JSON object with a single key "cases", which is an array of objects representing test queries the user might ask.
    Each object must have:
    - "name": string (a short snake_case name for the test)
    - "prompt": string (the simulated user query)
    - "expected_actions": list of strings (e.g. ["SHOW_ENTITIES", "COMPARE_ENTITIES", "START_BOOKING", "CAPTURE_LEAD"])
    - "expected_terms": optional list of strings
    - "required_terms": optional list of strings
    
    Make the tests highly specific to the domain's actual products/services found in the config if available.
    """
    
    try:
        from agent.llm import _get_client
        import json
        
        openai_client = _get_client()
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        cases = data.get("cases", [])
        
        return [
            _smoke_case(
                c.get("name", "test"),
                c.get("prompt", "Hello"),
                c.get("expected_actions", []),
                expected_terms=c.get("expected_terms"),
                required_terms=c.get("required_terms")
            ) for c in cases
        ][:3] or _fallback_assistant_smoke_cases(vertical_key)
    except Exception as exc:
        logger.error("Failed to generate dynamic smoke cases: %s", exc)
        return _fallback_assistant_smoke_cases(vertical_key)


def _external_smoke_llm_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    return bool(config.OPENAI_API_KEY)


def _fallback_assistant_smoke_cases(vertical_key: str) -> list[dict[str, Any]]:
    cases_by_vertical: dict[str, list[dict[str, Any]]] = {
        "ecommerce": [
            _smoke_case(
                "compare_apple_samsung_phone",
                "Compare Apple and Samsung phones.",
                ["SHOW_COMPARISON"],
                required_terms=["apple", "samsung"],
            ),
            _smoke_case(
                "sort_phones_low_to_high",
                "Sort phones low to high.",
                ["SORT_PRODUCTS"],
            ),
            _smoke_case(
                "recommend_phone_accessory",
                "Recommend a phone and tell me what accessory I should buy with it.",
                ["SHOW_PRODUCTS"],
                expected_terms=["accessory", "case"],
            ),
        ],
        "insurance": [
            _smoke_case(
                "compare_insurance_plans",
                "Compare available insurance plans for me.",
                ["COMPARE_ENTITIES", "SHOW_ENTITIES"],
            ),
            _smoke_case(
                "start_insurance_quote",
                "Help me get an insurance quote.",
                ["START_QUOTE", "HANDOFF_TO_AGENT", "HANDOFF_TO_LICENSED_AGENT"],
            ),
        ],
        "travel": [
            _smoke_case("search_travel_availability", "Find available trips for my dates.", ["SEARCH_AVAILABILITY", "SHOW_ENTITIES"]),
            _smoke_case("start_travel_booking", "Help me start a booking.", ["START_BOOKING", "HANDOFF_TO_AGENT"]),
        ],
        "finance_broker": [
            _smoke_case("run_finance_calculator", "Calculate options for my budget.", ["RUN_CALCULATOR", "RUN_AFFORDABILITY_CALCULATOR"]),
            _smoke_case("start_finance_application", "Help me start an application.", ["START_APPLICATION", "HANDOFF_TO_ADVISOR"]),
        ],
        "healthcare": [
            _smoke_case("find_healthcare_services", "Show me available services or providers.", ["SHOW_ENTITIES"]),
            _smoke_case("request_healthcare_appointment", "Help me request an appointment.", ["REQUEST_APPOINTMENT", "HANDOFF_TO_CLINIC"]),
        ],
        "food": [
            _smoke_case("show_food_menu", "Show me menu options.", ["SHOW_ENTITIES"]),
            _smoke_case("set_food_location", "Check delivery for my location.", ["SET_LOCATION", "CAPTURE_LEAD"]),
        ],
        "real_estate": [
            _smoke_case("show_real_estate_listings", "Show properties that match my needs.", ["SHOW_ENTITIES"]),
            _smoke_case("request_property_viewing", "Help me request a viewing.", ["REQUEST_VIEWING", "CONTACT_AGENT"]),
        ],
        "education": [
            _smoke_case("show_education_programs", "Show programs for my learning goal.", ["SHOW_ENTITIES", "BUILD_LEARNING_PATH"]),
            _smoke_case("start_education_enrollment", "Help me start enrollment.", ["START_ENROLLMENT", "REQUEST_COUNSELOR_CALLBACK"]),
        ],
        "automotive": [
            _smoke_case("compare_automotive_options", "Compare available vehicles for me.", ["COMPARE_ENTITIES", "SHOW_ENTITIES"]),
            _smoke_case("request_test_drive", "Help me request a test drive.", ["REQUEST_TEST_DRIVE", "CONTACT_AGENT"]),
        ],
        "legal_services": [
            _smoke_case("show_legal_services", "Show services for my matter.", ["SHOW_ENTITIES"]),
            _smoke_case("request_legal_consultation", "Help me request a consultation.", ["REQUEST_CONSULTATION", "HANDOFF_TO_LAWYER"]),
        ],
        "jobs_recruiting": [
            _smoke_case("match_jobs", "Match jobs to my role and skills.", ["MATCH_JOBS", "SHOW_ENTITIES"]),
            _smoke_case("start_job_application", "Help me start an application.", ["START_APPLICATION", "CAPTURE_LEAD"]),
        ],
        "events_ticketing": [
            _smoke_case("show_events", "Show available events.", ["SHOW_ENTITIES"]),
            _smoke_case("check_ticket_availability", "Check ticket availability.", ["CHECK_AVAILABILITY", "START_TICKET_PURCHASE"]),
        ],
        "construction": [
            _smoke_case("show_construction_services", "Show construction services for my project.", ["SHOW_ENTITIES", "OPEN_SERVICES"]),
            _smoke_case("request_construction_estimate", "Help me request an estimate.", ["REQUEST_ESTIMATE", "REQUEST_SITE_VISIT"]),
        ],
    }
    return cases_by_vertical.get(
        vertical_key,
        [
            _smoke_case("show_available_options", "Show me available options.", ["SHOW_ENTITIES"]),
            _smoke_case("navigate_to_contact", "Navigate me to the contact page.", ["NAVIGATE_TO", "OPEN_CONTACT"]),
        ],
    )


def _smoke_case(
    name: str,
    prompt: str,
    expected_actions: list[str],
    *,
    expected_terms: list[str] | None = None,
    required_terms: list[str] | None = None,
) -> dict[str, Any]:
    case: dict[str, Any] = {
        "name": name,
        "prompt": prompt,
        "expected_actions": expected_actions,
    }
    if expected_terms:
        case["expected_response_terms_any"] = expected_terms
    if required_terms:
        case["expected_response_terms_all"] = required_terms
    return case


def _run_assistant_turn(site_id: str, prompt: str) -> dict[str, Any]:
    from agent import orchestrator

    return orchestrator.run(
        site_id=site_id,
        audio_bytes=None,
        text_input=prompt,
        audio_filename="integration-smoke.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )


def _assistant_smoke_result(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
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
    blocked_phrase = _contains_blocked_smoke_phrase(response_text)
    matched_actions = sorted(set(action_names).intersection(expected_actions))
    matched_terms = [term for term in expected_terms if term in response_text.lower()]
    matched_required_terms = [term for term in required_terms if term in response_text.lower()]
    display_action_evidence = _display_action_evidence(actions)
    display_payload_ok = _display_payload_ok(matched_actions, display_action_evidence)
    passed = (
        bool(matched_actions)
        and not blocked_phrase
        and display_payload_ok
        and (not expected_terms or bool(matched_terms))
        and len(matched_required_terms) == len(required_terms)
    )
    failure_kind = "" if passed else _smoke_failure_kind(
        action_names,
        matched_actions,
        blocked_phrase,
        expected_terms,
        matched_terms,
        required_terms,
        matched_required_terms,
        display_payload_ok,
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
        "retrieval_evidence": retrieval_evidence,
        "intent": str(result.get("intent") or ""),
        "response_excerpt": response_text[:320],
        "failure_kind": failure_kind,
        "reason": "" if passed else _smoke_failure_reason(
            expected_actions,
            action_names,
            blocked_phrase,
            expected_terms,
            matched_terms,
            required_terms,
            matched_required_terms,
            display_payload_ok,
        ),
        "recommended_fix": "" if passed else _smoke_recommended_fix(failure_kind, expected_actions, retrieval_evidence),
    }


def _display_action_evidence(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _display_payload_ok(matched_actions: list[str], display_action_evidence: list[dict[str, Any]]) -> bool:
    required_actions = [action for action in matched_actions if action in DISPLAY_ACTION_ID_PARAMS]
    if not required_actions:
        return True
    return any(
        str(item.get("action") or "").upper() in required_actions and int(item.get("id_count") or 0) > 0
        for item in display_action_evidence
    )


def _contains_blocked_smoke_phrase(response_text: str) -> bool:
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


def _smoke_failure_reason(
    expected_actions: list[str],
    action_names: list[str],
    blocked_phrase: bool,
    expected_terms: list[str] | None = None,
    matched_terms: list[str] | None = None,
    required_terms: list[str] | None = None,
    matched_required_terms: list[str] | None = None,
    display_payload_ok: bool = True,
) -> str:
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


def _smoke_failure_kind(
    action_names: list[str],
    matched_actions: list[str],
    blocked_phrase: bool,
    expected_terms: list[str] | None = None,
    matched_terms: list[str] | None = None,
    required_terms: list[str] | None = None,
    matched_required_terms: list[str] | None = None,
    display_payload_ok: bool = True,
) -> str:
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


def _smoke_recommended_fix(
    failure_kind: str,
    expected_actions: list[str],
    retrieval_evidence: dict[str, Any] | None = None,
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
    return "Inspect the prompt profile, retrieved records, adapter actions, and runtime logs, then rerun prompt tests."


def _client_detail(site_id: str) -> dict[str, Any]:
    try:
        return admin_db.get_client_detail(site_id)
    except LookupError:
        return {"site_id": site_id, "vertical_config": {}}


def _existing_flow_report(site_id: str) -> dict[str, Any]:
    client = _client_detail(site_id)
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    flow_report = vertical_config.get("flow")
    return flow_report if isinstance(flow_report, dict) else {}


def _save_report(site_id: str, report: dict[str, Any]) -> None:
    try:
        admin_db.save_client_initialization_report(site_id, report)
    except (LookupError, ValueError) as exc:
        logger.warning("Initialization report could not be saved for %s: %s", site_id, exc)


def _report(
    site_id: str,
    site_url: str,
    vertical_key: str,
    status: str,
    stages: list[dict[str, Any]],
    started_at: str,
    started: float,
) -> dict[str, Any]:
    return {
        "source": INITIALIZATION_SOURCE,
        "status": status,
        "site_id": site_id,
        "site_url": site_url,
        "vertical_key": vertical_key,
        "started_at": started_at,
        "completed_at": _utc_now() if status != "running" else "",
        "duration_ms": (time.monotonic() - started) * 1000,
        "stages": [dict(stage) for stage in stages],
    }


def _stage(name: str, status: str, message: str, **extra: Any) -> dict[str, Any]:
    started_at = str(extra.pop("started_at", "") or "")
    completed_at = str(extra.pop("completed_at", "") or "")
    return {
        "name": name,
        "status": status,
        "message": message,
        "started_at": started_at,
        "completed_at": completed_at if status == "running" else completed_at or _utc_now(),
        **extra,
    }


def _start_stage(stages: list[dict[str, Any]], name: str, message: str) -> None:
    stages.append(_stage(name, "running", message, started_at=_utc_now(), completed_at=""))


def _overall_status(stages: list[dict[str, Any]]) -> str:
    failed = [stage for stage in stages if stage.get("status") == "failed"]
    succeeded = [stage for stage in stages if stage.get("status") == "ok"]
    if failed and succeeded:
        return "partial"
    if failed:
        return "error"
    return "ok"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
