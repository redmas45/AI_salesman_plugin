import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator
from agent.products.product_matching import ProductCatalogMatcher
from agent.runtime_helpers import retrieval_runtime


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


def test_history_reference_finds_latest_message_with_expected_product_count() -> None:
    products = [
        {"id": 1, "name": "First Choice"},
        {"id": 2, "name": "Second Choice"},
        {"id": 3, "name": "Extra Choice"},
    ]
    matcher = ProductCatalogMatcher(
        load_all_products=lambda site_id, limit: products,
        load_products_by_ids=lambda site_id, ids: [product for product in products if product["id"] in ids],
        recoverable_errors=(RuntimeError,),
        logger=orchestrator.logger,
    )
    history = [
        {"role": "assistant", "content": "First Choice compared with Second Choice."},
        {"role": "assistant", "content": "First Choice, Second Choice, and Extra Choice have different specs."},
    ]

    matches = matcher.extract_products_from_history(history, "demo", expected_count=2)

    assert [product["id"] for product in matches] == [1, 2]


def test_current_turn_price_limit_is_not_replaced_by_older_history_budget() -> None:
    extraction_inputs: list[str] = []
    products = [
        {"id": "within", "name": "Budget Phone", "price": 19_999},
        {"id": "outside", "name": "Premium Phone", "price": 41_399},
    ]

    def extract_constraints(query: str) -> dict[str, float]:
        extraction_inputs.append(query)
        return {"max_price": 20_000}

    context = retrieval_runtime.retrieve_context(
        "ai_kart",
        "What phones do you list below INR 20,000?",
        [{"role": "user", "content": "Show phones under INR 90,000."}],
        safe_user_profile=lambda site_id: {},
        augment_query_with_history=lambda query, history: (
            "phones under INR 90,000. What phones do you list below INR 20,000?"
        ),
        is_ecommerce_site=lambda site_id: True,
        retrieve_generic_context=lambda site_id, query, profile: retrieval_runtime.RetrievalContext({}, {}, []),
        extract_price_constraints=extract_constraints,
        retrieve_products=lambda *args, **kwargs: products,
        merge_products=lambda primary, supplemental, limit=None: [*supplemental, *primary],
        merge_history_products=lambda retrieved, history, site_id, query: retrieved,
        exact_products_from_query=lambda query, site_id: [],
        recoverable_errors=(RuntimeError,),
        logger=orchestrator.logger,
    )

    assert extraction_inputs == ["What phones do you list below INR 20,000?"]
    assert [product["id"] for product in context.products] == ["within"]


def test_referential_followup_uses_only_marked_history_products() -> None:
    products = [
        {"id": "first", "name": "First Moisturiser", "price": 299, "_history_context": True},
        {"id": "second", "name": "Second Moisturiser", "price": 899, "_history_context": True},
        {"id": "unrelated", "name": "Unrelated Laptop", "price": 50_000},
    ]

    context = retrieval_runtime.retrieve_context(
        "ai_kart",
        "Which of the compared products is better rated?",
        [{"role": "assistant", "content": "First Moisturiser and Second Moisturiser."}],
        safe_user_profile=lambda site_id: {},
        augment_query_with_history=lambda query, history: query,
        is_ecommerce_site=lambda site_id: True,
        retrieve_generic_context=lambda site_id, query, profile: retrieval_runtime.RetrievalContext({}, {}, []),
        extract_price_constraints=lambda query: {},
        retrieve_products=lambda *args, **kwargs: products,
        merge_products=lambda primary, supplemental, limit=None: [*supplemental, *primary],
        merge_history_products=lambda retrieved, history, site_id, query: retrieved,
        exact_products_from_query=lambda query, site_id: [products[-1]],
        recoverable_errors=(RuntimeError,),
        logger=orchestrator.logger,
    )

    assert [product["id"] for product in context.products] == ["first", "second"]


def test_comparison_action_respects_requested_two_product_limit() -> None:
    response = {
        "response_text": "Here are several options.",
        "intent": "product_compare",
        "ui_actions": [
            {
                "action": "SHOW_COMPARISON",
                "params": {"product_ids": ["one", "two", "three", "four"]},
            }
        ],
    }

    orchestrator._promote_comparison_action(
        response,
        "Compare the best two products.",
        [],
    )

    assert response["ui_actions"][0]["params"]["product_ids"] == ["one", "two"]


