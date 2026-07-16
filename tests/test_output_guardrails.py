"""Tests for input and output guardrails."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

pytestmark = pytest.mark.integration

from agent.guardrails import (
    InputGuardrailError,
    validate_input,
    validate_output,
)
import agent.guardrails as guardrails
from db.database import init_tenant_schema
from db.seed import seed


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_tenant_schema("site_1")
    seed()
    # Now let's insert a dummy category and product with ID 1
    from db.database import get_db
    with get_db("site_1") as conn:
        conn.execute(
            "INSERT INTO categories (id, name, slug) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (99999, "Test Category", "test-category")
        )
        conn.execute(
            """
            INSERT INTO products (id, name, brand, category_id, description, price, stock, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (1, "Test Product 1", "Test Brand", 99999, "Test Description 1", 100.0, 100, 1)
        )
        conn.execute(
            """
            INSERT INTO knowledge_items (id, entity_type, title, summary, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                title = EXCLUDED.title,
                summary = EXCLUDED.summary,
                is_active = EXCLUDED.is_active
            """,
            ("plan:test-1", "insurance_plan", "Test Plan", "Source-backed test plan", 1),
        )



class TestOutputGuardrails:
    def _make_response(self, **kwargs):
        base = {
            "response_text": "Here are some red shoes for you!",
            "intent": "product_search",
            "confidence": 0.95,
            "ui_actions": [],
        }
        base.update(kwargs)
        return base

    def test_valid_response_passes(self):
        resp = self._make_response()
        result = validate_output(resp, site_id="site_1")
        assert result["response_text"] == "Here are some red shoes for you!"

    def test_invalid_action_type_removed(self):
        resp = self._make_response(
            ui_actions=[
                {"action": "HACK_WEBSITE", "params": {}},
                {"action": "SHOW_PRODUCTS", "params": {"product_ids": []}},
            ]
        )
        result = validate_output(resp, site_id="site_1")
        action_types = [a["action"] for a in result["ui_actions"]]
        assert "HACK_WEBSITE" not in action_types

    def test_too_many_actions_capped(self):
        resp = self._make_response(
            ui_actions=[{"action": "CLEAR_FILTERS", "params": {}} for _ in range(10)]
        )
        result = validate_output(resp, site_id="site_1")
        assert len(result["ui_actions"]) <= 5

    def test_non_list_actions_reset(self):
        resp = self._make_response(ui_actions="invalid")
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == []

    def test_negative_price_clamped(self):
        resp = self._make_response(
            ui_actions=[{"action": "FILTER_PRODUCTS", "params": {"max_price": -1000}}]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"][0]["params"]["max_price"] == 0.0

    def test_rating_out_of_range_clamped(self):
        resp = self._make_response(
            ui_actions=[{"action": "FILTER_PRODUCTS", "params": {"min_rating": 10}}]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"][0]["params"]["min_rating"] == 5.0

    def test_empty_response_text_replaced(self):
        resp = self._make_response(response_text="")
        result = validate_output(resp, site_id="site_1")
        assert len(result["response_text"]) > 0

    def test_add_to_cart_invalid_product_id_removed(self):
        resp = self._make_response(
            ui_actions=[
                {"action": "ADD_TO_CART", "params": {"product_id": "not-a-number"}}
            ]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == []

    def test_add_to_cart_numeric_string_product_id_coerced(self):
        resp = self._make_response(
            ui_actions=[{"action": "ADD_TO_CART", "params": {"product_id": "1"}}]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == [
            {"action": "ADD_TO_CART", "params": {"product_id": "1"}}
        ]

    def test_show_products_drops_invalid_ids_and_keeps_valid(self):
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "SHOW_PRODUCTS",
                    "params": {"product_ids": [1, "bad", 999999]},
                }
            ]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == [
            {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["1"]}}
        ]

    def test_show_entities_drops_invalid_ids_and_keeps_active_tenant_records(self):
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "SHOW_ENTITIES",
                    "params": {
                        "entity_ids": ["plan:test-1", "plan:missing"],
                        "search_query": "health plan",
                    },
                }
            ]
        )

        result = validate_output(resp, site_id="site_1")

        assert result["ui_actions"] == [
            {
                "action": "SHOW_ENTITIES",
                "params": {"entity_ids": ["plan:test-1"], "search_query": "health plan"},
            }
        ]

    def test_show_entities_allows_current_retrieval_ids_without_db_lookup(self):
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "COMPARE_ENTITIES",
                    "params": {"entity_ids": ["plan:rag-1", "plan:missing"]},
                }
            ]
        )

        result = validate_output(resp, site_id="site_1", allowed_entity_ids=["plan:rag-1"])

        assert result["ui_actions"] == [
            {"action": "COMPARE_ENTITIES", "params": {"entity_ids": ["plan:rag-1"]}}
        ]

    def test_invalid_navigation_removed(self):
        resp = self._make_response(
            ui_actions=[{"action": "NAVIGATE_TO", "params": {"page": "admin"}}]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == []

    def test_static_customer_service_navigation_allowed(self):
        resp = self._make_response(
            ui_actions=[
                {"action": "NAVIGATE_TO", "params": {"page": "/support/"}},
                {
                    "action": "NAVIGATE_TO",
                    "params": {"page": "frequently-asked-questions"},
                },
                {"action": "NAVIGATE_TO", "params": {"page": "shipping-policy"}},
                {"action": "NAVIGATE_TO", "params": {"page": "return-policy"}},
            ]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == [
            {"action": "NAVIGATE_TO", "params": {"page": "support"}},
            {
                "action": "NAVIGATE_TO",
                "params": {"page": "frequently-asked-questions"},
            },
            {"action": "NAVIGATE_TO", "params": {"page": "shipping-policy"}},
            {"action": "NAVIGATE_TO", "params": {"page": "return-policy"}},
        ]

    def test_invalid_sort_removed(self):
        resp = self._make_response(
            ui_actions=[
                {"action": "SORT_PRODUCTS", "params": {"sort_by": "delete_all"}}
            ]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == []

    def test_unsupported_filter_key_removed(self):
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "FILTER_PRODUCTS",
                    "params": {"category": "shoes", "sql": "drop"},
                }
            ]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"][0]["params"] == {"category": "shoes"}

    def test_non_dict_params_removed(self):
        resp = self._make_response(
            ui_actions=[{"action": "FILTER_PRODUCTS", "params": "category=shoes"}]
        )
        result = validate_output(resp, site_id="site_1")
        assert result["ui_actions"] == []

    def test_run_dom_sequence_accepts_safe_steps(self):
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "RUN_DOM_SEQUENCE",
                    "params": {
                        "steps": [
                            {"op": "fill", "selector": "input[name='q']", "param": "query"},
                            {"op": "click", "label": "Search"},
                            {"op": "navigate", "path": "/contact?source=ai"},
                        ]
                    },
                }
            ]
        )
        result = validate_output(resp, site_id="site_1")

        assert result["ui_actions"] == [
            {
                "action": "RUN_DOM_SEQUENCE",
                "params": {
                    "steps": [
                        {"op": "fill", "param": "query", "selector": "input[name='q']"},
                        {"op": "click", "label": "Search"},
                        {"op": "navigate", "path": "/contact?source=ai"},
                    ]
                },
            }
        ]

    def test_run_dom_sequence_rejects_external_navigation(self):
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "RUN_DOM_SEQUENCE",
                    "params": {"steps": [{"op": "navigate", "path": "https://evil.example"}]},
                }
            ]
        )
        result = validate_output(resp, site_id="site_1")

        assert result["ui_actions"] == []

    def test_run_dom_sequence_caps_wait_and_step_count(self):
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "RUN_DOM_SEQUENCE",
                    "params": {"steps": [{"op": "wait", "ms": 999999} for _ in range(40)]},
                }
            ]
        )
        result = validate_output(resp, site_id="site_1")
        steps = result["ui_actions"][0]["params"]["steps"]

        assert len(steps) == 30
        assert steps[0] == {"op": "wait", "ms": 5000}

    def test_dynamic_navigation_allows_generated_adapter_routes(self, monkeypatch):
        monkeypatch.setattr(
            guardrails,
            "_client_vertical_config",
            lambda site_id: {"routes": {"services": "/services", "quote": "/get-quote"}},
        )
        resp = self._make_response(
            ui_actions=[
                {"action": "NAVIGATE_TO", "params": {"page": "services"}},
                {"action": "NAVIGATE_TO", "params": {"page": "/get-quote"}},
            ]
        )

        result = validate_output(resp, site_id="builder_demo")

        assert result["ui_actions"] == [
            {"action": "NAVIGATE_TO", "params": {"page": "services"}},
            {"action": "NAVIGATE_TO", "params": {"page": "get-quote"}},
        ]

    def test_navigation_uses_observed_interaction_links(self, monkeypatch):
        monkeypatch.setattr(
            guardrails,
            "_client_vertical_config",
            lambda site_id: {
                "routes": {"plans": "/insurance/health"},
                "interaction_events": [
                    {
                        "label": "Life",
                        "href": "http://localhost:5173/insurance/life",
                        "origin": "http://localhost:5173",
                    }
                ],
            },
        )
        resp = self._make_response(
            ui_actions=[{"action": "NAVIGATE_TO", "params": {"page": "life"}}]
        )

        result = validate_output(resp, site_id="policy_site")

        assert result["ui_actions"] == [
            {"action": "NAVIGATE_TO", "params": {"page": "insurance/life"}}
        ]

    def test_navigation_page_not_stripped_by_generated_action_config(self, monkeypatch):
        monkeypatch.setattr(
            guardrails,
            "_client_vertical_config",
            lambda site_id: {
                "routes": {"life": "/insurance/life"},
                "actions": {"NAVIGATE_TO": {"type": "navigate", "path": "/"}},
            },
        )
        resp = self._make_response(
            ui_actions=[{"action": "NAVIGATE_TO", "params": {"page": "life"}}]
        )

        result = validate_output(resp, site_id="policy_site")

        assert result["ui_actions"] == [
            {"action": "NAVIGATE_TO", "params": {"page": "insurance/life"}}
        ]

    def test_navigation_uses_current_page_context_links(self, monkeypatch):
        monkeypatch.setattr(
            guardrails,
            "_client_vertical_config",
            lambda site_id: {"routes": {"plans": "/insurance/health"}},
        )
        resp = self._make_response(
            ui_actions=[{"action": "NAVIGATE_TO", "params": {"page": "travel"}}]
        )

        result = validate_output(
            resp,
            site_id="policy_site",
            runtime_context={
                "url": "http://localhost:5173/",
                "links": [{"label": "Travel", "href": "/insurance/travel"}],
            },
        )

        assert result["ui_actions"] == [
            {"action": "NAVIGATE_TO", "params": {"page": "insurance/travel"}}
        ]

    def test_navigation_uses_semantic_alias_for_current_page_links(self, monkeypatch):
        monkeypatch.setattr(
            guardrails,
            "_client_vertical_config",
            lambda site_id: {"routes": {"plans": "/insurance/health"}},
        )
        resp = self._make_response(
            ui_actions=[{"action": "NAVIGATE_TO", "params": {"page": "car"}}]
        )

        result = validate_output(
            resp,
            site_id="policy_site",
            runtime_context={
                "url": "http://localhost:5173/",
                "links": [{"label": "Motor", "href": "/insurance/motor"}],
            },
        )

        assert result["ui_actions"] == [
            {"action": "NAVIGATE_TO", "params": {"page": "insurance/motor"}}
        ]

    def test_navigation_rejects_external_observed_links(self, monkeypatch):
        monkeypatch.setattr(
            guardrails,
            "_client_vertical_config",
            lambda site_id: {
                "interaction_events": [
                    {
                        "label": "Billing",
                        "href": "https://evil.example/billing",
                        "origin": "https://client.example",
                    },
                    {"label": "Protocol relative", "href": "//evil.example/path"},
                ],
            },
        )
        resp = self._make_response(
            ui_actions=[
                {"action": "NAVIGATE_TO", "params": {"page": "billing"}},
                {"action": "NAVIGATE_TO", "params": {"page": "protocol relative"}},
            ]
        )

        result = validate_output(resp, site_id="policy_site")

        assert result["ui_actions"] == []

    def test_configured_form_action_keeps_only_contract_params(self, monkeypatch):
        monkeypatch.setattr(
            guardrails,
            "_client_vertical_config",
            lambda site_id: {
                "actions": {
                    "REQUEST_ESTIMATE": {
                        "type": "sequence",
                        "fields": ["phone", "budget"],
                        "steps": [{"op": "fill", "param": "message"}],
                    }
                }
            },
        )
        resp = self._make_response(
            ui_actions=[
                {
                    "action": "REQUEST_ESTIMATE",
                    "params": {
                        "phone": "9999999999",
                        "budget": 250000,
                        "message": "Need a site visit",
                        "selector": "button.evil",
                        "__proto__": "pollute",
                        "nested": {"bad": True},
                    },
                }
            ]
        )

        result = validate_output(resp, site_id="builder_demo")

        assert result["ui_actions"] == [
            {
                "action": "REQUEST_ESTIMATE",
                "params": {
                    "phone": "9999999999",
                    "budget": 250000,
                    "message": "Need a site visit",
                },
            }
        ]
