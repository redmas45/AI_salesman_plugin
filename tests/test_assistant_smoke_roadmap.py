import pytest

from agent.adapters.shopify import ShopifyAdapter
from agent.adapters.woocommerce import WooCommerceAdapter
from agent.adapter_repair import build_action_repair_proposals
from agent.extractor import extract_selectors_from_html
from agent.client_initialization import run_widget_initialization
from agent.scanner import (
    SiteCapability,
    _barrier_capabilities,
    _check_cart,
    _check_checkout,
    _client_hook_capabilities,
    _flow_capabilities,
    _is_client_hook_adapter,
    _rehearsal_capabilities,
    _vertical_data_capabilities,
    _vertical_expected_action_capabilities,
)
from agent.tenant_isolation import build_tenant_isolation_audit
from agent.verticals.registry import list_verticals
from db.admin import _validated_settings

def test_assistant_smoke_cases_cover_registered_verticals() -> None:
    from agent import client_initialization

    generic_names = {case["name"] for case in client_initialization._assistant_smoke_cases("generic")}
    domain_specific = {vertical.key for vertical in list_verticals()} - {"generic"}

    for vertical in list_verticals():
        cases = client_initialization._assistant_smoke_cases(vertical.key)

        assert len(cases) >= 2
        assert all(str(case.get("prompt") or "").strip() for case in cases)
        assert all(case.get("expected_actions") for case in cases)
        if vertical.key in domain_specific:
            assert {case["name"] for case in cases} != generic_names


def test_assistant_smoke_cases_include_required_action_schema(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "vertical_config": {
                "actions": {
                    "RUN_CALCULATOR": {
                        "type": "sequence",
                        "fields": ["primary_value", "secondary_value", "requested_date", "quantity"],
                        "required_fields": ["primary_value", "secondary_value", "requested_date", "quantity"],
                        "required_fields_known": True,
                        "field_schema": [
                            {"param": "primary_value", "label": "Primary value", "type": "text", "required": True},
                            {"param": "secondary_value", "label": "Secondary value", "type": "text", "required": True},
                            {"param": "requested_date", "label": "Requested date", "type": "date", "required": True},
                            {"param": "quantity", "label": "Quantity", "type": "number", "required": True},
                        ],
                    }
                }
            },
        },
    )

    cases = client_initialization._assistant_smoke_cases("schema_demo", "generic")
    availability_case = next(case for case in cases if "RUN_CALCULATOR" in case["expected_actions"])

    assert availability_case["schema_enriched"] is True
    assert "primary value: Sample primary value" in availability_case["prompt"]
    assert "secondary value: Sample secondary value" in availability_case["prompt"]
    assert "requested date: 2026-08-15" in availability_case["prompt"]
    assert "quantity: 2" in availability_case["prompt"]


def test_assistant_smoke_cases_skip_credential_based_result_contract(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "vertical_config": {
                "actions": {
                    "FILTER_PRODUCTS": {
                        "type": "form",
                        "form": "form.login",
                        "input": "input[name='email']",
                        "submit": "button.login",
                        "required_fields": ["email", "password"],
                        "required_fields_known": True,
                        "field_schema": [
                            {"param": "email", "label": "Email", "type": "email", "required": True},
                            {"param": "password", "label": "Password", "type": "password", "required": True},
                        ],
                    }
                }
            },
        },
    )

    cases = client_initialization._assistant_smoke_cases("schema_demo", "ecommerce")

    assert all("FILTER_PRODUCTS" not in case["expected_actions"] for case in cases)
    assert [case["name"] for case in cases][:2] == [
        "compare_apple_samsung_phone",
        "sort_phones_low_to_high",
    ]


