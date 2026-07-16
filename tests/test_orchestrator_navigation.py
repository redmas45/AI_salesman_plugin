import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator


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


def test_navigation_leaves_product_discovery_and_detail_requests_to_sales_pipeline(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "routes": {
                    "shop": "/shop",
                    "beauty": "/shop?category=beauty-personal-care",
                }
            }
        },
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")

    assert orchestrator._navigation_page_from_transcript(
        "ai_kart",
        "Show me well-rated beauty products under Rs 2,000.",
    ) == ""
    assert orchestrator._navigation_page_from_transcript(
        "ai_kart",
        "My skin is dry. Show suitable moisturisers or serums from this store.",
    ) == ""
    assert orchestrator._navigation_page_from_transcript(
        "ai_kart",
        "Now show me moisturiser products rather than just the section.",
    ) == ""
    assert orchestrator._navigation_page_from_transcript(
        "ai_kart",
        "Show college laptops under INR 60,000 from the actual catalog.",
    ) == ""
    assert orchestrator._navigation_page_from_transcript(
        "ai_kart",
        "Go back to phones and show me details of the cheaper shortlisted one.",
    ) == ""
    assert orchestrator._navigation_page_from_transcript(
        "ai_kart",
        "Take me to the Beauty section so I can browse myself.",
    ) == "shop?category=beauty-personal-care"


def test_navigation_resolves_returns_to_discovered_shipping_page(monkeypatch):
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator,
        "get_client_detail",
        lambda site_id: {
            "vertical_config": {
                "routes": {"shipping-and-returns": "/shipping-and-returns"}
            }
        },
    )
    monkeypatch.setattr(orchestrator, "_lead_flow_action_from_transcript", lambda transcript, site_id: "")

    assert orchestrator._navigation_page_from_transcript(
        "ai_kart",
        "What does this website say about returns, and can you open that page?",
    ) == "shipping-and-returns"
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
