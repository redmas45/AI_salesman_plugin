"""Assistant smoke-test case generation for client setup."""

from __future__ import annotations

from typing import Any, Callable

from agent.actions.registry import get_action

ClientDetailLoader = Callable[[str], dict[str, Any]]

SMOKE_RESULT_ACTIONS = frozenset(
    {
        "CHECK_AVAILABILITY",
        "CHECK_DELIVERY_AVAILABILITY",
        "FILTER_ENTITIES",
        "FILTER_PRODUCTS",
        "MATCH_JOBS",
        "RUN_AFFORDABILITY_CALCULATOR",
        "RUN_CALCULATOR",
        "SEARCH_AVAILABILITY",
        "SET_LOCATION",
    }
)
SMOKE_CREDENTIAL_TERMS = frozenset(
    {
        "current password",
        "login",
        "one time password",
        "otp",
        "passcode",
        "password",
        "sign in",
        "signin",
        "username",
        "verification code",
    }
)


def assistant_smoke_cases(
    site_id: str,
    vertical_key: str | None = None,
    *,
    client_detail: ClientDetailLoader,
) -> list[dict[str, Any]]:
    if vertical_key is None:
        return fallback_assistant_smoke_cases(site_id)

    contract_cases = action_contract_smoke_cases(site_id, client_detail=client_detail)
    if contract_cases:
        return contract_cases

    return schema_aware_smoke_cases(
        site_id,
        vertical_key,
        fallback_assistant_smoke_cases(vertical_key),
        client_detail=client_detail,
    )


def fallback_assistant_smoke_cases(vertical_key: str) -> list[dict[str, Any]]:
    cases_by_vertical: dict[str, list[dict[str, Any]]] = {
        "ecommerce": [
            smoke_case(
                "compare_apple_samsung_phone",
                "Compare Apple and Samsung phones.",
                ["SHOW_COMPARISON"],
                required_terms=["apple", "samsung"],
            ),
            smoke_case("sort_phones_low_to_high", "Sort phones low to high.", ["SORT_PRODUCTS"]),
            smoke_case(
                "recommend_phone_accessory",
                "Recommend a phone and tell me what accessory I should buy with it.",
                ["SHOW_PRODUCTS"],
                expected_terms=["accessory", "case"],
            ),
        ],
        "insurance": [
            smoke_case("compare_insurance_plans", "Compare available insurance plans for me.", ["COMPARE_ENTITIES", "SHOW_ENTITIES"]),
            smoke_case("start_insurance_quote", "Help me get an insurance quote.", ["START_QUOTE", "HANDOFF_TO_AGENT", "HANDOFF_TO_LICENSED_AGENT"]),
        ],
        "travel": [
            smoke_case("search_travel_availability", "Find available trips for my dates.", ["SEARCH_AVAILABILITY", "SHOW_ENTITIES"]),
            smoke_case("start_travel_booking", "Help me start a booking.", ["START_BOOKING", "HANDOFF_TO_AGENT"]),
        ],
        "finance_broker": [
            smoke_case("run_finance_calculator", "Calculate options for my budget.", ["RUN_CALCULATOR", "RUN_AFFORDABILITY_CALCULATOR"]),
            smoke_case("start_finance_application", "Help me start an application.", ["START_APPLICATION", "HANDOFF_TO_ADVISOR"]),
        ],
        "healthcare": [
            smoke_case("find_healthcare_services", "Show me available services or providers.", ["SHOW_ENTITIES"]),
            smoke_case("request_healthcare_appointment", "Help me request an appointment.", ["REQUEST_APPOINTMENT", "HANDOFF_TO_CLINIC"]),
        ],
        "food": [
            smoke_case("show_food_menu", "Show me menu options.", ["SHOW_ENTITIES"]),
            smoke_case("set_food_location", "Check delivery for my location.", ["SET_LOCATION", "CAPTURE_LEAD"]),
        ],
        "real_estate": [
            smoke_case("show_real_estate_listings", "Show properties that match my needs.", ["SHOW_ENTITIES"]),
            smoke_case("request_property_viewing", "Help me request a viewing.", ["REQUEST_VIEWING", "CONTACT_AGENT"]),
        ],
        "education": [
            smoke_case("show_education_programs", "Show programs for my learning goal.", ["SHOW_ENTITIES", "BUILD_LEARNING_PATH"]),
            smoke_case("start_education_enrollment", "Help me start enrollment.", ["START_ENROLLMENT", "REQUEST_COUNSELOR_CALLBACK"]),
        ],
        "automotive": [
            smoke_case("compare_automotive_options", "Compare available vehicles for me.", ["COMPARE_ENTITIES", "SHOW_ENTITIES"]),
            smoke_case("request_test_drive", "Help me request a test drive.", ["REQUEST_TEST_DRIVE", "CONTACT_AGENT"]),
        ],
        "legal_services": [
            smoke_case("show_legal_services", "Show services for my matter.", ["SHOW_ENTITIES"]),
            smoke_case("request_legal_consultation", "Help me request a consultation.", ["REQUEST_CONSULTATION", "HANDOFF_TO_LAWYER"]),
        ],
        "jobs_recruiting": [
            smoke_case("match_jobs", "Match jobs to my role and skills.", ["MATCH_JOBS", "SHOW_ENTITIES"]),
            smoke_case("start_job_application", "Help me start an application.", ["START_APPLICATION", "CAPTURE_LEAD"]),
        ],
        "events_ticketing": [
            smoke_case("show_events", "Show available events.", ["SHOW_ENTITIES"]),
            smoke_case("check_ticket_availability", "Check ticket availability.", ["CHECK_AVAILABILITY", "START_TICKET_PURCHASE"]),
        ],
        "construction": [
            smoke_case("show_construction_services", "Show construction services for my project.", ["SHOW_ENTITIES", "OPEN_SERVICES"]),
            smoke_case("request_construction_estimate", "Help me request an estimate.", ["REQUEST_ESTIMATE", "REQUEST_SITE_VISIT"]),
        ],
    }
    return cases_by_vertical.get(
        vertical_key,
        [
            smoke_case("show_available_options", "Show me available options.", ["SHOW_ENTITIES"]),
            smoke_case("navigate_to_contact", "Navigate me to the contact page.", ["NAVIGATE_TO", "OPEN_CONTACT"]),
        ],
    )


