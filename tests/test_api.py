"""
API endpoint tests using FastAPI's TestClient.
Run with: pytest tests/test_api.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a test client (no real server needed)."""
    import config
    from api.main import app
    from db.admin import _connect, init_admin_schema
    from db.seed import seed

    seed([config.DEFAULT_SITE_ID])
    init_admin_schema()
    with _connect() as conn:
        conn.execute("DELETE FROM hub_usage_events WHERE site_id = %s", (config.DEFAULT_SITE_ID,))
        conn.execute("DELETE FROM hub_conversation_sessions WHERE site_id = %s", (config.DEFAULT_SITE_ID,))
        conn.commit()

    return TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "models" in data

    def test_health_has_model_names(self, client):
        data = client.get("/health").json()
        assert "stt" in data["models"]
        assert "llm" in data["models"]
        assert "tts" in data["models"]


class TestProductsEndpoint:
    def test_products_returns_list(self, client):
        res = client.get("/v1/products")
        assert res.status_code == 200
        products = res.json()
        assert isinstance(products, list)
        assert len(products) > 0

    def test_products_have_required_fields(self, client):
        products = client.get("/v1/products").json()
        for p in products[:5]:
            assert "id" in p
            assert "name" in p
            assert "price" in p
            assert "rating" in p

    def test_all_prices_positive(self, client):
        products = client.get("/v1/products").json()
        for p in products:
            assert p["price"] > 0

    def test_product_ids_are_json_strings(self, client):
        products = client.get("/v1/products").json()
        assert products
        assert isinstance(products[0]["id"], str)


class TestCartEndpoint:
    def test_cart_add_rejects_malformed_product_id(self, client):
        res = client.post(
            "/v1/cart/add",
            json={"site_id": "site_1", "product_id": "gid://shopify/Product/9401822679353", "quantity": 1},
        )
        assert res.status_code == 400

    def test_cart_add_returns_404_for_missing_numeric_product_id(self, client):
        res = client.post(
            "/v1/cart/add",
            json={"site_id": "site_1", "product_id": "999999999999999999", "quantity": 1},
        )
        assert res.status_code == 404


class TestShopEndpoint:
    def test_text_input_returns_response(self, client):
        res = client.post(
            "/v1/shop", data={"text": "Show me red shoes", "skip_tts": "true"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "response_text" in data
        assert "ui_actions" in data
        assert "intent" in data
        assert "transcript" in data

    def test_no_input_returns_422(self, client):
        res = client.post("/v1/shop")
        assert res.status_code == 422

    def test_empty_text_returns_422(self, client):
        res = client.post("/v1/shop", data={"text": "   ", "skip_tts": "true"})
        assert res.status_code in (400, 422)

    def test_response_has_valid_confidence(self, client):
        res = client.post(
            "/v1/shop", data={"text": "Show me yoga mat", "skip_tts": "true"}
        )
        data = res.json()
        assert 0.0 <= data["confidence"] <= 1.0

    def test_ui_actions_are_list(self, client):
        res = client.post(
            "/v1/shop", data={"text": "Show me electronics", "skip_tts": "true"}
        )
        data = res.json()
        assert isinstance(data["ui_actions"], list)

    def test_latency_ms_present(self, client):
        res = client.post(
            "/v1/shop", data={"text": "Best running shoes", "skip_tts": "true"}
        )
        data = res.json()
        assert "latency_ms" in data
        assert data["latency_ms"]["total_ms"] > 0

    def test_shop_canonicalizes_auto_site_ids_before_runtime(self, client, monkeypatch):
        from api import main

        captured = {}
        monkeypatch.setattr(main.admin_db, "is_client_widget_enabled", lambda site_id: True)
        monkeypatch.setattr(main.admin_db, "assert_usage_allowed", lambda site_id, session_id: None)
        monkeypatch.setattr(main, "get_session_summary", lambda site_id, session_id: {})
        monkeypatch.setattr(main, "_record_usage_result", lambda **kwargs: None)

        def fake_run(**kwargs):
            captured["site_id"] = kwargs["site_id"]
            return {
                "transcript": kwargs.get("text_input") or "",
                "response_text": "ok",
                "intent": "test",
                "confidence": 1.0,
                "answer_scope": "grounded_fact",
                "ui_actions": [],
                "audio_b64": "",
                "latency_ms": {"total_ms": 1},
            }

        monkeypatch.setattr(main.orchestrator, "run", fake_run)

        res = client.post(
            "/v1/shop",
            data={
                "site_id": "auto_vercel-website-frontend_vercel_app_1m8d6rk",
                "text": "I want to buy iPhone.",
                "skip_tts": "true",
            },
        )

        assert res.status_code == 200
        assert captured["site_id"] == "auto_vercel_website_frontend_vercel_app_1m8d6rk"

    def test_off_topic_query(self, client):
        res = client.post(
            "/v1/shop",
            data={"text": "What is the capital of India?", "skip_tts": "true"},
        )
        assert res.status_code == 200
        data = res.json()
        # Should respond gracefully (not crash)
        assert data["response_text"]
