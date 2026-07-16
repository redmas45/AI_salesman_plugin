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

def test_client_hook_requires_explicit_adapter_name() -> None:
    assert not _is_client_hook_adapter("generic_adapter.js", "ai_kart")
    assert _is_client_hook_adapter("verified-client-hook.js", "ai_kart")
    caps = {cap.name: cap for cap in _client_hook_capabilities("verified-client-hook.js")}
    assert caps["cart"].supported
    assert caps["checkout"].supported


def test_insurance_readiness_uses_vertical_data_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.knowledge_stats",
        lambda site_id: {"active_items": 19, "entity_types": 3, "missing_embeddings": 0},
    )

    caps = {cap.name: cap for cap in _vertical_data_capabilities("policy_site", "insurance")}

    assert caps["plans"].supported
    assert caps["groups"].supported
    assert caps["vectors"].supported
    assert "cart" not in caps
    assert "checkout" not in caps


def test_vertical_expected_action_readiness_flags_mapped_and_missing_actions(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.knowledge_stats",
        lambda site_id: {"active_items": 5, "entity_types": 1, "missing_embeddings": 0},
    )

    caps = {
        cap.name: cap
        for cap in _vertical_expected_action_capabilities(
            "builder_demo",
            "construction",
            {
                "actions": {
                    "REQUEST_ESTIMATE": {"type": "form"},
                    "OPEN_PROJECTS": {"type": "navigate", "path": "/projects"},
                }
            },
        )
    }

    assert caps["domain_action_coverage"].supported is False
    assert "Missing:" in caps["domain_action_coverage"].evidence
    assert caps["expected_action:SHOW_ENTITIES"].supported
    assert "5 active services" in caps["expected_action:SHOW_ENTITIES"].evidence
    assert caps["expected_action:REQUEST_ESTIMATE"].supported
    assert caps["expected_action:OPEN_PROJECTS"].supported
    assert not caps["expected_action:REQUEST_SITE_VISIT"].supported
    assert "not mapped" in caps["expected_action:REQUEST_SITE_VISIT"].evidence


def test_ecommerce_expected_action_readiness_uses_product_rendering(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.tenant_catalog_stats",
        lambda site_id: {"active_products": 12, "total_products": 12, "missing_embeddings": 0},
    )

    caps = {
        cap.name: cap
        for cap in _vertical_expected_action_capabilities(
            "ai_kart",
            "ecommerce",
            {"actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}}},
        )
    }

    assert caps["expected_action:SHOW_PRODUCTS"].supported
    assert "AI Hub product rendering" in caps["expected_action:SHOW_PRODUCTS"].evidence
    assert caps["expected_action:SHOW_COMPARISON"].supported
    assert caps["expected_action:SORT_PRODUCTS"].supported
    assert caps["expected_action:FILTER_PRODUCTS"].supported
    assert caps["expected_action:ADD_TO_CART"].supported
    assert not caps["expected_action:CHECKOUT"].supported
    assert "Missing: CHECKOUT" in caps["domain_action_coverage"].evidence

    caps_with_checkout = {
        cap.name: cap
        for cap in _vertical_expected_action_capabilities(
            "ai_kart",
            "ecommerce",
            {"actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}}},
            [SiteCapability("checkout", True, 0.4, "Checkout page at https://shop.example.com/checkout")],
        )
    }

    assert caps_with_checkout["expected_action:CHECKOUT"].supported
    assert "detected checkout capability" in caps_with_checkout["expected_action:CHECKOUT"].evidence
    assert caps_with_checkout["domain_action_coverage"].supported


def test_auth_barrier_readiness_is_supported_when_handoff_policy_exists() -> None:
    caps = _barrier_capabilities(
        {
            "barriers": {
                "summary": {"total": 1, "high": 1, "medium": 0, "keys": ["auth_required"]},
                "findings": [
                    {
                        "key": "auth_required",
                        "severity": "high",
                        "handling": "Require login before quote flow.",
                    }
                ],
            }
        },
        "insurance",
    )

    assert caps[0].name == "flow_barriers"
    assert caps[0].supported is True
    assert caps[0].blocking is False
    assert "handoff policy" in caps[0].evidence


@pytest.mark.asyncio
async def test_custom_cart_probe_accepts_html_cart_page(monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    async def fake_probe(client, url: str, *, method: str = "GET", accept: str = "application/json"):
        calls.append({"url": url, "method": method, "accept": accept})
        return 200, "", {}

    monkeypatch.setattr("agent.scanner._probe_url", fake_probe)

    cap = await _check_cart("https://shop.example.com", "custom", object())

    assert cap.supported
    assert "Cart page" in cap.evidence
    assert calls == [{"url": "https://shop.example.com/cart", "method": "HEAD", "accept": "text/html"}]


@pytest.mark.asyncio
async def test_custom_checkout_probe_requests_html_accept(monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    async def fake_probe(client, url: str, *, method: str = "GET", accept: str = "application/json"):
        calls.append({"url": url, "method": method, "accept": accept})
        return 200, "", {}

    monkeypatch.setattr("agent.scanner._probe_url", fake_probe)

    cap = await _check_checkout("https://shop.example.com", "custom", object())

    assert cap.supported
    assert calls == [{"url": "https://shop.example.com/checkout", "method": "HEAD", "accept": "text/html"}]


def test_flow_graph_uses_generated_adapter_actions_for_js_static_gap() -> None:
    caps = {
        cap.name: cap
        for cap in _flow_capabilities(
            {
                "actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}},
                "flow": {
                    "engine": "http_fallback",
                    "summary": {"pages": 6, "actions": 0},
                    "prompt_suggestions": [],
                },
            }
        )
    }

    assert caps["flow_graph"].supported
    assert "generated adapter exposes 1 runtime action" in caps["flow_graph"].evidence


def test_empty_rehearsal_uses_validated_adapter_actions_for_js_static_gap() -> None:
    caps = {
        cap.name: cap
        for cap in _rehearsal_capabilities(
            {
                "actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}},
                "validation": {"actions": {"ADD_TO_CART": {"supported": True, "status": "ok"}}},
                "rehearsal": {
                    "engine": "empty",
                    "summary": {"total": 0, "supported": 0, "blocked": 0, "needs_confirmation": 0},
                },
            }
        )
    }

    assert caps["flow_rehearsal"].supported
    assert "browser validation supports 1/1 adapter action" in caps["flow_rehearsal"].evidence
    assert caps["flow_confirmation_policy"].supported


def test_vertical_expected_action_readiness_covers_every_registered_vertical(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.knowledge_stats",
        lambda site_id: {"active_items": 0, "entity_types": 0, "missing_embeddings": 0},
    )

    for vertical in list_verticals():
        caps = {
            cap.name: cap
            for cap in _vertical_expected_action_capabilities("demo_site", vertical.key, {"actions": {}})
        }

        assert "domain_action_coverage" in caps
        for action in vertical.action_types:
            assert f"expected_action:{action}" in caps



