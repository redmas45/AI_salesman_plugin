import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator


def test_run_recovers_explicit_add_to_cart_when_llm_misses_action(monkeypatch):
    products = [
        {
            "id": "1",
            "name": "NOVA Daily Phone",
            "category_name": "Phones",
            "description": "Reliable daily smartphone.",
            "price": 499,
            "stock": 4,
        }
    ]

    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "ecommerce")
    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda site_id: {})
    monkeypatch.setattr(orchestrator, "_cart_context_for_site", lambda site_id, ecommerce_runtime: "cart empty")
    monkeypatch.setattr(orchestrator, "plan_universal_flow", lambda **kwargs: None)
    monkeypatch.setattr(orchestrator.rag, "extract_price_constraints", lambda query: {})
    monkeypatch.setattr(orchestrator.rag, "retrieve", lambda query, site_id, price_constraints=None: products)
    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "This phone is a good everyday pick.",
            "intent": "product_search",
            "confidence": 0.7,
            "ui_actions": [],
        },
    )
    monkeypatch.setattr(orchestrator, "_add_variant_ids_to_cart_actions", lambda site_id, actions: actions)
    monkeypatch.setattr(
        orchestrator,
        "_apply_capability_filter_result",
        lambda site_id, actions: {"status": "ok", "actions": actions, "removed_actions": []},
    )
    monkeypatch.setattr(
        orchestrator,
        "tenant_inventory_summary",
        lambda site_id: {
            "total_products": 1,
            "active_products": 1,
            "in_stock_products": 1,
            "missing_embeddings": 0,
            "total_categories": 1,
        },
    )

    result = orchestrator.run(
        site_id="ai_kart",
        text_input="Add this phone to my cart.",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "add_to_cart"
    assert result["response_text"] == "I'll try to add NOVA Daily Phone to your cart now."
    assert result["ui_actions"] == [{"action": "ADD_TO_CART", "params": {"product_id": "1"}}]


def test_run_recovers_phone_search_from_catalog_when_vector_retrieval_misses(monkeypatch):
    products = [
        {
            "id": "phone-1",
            "name": "NOVA Daily Phone",
            "brand": "NOVA",
            "category_name": "Phones",
            "description": "Reliable everyday smartphone.",
            "tags": ["smartphone", "phone"],
            "price": 499,
            "stock": 4,
        },
        {
            "id": "phone-2",
            "name": "Samsung Galaxy Daily",
            "brand": "Samsung",
            "category_name": "Phones",
            "description": "Android smartphone.",
            "tags": ["smartphone", "phone", "android"],
            "price": 699,
            "stock": 6,
        },
    ]

    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "ecommerce")
    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda site_id: {})
    monkeypatch.setattr(orchestrator, "_cart_context_for_site", lambda site_id, ecommerce_runtime: "cart empty")
    monkeypatch.setattr(orchestrator, "plan_universal_flow", lambda **kwargs: None)
    monkeypatch.setattr(orchestrator.rag, "extract_price_constraints", lambda query: {})
    monkeypatch.setattr(orchestrator.rag, "retrieve", lambda query, site_id, price_constraints=None: [])
    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "I don't have phones right now.",
            "intent": "out_of_stock",
            "confidence": 0.4,
            "ui_actions": [],
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "_apply_capability_filter_result",
        lambda site_id, actions: {"status": "ok", "actions": actions, "removed_actions": []},
    )
    monkeypatch.setattr(
        orchestrator,
        "tenant_inventory_summary",
        lambda site_id: {
            "total_products": 2,
            "active_products": 2,
            "in_stock_products": 2,
            "missing_embeddings": 0,
            "total_categories": 1,
        },
    )

    result = orchestrator.run(
        site_id="ai_kart",
        text_input="I wanna buy a phone.",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "product_search"
    assert "don't have phones" not in result["response_text"].lower()
    assert "NOVA Daily Phone" in result["response_text"]
    assert result["ui_actions"][0]["action"] == "SHOW_PRODUCTS"
    assert set(result["ui_actions"][0]["params"]["product_ids"]) == {"phone-1", "phone-2"}
    assert result["ui_actions"][0]["params"]["search_query"] == "phone"
    assert result["retrieval"]["retrieved_count"] == 2
    assert result["retrieval"]["issue"] == "ok"


def test_cart_recovery_resolves_ordinal_without_treating_option_as_quantity() -> None:
    response = {"response_text": "The second one is a strong option.", "intent": "product_search", "confidence": 0.6, "ui_actions": []}
    products = [
        {"id": "1", "name": "Budget Phone", "price": 299, "stock": 5},
        {"id": "2", "name": "Premium Phone", "price": 699, "stock": 5},
    ]

    orchestrator._ensure_cart_request_response(response, "Add option 2 to my cart.", products)

    assert response["ui_actions"] == [{"action": "ADD_TO_CART", "params": {"product_id": "2"}}]
    assert response["response_text"] == "I'll try to add Premium Phone to your cart now."


def test_cart_recovery_caps_requested_quantity_to_stock() -> None:
    response = {"response_text": "The cap is available.", "intent": "product_search", "confidence": 0.6, "ui_actions": []}
    products = [{"id": "10", "name": "NOVA Cap", "price": 20, "stock": 2}]

    orchestrator._ensure_cart_request_response(response, "Add 5 NOVA Cap to my cart.", products)

    assert response["ui_actions"] == [
        {"action": "ADD_TO_CART", "params": {"product_id": "10", "quantity": 2}}
    ]
    assert response["response_text"] == "I'll try to add 2 x NOVA Cap to your cart now."


def test_cart_recovery_repairs_empty_llm_action_from_named_response() -> None:
    response = {
        "response_text": "Samsung Galaxy Daily is the best fit, so I will add it.",
        "intent": "add_to_cart",
        "confidence": 0.8,
        "ui_actions": [{"action": "ADD_TO_CART", "params": {}}],
    }
    products = [
        {"id": "1", "name": "NOVA Daily Phone", "price": 499, "stock": 5},
        {"id": "2", "name": "Samsung Galaxy Daily", "price": 699, "stock": 5},
    ]

    orchestrator._ensure_cart_request_response(
        response,
        "Choose the better option and add one to my cart.",
        products,
    )

    assert response["ui_actions"] == [
        {"action": "ADD_TO_CART", "params": {"product_id": "2"}}
    ]
    assert response["response_text"] == "I'll try to add Samsung Galaxy Daily to your cart now."


def test_cart_recovery_selects_best_store_backed_referenced_choice() -> None:
    response = {
        "response_text": "Which one should I add?",
        "intent": "add_to_cart",
        "confidence": 0.7,
        "ui_actions": [],
    }
    products = [
        {"id": "1", "name": "Lower Rated Stay", "price": 500, "stock": 8, "rating": 4.1, "review_count": 90},
        {"id": "2", "name": "Better Rated Stay", "price": 650, "stock": 4, "rating": 4.7, "review_count": 40},
        {"id": "3", "name": "Unrelated Result", "price": 100, "stock": 20, "rating": 5.0, "review_count": 500},
    ]

    orchestrator._ensure_cart_request_response(
        response,
        "Choose the better of those two and add it to my cart.",
        products,
    )

    assert response["ui_actions"] == [
        {"action": "ADD_TO_CART", "params": {"product_id": "2"}}
    ]
    assert "Better Rated Stay" in response["response_text"]


def test_cart_recovery_selects_better_rated_referential_choice_without_count() -> None:
    response = {
        "response_text": "Which one should I add?",
        "intent": "add_to_cart",
        "confidence": 0.7,
        "ui_actions": [],
    }
    products = [
        {"id": "1", "name": "Lower Rated Phone", "stock": 8, "rating": 4.1, "review_count": 90},
        {"id": "2", "name": "Better Rated Phone", "stock": 4, "rating": 4.7, "review_count": 40},
    ]

    orchestrator._ensure_cart_request_response(
        response,
        "Pick the better-rated one and add it to my cart.",
        products,
    )

    assert response["ui_actions"] == [
        {"action": "ADD_TO_CART", "params": {"product_id": "2"}}
    ]


def test_run_recovers_source_backed_product_fact_answer_when_llm_misses_display_action(monkeypatch):
    products = [
        {
            "id": "phone-1",
            "name": "NOVA Daily Phone",
            "brand": "NOVA",
            "category_name": "Phones",
            "description": "Reliable everyday smartphone with long battery life.",
            "price": 499,
            "stock": 3,
        }
    ]

    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "ecommerce")
    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda site_id: {})
    monkeypatch.setattr(orchestrator, "_cart_context_for_site", lambda site_id, ecommerce_runtime: "cart empty")
    monkeypatch.setattr(orchestrator.rag, "extract_price_constraints", lambda query: {})
    monkeypatch.setattr(orchestrator.rag, "retrieve", lambda query, site_id, price_constraints=None: products)
    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "It is a good option.",
            "intent": "product_detail",
            "confidence": 0.6,
            "ui_actions": [],
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "_apply_capability_filter_result",
        lambda site_id, actions: {"status": "ok", "actions": actions, "removed_actions": []},
    )
    monkeypatch.setattr(
        orchestrator,
        "tenant_inventory_summary",
        lambda site_id: {
            "total_products": 1,
            "active_products": 1,
            "in_stock_products": 1,
            "missing_embeddings": 0,
            "total_categories": 1,
        },
    )

    result = orchestrator.run(
        site_id="ai_kart",
        text_input="Why should I buy NOVA Daily Phone?",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "product_detail"
    assert "NOVA Daily Phone" in result["response_text"]
    assert "Reliable everyday smartphone" in result["response_text"]
    assert "Price: 499" in result["response_text"]
    assert result["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["phone-1"], "search_query": "nova daily phone"},
        }
    ]


