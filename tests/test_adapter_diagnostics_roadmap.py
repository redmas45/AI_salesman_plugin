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

def test_assistant_smoke_result_reports_runtime_filter_failures() -> None:
    from agent import client_initialization

    result = client_initialization._assistant_smoke_result(
        {
            "name": "start_quote",
            "prompt": "Start my quote.",
            "expected_actions": ["START_QUOTE", "HANDOFF_TO_AGENT"],
        },
        {
            "response_text": "I will start the quote.",
            "intent": "quote",
            "ui_actions": [],
            "action_filter": {
                "status": "changed",
                "actions": [],
                "removed_actions": [
                    {
                        "action": "START_QUOTE",
                        "reason": "blocked_by_policy",
                        "message": "START_QUOTE is blocked by this site's safety policy.",
                    }
                ],
            },
        },
    )

    assert result["status"] == "failed"
    assert result["failure_kind"] == "blocked_action_filtered"
    assert result["filtered_actions"][0]["action"] == "START_QUOTE"
    assert "handoff" in result["recommended_fix"].lower()


def test_shopify_variant_id_preserves_large_integer() -> None:
    raw = {
        "id": 123,
        "title": "T Shirt",
        "handle": "t-shirt",
        "options": [{"name": "Color"}],
        "variants": [
            {
                "id": 11111111111111111,
                "title": "Red",
                "option1": "Red",
                "price": "999.00",
                "available": True,
            }
        ],
    }

    variants = ShopifyAdapter().extract_variants(raw, 123, "https://shop.test/products/t-shirt")

    assert variants[0]["id"] == 11111111111111111
    assert variants[0]["cart_id"] == "11111111111111111"


def test_woocommerce_variation_ids_become_variant_rows() -> None:
    raw = {
        "id": 55,
        "name": "Variable Hoodie",
        "prices": {"price": "2500", "currency_minor_unit": 2},
        "is_in_stock": True,
        "variations": [101, 102],
        "attributes": [
            {
                "name": "Size",
                "variation": True,
                "terms": [{"name": "S"}, {"name": "M"}],
            }
        ],
    }

    variants = WooCommerceAdapter().extract_variants(raw, 55, "https://woo.test/product/hoodie")

    assert [variant["id"] for variant in variants] == [101, 102]
    assert [variant["option1_value"] for variant in variants] == ["S", "M"]


def test_llm_extractor_requires_explicit_flag(monkeypatch) -> None:
    monkeypatch.setattr("config.LLM_EXTRACTOR_ENABLED", False)
    monkeypatch.setattr("config.AZURE_OPENAI_API_KEY", "test-key")

    result = extract_selectors_from_html("<h1>Product</h1>", "site_1")

    assert result is None


def test_action_repair_proposals_include_health_validation_and_candidates() -> None:
    proposals = build_action_repair_proposals(
        vertical_key="construction",
        vertical_config={
            "action_health": {
                "needs_repair": [
                    {
                        "action": "REQUEST_ESTIMATE",
                        "last_reason": "missing selector",
                        "repair_candidate": {
                            "type": "click",
                            "selector": "button.estimate-new",
                            "confidence": 0.9,
                        },
                    }
                ]
            },
            "validation": {
                "actions": {
                    "REQUEST_SITE_VISIT": {
                        "evidence": "replacement found",
                        "repair": {
                            "type": "click",
                            "selector": "button.visit-new",
                            "confidence": 0.82,
                        },
                    }
                }
            },
            "action_candidates": [
                {
                    "action": "OPEN_PROJECTS",
                    "type": "navigate",
                    "path": "/projects",
                    "label": "Projects",
                    "confidence": 0.8,
                }
            ],
        },
    )

    rows = {proposal["action"]: proposal for proposal in proposals}

    assert rows["REQUEST_ESTIMATE"]["kind"] == "runtime_repair"
    assert rows["REQUEST_SITE_VISIT"]["kind"] == "validation_repair"
    assert rows["OPEN_PROJECTS"]["config"]["path"] == "/projects"


