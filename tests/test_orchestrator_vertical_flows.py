import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import orchestrator


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

