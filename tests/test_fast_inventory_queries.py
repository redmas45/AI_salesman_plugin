import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_inventory_type_count_uses_catalog_without_llm(monkeypatch):
    from agent import orchestrator

    products = [
        {"id": "1", "name": "NOVA Baby Cap", "category_name": "Headwear", "stock": 4},
        {"id": "2", "name": "NOVA Cap", "category_name": "Headwear", "stock": 8},
        {"id": "3", "name": "NOVA Sticker", "category_name": "Stickers", "stock": 10},
    ]

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    events = list(
        orchestrator.run_stream(
            site_id="ai_kart",
            text_input="How many types of caps do you have?",
            skip_tts=True,
        )
    )

    response = next(event for event in events if event["event"] == "response")
    actions = next(event for event in events if event["event"] == "actions")
    metrics = next(event for event in events if event["event"] == "metrics")

    assert "2 caps" in response["data"]["response_text"]
    assert actions["data"]["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["1", "2"], "search_query": "cap"},
        }
    ]
    assert metrics["data"]["latency_ms"]["inventory_lookup_ms"] >= 0
    assert "llm_ms" not in metrics["data"]["latency_ms"]


def test_inventory_type_missing_uses_real_categories_without_llm(monkeypatch):
    from agent import orchestrator

    products = [
        {"id": "1", "name": "NOVA Cap", "category_name": "Headwear", "stock": 8},
        {"id": "2", "name": "NOVA Sticker", "category_name": "Stickers", "stock": 10},
    ]

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    events = list(
        orchestrator.run_stream(
            site_id="ai_kart",
            text_input="How many types of card do you have?",
            skip_tts=True,
        )
    )

    response = next(event for event in events if event["event"] == "response")
    actions = next(event for event in events if event["event"] == "actions")

    assert "I don't have cards right now" in response["data"]["response_text"]
    assert "Headwear" in response["data"]["response_text"]
    assert "Stickers" in response["data"]["response_text"]
    assert actions["data"]["ui_actions"] == []
