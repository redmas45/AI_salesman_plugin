import json

from fastapi.testclient import TestClient

from agent import llm, orchestrator
from agent.context_budget import build_context_messages, summarize_turns
from agent.prompts import generic as generic_prompt
from agent.relevance import (
    SCOPE_BUYING_GUIDANCE,
    SCOPE_GROUNDED_FACT,
    SCOPE_UNSUPPORTED,
    answer_scope_for,
    bounded_unsupported_response,
    is_safe_cache_response,
    should_bypass_answer_cache,
)
from agent.tenant_isolation import build_tenant_isolation_audit
from api.main import app


def test_relevance_bounds_deep_offsite_question_without_source_support() -> None:
    response = bounded_unsupported_response(
        "Compare the processor architecture of these two phones.",
        [{"id": "phone-1", "title": "Phone", "summary": "Published specs include price and camera."}],
    )

    assert "not in the site data" in response
    assert answer_scope_for("processor architecture details", []) == SCOPE_UNSUPPORTED


def test_relevance_allows_deep_detail_when_retrieved_source_contains_it() -> None:
    scope = answer_scope_for(
        "Compare the processor architecture.",
        [{"id": "phone-1", "summary": "Processor architecture: custom ARM cores."}],
        [],
    )

    assert scope == SCOPE_GROUNDED_FACT


def test_side_effect_requests_bypass_cache() -> None:
    assert should_bypass_answer_cache("Add this plan to my cart.")
    assert should_bypass_answer_cache("I want to start a quote for myself.")
    assert not should_bypass_answer_cache("Why should I buy this plan?")


def test_safe_cache_write_policy_allows_grounded_answer_and_blocks_actions() -> None:
    safe_result = {
        "response_text": "This plan has cashless hospitalization in the website data.",
        "answer_scope": SCOPE_GROUNDED_FACT,
        "confidence": 0.9,
        "ui_actions": [{"action": "SHOW_ENTITIES", "params": {"entity_ids": ["plan:1"]}}],
    }
    action_result = {
        **safe_result,
        "answer_scope": "website_action",
        "ui_actions": [{"action": "START_QUOTE", "params": {"city": "Pune"}}],
    }

    assert is_safe_cache_response("What does this plan cover?", safe_result, [{"id": "plan:1"}])
    assert not is_safe_cache_response("Start a quote for me", action_result, [{"id": "plan:1"}])


def test_context_budget_uses_summary_and_recent_messages_only() -> None:
    history = [
        {"role": "user", "content": f"user {index}"}
        if index % 2
        else {"role": "assistant", "content": f"assistant {index}"}
        for index in range(10)
    ]

    messages = build_context_messages(history, session_summary="User wants health cover.", max_recent_messages=3)

    assert messages[0]["role"] == "assistant"
    assert "Session memory summary" in messages[0]["content"]
    assert [message["content"] for message in messages[1:]] == ["user 7", "assistant 8", "user 9"]


def test_session_summary_is_deterministic_and_bounded() -> None:
    summary = summarize_turns(
        "User: Wants self cover",
        [{"role": "user", "content": "I live in Pune"}],
        "I am 27 years old.",
        "I have your city and age.",
    )

    assert "User: Wants self cover" in summary
    assert "User: I am 27 years old." in summary
    assert "Maya: I have your city and age." in summary
    assert len(summary) <= 1200


def test_orchestrator_cache_hit_skips_retrieval_and_llm(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(
        orchestrator,
        "lookup_answer_cache",
        lambda site_id, question: {
            "answer_text": "The website says this plan includes cashless hospitalization.",
            "answer_scope": SCOPE_GROUNDED_FACT,
            "confidence": 0.95,
            "ui_actions": [{"action": "SHOW_ENTITIES", "params": {"entity_ids": ["plan:1"]}}],
            "match_type": "exact",
            "match_score": 1.0,
            "data_version": 3,
            "source_ids": ["plan:1"],
            "source_urls": [],
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "_retrieve_context",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("cache hit should skip RAG")),
    )
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("cache hit should skip LLM")),
    )

    result = orchestrator.run(
        site_id="policy_site",
        text_input="What does this plan cover?",
        audio_bytes=None,
        audio_filename="test.txt",
        skip_tts=True,
        conversation_history=[],
        page_context={},
    )

    assert result["intent"] == "discovery"
    assert result["answer_scope"] == SCOPE_GROUNDED_FACT
    assert result["retrieval"]["cache_hit"] is True
    assert result["ui_actions"] == [{"action": "SHOW_ENTITIES", "params": {"entity_ids": ["plan:1"]}}]


