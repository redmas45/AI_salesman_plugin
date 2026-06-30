import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator


def test_retrieval_evidence_labels_generic_zero_retrieval(monkeypatch):
    monkeypatch.setattr(
        "db.knowledge.knowledge_stats",
        lambda site_id: {
            "total_items": 4,
            "active_items": 4,
            "missing_embeddings": 0,
            "entity_types": 1,
        },
    )

    evidence = orchestrator._retrieval_evidence("policy_site", False, [])

    assert evidence["source"] == "knowledge_items"
    assert evidence["active_records"] == 4
    assert evidence["retrieved_count"] == 0
    assert evidence["issue"] == "retrieval_returned_zero"


def test_retrieval_evidence_includes_ecommerce_titles_and_vector_issue(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "tenant_inventory_summary",
        lambda site_id: {
            "total_products": 3,
            "active_products": 3,
            "in_stock_products": 2,
            "missing_embeddings": 1,
            "total_categories": 2,
        },
    )

    evidence = orchestrator._retrieval_evidence(
        "ai_kart",
        True,
        [{"id": "p1", "name": "Apple Prime Phone"}, {"id": "p2", "name": "Samsung Daily Phone"}],
    )

    assert evidence["source"] == "products"
    assert evidence["retrieved_ids"] == ["p1", "p2"]
    assert evidence["retrieved_titles"] == ["Apple Prime Phone", "Samsung Daily Phone"]
    assert evidence["issue"] == "some_vectors_missing"


def test_normalize_response_fills_missing_entity_ids_from_retrieval():
    response = {
        "response_text": "Here are options.",
        "intent": "discovery",
        "confidence": 0.9,
        "ui_actions": [{"action": "SHOW_ENTITIES", "params": {}}],
    }
    retrieved = [
        {"id": "service:renovation", "name": "Renovation"},
        {"id": "service:roofing", "name": "Roofing"},
    ]

    normalized = orchestrator._normalize_llm_response(response, retrieved)

    assert normalized["ui_actions"] == [
        {
            "action": "SHOW_ENTITIES",
            "params": {"entity_ids": ["service:renovation", "service:roofing"]},
        }
    ]


def test_normalize_response_drops_empty_entity_action_without_retrieval():
    response = {
        "response_text": "No matching records were retrieved.",
        "intent": "unknown",
        "confidence": 0.2,
        "ui_actions": [{"action": "SHOW_ENTITIES", "params": {}}],
    }

    normalized = orchestrator._normalize_llm_response(response, [])

    assert normalized["ui_actions"] == []


def test_navigation_intent_uses_discovered_routes(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "routes": {
                    "plans": "/plans",
                    "claims": "/claims",
                }
            }
        },
    )

    assert orchestrator._navigation_page_from_transcript("policy_site", "Please open claims page") == "claims"
    assert orchestrator._navigation_page_from_transcript("policy_site", "Go to plans") == "plans"


def test_sort_intent_returns_entity_sort_for_insurance(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")

    response = orchestrator._sort_intent_response(
        "policy_site",
        "Can you sort them between low to high?",
        "Can you sort them between low to high?",
        ecommerce_runtime=False,
        skip_tts=True,
        timings={},
        start_time=0,
    )

    assert response is not None
    assert response["intent"] == "sort"
    assert response["ui_actions"] == [
        {"action": "SORT_ENTITIES", "params": {"sort_by": "price_asc"}}
    ]
    assert "plans" in response["response_text"]


def test_run_sort_premium_takes_precedence_over_plan_navigation(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(
        orchestrator,
        "_navigation_intent_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("sort prompt must not navigate")),
    )
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("sort prompt must not call LLM")),
    )

    response = orchestrator.run(
        site_id="policy_site",
        text_input="Show health insurance plans from low to high premium.",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert response["intent"] == "sort"
    assert response["ui_actions"] == [
        {"action": "SORT_ENTITIES", "params": {"sort_by": "price_asc"}}
    ]
    assert "plans" in response["response_text"]


def test_sort_intent_returns_product_sort_for_ecommerce():
    response = orchestrator._sort_intent_response(
        "ai_kart",
        "Sort products high to low",
        "Sort products high to low",
        ecommerce_runtime=True,
        skip_tts=True,
        timings={},
        start_time=0,
    )

    assert response is not None
    assert response["ui_actions"] == [
        {"action": "SORT_PRODUCTS", "params": {"sort_by": "price_desc"}}
    ]


def test_exact_products_from_query_finds_named_comparison_products(monkeypatch):
    products = [
        {"id": 1, "name": "NOVA Rainbow Sticker", "price": 4, "category_name": "Stickers"},
        {"id": 2, "name": "NOVA Sticker", "price": 4, "category_name": "Stickers"},
        {"id": 3, "name": "NOVA T-Shirt", "price": 20, "category_name": "Shirts"},
    ]

    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)

    matches = orchestrator._exact_products_from_query(
        "Compare Nova sticker with Nova T-shirt.",
        "ai_kart",
    )

    assert [product["name"] for product in matches[:2]] == ["NOVA Sticker", "NOVA T-Shirt"]
    assert all(product["_exact_name_match"] is True for product in matches[:2])


