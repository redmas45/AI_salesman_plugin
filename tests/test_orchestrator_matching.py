import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator


def test_exact_products_from_query_finds_named_comparison_products(monkeypatch):
    products = [
        {"id": 1, "name": "NOVA Rainbow Sticker", "price": 4, "category_name": "Stickers"},
        {"id": 2, "name": "NOVA Sticker", "price": 4, "category_name": "Stickers"},
        {"id": 3, "name": "NOVA T-Shirt", "price": 20, "category_name": "Shirts"},
    ]

    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)

    matches = orchestrator._exact_products_from_query(
        "Compare Nova sticker with Nova T-shirt.",
        "ai_kart_main",
    )

    assert [product["name"] for product in matches[:2]] == ["NOVA Sticker", "NOVA T-Shirt"]
    assert all(product["_exact_name_match"] is True for product in matches[:2])


def test_named_comparison_response_is_forced_when_llm_misses_exact_products():
    response = {
        "response_text": "We do not have that sticker.",
        "intent": "out_of_stock",
        "confidence": 0.4,
        "ui_actions": [],
    }
    products = [
        {"id": 2, "name": "NOVA Sticker", "price": 4, "category_name": "Stickers", "_exact_name_match": True},
        {"id": 3, "name": "NOVA T-Shirt", "price": 20, "category_name": "Shirts", "_exact_name_match": True},
    ]

    orchestrator._ensure_named_comparison_response(
        response,
        "Compare Nova sticker with Nova T-shirt.",
        products,
    )

    assert response["intent"] == "product_compare"
    assert response["ui_actions"] == [
        {"action": "SHOW_COMPARISON", "params": {"product_ids": ["2", "3"]}}
    ]
    assert "NOVA Sticker" in response["response_text"]
    assert "NOVA T-Shirt" in response["response_text"]
