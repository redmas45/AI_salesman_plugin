from agent.adapters.shopify import ShopifyAdapter
from agent.adapters.woocommerce import WooCommerceAdapter
from agent.extractor import extract_selectors_from_html
from agent.scanner import _client_hook_capabilities, _is_client_hook_adapter


def test_aikart_site_id_is_client_hook_adapter() -> None:
    assert _is_client_hook_adapter("generic_adapter.js", "ai_kart_main")
    caps = {cap.name: cap for cap in _client_hook_capabilities("generic_adapter.js")}
    assert caps["cart"].supported
    assert caps["checkout"].supported


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
    monkeypatch.setattr("config.OPENAI_API_KEY", "test-key")

    result = extract_selectors_from_html("<h1>Product</h1>", "site_1")

    assert result is None