def test_exact_products_from_query_finds_brand_phone_comparison_products(monkeypatch):
    products = [
        {
            "id": "apple-phone-1",
            "name": "Apple Prime Android Flagship / iPhone 1",
            "brand": "Apple",
            "vendor": "Apple",
            "subcategory": "Electronics > Smartphones > Android Flagship / iPhone",
            "description": "Premium smartphone with iOS features.",
            "tags": ["smartphone", "phone", "iphone"],
            "stock": 4,
        },
        {
            "id": "samsung-phone-1",
            "name": "Samsung Daily Android Budget 3",
            "brand": "Samsung",
            "vendor": "Samsung",
            "subcategory": "Electronics > Smartphones > Android Budget",
            "description": "Android smartphone with Galaxy-style camera features.",
            "tags": ["smartphone", "phone", "android"],
            "stock": 8,
        },
        {
            "id": "apple-watch-1",
            "name": "Apple Flex Smartwatches & Fitness Bands 3",
            "brand": "Apple",
            "vendor": "Apple",
            "subcategory": "Electronics > Smartwatches & Fitness Bands",
            "description": "Smartwatch for fitness tracking.",
            "tags": ["smartwatch"],
            "stock": 5,
        },
    ]

    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)

    matches = orchestrator._exact_products_from_query(
        "Compare Apple and Samsung phone",
        "ai_kart",
    )

    assert [product["id"] for product in matches[:2]] == ["apple-phone-1", "samsung-phone-1"]
    assert all(product["_exact_name_match"] is True for product in matches[:2])


def test_exact_products_from_query_falls_back_to_product_type(monkeypatch):
    products = [
        {
            "id": "phone-1",
            "name": "Vivo Prime Android Mid-range 9",
            "brand": "Vivo",
            "category_name": "Electronics",
            "subcategory": "Smartphones",
            "description": "Android smartphone with long battery life.",
            "tags": ["smartphone", "phone", "android"],
            "stock": 5,
        },
        {
            "id": "shoe-1",
            "name": "Runner Daily Shoe",
            "brand": "NOVA",
            "category_name": "Footwear",
            "description": "Running shoe.",
            "tags": ["shoe"],
            "stock": 8,
        },
    ]

    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)

    matches = orchestrator._exact_products_from_query(
        "Recommend a phone and tell me what accessory I should buy with it.",
        "ai_kart",
    )

    assert [product["id"] for product in matches] == ["phone-1"]
    assert matches[0]["_lexical_query_match"] is True


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


