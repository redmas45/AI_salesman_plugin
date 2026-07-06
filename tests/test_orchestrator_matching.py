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
    assert orchestrator._display_search_query("Only Samsung phones. I did not ask for Oppo.") == "samsung phone"


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


def test_product_detail_grounding_preserves_accessory_recommendation(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Try this phone.",
        "intent": "product_detail",
        "confidence": 0.8,
        "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="Recommend a phone and tell me what accessory I should buy with it.",
        retrieved_products=[
            {
                "id": "phone-1",
                "name": "OPPO Active Android Budget 9",
                "brand": "OPPO",
                "category_name": "electronics",
                "description": "<p>Long phone paragraph should not be spoken as HTML.</p>",
                "price": 14199,
                "stock": 5,
            }
        ],
        blocked_text="Blocked.",
    )

    assert "accessory" in validated["response_text"].lower()
    assert "case" in validated["response_text"].lower()
    assert "<p>" not in validated["response_text"]
    assert "</p>" not in validated["response_text"]
    assert validated["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["phone-1"], "search_query": "phone accessory"},
        }
    ]


def test_product_display_response_is_grounded_to_selected_rows(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "Try Bloomsbury Luxe Fiction 5 for Rs 649.",
        "intent": "product_search",
        "confidence": 0.8,
        "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["book-1"]}}],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="I asked for books.",
        retrieved_products=[
            {
                "id": "book-1",
                "name": "Penguin Luxe Self-Help & Business 4",
                "brand": "Penguin",
                "category_name": "Books Stationery",
                "description": "<p>Long catalog paragraph that should not be spoken for a search result.</p>",
                "price": 549,
                "stock": 5,
            }
        ],
        blocked_text="Blocked.",
    )

    assert "Penguin Luxe Self-Help & Business 4" in validated["response_text"]
    assert "Price: 549" in validated["response_text"]
    assert "<p>" not in validated["response_text"]
    assert "Long catalog paragraph" not in validated["response_text"]
    assert "Bloomsbury" not in validated["response_text"]
    assert "Rs 649" not in validated["response_text"]
    assert validated["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["book-1"], "search_query": "books"},
        }
    ]


def test_retrieved_products_override_false_no_match_claim(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: True)

    response = {
        "response_text": "I couldn't find watches right now.",
        "intent": "out_of_stock",
        "confidence": 0.4,
        "ui_actions": [],
    }
    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="I'm looking for watches.",
        retrieved_products=[
            {"id": 1, "name": "Amazfit Smartwatches & Fitness Bands"},
            {"id": 2, "name": "Noise Signature Smartwatches & Fitness Bands"},
        ],
        blocked_text="Blocked.",
    )

    assert validated["intent"] == "product_search"
    assert "I found 2 matching products" in validated["response_text"]
    assert validated["ui_actions"] == [
        {
            "action": "SHOW_PRODUCTS",
            "params": {"product_ids": ["1", "2"], "search_query": "watches"},
        }
    ]


def test_navigation_intent_uses_observed_interaction_links(monkeypatch):
    vertical_config = {
        "routes": {"plans": "/insurance/health"},
        "interaction_events": [
            {
                "label": "Life",
                "href": "http://localhost:5173/insurance/life",
                "origin": "http://localhost:5173",
            }
        ],
    }
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": vertical_config},
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")

    assert (
        orchestrator._navigation_page_from_transcript("policy_site", "Take me to life")
        == "insurance/life"
    )


def test_navigation_specific_route_beats_generic_plan_term(monkeypatch):
    vertical_config = {
        "routes": {"plans": "/insurance/health"},
        "interaction_events": [
            {
                "label": "Life",
                "href": "http://localhost:5173/insurance/life",
                "origin": "http://localhost:5173",
            }
        ],
    }
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": vertical_config},
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")

    assert (
        orchestrator._navigation_page_from_transcript("policy_site", "Open life insurance plans")
        == "insurance/life"
    )


def test_navigation_interest_phrase_uses_discovered_route_without_llm(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": {"routes": {"plans": "/insurance/health"}}},
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("navigation must not call LLM")),
    )

    response = orchestrator.run(
        site_id="policy_site",
        text_input="I'm interested in buying life insurances.",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={"links": [{"label": "Life", "href": "/insurance/life"}]},
    )

    assert response["intent"] == "navigate"
    assert response["response_text"] == "I'll try to open life insurance."
    assert response["ui_actions"] == [
        {"action": "NAVIGATE_TO", "params": {"page": "insurance/life"}}
    ]


