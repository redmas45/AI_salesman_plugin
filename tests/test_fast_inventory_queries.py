import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ECOMMERCE_TEST_SITE_ID = "ecommerce_site"


def test_inventory_type_count_uses_catalog_without_llm(monkeypatch):
    from agent import orchestrator

    products = [
        {"id": "1", "name": "NOVA Baby Cap", "category_name": "Headwear", "stock": 4},
        {"id": "2", "name": "NOVA Cap", "category_name": "Headwear", "stock": 8},
        {"id": "3", "name": "NOVA Sticker", "category_name": "Stickers", "stock": 10},
    ]

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    events = list(
        orchestrator.run_stream(
            site_id=ECOMMERCE_TEST_SITE_ID,
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
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    events = list(
        orchestrator.run_stream(
            site_id=ECOMMERCE_TEST_SITE_ID,
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


def test_inventory_type_cleans_other_phone_modifier(monkeypatch):
    from agent import orchestrator

    products = [
        {"id": "1", "name": "OPPO Active Android Budget 9", "category_name": "Electronics", "tags": ["phone", "android"], "stock": 4},
        {"id": "2", "name": "iPhone 17", "brand": "Apple", "category_name": "Electronics", "stock": 8},
    ]

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    events = list(
        orchestrator.run_stream(
            site_id=ECOMMERCE_TEST_SITE_ID,
            text_input="Do you have any other phone?",
            skip_tts=True,
        )
    )

    response = next(event for event in events if event["event"] == "response")
    actions = next(event for event in events if event["event"] == "actions")

    assert "I found 2 phones in stock" in response["data"]["response_text"]
    assert actions["data"]["ui_actions"][0]["params"]["product_ids"] == ["1", "2"]
    assert actions["data"]["ui_actions"][0]["params"]["search_query"] == "phone"


def test_inventory_type_prioritizes_actual_iphone_names(monkeypatch):
    from agent import orchestrator

    products = [
        {
            "id": "generic-iphone-category",
            "name": "Samsung Flex Flagship Smartphone 6",
            "brand": "Samsung",
            "category_name": "Electronics",
            "description": "Android smartphone.",
            "tags": ["smartphone", "phone", "android"],
            "stock": 5,
        },
        {
            "id": "iphone-17-pro",
            "name": "iPhone 17 Pro",
            "brand": "Apple",
            "category_name": "Electronics",
            "description": "Premium iPhone.",
            "stock": 9,
        },
        {
            "id": "iphone-air",
            "name": "iPhone Air",
            "brand": "Apple",
            "category_name": "Electronics",
            "description": "Thin iPhone.",
            "stock": 7,
        },
        {
            "id": "airpods-pro",
            "name": "AirPods Pro",
            "brand": "Apple",
            "category_name": "Electronics",
            "description": "Wireless earbuds for Apple devices.",
            "stock": 6,
        },
        {
            "id": "apple-charger",
            "name": "20W USB-C Power Adapter",
            "brand": "Apple",
            "category_name": "Electronics",
            "description": "Fast charger for Apple devices.",
            "stock": 11,
        },
    ]

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    events = list(
        orchestrator.run_stream(
            site_id=ECOMMERCE_TEST_SITE_ID,
            text_input="Do you have iPhone?",
            skip_tts=True,
        )
    )

    response = next(event for event in events if event["event"] == "response")
    actions = next(event for event in events if event["event"] == "actions")

    assert "I found 2 iphones in stock: iPhone 17 Pro, iPhone Air." == response["data"]["response_text"]
    assert actions["data"]["ui_actions"][0]["params"]["product_ids"] == ["iphone-17-pro", "iphone-air"]


def test_product_interest_phrases_use_catalog_without_llm(monkeypatch):
    from agent import orchestrator

    products = [
        {
            "id": "iphone-17-pro",
            "name": "iPhone 17 Pro",
            "brand": "Apple",
            "category_name": "Electronics",
            "stock": 9,
        },
        {
            "id": "shoe-1",
            "name": "Runner Daily Shoe",
            "brand": "NOVA",
            "category_name": "Footwear",
            "stock": 7,
        },
    ]

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    for phrase in (
        "I am interested in buying iPhone",
        "I want to buy an iPhone",
        "Do you sell iPhone?",
        "Is iPhone available?",
    ):
        events = list(
            orchestrator.run_stream(
                site_id=ECOMMERCE_TEST_SITE_ID,
                text_input=phrase,
                skip_tts=True,
            )
        )
        actions = next(event for event in events if event["event"] == "actions")
        response = next(event for event in events if event["event"] == "response")

        assert actions["data"]["ui_actions"][0]["params"]["product_ids"] == ["iphone-17-pro"]
        assert actions["data"]["ui_actions"][0]["params"]["search_query"] == "iphone"
        assert "iPhone 17 Pro" in response["data"]["response_text"]