def test_assistant_smoke_stage_passes_when_expected_actions_return(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "A protective case is a useful accessory to buy with the phone.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        response_text = (
            "Apple and Samsung phones are both available to compare."
            if action == "SHOW_COMPARISON"
            else "Here is a useful source-backed answer."
        )
        return {
            "response_text": response_text,
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "ok"
    assert stage["passed"] == 3
    assert stage["failed"] == 0
    assert stage["tests"][0]["matched_actions"] == ["SHOW_COMPARISON"]
    assert stage["tests"][0]["matched_response_terms_all"] == ["apple", "samsung"]
    assert stage["tests"][0]["display_action_evidence"][0]["id_count"] == 2
    assert stage["tests"][0]["failure_kind"] == ""
    assert stage["tests"][0]["recommended_fix"] == ""
    assert stage["tests"][2]["matched_response_terms"] == ["accessory", "case"]


def test_assistant_smoke_stage_fails_shallow_named_comparison(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "A protective case is a useful accessory to buy with the phone.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        return {
            "response_text": "Here is a useful source-backed comparison.",
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "failed"
    assert stage["tests"][0]["name"] == "compare_apple_samsung_phone"
    assert stage["tests"][0]["failure_kind"] == "missing_response_terms"
    assert stage["tests"][0]["matched_actions"] == ["SHOW_COMPARISON"]
    assert stage["tests"][0]["expected_response_terms_all"] == ["apple", "samsung"]
    assert stage["tests"][0]["matched_response_terms_all"] == []
    assert "missing apple, samsung" in stage["tests"][0]["reason"]


def test_assistant_smoke_stage_fails_display_action_without_ids(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "A protective case is a useful accessory to buy with the phone.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        return {
            "response_text": "Apple and Samsung phones are available to compare.",
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "failed"
    assert stage["tests"][0]["failure_kind"] == "missing_action_ids"
    assert stage["tests"][0]["display_action_evidence"][0]["action"] == "SHOW_COMPARISON"
    assert stage["tests"][0]["display_action_evidence"][0]["id_count"] == 0
    assert "product_ids or entity_ids" in stage["tests"][0]["reason"]
    assert "action params" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_stage_fails_no_records_response(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_run_assistant_turn",
        lambda site_id, prompt: {
            "response_text": "No records found for that request.",
            "intent": "smoke",
            "ui_actions": [{"action": "COMPARE_ENTITIES", "params": {}}],
        },
    )

    stage = client_initialization._assistant_smoke_stage("policy_site", "insurance")

    assert stage["status"] == "failed"
    assert stage["failed"] == 2
    assert stage["tests"][0]["reason"] == "Assistant response used a no-data or no-records fallback."
    assert stage["tests"][0]["failure_kind"] == "no_data_fallback"
    assert "Data storage and Crawl report" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_stage_includes_retrieval_evidence_in_fix(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_run_assistant_turn",
        lambda site_id, prompt: {
            "response_text": "No records found for that request.",
            "intent": "smoke",
            "ui_actions": [{"action": "COMPARE_ENTITIES", "params": {}}],
            "retrieval": {
                "source": "knowledge_items",
                "active_records": 4,
                "missing_embeddings": 0,
                "retrieved_count": 0,
                "issue": "retrieval_returned_zero",
            },
        },
    )

    stage = client_initialization._assistant_smoke_stage("policy_site", "insurance")

    assert stage["tests"][0]["retrieval_evidence"]["source"] == "knowledge_items"
    assert stage["tests"][0]["retrieval_evidence"]["issue"] == "retrieval_returned_zero"
    assert "retrieval returned zero records" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_stage_fails_missing_accessory_recommendation(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "Here are phones that match the request.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        response_text = (
            "Apple and Samsung phones are available to compare."
            if action == "SHOW_COMPARISON"
            else "Here is a useful source-backed answer."
        )
        return {
            "response_text": response_text,
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "failed"
    assert stage["passed"] == 2
    assert stage["failed"] == 1
    assert stage["tests"][2]["name"] == "recommend_phone_accessory"
    assert stage["tests"][2]["matched_actions"] == ["SHOW_PRODUCTS"]
    assert stage["tests"][2]["matched_response_terms"] == []
    assert stage["tests"][2]["failure_kind"] == "missing_response_terms"
    assert "Expected response to mention one of" in stage["tests"][2]["reason"]
    assert "recommendation detail" in stage["tests"][2]["recommended_fix"]


def test_assistant_smoke_stage_fails_when_prompt_has_no_ui_action(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_run_assistant_turn",
        lambda site_id, prompt: {
            "response_text": "I can help with that.",
            "intent": "smoke",
            "ui_actions": [],
        },
    )

    stage = client_initialization._assistant_smoke_stage("travel_site", "travel")

    assert stage["status"] == "failed"
    assert stage["failed"] == 2
    assert stage["tests"][0]["failure_kind"] == "no_ui_action"
    assert "without emitting one of" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_cases_do_not_call_external_llm(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(client_initialization.config, "AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(client_initialization, "_action_contract_smoke_cases", lambda site_id: [])

    cases = client_initialization._assistant_smoke_cases("ai_kart", "ecommerce")

    assert [case["name"] for case in cases] == [
        "compare_apple_samsung_phone",
        "sort_phones_low_to_high",
        "recommend_phone_accessory",
    ]