def test_brand_phone_comparison_response_is_forced_when_llm_misses_products(monkeypatch):
    response = {
        "response_text": "I don't have those phones right now.",
        "intent": "out_of_stock",
        "confidence": 0.4,
        "ui_actions": [],
    }
    products = [
        {
            "id": "apple-phone-1",
            "name": "Apple Prime Android Flagship / iPhone 1",
            "brand": "Apple",
            "description": "Premium smartphone.",
            "tags": ["smartphone", "phone", "iphone"],
        },
        {
            "id": "samsung-phone-1",
            "name": "Samsung Daily Android Budget 3",
            "brand": "Samsung",
            "description": "Android smartphone.",
            "tags": ["smartphone", "phone", "android"],
        },
    ]

    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)
    retrieved = orchestrator._exact_products_from_query("Compare Apple and Samsung phone", "ai_kart")

    orchestrator._ensure_named_comparison_response(
        response,
        "Compare Apple and Samsung phone",
        retrieved,
    )

    assert response["intent"] == "product_compare"
    assert response["ui_actions"] == [
        {"action": "SHOW_COMPARISON", "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]}}
    ]
    assert "Apple Prime" in response["response_text"]
    assert "Samsung Daily" in response["response_text"]


def test_generic_comparison_response_is_forced_when_llm_misses_retrieved_records():
    response = {
        "response_text": "No records found.",
        "intent": "not_found",
        "confidence": 0.3,
        "ui_actions": [],
    }
    retrieved = [
        {
            "id": "product:H001",
            "title": "IndividualCare Plan",
            "entity_type": "insurance_plan",
            "summary": "Health insurance plan with cashless hospitalization.",
            "price": 899,
        },
        {
            "id": "product:H002",
            "title": "FamilyShield Floater",
            "entity_type": "insurance_plan",
            "summary": "Family health insurance plan with maternity benefit.",
            "price": 1499,
        },
    ]

    orchestrator._ensure_generic_comparison_response(
        response,
        "Compare health insurance for me, I am 20 year old",
        retrieved,
    )

    assert response["intent"] == "compare"
    assert response["ui_actions"] == [
        {"action": "COMPARE_ENTITIES", "params": {"entity_ids": ["product:H001", "product:H002"]}}
    ]
    assert "IndividualCare Plan" in response["response_text"]
    assert "FamilyShield Floater" in response["response_text"]


def test_run_forces_apple_samsung_comparison_when_llm_returns_no_records(monkeypatch):
    products = [
        {
            "id": "apple-phone-1",
            "name": "Apple Prime Android Flagship / iPhone 1",
            "brand": "Apple",
            "vendor": "Apple",
            "category_name": "Phones",
            "subcategory": "Electronics > Smartphones",
            "description": "Premium smartphone with iOS features.",
            "tags": ["smartphone", "phone", "iphone"],
            "price": 999,
            "stock": 4,
        },
        {
            "id": "samsung-phone-1",
            "name": "Samsung Daily Android Budget 3",
            "brand": "Samsung",
            "vendor": "Samsung",
            "category_name": "Phones",
            "subcategory": "Electronics > Smartphones",
            "description": "Android smartphone with Galaxy-style camera features.",
            "tags": ["smartphone", "phone", "android"],
            "price": 699,
            "stock": 8,
        },
        {
            "id": "apple-watch-1",
            "name": "Apple Flex Smartwatches & Fitness Bands 3",
            "brand": "Apple",
            "vendor": "Apple",
            "category_name": "Wearables",
            "subcategory": "Electronics > Smartwatches & Fitness Bands",
            "description": "Smartwatch for fitness tracking.",
            "tags": ["smartwatch"],
            "price": 349,
            "stock": 5,
        },
    ]

    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "ecommerce")
    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda site_id: {})
    monkeypatch.setattr(orchestrator, "_cart_context_for_site", lambda site_id, ecommerce_runtime: "cart unavailable")
    monkeypatch.setattr(orchestrator.rag, "extract_price_constraints", lambda query: {})
    monkeypatch.setattr(orchestrator.rag, "retrieve", lambda query, site_id, price_constraints=None: [])
    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "No records found.",
            "intent": "not_found",
            "confidence": 0.2,
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
            "total_products": 3,
            "active_products": 3,
            "in_stock_products": 3,
            "missing_embeddings": 0,
            "total_categories": 2,
        },
    )

    result = orchestrator.run(
        site_id="ai_kart",
        text_input="Compare Apple and Samsung phone",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "product_compare"
    assert "Apple Prime" in result["response_text"]
    assert "Samsung Daily" in result["response_text"]
    assert result["ui_actions"] == [
        {
            "action": "SHOW_COMPARISON",
            "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]},
        }
    ]
    assert result["retrieval"]["source"] == "products"
    assert result["retrieval"]["retrieved_count"] >= 2
    assert result["retrieval"]["retrieved_ids"][:2] == ["apple-phone-1", "samsung-phone-1"]
    assert result["retrieval"]["issue"] == "ok"


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
    assert result["response_text"] == "Added NOVA Daily Phone to your cart."
    assert result["ui_actions"] == [{"action": "ADD_TO_CART", "params": {"product_id": "1"}}]


def test_cart_recovery_resolves_ordinal_without_treating_option_as_quantity() -> None:
    response = {"response_text": "The second one is a strong option.", "intent": "product_search", "confidence": 0.6, "ui_actions": []}
    products = [
        {"id": "1", "name": "Budget Phone", "price": 299, "stock": 5},
        {"id": "2", "name": "Premium Phone", "price": 699, "stock": 5},
    ]

    orchestrator._ensure_cart_request_response(response, "Add option 2 to my cart.", products)

    assert response["ui_actions"] == [{"action": "ADD_TO_CART", "params": {"product_id": "2"}}]
    assert response["response_text"] == "Added Premium Phone to your cart."


def test_cart_recovery_caps_requested_quantity_to_stock() -> None:
    response = {"response_text": "The cap is available.", "intent": "product_search", "confidence": 0.6, "ui_actions": []}
    products = [{"id": "10", "name": "NOVA Cap", "price": 20, "stock": 2}]

    orchestrator._ensure_cart_request_response(response, "Add 5 NOVA Cap to my cart.", products)

    assert response["ui_actions"] == [
        {"action": "ADD_TO_CART", "params": {"product_id": "10", "quantity": 2}}
    ]
    assert response["response_text"] == "Added 2 x NOVA Cap to your cart."


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
        {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}
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


def test_run_recovers_insurance_quote_action_when_llm_omits_ui_action(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda site_id: {})
    monkeypatch.setattr(
        "agent.retrieval.generic_rag.retrieve_knowledge",
        lambda query, site_id: [],
    )
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: {
            "response_text": "I can help with that.",
            "intent": "lead",
            "confidence": 0.5,
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
            "total_items": 0,
            "active_items": 0,
            "missing_embeddings": 0,
            "entity_types": 0,
        },
    )

    result = orchestrator.run(
        site_id="policy_site",
        text_input="I am 27 years old and want health insurance quotes.",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "lead_flow"
    assert result["response_text"] == "I can start the quote flow now."
    assert result["ui_actions"] == [{"action": "START_QUOTE", "params": {}}]


def test_lead_flow_mapping_uses_current_vertical_actions(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "construction")
    monkeypatch.setattr(
        "agent.capabilities.get_allowed_actions",
        lambda site_id: {"SHOW_ENTITIES", "REQUEST_ESTIMATE"},
    )

    action = orchestrator._lead_flow_action_from_transcript(
        "Can I get a quote for a kitchen renovation?",
        "builder_site",
    )

    assert action == "REQUEST_ESTIMATE"


def test_run_forces_health_insurance_age_comparison_when_llm_returns_no_records(monkeypatch):
    knowledge_items = [
        {
            "id": "product:H001",
            "title": "IndividualCare Plan",
            "name": "IndividualCare Plan",
            "entity_type": "insurance_plan",
            "summary": "Health insurance plan for a 20 year old with cashless hospitalization.",
            "price": 899,
        },
        {
            "id": "product:H002",
            "title": "FamilyShield Floater",
            "name": "FamilyShield Floater",
            "entity_type": "insurance_plan",
            "summary": "Family health insurance plan with maternity and hospitalization benefits.",
            "price": 1499,
        },
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
            "response_text": "No records found.",
            "intent": "not_found",
            "confidence": 0.2,
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
            "total_items": 2,
            "active_items": 2,
            "missing_embeddings": 0,
            "entity_types": 1,
        },
    )

    result = orchestrator.run(
        site_id="policy_site",
        text_input="Compare health insurance for me, I am 20 year old",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "compare"
    assert "No records found" not in result["response_text"]
    assert "IndividualCare Plan" in result["response_text"]
    assert "FamilyShield Floater" in result["response_text"]
    assert result["ui_actions"] == [
        {
            "action": "COMPARE_ENTITIES",
            "params": {"entity_ids": ["product:H001", "product:H002"]},
        }
    ]
    assert result["retrieval"]["source"] == "knowledge_items"
    assert result["retrieval"]["retrieved_count"] == 2
    assert result["retrieval"]["retrieved_ids"] == ["product:H001", "product:H002"]
    assert result["retrieval"]["issue"] == "ok"


def test_false_empty_inventory_claim_is_rewritten_for_cart_language(monkeypatch):
    response = {
        "response_text": "Right now, it seems we don't have any items available in our inventory.",
        "intent": "out_of_stock",
        "confidence": 0.6,
        "ui_actions": [],
    }

    monkeypatch.setattr(orchestrator, "tenant_inventory_summary", lambda site_id: {"in_stock_products": 12})
    monkeypatch.setattr(
        orchestrator,
        "get_all_products",
        lambda site_id, limit=1000: [
            {"category_name": "Headwear"},
            {"category_name": "Drinkware"},
            {"category_name": "Stickers"},
        ],
    )

    orchestrator._prevent_false_empty_inventory_claim(
        response,
        "If you don't have any item in my tray, how could a shop?",
        "ai_kart",
    )

    assert "cart or tray looks empty" in response["response_text"]
    assert "plenty of products in stock" in response["response_text"]
    assert "Headwear" in response["response_text"]
    assert response["intent"] == "chitchat"
    assert response["ui_actions"] == []
