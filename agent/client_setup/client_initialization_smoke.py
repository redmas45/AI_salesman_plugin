"""Assistant smoke-test orchestration for client initialization."""

from __future__ import annotations

import time
from typing import Any

from agent.client_setup import client_smoke_audit, client_smoke_cases, client_smoke_results

SMOKE_EXCEPTION_FIX = (
    "Check the assistant runtime error, API keys, model provider, and client prompt profile "
    "before rerunning prompt tests."
)


def exports(runtime: Any) -> dict[str, Any]:
    def assistant_smoke_stage(site_id: str, vertical_key: str) -> dict[str, Any]:
        tests: list[dict[str, Any]] = []
        for case in runtime._assistant_smoke_cases(site_id, vertical_key):
            attempts = 0
            success = False
            last_result = None
            while attempts < runtime.SMOKE_MAX_ATTEMPTS and not success:
                attempts += 1
                try:
                    result = runtime._run_assistant_turn(site_id, case["prompt"])
                    test_result = runtime._assistant_smoke_result(case, result)
                    last_result = test_result
                    if test_result["status"] == "ok":
                        success = True
                    else:
                        runtime._record_smoke_repair_need(site_id, case, test_result)
                except Exception as exc:
                    runtime.logger.error("Assistant smoke test failed for %s/%s: %s", site_id, case["name"], exc)
                    last_result = _exception_result(case, exc)
                    break

            if last_result:
                tests.append(last_result)

        passed = sum(1 for item in tests if item["status"] == "ok")
        failed = len(tests) - passed
        status = "ok" if failed == 0 else "failed"
        return runtime._stage(
            "assistant_smoke_tests",
            status,
            f"{passed}/{len(tests)} assistant smoke tests passed.",
            total=len(tests),
            passed=passed,
            failed=failed,
            tests=tests,
        )

    def record_smoke_repair_need(site_id: str, case: dict[str, Any], test_result: dict[str, Any]) -> None:
        client_smoke_audit.record_smoke_repair_need(site_id, case, test_result, runtime.admin_db, runtime.logger)

    def run_assistant_smoke_tests(site_id: str, vertical_key: str) -> dict[str, Any]:
        started = time.monotonic()
        started_at = runtime._utc_now()
        stage = runtime._assistant_smoke_stage(site_id, vertical_key)
        return {
            "source": "crm_assistant_smoke_tests",
            "status": stage["status"],
            "site_id": site_id,
            "vertical_key": vertical_key,
            "started_at": started_at,
            "completed_at": runtime._utc_now(),
            "duration_ms": (time.monotonic() - started) * 1000,
            "message": stage.get("message", ""),
            "total": stage.get("total", 0),
            "passed": stage.get("passed", 0),
            "failed": stage.get("failed", 0),
            "tests": stage.get("tests", []),
        }

    def assistant_smoke_cases(site_id: str, vertical_key: str | None = None) -> list[dict[str, Any]]:
        if vertical_key is None:
            return runtime._fallback_assistant_smoke_cases(site_id)
        contract_cases = runtime._action_contract_smoke_cases(site_id)
        if contract_cases:
            return contract_cases
        return runtime._schema_aware_smoke_cases(
            site_id,
            vertical_key,
            runtime._fallback_assistant_smoke_cases(vertical_key),
        )

    def fallback_assistant_smoke_cases(vertical_key: str) -> list[dict[str, Any]]:
        return client_smoke_cases.fallback_assistant_smoke_cases(vertical_key)

    def schema_aware_smoke_cases(site_id: str, vertical_key: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return client_smoke_cases.schema_aware_smoke_cases(
            site_id,
            vertical_key,
            cases,
            client_detail=runtime._client_detail,
        )

    def action_contract_smoke_cases(site_id: str) -> list[dict[str, Any]]:
        return client_smoke_cases.action_contract_smoke_cases(site_id, client_detail=runtime._client_detail)

    def smoke_action_configs(site_id: str) -> dict[str, dict[str, Any]]:
        return client_smoke_cases.smoke_action_configs(site_id, client_detail=runtime._client_detail)

    def run_assistant_turn(site_id: str, prompt: str) -> dict[str, Any]:
        from agent.orchestration import orchestrator_facade as orchestrator

        return orchestrator.run(
            site_id=site_id,
            audio_bytes=None,
            text_input=prompt,
            audio_filename="integration-smoke.txt",
            skip_tts=True,
            conversation_history=[],
            page_context={},
        )

    return {
        "_assistant_smoke_stage": assistant_smoke_stage,
        "_record_smoke_repair_need": record_smoke_repair_need,
        "run_assistant_smoke_tests": run_assistant_smoke_tests,
        "_assistant_smoke_cases": assistant_smoke_cases,
        "_fallback_assistant_smoke_cases": fallback_assistant_smoke_cases,
        "_schema_aware_smoke_cases": schema_aware_smoke_cases,
        "_action_contract_smoke_cases": action_contract_smoke_cases,
        "_smoke_action_configs": smoke_action_configs,
        "_smoke_required_param_clause": client_smoke_cases.smoke_required_param_clause,
        "_smoke_action_config_rejected": client_smoke_cases.smoke_action_config_rejected,
        "_smoke_action_config_text": client_smoke_cases.smoke_action_config_text,
        "_smoke_action_required_params": client_smoke_cases.smoke_action_required_params,
        "_smoke_schema_by_param": client_smoke_cases.smoke_schema_by_param,
        "_unique_smoke_params": client_smoke_cases.unique_smoke_params,
        "_smoke_value_for_param": client_smoke_cases.smoke_value_for_param,
        "_smoke_option_value": client_smoke_cases.smoke_option_value,
        "_append_smoke_details": client_smoke_cases.append_smoke_details,
        "_humanize_smoke_param": client_smoke_cases.humanize_smoke_param,
        "_smoke_case": client_smoke_cases.smoke_case,
        "_run_assistant_turn": run_assistant_turn,
        "_assistant_smoke_result": client_smoke_results.assistant_smoke_result,
        "_display_action_evidence": client_smoke_results.display_action_evidence_for,
        "_display_payload_ok": client_smoke_results.display_payload_is_valid,
        "_contains_blocked_smoke_phrase": client_smoke_results.contains_blocked_smoke_phrase,
        "_smoke_failure_reason": client_smoke_results.smoke_failure_reason,
        "_smoke_failure_kind": client_smoke_results.smoke_failure_kind,
        "_smoke_recommended_fix": client_smoke_results.smoke_recommended_fix,
        "_primary_smoke_filter_reason": client_smoke_results.primary_smoke_filter_reason,
        "_filtered_missing_params": client_smoke_results.filtered_missing_params,
    }


def _exception_result(case: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "name": case["name"],
        "prompt": case["prompt"],
        "status": "failed",
        "expected_actions": [str(action).upper() for action in case.get("expected_actions") or []],
        "expected_response_terms_any": [
            str(term).lower()
            for term in case.get("expected_response_terms_any") or []
            if str(term).strip()
        ],
        "expected_response_terms_all": [
            str(term).lower()
            for term in case.get("expected_response_terms_all") or []
            if str(term).strip()
        ],
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
        "recommended_fix": SMOKE_EXCEPTION_FIX,
    }