def test_navigation_intent_uses_current_page_context_links(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": {"routes": {"plans": "/insurance/health"}}},
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")

    assert (
        orchestrator._navigation_page_from_transcript(
            "policy_site",
            "Open travel insurance",
            {"links": [{"label": "Travel", "href": "/insurance/travel"}]},
        )
        == "insurance/travel"
    )


def test_run_navigation_uses_current_page_context_before_llm(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": {"routes": {"plans": "/insurance/health"}}},
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("navigation must not call LLM")),
    )

    response = orchestrator.run(
        site_id="policy_site",
        text_input="Open travel insurance",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={"links": [{"label": "Travel", "href": "/insurance/travel"}]},
    )

    assert response["intent"] == "navigate"
    assert response["response_text"] == "I'll try to open travel insurance."
    assert response["ui_actions"] == [
        {"action": "NAVIGATE_TO", "params": {"page": "insurance/travel"}}
    ]


def test_run_navigation_uses_semantic_alias_for_visible_route(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": {"routes": {"plans": "/insurance/health"}}},
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("navigation must not call LLM")),
    )

    response = orchestrator.run(
        site_id="policy_site",
        text_input="Take me to the car insurance page.",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={"links": [{"label": "Motor", "href": "/insurance/motor"}]},
    )

    assert response["intent"] == "navigate"
    assert response["response_text"] == "I'll try to open car insurance."
    assert response["ui_actions"] == [
        {"action": "NAVIGATE_TO", "params": {"page": "insurance/motor"}}
    ]


def test_navigation_ignores_generic_action_name_aliases(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "actions": {
                    "NAVIGATE_TO": {"type": "navigate", "path": "/"},
                    "SHOW_ENTITIES": {"type": "navigate", "path": "/insurance/health"},
                    "CAPTURE_LEAD": {
                        "type": "navigate",
                        "path": "/",
                        "label": "Open contact or enquiry page",
                    },
                },
                "interaction_events": [
                    {
                        "label": "Home",
                        "href": "http://localhost:5173/insurance/home",
                        "origin": "http://localhost:5173",
                    }
                ],
            }
        },
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")

    routes = orchestrator._client_navigation_route_map("policy_site")

    assert "navigate-to" not in routes
    assert "show-entities" not in routes
    assert "capture-lead" not in routes
    assert (
        orchestrator._navigation_page_from_transcript(
            "policy_site",
            "Can you navigate to home insurance?",
        )
        == "insurance/home"
    )