def test_orchestrator_stores_safe_source_answer(monkeypatch) -> None:
    captured = {}

    def fake_store(site_id: str, **kwargs):
        captured.update({"site_id": site_id, **kwargs})
        return {"data_version": 7}

    monkeypatch.setattr(orchestrator, "store_answer_cache", fake_store)
    evidence = {}

    orchestrator._maybe_store_answer_cache(
        "policy_site",
        "What does this plan cover?",
        {
            "response_text": "The website says this plan includes cashless hospitalization.",
            "answer_scope": SCOPE_GROUNDED_FACT,
            "confidence": 0.9,
            "ui_actions": [{"action": "SHOW_ENTITIES", "params": {"entity_ids": ["plan:1"]}}],
        },
        [{"id": "plan:1", "url": "https://example.com/plan"}],
        evidence,
    )

    assert captured["site_id"] == "policy_site"
    assert captured["source_ids"] == ["plan:1"]
    assert captured["source_urls"] == ["https://example.com/plan"]
    assert evidence["cache_write"] == "stored"
    assert evidence["cache_data_version"] == 7


def test_llm_uses_session_summary_and_parses_answer_scope(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(llm, "get_client_vertical_key", lambda site_id: "insurance")
    monkeypatch.setattr(generic_prompt, "get_allowed_actions", lambda site_id: {"SHOW_ENTITIES"})
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")
    monkeypatch.setattr(generic_prompt, "capability_prompt_context", lambda site_id: "")

    def fake_call(system_prompt: str, messages: list[dict]):
        captured["messages"] = messages
        return json.dumps(
            {
                "response_text": "This is source-backed.",
                "intent": "discovery",
                "confidence": 0.9,
                "answer_scope": SCOPE_BUYING_GUIDANCE,
                "ui_actions": [],
            }
        )

    monkeypatch.setattr(llm, "_call_llm", fake_call)

    response = llm.generate_response(
        "policy_site",
        "Which plan is better?",
        [{"id": "plan:1", "title": "Plan"}],
        conversation_history=[{"role": "user", "content": "I live in Pune."}],
        session_summary="User is 27 and wants self cover.",
    )

    assert response["answer_scope"] == SCOPE_BUYING_GUIDANCE
    assert "Session memory summary" in captured["messages"][0]["content"]
    assert captured["messages"][-1]["content"] == "Which plan is better?"


def test_generic_prompt_declares_answer_scope_and_sales_relevance(monkeypatch) -> None:
    monkeypatch.setattr(generic_prompt, "get_allowed_actions", lambda site_id: {"SHOW_ENTITIES"})
    monkeypatch.setattr(generic_prompt, "prompt_profile_context", lambda site_id: "")

    prompt = generic_prompt.build_generic_system_prompt(
        site_id="policy_site",
        vertical_key="insurance",
        knowledge_context='[ID:"plan:1"] Health Plan | Type: insurance_plan',
    )

    assert "## Sales Relevance And Grounding" in prompt
    assert "answer_scope" in prompt
    assert "unsupported_or_offsite" in prompt
    assert "Do not expose chain-of-thought" in prompt
    assert "BROWSER_ACTION_RESULTS" in prompt
    assert "browser execution proof" in prompt


def test_tenant_isolation_audit_checks_answer_cache_scope() -> None:
    audit = build_tenant_isolation_audit(
        site_id="site_a",
        client={"site_id": "site_a"},
        runtime_config={
            "site_id": "site_a",
            "install": {"widget_script": "https://hub.example.com/mayabot.js?site=site_a"},
        },
        prompt_profile={"profile": {"id": "profile_1", "site_id": "site_a"}, "versions": []},
        knowledge={"stats": {}, "items": []},
        answer_cache={"site_id": "site_b", "items": []},
    )

    failed = {row["key"] for row in audit["checks"] if row["status"] == "failed"}

    assert audit["status"] == "failed"
    assert "answer_cache_tenant_schema" in failed


def test_crm_answer_cache_endpoint_returns_tenant_summary(monkeypatch) -> None:
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    monkeypatch.setattr(
        "db.answer_cache.answer_cache_summary",
        lambda site_id, limit=20: {
            "site_id": site_id,
            "data_version": 4,
            "total": 2,
            "fresh": 1,
            "stale": 1,
            "hits": 5,
            "estimated_tokens_saved": 120,
            "items": [{"question": "What does this cover?", "hit_count": 5}],
        },
    )

    res = TestClient(app).get(
        "/v1/admin/clients/policy_site/answer-cache",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["answer_cache"]["site_id"] == "policy_site"
    assert res.json()["answer_cache"]["hits"] == 5