def schema_aware_smoke_cases(
    site_id: str,
    vertical_key: str,
    cases: list[dict[str, Any]],
    *,
    client_detail: ClientDetailLoader,
) -> list[dict[str, Any]]:
    action_configs = smoke_action_configs(site_id, client_detail=client_detail)
    if not action_configs:
        return cases

    enriched_cases: list[dict[str, Any]] = []
    for case in cases:
        updated = dict(case)
        prompt = str(updated.get("prompt") or "")
        for action_name in [str(action or "").upper() for action in updated.get("expected_actions") or []]:
            clause = smoke_required_param_clause(action_configs.get(action_name) or {})
            if clause:
                prompt = append_smoke_details(prompt, clause)
                updated["schema_enriched"] = True
                break
        updated["prompt"] = prompt
        enriched_cases.append(updated)
    return enriched_cases


def action_contract_smoke_cases(site_id: str, *, client_detail: ClientDetailLoader) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for action_name, action_config in smoke_action_configs(site_id, client_detail=client_detail).items():
        if not get_action(action_name):
            continue
        if smoke_action_config_rejected(action_name, action_config):
            continue
        clause = smoke_required_param_clause(action_config)
        if not clause:
            continue
        label = str(action_config.get("label") or action_name.replace("_", " ").title()).strip()
        case = smoke_case(
            f"{action_name.lower()}_contract",
            f"Please run {label}. Use these exact field values: {clause}.",
            [action_name],
        )
        case["schema_enriched"] = True
        cases.append(case)
        if len(cases) >= 3:
            break
    return cases


def smoke_action_configs(site_id: str, *, client_detail: ClientDetailLoader) -> dict[str, dict[str, Any]]:
    client = client_detail(site_id)
    vertical_config = client.get("vertical_config") if isinstance(client.get("vertical_config"), dict) else {}
    actions = vertical_config.get("actions") if isinstance(vertical_config, dict) else {}
    if not isinstance(actions, dict):
        return {}
    return {
        str(action_name or "").upper(): action_config
        for action_name, action_config in actions.items()
        if str(action_name or "").strip() and isinstance(action_config, dict)
    }


def smoke_required_param_clause(action_config: dict[str, Any]) -> str:
    params = smoke_action_required_params(action_config)
    if not params:
        return ""
    schema_by_param = smoke_schema_by_param(action_config)
    parts = []
    for param in params[:6]:
        value = smoke_value_for_param(param, schema_by_param.get(param) or {})
        if value:
            parts.append(f"{humanize_smoke_param(param)}: {value}")
    if len(parts) < len(params[:6]):
        return ""
    return "; ".join(parts)


def smoke_action_config_rejected(action_name: str, action_config: dict[str, Any]) -> bool:
    text = smoke_action_config_text(action_config)
    if any(term in text for term in SMOKE_CREDENTIAL_TERMS):
        return True
    if str(action_name or "").upper() in SMOKE_RESULT_ACTIONS and " password " in f" {text} ":
        return True
    return False


