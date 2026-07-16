import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator
from agent.responses.inventory_responses import is_inventory_stats_query
from agent.runtime_helpers.response_validation import normalize_product_action_ids


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


def test_normalize_response_drops_empty_product_filter_actions():
    response = {
        "response_text": "Here are phones.",
        "intent": "product_search",
        "confidence": 0.9,
        "ui_actions": [
            {"action": "FILTER_PRODUCTS", "params": {}},
            {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}},
        ],
    }
    retrieved = [{"id": "phone-1", "name": "Samsung Phone"}]

    normalized = orchestrator._normalize_llm_response(response, retrieved)

    assert normalized["ui_actions"] == [
        {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}
    ]


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


def test_incomplete_transcript_gets_clarification_without_llm(monkeypatch):
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("clarification should not call LLM")),
    )

    response = orchestrator.run(
        site_id="ai_kart",
        text_input="Hello, I'm looking for, I think,",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert response["intent"] == "clarify"
    assert response["ui_actions"] == []
    assert "What should I help you find" in response["response_text"]


def test_real_need_transcript_does_not_trigger_clarification():
    assert not orchestrator._needs_transcript_clarification("I need health insurance for myself")


def test_product_need_with_greeting_is_not_treated_as_greeting():
    assert not orchestrator._is_simple_greeting("Hey, I need a smartwatch")


def test_looking_for_product_transcript_is_not_clarified():
    assert not orchestrator._needs_transcript_clarification("I'm looking for watches")


def test_display_search_query_removes_speech_fillers_and_corrections():
    assert orchestrator._display_search_query("okay we iphone") == "iphone"
    assert orchestrator._display_search_query("I asked for books.") == "books"
    assert orchestrator._display_search_query("you books") == "books"
    assert orchestrator._display_search_query("on phone wanna phones") == "phone"
    assert orchestrator._display_search_query("q: of iphone 17") == "iphone 17"
    assert orchestrator._display_search_query("I am interested in buying iPhone") == "iphone"
    assert orchestrator._display_search_query("Do you sell iPhone?") == "iphone"
    assert orchestrator._display_search_query("Only Samsung phones. I did not ask for Oppo.") == "samsung phone"
    assert (
        orchestrator._display_search_query(
            "I don't know, I have a budget of 50,000 rupees.",
            [{"id": "p1", "subcategory": "Smartphones", "name": "OPPO Active Android Budget 9"}],
        )
        == "phone"
    )


def test_budget_followup_augments_retrieval_query_with_prior_product_need():
    query = orchestrator._augment_query_with_history(
        "I don't know, I have a budget of 50,000 rupees.",
        [{"role": "user", "content": "I want to buy a phone. Can you recommend me something?"}],
    )

    assert query.startswith("phone.")
    assert "50,000 rupees" in query


def test_context_only_followup_augments_retrieval_query_with_prior_product_need():
    query = orchestrator._augment_query_with_history(
        "Show me the cheaper one.",
        [{"role": "user", "content": "Can you recommend a phone under 50,000 rupees?"}],
    )

    assert query.startswith("phone.")
    assert "cheaper one" in query


def test_referential_followup_skips_offtopic_and_deep_history_turns():
    query = orchestrator._augment_query_with_history(
        "Stay with website facts: which compared option is in stock and better rated?",
        [
            {"role": "user", "content": "I need beauty products for dry skin."},
            {"role": "user", "content": "Compare two relevant options."},
            {"role": "user", "content": "Explain their molecular architecture in depth."},
            {"role": "user", "content": "Who is the prime minister of India?"},
        ],
    )

    assert query.startswith("beauty dry skin.")


def test_review_count_question_is_not_mistaken_for_catalog_count() -> None:
    assert not is_inventory_stats_query(
        "Compare these products by ingredients, rating, price, and review count."
    )
    assert is_inventory_stats_query("What is the total number of products in the catalog?")


def test_product_action_ids_are_normalized_before_guardrails() -> None:
    actions = normalize_product_action_ids(
        [
            {"action": "SHOW_PRODUCT_DETAIL", "params": {"product_id": '\"123\"'}},
            {"action": "SHOW_COMPARISON", "params": {"product_ids": ["'1'", '\"2\"']}},
        ]
    )

    assert actions == [
        {"action": "SHOW_PRODUCT_DETAIL", "params": {"product_id": "123"}},
        {"action": "SHOW_COMPARISON", "params": {"product_ids": ["1", "2"]}},
    ]


def test_comparison_with_one_llm_id_recovers_second_retrieved_product():
    response = {
        "intent": "product_compare",
        "ui_actions": [{"action": "SHOW_COMPARISON", "params": {"product_ids": ["1"]}}],
    }

    orchestrator._promote_comparison_action(
        response,
        "Compare these two options.",
        [{"id": "1"}, {"id": "2"}, {"id": "3"}],
    )

    assert response["ui_actions"] == [
        {"action": "SHOW_COMPARISON", "params": {"product_ids": ["1", "2", "3"]}}
    ]


def test_explicit_single_product_detail_uses_detail_action():
    response = {
        "ui_actions": [
            {
                "action": "SHOW_PRODUCTS",
                "params": {"product_ids": ["phone-1"], "search_query": "phone"},
            }
        ]
    }

    orchestrator._ensure_product_display_search_queries(
        response,
        "Open the details of the cheaper shortlisted one.",
        [{"id": "phone-1", "name": "NOVA Phone"}],
    )

    assert response["ui_actions"] == [
        {"action": "SHOW_PRODUCT_DETAIL", "params": {"product_id": "phone-1"}}
    ]


def test_budget_followup_uses_augmented_query_for_exact_product_supplement(monkeypatch):
    captured_queries: list[str] = []
    iphone = {"id": "iphone-1", "name": "iPhone 17", "price": 79999, "stock": 4}

    monkeypatch.setattr(orchestrator, "_safe_user_profile", lambda _site_id: {})
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda _site_id: True)
    monkeypatch.setattr(orchestrator.rag, "extract_price_constraints", lambda _query: {"max_price": 80000})
    monkeypatch.setattr(orchestrator.rag, "retrieve", lambda *_args, **_kwargs: [iphone])
    monkeypatch.setattr(orchestrator, "_merge_history_products", lambda products, *_args: products)

    def exact_products(query: str, _site_id: str, limit: int = 6) -> list[dict]:
        captured_queries.append(query)
        return [iphone] if "iphone" in query.lower() else []

    monkeypatch.setattr(orchestrator, "_exact_products_from_query", exact_products)

    context = orchestrator._retrieve_context(
        "ai_kart",
        "Show me the best option under 80000",
        [{"role": "user", "content": "I am interested in buying an iPhone"}],
    )

    assert captured_queries == ["iphone. Show me the best option under 80000"]
    assert context.products[0]["name"] == "iPhone 17"


