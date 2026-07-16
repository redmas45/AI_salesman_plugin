import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator


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