def test_grounded_product_facts_include_rating_and_review_count() -> None:
    text = orchestrator._comparison_fallback_text(
        [
            {"id": "one", "name": "First Choice", "price": 499, "rating": 4.7, "review_count": 183},
            {"id": "two", "name": "Second Choice", "price": 699, "rating": 4.4, "review_count": 91},
        ]
    )

    assert "Rating: 4.7/5 (183 reviews)." in text
    assert "Rating: 4.4/5 (91 reviews)." in text


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


def test_exact_products_from_query_finds_partial_product_title_comparison(monkeypatch):
    products = [
        {
            "id": "gaming-2",
            "name": "Acer Classic Gaming 2",
            "brand": "Acer",
            "category_name": "electronics",
            "description": "Gaming laptop with RTX graphics.",
            "tags": ["laptop", "gaming", "rtx", "acer"],
            "stock": 14,
        },
        {
            "id": "student-7",
            "name": "Acer Active Student / Budget 7",
            "brand": "Acer",
            "category_name": "electronics",
            "description": "Budget student laptop.",
            "tags": ["laptop", "student", "budget", "acer"],
            "stock": 18,
        },
    ]

    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)

    matches = orchestrator._exact_products_from_query(
        "Can you compare this Acer Classic Gaming 2 versus Acer Active Student?",
        "ai_kart",
    )

    assert [product["id"] for product in matches[:2]] == ["gaming-2", "student-7"]
    assert matches[0]["_exact_name_match"] is True
    assert matches[1]["_lexical_query_match"] is True


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


def test_exact_products_from_query_prioritizes_explicit_iphone_over_generic_android(monkeypatch):
    products = [
        {
            "id": "android-1",
            "name": "OPPO Active Android Budget 9",
            "brand": "OPPO",
            "category_name": "Electronics",
            "description": "Android smartphone.",
            "tags": ["smartphone", "phone", "android"],
            "stock": 9,
        },
        {
            "id": "iphone-air",
            "name": "iPhone Air",
            "brand": "Apple",
            "category_name": "Electronics",
            "description": "Thin, light premium iPhone.",
            "tags": ["electronics"],
            "stock": 18,
        },
        {
            "id": "iphone-17",
            "name": "iPhone 17",
            "brand": "Apple",
            "category_name": "Electronics",
            "description": "Latest iPhone.",
            "tags": ["electronics"],
            "stock": 8,
        },
    ]

    monkeypatch.setattr("db.database.get_all_products", lambda site_id, limit=1000: products)

    matches = orchestrator._exact_products_from_query("I want to buy iPhone.", "ai_kart")

    assert [product["id"] for product in matches[:2]] == ["iphone-17", "iphone-air"]
    assert "android-1" not in [product["id"] for product in matches[:2]]


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


def test_product_comparison_fallback_does_not_invent_zero_price():
    text = orchestrator._comparison_fallback_text(
        [
            {"id": "p1", "name": "NOVA Phone", "category_name": "Phones", "description": "Compact phone."},
            {"id": "p2", "name": "ORBIT Phone", "category_name": "Phones", "price": 599, "stock": 3},
        ]
    )

    assert "$0.00" not in text
    assert "Price not published in retrieved data" in text
    assert "Price: 599" in text


def test_generic_comparison_fallback_uses_nested_pricing_and_availability():
    text = orchestrator._generic_comparison_fallback_text(
        [
            {
                "id": "plan:1",
                "title": "Care Plan",
                "entity_type": "insurance_plan",
                "pricing": {"monthly_premium": 899},
                "availability": {"status": "quote required"},
                "summary": "Cashless hospitalization.",
            },
            {
                "id": "plan:2",
                "title": "Travel Plan",
                "entity_type": "travel_plan",
                "location": {"city": "Pune"},
                "summary": "Trip cover.",
            },
        ]
    )

    assert "published price or premium 899" in text
    assert "availability: quote required" in text
    assert "location: Pune" in text


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