def test_recommendation_response_does_not_ask_which_one_to_add(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)
    response = {
        "response_text": "Which one should I add: OPPO Active Android Budget 9, Realme Pro Android Budget 2?",
        "intent": "buy",
        "confidence": 0.8,
        "ui_actions": [],
    }

    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="I want to buy a phone. Can you recommend me something?",
        retrieved_products=[
            {"id": "p1", "subcategory": "Smartphones", "name": "OPPO Active Android Budget 9"},
            {"id": "p2", "subcategory": "Smartphones", "name": "Realme Pro Android Budget 2"},
        ],
        blocked_text="Blocked.",
    )

    assert validated["intent"] == "product_search"
    assert validated["ui_actions"][0]["action"] == "SHOW_PRODUCTS"
    assert validated["ui_actions"][0]["params"]["search_query"] == "phone"
    assert "Which one should I add" not in validated["response_text"]


def test_ecommerce_discovery_cache_bypassed_for_corrections(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator,
        "lookup_answer_cache",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("cache should be bypassed")),
    )

    assert (
        orchestrator._cached_answer_response(
            "ai_kart",
            "I asked for books.",
            "I asked for books.",
            skip_tts=True,
            timings={},
            start_time=0,
        )
        is None
    )


def test_ecommerce_discovery_cache_allowed_for_standalone_product_guidance(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator,
        "lookup_answer_cache",
        lambda *args, **kwargs: {
            "answer_text": "I found phones under your budget.",
            "answer_scope": "buying_guidance",
            "confidence": 0.95,
            "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["1"], "search_query": "phone"}}],
            "match_type": "semantic",
            "match_score": 0.91,
            "data_version": 3,
            "source_ids": ["1"],
            "source_urls": [],
        },
    )

    result = orchestrator._cached_answer_response(
        "ai_kart",
        "Can you recommend a phone under 50000 rupees?",
        "Can you recommend a phone under 50000 rupees?",
        skip_tts=True,
        timings={},
        start_time=0,
    )

    assert result is not None
    assert result["retrieval"]["cache_hit"] is True
    assert result["ui_actions"][0]["params"]["search_query"] == "phone"


def test_bad_existing_product_search_query_is_sanitized():
    response = {
        "ui_actions": [
            {
                "action": "SHOW_PRODUCTS",
                "params": {"product_ids": ["17"], "search_query": "of iphone 17"},
            }
        ]
    }

    orchestrator._ensure_product_display_search_queries(
        response,
        "Show me iPhone 17.",
        [{"id": "17", "name": "iPhone 17", "subcategory": "Smartphones"}],
    )

    assert response["ui_actions"][0]["params"]["search_query"] == "iphone 17"


def test_single_product_action_replaces_broad_category_query_with_product_name():
    response = {
        "ui_actions": [
            {
                "action": "SHOW_PRODUCTS",
                "params": {"product_ids": ["17"], "search_query": "electronics"},
            }
        ]
    }

    orchestrator._ensure_product_display_search_queries(
        response,
        "Show me the best option under 80000.",
        [
            {"id": "17", "name": "iPhone 17", "category_name": "Electronics"},
            {"id": "17", "name": "iPhone 17", "category_name": "Electronics"},
            {"id": "17e", "name": "iPhone 17e", "category_name": "Electronics"},
        ],
    )

    assert response["ui_actions"][0]["params"]["search_query"] == "iphone 17"