def smoke_action_config_text(action_config: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ("label", "type", "form", "input", "submit"):
        values.append(str(action_config.get(key) or ""))
    for param in smoke_action_required_params(action_config):
        values.append(str(param or ""))
    schema = action_config.get("field_schema")
    if isinstance(schema, list):
        for item in schema:
            if not isinstance(item, dict):
                continue
            for key in ("param", "label", "name", "placeholder", "type", "autocomplete"):
                values.append(str(item.get(key) or ""))
    return " ".join(" ".join(values).lower().replace("_", " ").replace("-", " ").split())


def smoke_action_required_params(action_config: dict[str, Any]) -> list[str]:
    required_fields = action_config.get("required_fields")
    if isinstance(required_fields, list):
        return unique_smoke_params(required_fields)
    params: list[str] = []
    steps = action_config.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict) or step.get("optional") is True:
                continue
            param = str(step.get("param") or step.get("parameter") or step.get("name") or "").strip()
            if param:
                params.append(param)
    return unique_smoke_params(params)


def smoke_schema_by_param(action_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    schema = action_config.get("field_schema")
    if not isinstance(schema, list):
        return {}
    return {
        str(item.get("param") or "").strip(): item
        for item in schema
        if isinstance(item, dict) and str(item.get("param") or "").strip()
    }


def unique_smoke_params(params: list[Any]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for param in params:
        clean = str(param or "").strip()
        key = clean.lower().replace("-", "_")
        if not clean or key in seen:
            continue
        seen.add(key)
        rows.append(clean)
    return rows


def smoke_value_for_param(param: str, schema: dict[str, Any]) -> str:
    option_value = smoke_option_value(schema.get("options"))
    if option_value:
        return option_value
    text = f"{param} {schema.get('label') or ''} {schema.get('type') or ''}".lower().replace("_", " ")
    field_type = str(schema.get("type") or "").lower()
    label = humanize_smoke_param(param)
    if field_type in {"date", "datetime", "datetime-local", "month", "time"}:
        return "2026-08-15"
    if field_type in {"number", "range"}:
        if "age" in text or "eldest" in text:
            return "27"
        if any(term in text for term in ("budget", "amount", "price", "cost", "premium", "income", "loan", "emi", "salary")):
            return "5000"
        return "2"
    if field_type in {"email"}:
        return "test@example.com"
    if field_type in {"tel", "phone"}:
        return "5550100"
    if "age" in text or "eldest" in text:
        return "27"
    if any(term in text for term in ("date", "day", "check in", "arrival", "departure", "start", "end", "when")):
        return "2026-08-15"
    if any(term in text for term in ("traveler", "traveller", "guest", "people", "passenger", "ticket", "adult", "room", "night", "party", "count", "size", "quantity")):
        return "2"
    if "child" in text or "children" in text:
        return "0"
    if any(term in text for term in ("budget", "amount", "price", "cost", "premium", "income", "loan", "emi", "salary")):
        return "5000"
    if "phone" in text or "mobile" in text:
        return "5550100"
    if "email" in text:
        return "test@example.com"
    if "name" in text:
        return "Aarav Sharma"
    if any(term in text for term in ("city", "location", "area", "origin", "source", "destination", "target", "from", "to", "port", "station", "terminal", "branch")):
        return f"Sample {label}"
    if any(term in text for term in ("category", "type", "service", "scope", "goal", "matter", "role", "skill", "course", "program", "vehicle", "cover", "coverage")):
        return f"Sample {label}"
    return f"Sample {label}"


def smoke_option_value(options: Any) -> str:
    if not isinstance(options, list):
        return ""
    preferred_terms = ("27", "self", "individual", "standard", "economy", "basic")
    candidates: list[str] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        label = str(option.get("label") or "").strip()
        value = str(option.get("value") or "").strip()
        candidate = value or label
        if not candidate:
            continue
        text = f"{label} {value}".lower()
        if any(term in text for term in preferred_terms):
            return candidate
        candidates.append(candidate)
    return candidates[0] if candidates else ""


def append_smoke_details(prompt: str, clause: str) -> str:
    clean_prompt = str(prompt or "").strip()
    suffix = f" Use these exact field values: {clause}."
    if not clean_prompt:
        return suffix.strip()
    if clause.lower() in clean_prompt.lower():
        return clean_prompt
    return clean_prompt.rstrip(" .") + "." + suffix


def humanize_smoke_param(param: str) -> str:
    return " ".join(str(param or "").replace("_", " ").replace("-", " ").split())


def smoke_case(
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