def test_removed_navigation_action_does_not_claim_opening(monkeypatch):
    vertical_config = {
        "routes": {"plans": "/insurance/health"},
        "interaction_events": [
            {
                "label": "Life",
                "href": "http://localhost:5173/insurance/life",
                "origin": "http://localhost:5173",
            }
        ],
    }
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": vertical_config},
    )
    monkeypatch.setattr(
        "agent.guardrails._client_vertical_config",
        lambda site_id: vertical_config,
    )
    response = {
        "response_text": "Opening travel insurance plans.",
        "intent": "navigate",
        "confidence": 1.0,
        "ui_actions": [{"action": "NAVIGATE_TO", "params": {"page": "insurance/travel"}}],
    }

    validated = orchestrator._validate_agent_response(
        response,
        site_id="policy_site",
        safe_transcript="Open travel insurance",
        retrieved_products=[],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == []
    assert validated["intent"] == "navigation_unavailable"
    assert "Opening" not in validated["response_text"]
    assert "could not find" in validated["response_text"]
    assert "Life" in validated["response_text"]


def test_removed_explicit_navigation_does_not_recover_as_lead_flow(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(
        orchestrator,
        "_lead_flow_action_from_transcript",
        lambda transcript, site_id: "CAPTURE_LEAD",
    )
    monkeypatch.setattr(
        "agent.guardrails._client_vertical_config",
        lambda site_id: {"routes": {"plans": "/insurance/health"}},
    )
    response = {
        "response_text": "Opening car insurance plans.",
        "intent": "navigate",
        "confidence": 1.0,
        "ui_actions": [{"action": "NAVIGATE_TO", "params": {}}],
    }

    validated = orchestrator._validate_agent_response(
        response,
        site_id="policy_site",
        safe_transcript="Take me to the car insurance page.",
        retrieved_products=[],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == []
    assert validated["intent"] == "navigation_unavailable"
    assert "Opening" not in validated["response_text"]


def test_removed_entity_display_action_rewrites_here_are_response(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")
    monkeypatch.setattr("agent.guardrails._client_vertical_config", lambda site_id: {})
    response = {
        "response_text": "Here are matching plans for you.",
        "intent": "discovery",
        "confidence": 0.9,
        "ui_actions": [{"action": "SHOW_ENTITIES", "params": {"entity_ids": ["plan:missing"]}}],
    }

    validated = orchestrator._validate_agent_response(
        response,
        site_id="policy_site",
        safe_transcript="Show me plans",
        retrieved_products=[],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == []
    assert validated["intent"] == "display_unavailable"
    assert validated["response_text"] == "I could not verify matching records on this site right now."


def test_removed_product_display_action_rewrites_here_are_response(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr("agent.guardrails.product_exists", lambda site_id, product_id: False)
    response = {
        "response_text": "Here are the phones I found.",
        "intent": "product_compare",
        "confidence": 0.9,
        "ui_actions": [{"action": "SHOW_COMPARISON", "params": {"product_ids": ["9991", "9992"]}}],
    }

    validated = orchestrator._validate_agent_response(
        response,
        site_id="ai_kart",
        safe_transcript="Compare phones",
        retrieved_products=[],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == []
    assert validated["intent"] == "display_unavailable"
    assert validated["response_text"] == "I could not verify matching products on this site right now."


def test_pending_navigation_wording_does_not_claim_success_before_ack():
    response_text = orchestrator._neutralize_pending_action_claims(
        "Opening life insurance plans.",
        [{"action": "NAVIGATE_TO", "params": {"page": "insurance/life"}}],
    )

    assert response_text == "I'll try to open life insurance plans."


def test_pending_enriched_quote_wording_preserves_known_params_context():
    response_text = orchestrator._neutralize_pending_action_claims(
        "I have your age and city. Starting the quote flow now.",
        [{"action": "START_QUOTE", "params": {"age_of_eldest_member": "27", "city": "Pune"}}],
    )

    assert response_text == "I have your age and city. I'll try to start the quote flow now."


def test_pending_cart_wording_rewrites_past_tense_claim():
    response_text = orchestrator._neutralize_pending_action_claims(
        "Added NOVA Daily Phone to your cart.",
        [{"action": "ADD_TO_CART", "params": {"product_id": "1"}}],
    )

    assert response_text == "I'll try to add NOVA Daily Phone to your cart."


def test_missing_navigation_page_is_repaired_from_response_text(monkeypatch):
    vertical_config = {
        "routes": {"plans": "/insurance/health"},
        "interaction_events": [
            {
                "label": "Life",
                "href": "http://localhost:5173/insurance/life",
                "origin": "http://localhost:5173",
            }
        ],
    }
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")
    monkeypatch.setattr(
        "agent.guardrails._client_vertical_config",
        lambda site_id: vertical_config,
    )
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": vertical_config},
    )
    response = {
        "response_text": "Opening life insurance plans.",
        "intent": "navigate",
        "confidence": 1.0,
        "ui_actions": [{"action": "NAVIGATE_TO", "params": {}}],
    }

    validated = orchestrator._validate_agent_response(
        response,
        site_id="policy_site",
        safe_transcript="Yeah, open it. I'm still waiting. Open it.",
        retrieved_products=[],
        blocked_text="Blocked.",
    )

    assert validated["ui_actions"] == [
        {"action": "NAVIGATE_TO", "params": {"page": "insurance/life"}}
    ]
    assert validated["response_text"] == "I'll try to open life insurance plans."


def test_validate_agent_response_keeps_navigation_from_current_page_context(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: False)
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")
    monkeypatch.setattr(
        "agent.guardrails._client_vertical_config",
        lambda site_id: {"routes": {"plans": "/insurance/health"}},
    )
    response = {
        "response_text": "Opening travel insurance.",
        "intent": "navigate",
        "confidence": 1.0,
        "ui_actions": [{"action": "NAVIGATE_TO", "params": {"page": "travel"}}],
    }

    validated = orchestrator._validate_agent_response(
        response,
        site_id="policy_site",
        safe_transcript="Open travel insurance",
        retrieved_products=[],
        blocked_text="Blocked.",
        page_context={"links": [{"label": "Travel", "href": "/insurance/travel"}]},
    )

    assert validated["ui_actions"] == [
        {"action": "NAVIGATE_TO", "params": {"page": "insurance/travel"}}
    ]
    assert validated["response_text"] == "I'll try to open travel insurance."


def test_quote_flow_intent_is_not_stolen_by_show_quote_navigation(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(
        "agent.capabilities.get_allowed_actions",
        lambda site_id: {"START_QUOTE", "NAVIGATE_TO"},
    )

    assert orchestrator._navigation_page_from_transcript("policy_site", "Show me quotes") == ""
    assert orchestrator._navigation_page_from_transcript("policy_site", "Open quote page") == "quote"


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


def test_run_recovers_insurance_quote_action_when_llm_omits_ui_action(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "actions": {
                    "START_QUOTE": {
                        "type": "sequence",
                        "fields": ["age_of_eldest_member"],
                        "required_fields": ["age_of_eldest_member"],
                        "field_schema": [
                            {"param": "age_of_eldest_member", "label": "Age of eldest member", "type": "number", "required": True},
                        ],
                    }
                }
            }
        },
    )
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
    assert result["ui_actions"] == [{"action": "START_QUOTE", "params": {"age_of_eldest_member": "27"}}]


def test_insurance_quote_params_are_extracted_from_natural_language(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "actions": {
                    "START_QUOTE": {
                        "type": "sequence",
                        "fields": ["age_of_eldest_member", "city"],
                        "required_fields": ["age_of_eldest_member", "city"],
                        "field_schema": [
                            {"param": "age_of_eldest_member", "label": "Age of eldest member", "type": "number", "required": True},
                            {"param": "city", "label": "City", "type": "text", "required": True},
                        ],
                    }
                }
            }
        },
    )

    actions = orchestrator._enrich_action_params_from_context(
        "policy_site",
        "I am 27yo old male looking for coverage for myself. I live in riverton.",
        [],
        [{"action": "START_QUOTE", "params": {}}],
    )

    assert actions == [
        {"action": "START_QUOTE", "params": {"age_of_eldest_member": "27", "city": "Riverton"}}
    ]


def test_action_params_are_extracted_from_discovered_schema(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "actions": {
                    "RUN_CALCULATOR": {
                        "type": "sequence",
                        "fields": ["start_location", "end_location", "service_date", "party_size"],
                        "required_fields": ["start_location", "end_location", "service_date", "party_size"],
                        "required_fields_known": True,
                        "field_schema": [
                            {"param": "start_location", "label": "Start location", "type": "text", "required": True},
                            {"param": "end_location", "label": "End location", "type": "text", "required": True},
                            {"param": "service_date", "label": "Service date", "type": "date", "required": True},
                            {"param": "party_size", "label": "Party size", "type": "number", "required": True},
                        ],
                    }
                }
            }
        },
    )

    actions = orchestrator._enrich_action_params_from_context(
        "schema_site",
        "Please run it with start location: Sample start location; end location: Sample end location; service date: 2026-08-15; party size: 2.",
        [],
        [{"action": "RUN_CALCULATOR", "params": {}}],
    )

    assert actions == [
        {
            "action": "RUN_CALCULATOR",
            "params": {
                "start_location": "Sample start location",
                "end_location": "Sample end location",
                "service_date": "2026-08-15",
                "party_size": "2",
            },
        }
    ]


def test_stale_quote_param_question_is_rewritten_when_action_has_params():
    response_text = orchestrator._align_response_with_enriched_action_params(
        "Let's start the quote process. I'll need to confirm the age of the eldest member.",
        [{"action": "START_QUOTE", "params": {"age_of_eldest_member": "27", "city": "Riverton"}}],
    )

    assert response_text == "I have your age and city. Starting the quote flow now."


def test_insurance_quote_city_from_history_is_not_asked_again(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    vertical_config = {
        "actions": {
            "START_QUOTE": {
                "type": "sequence",
                "fields": ["age_of_eldest_member", "city"],
                "required_fields": ["age_of_eldest_member", "city"],
                "required_fields_known": True,
            }
        }
    }
    monkeypatch.setattr(
        "agent.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "insurance", "vertical_config_json": vertical_config},
    )
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {"vertical_config": vertical_config},
    )
    monkeypatch.setattr("agent.capabilities.admin_db.get_readiness_report", lambda site_id: None)

    actions = orchestrator._enrich_action_params_from_context(
        "policy_site",
        "I need coverage for myself. I live in Riverton.",
        [],
        [{"action": "START_QUOTE", "params": {}}],
    )
    report = orchestrator._apply_capability_filter_result("policy_site", actions)

    assert report["actions"] == []
    assert report["removed_actions"][0]["missing_params"] == ("age_of_eldest_member",)
    assert "age of the eldest member" in report["removed_actions"][0]["question"].lower()


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


def test_lead_flow_single_current_action_handles_generic_request(monkeypatch):
    class EmptyVertical:
        action_types = set()

    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "generic")
    monkeypatch.setattr("agent.verticals.registry.get_vertical", lambda vertical_key: EmptyVertical())
    monkeypatch.setattr("agent.capabilities.get_allowed_actions", lambda site_id: {"REQUEST_ESTIMATE"})
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "actions": {
                    "REQUEST_ESTIMATE": {
                        "label": "Request estimate",
                        "required_fields": ["request_scope"],
                        "field_schema": [
                            {"param": "request_scope", "label": "Request scope", "type": "text", "required": True}
                        ],
                    }
                }
            }
        },
    )

    action = orchestrator._lead_flow_action_from_transcript(
        "I need help with this service.",
        "schema_site",
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