def test_run_recovers_source_backed_entity_fact_answer_when_llm_misses_display_action(monkeypatch):
    knowledge_items = [
        {
            "id": "plan:H001",
            "title": "IndividualCare Plan",
            "entity_type": "insurance_plan",
            "summary": "Health insurance plan with cashless hospitalization and renewal support.",
            "price": 899,
        }
    ]

    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda site_id: {})
    monkeypatch.setattr(
        "agent.retrieval.generic_rag.retrieve_knowledge",
        lambda query, site_id: knowledge_items,
    )
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "It has useful coverage.",
            "intent": "discovery",
            "confidence": 0.6,
            "ui_actions": [],
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "_apply_capability_filter_result",
        lambda site_id, actions: {"status": "ok", "actions": actions, "removed_actions": []},
    )
    monkeypatch.setattr(
        "db.knowledge.knowledge_stats",
        lambda site_id: {
            "total_items": 1,
            "active_items": 1,
            "missing_embeddings": 0,
            "entity_types": 1,
        },
    )

    result = orchestrator.run(
        site_id="policy_site",
        text_input="Tell me facts about IndividualCare Plan.",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "discovery"
    assert "IndividualCare Plan" in result["response_text"]
    assert "cashless hospitalization" in result["response_text"]
    assert result["ui_actions"] == [
        {"action": "SHOW_ENTITIES", "params": {"entity_ids": ["plan:H001"]}}
    ]