def test_single_product_action_uses_product_name_after_query_is_stripped():
    response = {
        "ui_actions": [
            {
                "action": "SHOW_PRODUCTS",
                "params": {"product_ids": ["17"]},
            }
        ]
    }

    orchestrator._ensure_product_display_search_queries(
        response,
        "Show me the best option under 80000.",
        [{"id": "17", "name": "iPhone 17", "category_name": "Electronics"}],
    )

    assert response["ui_actions"][0]["params"]["search_query"] == "iphone 17"


def test_product_display_action_gets_search_query_after_guardrail(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Here are smartwatches.",
        "intent": "product_search",
        "confidence": 0.8,
        "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["1"]}}],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="Yes, show me smartwatches.",
        retrieved_products=[{"id": 1, "name": "Amazfit Smartwatches & Fitness Bands"}],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["1"], "search_query": "smartwatches"},
        }
    ]


def test_product_comparison_action_does_not_get_search_navigation(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Here is the comparison.",
        "intent": "product_compare",
        "confidence": 0.9,
        "ui_actions": [
            {
                "action": "SHOW_COMPARISON",
                "params": {"product_ids": ["1", "2"]},
            }
        ],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="Compare iphone and oppo",
        retrieved_products=[
            {"id": 1, "name": "Apple iPhone", "brand": "Apple", "price": 79999, "stock": 5},
            {"id": 2, "name": "OPPO Phone", "brand": "OPPO", "price": 21999, "stock": 5},
        ],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {
            "action": "SHOW_COMPARISON",
            "params": {"product_ids": ["1", "2"]},
        }
    ]


def test_comparison_request_recovers_comparison_when_model_omits_action(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)

    response = {
        "response_text": "Here are two choices.",
        "intent": "product_compare",
        "confidence": 0.7,
        "ui_actions": [],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="Compare two good choices by price and rating.",
        retrieved_products=[
            {"id": 1, "name": "First Serum", "price": 800, "stock": 5},
            {"id": 2, "name": "Second Serum", "price": 900, "stock": 5},
        ],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {"action": "SHOW_COMPARISON", "params": {"product_ids": ["1", "2"]}}
    ]


def test_open_cheaper_compared_item_promotes_single_result_to_detail(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Here is the cheaper item.",
        "intent": "product_detail",
        "confidence": 0.8,
        "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["1"]}}],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="Open the cheaper of those compared beauty products.",
        retrieved_products=[{"id": 1, "name": "Daily Serum", "price": 800, "stock": 5}],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {"action": "SHOW_PRODUCT_DETAIL", "params": {"product_id": "1"}}
    ]


def test_comparison_drops_competing_product_list_and_search_navigation(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Compare these options.",
        "intent": "product_compare",
        "confidence": 0.9,
        "ui_actions": [
            {"action": "SHOW_COMPARISON", "params": {"product_ids": ["1", "2"]}},
            {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["3"], "search_query": "phones"}},
            {"action": "NAVIGATE_TO", "params": {"page": "shop?q=phones"}},
        ],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="I am confused between these phones.",
        retrieved_products=[
            {"id": 1, "name": "Phone One", "price": 10000, "stock": 5},
            {"id": 2, "name": "Phone Two", "price": 12000, "stock": 5},
            {"id": 3, "name": "Phone Three", "price": 14000, "stock": 5},
        ],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {"action": "SHOW_COMPARISON", "params": {"product_ids": ["1", "2"]}}
    ]
    assert "What matters most to you" in validated["response_text"]


def test_validated_product_response_drops_empty_filter_action(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Here are phones.",
        "intent": "product_search",
        "confidence": 0.8,
        "ui_actions": [
            {"action": "FILTER_PRODUCTS", "params": {}},
            {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["1"]}},
        ],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="show me on phone wanna phones",
        retrieved_products=[{"id": 1, "name": "Samsung Daily Phone"}],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["1"], "search_query": "phone"},
        }
    ]


def test_product_search_without_llm_action_gets_display_action(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Do you have a brand preference?",
        "intent": "product_search",
        "confidence": 0.8,
        "ui_actions": [],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="I am looking for phone",
        retrieved_products=[
            {
                "id": "phone-1",
                "name": "Samsung Daily Phone",
                "brand": "Samsung",
                "price": 9549,
                "stock": 5,
                "description": "<p>Long phone paragraph should not be spoken.</p>",
            },
            {"id": "phone-2", "name": "OPPO Active Phone", "brand": "OPPO", "price": 14199, "stock": 3},
        ],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["phone-1", "phone-2"], "search_query": "phone"},
        }
    ]
    assert "I found 2 matching products" in validated["response_text"]
    assert "Long phone paragraph" not in validated["response_text"]
