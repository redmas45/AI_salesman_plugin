import pytest

from agent.adapters.shopify import ShopifyAdapter
from agent.adapters.woocommerce import WooCommerceAdapter
from agent.adapter_repair import build_action_repair_proposals
from agent.extractor import extract_selectors_from_html
from agent.client_initialization import run_widget_initialization
from agent.scanner import (
    SiteCapability,
    _barrier_capabilities,
    _check_cart,
    _check_checkout,
    _client_hook_capabilities,
    _flow_capabilities,
    _is_client_hook_adapter,
    _rehearsal_capabilities,
    _vertical_data_capabilities,
    _vertical_expected_action_capabilities,
)
from agent.tenant_isolation import build_tenant_isolation_audit
from agent.verticals.registry import list_verticals
from db.admin import _validated_settings


def test_client_hook_requires_explicit_adapter_name() -> None:
    assert not _is_client_hook_adapter("generic_adapter.js", "ai_kart")
    assert _is_client_hook_adapter("verified-client-hook.js", "ai_kart")
    caps = {cap.name: cap for cap in _client_hook_capabilities("verified-client-hook.js")}
    assert caps["cart"].supported
    assert caps["checkout"].supported


def test_insurance_readiness_uses_vertical_data_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.knowledge_stats",
        lambda site_id: {"active_items": 19, "entity_types": 3, "missing_embeddings": 0},
    )

    caps = {cap.name: cap for cap in _vertical_data_capabilities("policy_site", "insurance")}

    assert caps["plans"].supported
    assert caps["groups"].supported
    assert caps["vectors"].supported
    assert "cart" not in caps
    assert "checkout" not in caps


def test_vertical_expected_action_readiness_flags_mapped_and_missing_actions(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.knowledge_stats",
        lambda site_id: {"active_items": 5, "entity_types": 1, "missing_embeddings": 0},
    )

    caps = {
        cap.name: cap
        for cap in _vertical_expected_action_capabilities(
            "builder_demo",
            "construction",
            {
                "actions": {
                    "REQUEST_ESTIMATE": {"type": "form"},
                    "OPEN_PROJECTS": {"type": "navigate", "path": "/projects"},
                }
            },
        )
    }

    assert caps["domain_action_coverage"].supported is False
    assert "Missing:" in caps["domain_action_coverage"].evidence
    assert caps["expected_action:SHOW_ENTITIES"].supported
    assert "5 active services" in caps["expected_action:SHOW_ENTITIES"].evidence
    assert caps["expected_action:REQUEST_ESTIMATE"].supported
    assert caps["expected_action:OPEN_PROJECTS"].supported
    assert not caps["expected_action:REQUEST_SITE_VISIT"].supported
    assert "not mapped" in caps["expected_action:REQUEST_SITE_VISIT"].evidence


def test_ecommerce_expected_action_readiness_uses_product_rendering(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.tenant_catalog_stats",
        lambda site_id: {"active_products": 12, "total_products": 12, "missing_embeddings": 0},
    )

    caps = {
        cap.name: cap
        for cap in _vertical_expected_action_capabilities(
            "ai_kart",
            "ecommerce",
            {"actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}}},
        )
    }

    assert caps["expected_action:SHOW_PRODUCTS"].supported
    assert "AI Hub product rendering" in caps["expected_action:SHOW_PRODUCTS"].evidence
    assert caps["expected_action:SHOW_COMPARISON"].supported
    assert caps["expected_action:SORT_PRODUCTS"].supported
    assert caps["expected_action:FILTER_PRODUCTS"].supported
    assert caps["expected_action:ADD_TO_CART"].supported
    assert not caps["expected_action:CHECKOUT"].supported
    assert "Missing: CHECKOUT" in caps["domain_action_coverage"].evidence

    caps_with_checkout = {
        cap.name: cap
        for cap in _vertical_expected_action_capabilities(
            "ai_kart",
            "ecommerce",
            {"actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}}},
            [SiteCapability("checkout", True, 0.4, "Checkout page at https://shop.example.com/checkout")],
        )
    }

    assert caps_with_checkout["expected_action:CHECKOUT"].supported
    assert "detected checkout capability" in caps_with_checkout["expected_action:CHECKOUT"].evidence
    assert caps_with_checkout["domain_action_coverage"].supported


def test_auth_barrier_readiness_is_supported_when_handoff_policy_exists() -> None:
    caps = _barrier_capabilities(
        {
            "barriers": {
                "summary": {"total": 1, "high": 1, "medium": 0, "keys": ["auth_required"]},
                "findings": [
                    {
                        "key": "auth_required",
                        "severity": "high",
                        "handling": "Require login before quote flow.",
                    }
                ],
            }
        },
        "insurance",
    )

    assert caps[0].name == "flow_barriers"
    assert caps[0].supported is True
    assert caps[0].blocking is False
    assert "handoff policy" in caps[0].evidence


@pytest.mark.asyncio
async def test_custom_cart_probe_accepts_html_cart_page(monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    async def fake_probe(client, url: str, *, method: str = "GET", accept: str = "application/json"):
        calls.append({"url": url, "method": method, "accept": accept})
        return 200, "", {}

    monkeypatch.setattr("agent.scanner._probe_url", fake_probe)

    cap = await _check_cart("https://shop.example.com", "custom", object())

    assert cap.supported
    assert "Cart page" in cap.evidence
    assert calls == [{"url": "https://shop.example.com/cart", "method": "HEAD", "accept": "text/html"}]


@pytest.mark.asyncio
async def test_custom_checkout_probe_requests_html_accept(monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    async def fake_probe(client, url: str, *, method: str = "GET", accept: str = "application/json"):
        calls.append({"url": url, "method": method, "accept": accept})
        return 200, "", {}

    monkeypatch.setattr("agent.scanner._probe_url", fake_probe)

    cap = await _check_checkout("https://shop.example.com", "custom", object())

    assert cap.supported
    assert calls == [{"url": "https://shop.example.com/checkout", "method": "HEAD", "accept": "text/html"}]


def test_flow_graph_uses_generated_adapter_actions_for_js_static_gap() -> None:
    caps = {
        cap.name: cap
        for cap in _flow_capabilities(
            {
                "actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}},
                "flow": {
                    "engine": "http_fallback",
                    "summary": {"pages": 6, "actions": 0},
                    "prompt_suggestions": [],
                },
            }
        )
    }

    assert caps["flow_graph"].supported
    assert "generated adapter exposes 1 runtime action" in caps["flow_graph"].evidence


def test_empty_rehearsal_uses_validated_adapter_actions_for_js_static_gap() -> None:
    caps = {
        cap.name: cap
        for cap in _rehearsal_capabilities(
            {
                "actions": {"ADD_TO_CART": {"type": "click", "selector": "button.add"}},
                "validation": {"actions": {"ADD_TO_CART": {"supported": True, "status": "ok"}}},
                "rehearsal": {
                    "engine": "empty",
                    "summary": {"total": 0, "supported": 0, "blocked": 0, "needs_confirmation": 0},
                },
            }
        )
    }

    assert caps["flow_rehearsal"].supported
    assert "browser validation supports 1/1 adapter action" in caps["flow_rehearsal"].evidence
    assert caps["flow_confirmation_policy"].supported


def test_vertical_expected_action_readiness_covers_every_registered_vertical(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.scanner.knowledge_stats",
        lambda site_id: {"active_items": 0, "entity_types": 0, "missing_embeddings": 0},
    )

    for vertical in list_verticals():
        caps = {
            cap.name: cap
            for cap in _vertical_expected_action_capabilities("demo_site", vertical.key, {"actions": {}})
        }

        assert "domain_action_coverage" in caps
        for action in vertical.action_types:
            assert f"expected_action:{action}" in caps


def test_auto_initialization_runs_readiness_stage(monkeypatch) -> None:
    saved_reports = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._crawl_stage",
        lambda *args, **kwargs: {"name": "crawl", "status": "ok", "message": "done"},
    )
    monkeypatch.setattr(
        "agent.client_initialization._flow_stage",
        lambda *args, **kwargs: (
            {"summary": {"pages": 2}},
            {"name": "flow_discovery", "status": "ok", "message": "done"},
        ),
    )
    monkeypatch.setattr(
        "agent.client_initialization._rehearsal_stage",
        lambda *args, **kwargs: (
            {"summary": {"verified": 1}},
            {"name": "flow_rehearsal", "status": "ok", "message": "done"},
        ),
    )
    monkeypatch.setattr(
        "agent.client_initialization._regression_stage",
        lambda *args, **kwargs: {"name": "flow_regression", "status": "ok", "message": "done"},
    )
    monkeypatch.setattr(
        "agent.client_initialization._readiness_stage",
        lambda *args, **kwargs: {"name": "readiness_scan", "status": "ok", "message": "done"},
    )

    report = run_widget_initialization(
        "policy_site",
        "https://policy.example.com",
        vertical_key="insurance",
        run_crawl=True,
        run_flow=True,
        run_rehearsal=True,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=True,
    )

    assert report["status"] == "ok"
    assert [stage["name"] for stage in report["stages"]] == [
        "crawl",
        "flow_discovery",
        "flow_rehearsal",
        "flow_regression",
        "readiness_scan",
    ]
    assert saved_reports[0]["status"] == "running"


def test_auto_initialization_persists_live_stage_progress(monkeypatch) -> None:
    saved_reports = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._crawl_stage",
        lambda *args, **kwargs: {"name": "crawl", "status": "ok", "message": "crawl done"},
    )
    monkeypatch.setattr(
        "agent.client_initialization._readiness_stage",
        lambda *args, **kwargs: {"name": "readiness_scan", "status": "ok", "message": "ready"},
    )

    report = run_widget_initialization(
        "policy_site",
        "https://policy.example.com",
        vertical_key="insurance",
        run_crawl=True,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=True,
    )

    running_crawl = next(
        saved
        for saved in saved_reports
        if saved.get("stages") and saved["stages"][-1]["name"] == "crawl" and saved["stages"][-1]["status"] == "running"
    )
    completed_crawl = next(
        saved
        for saved in saved_reports
        if saved.get("stages") and saved["stages"][-1]["name"] == "crawl" and saved["stages"][-1]["status"] == "ok"
    )
    running_readiness = next(
        saved
        for saved in saved_reports
        if saved.get("stages")
        and saved["stages"][-1]["name"] == "readiness_scan"
        and saved["stages"][-1]["status"] == "running"
    )

    assert report["status"] == "ok"
    assert running_crawl["stages"][-1]["completed_at"] == ""
    assert running_crawl["stages"][-1]["started_at"]
    assert completed_crawl["stages"][-1]["message"] == "crawl done"
    assert running_readiness["stages"][0]["status"] == "ok"


def test_auto_initialization_stops_when_cancel_requested(monkeypatch) -> None:
    from agent import client_initialization

    saved_reports = []
    cancel_requested = {"value": False}

    monkeypatch.setattr(client_initialization, "_save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr(client_initialization, "_client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(client_initialization.admin_db, "setup_cancel_requested", lambda site_id, run_id="": cancel_requested["value"])
    monkeypatch.setattr(client_initialization.admin_db, "update_client_crawl_status", lambda *args, **kwargs: None)

    def fake_crawl(*args, **kwargs):
        cancel_requested["value"] = True
        return {"name": "crawl", "status": "ok", "message": "crawl done"}

    monkeypatch.setattr(client_initialization, "_crawl_stage", fake_crawl)
    monkeypatch.setattr(
        client_initialization,
        "_readiness_stage",
        lambda *args, **kwargs: {"name": "readiness_scan", "status": "ok", "message": "should not run"},
    )

    report = run_widget_initialization(
        "policy_site",
        "https://policy.example.com",
        vertical_key="insurance",
        run_crawl=True,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=True,
    )

    assert report["status"] == "canceled"
    assert report["error"] == "Setup run canceled by admin."
    assert [stage["name"] for stage in report["stages"]] == ["crawl", "setup_stopped"]
    assert saved_reports[-1]["run_id"]
    assert saved_reports[-1]["timeout_seconds"] > 0


def test_initialization_save_does_not_overwrite_terminal_same_run(monkeypatch) -> None:
    from db import clients as clients_db

    writes = []
    monkeypatch.setattr(
        clients_db,
        "_client_vertical_config",
        lambda site_id: {"initialization": {"status": "timed_out", "run_id": "run-1", "error": "old timeout"}},
    )
    monkeypatch.setattr(clients_db, "_write_client_vertical_config", lambda site_id, vertical_config: writes.append(vertical_config))
    monkeypatch.setattr(clients_db, "get_client_detail", lambda site_id: {"site_id": site_id, "status": "live"})

    result = clients_db.save_client_initialization_report(
        "demo_site",
        {
            "status": "running",
            "run_id": "run-1",
            "site_id": "demo_site",
            "stages": [{"name": "crawl", "status": "ok", "message": "late write"}],
        },
    )

    assert result == {"site_id": "demo_site", "status": "live"}
    assert writes == []


def test_auto_initialization_runs_assistant_smoke_stage_when_requested(monkeypatch) -> None:
    saved_reports = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: saved_reports.append(report))
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._assistant_smoke_stage",
        lambda *args, **kwargs: {
            "name": "assistant_smoke_tests",
            "status": "ok",
            "message": "2/2 assistant smoke tests passed.",
            "total": 2,
            "passed": 2,
            "failed": 0,
        },
    )

    report = run_widget_initialization(
        "ai_kart",
        "https://shop.example.com",
        vertical_key="ecommerce",
        run_crawl=False,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=False,
        run_smoke_tests=True,
    )

    running_smoke = next(
        saved
        for saved in saved_reports
        if saved.get("stages")
        and saved["stages"][-1]["name"] == "assistant_smoke_tests"
        and saved["stages"][-1]["status"] == "running"
    )

    assert report["status"] == "ok"
    assert [stage["name"] for stage in report["stages"]] == ["assistant_smoke_tests"]
    assert running_smoke["stages"][-1]["message"] == "Assistant prompt smoke tests are running."


def test_auto_initialization_clears_setup_when_only_prompt_checks_need_repair(monkeypatch) -> None:
    setup_updates = []

    monkeypatch.setattr("agent.client_initialization._save_report", lambda site_id, report: None)
    monkeypatch.setattr("agent.client_initialization._client_detail", lambda site_id: {"site_id": site_id, "vertical_config": {}})
    monkeypatch.setattr(
        "agent.client_initialization._crawl_stage",
        lambda *args, **kwargs: {"name": "crawl", "status": "ok", "message": "Content crawl completed."},
    )
    monkeypatch.setattr(
        "agent.client_initialization._assistant_smoke_stage",
        lambda *args, **kwargs: {
            "name": "assistant_smoke_tests",
            "status": "failed",
            "message": "0/1 assistant smoke tests passed.",
            "total": 1,
            "passed": 0,
            "failed": 1,
        },
    )
    monkeypatch.setattr(
        "agent.client_initialization.admin_db.update_client_setup_status",
        lambda site_id, **kwargs: setup_updates.append((site_id, kwargs)),
    )

    report = run_widget_initialization(
        "ai_kart",
        "https://shop.example.com",
        vertical_key="ecommerce",
        run_crawl=True,
        run_flow=False,
        run_rehearsal=False,
        crawl_max_pages=5,
        crawl_max_depth=2,
        run_readiness=False,
        run_smoke_tests=True,
    )

    assert report["status"] == "partial"
    assert setup_updates
    assert setup_updates[-1][0] == "ai_kart"
    assert setup_updates[-1][1]["needs_setup"] is False


def test_operation_status_does_not_mark_setup_failed_for_prompt_repair_only() -> None:
    from api import crm

    operation_status = crm._client_operation_status(
        {
            "site_id": "ai_kart",
            "vertical_config": {
                "initialization": {
                    "status": "partial",
                    "started_at": "2026-07-06T10:00:00+00:00",
                    "completed_at": "2026-07-06T10:05:00+00:00",
                    "duration_ms": 300000,
                    "stages": [
                        {"name": "crawl", "status": "ok", "message": "Content crawl completed."},
                        {"name": "readiness_scan", "status": "ok", "message": "Readiness scan completed."},
                        {
                            "name": "assistant_smoke_tests",
                            "status": "failed",
                            "message": "0/1 assistant smoke tests passed.",
                            "total": 1,
                            "passed": 0,
                            "failed": 1,
                        },
                    ],
                }
            },
        }
    )

    integration = operation_status["operations"]["integration"]

    assert integration["status"] == "complete"
    assert "Prompt checks found repair items" in integration["message"]
    assert integration["stages"][2]["status"] == "failed"


def test_assistant_smoke_cases_cover_registered_verticals() -> None:
    from agent import client_initialization

    generic_names = {case["name"] for case in client_initialization._assistant_smoke_cases("generic")}
    domain_specific = {vertical.key for vertical in list_verticals()} - {"generic"}

    for vertical in list_verticals():
        cases = client_initialization._assistant_smoke_cases(vertical.key)

        assert len(cases) >= 2
        assert all(str(case.get("prompt") or "").strip() for case in cases)
        assert all(case.get("expected_actions") for case in cases)
        if vertical.key in domain_specific:
            assert {case["name"] for case in cases} != generic_names


def test_assistant_smoke_cases_include_required_action_schema(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "vertical_config": {
                "actions": {
                    "RUN_CALCULATOR": {
                        "type": "sequence",
                        "fields": ["primary_value", "secondary_value", "requested_date", "quantity"],
                        "required_fields": ["primary_value", "secondary_value", "requested_date", "quantity"],
                        "required_fields_known": True,
                        "field_schema": [
                            {"param": "primary_value", "label": "Primary value", "type": "text", "required": True},
                            {"param": "secondary_value", "label": "Secondary value", "type": "text", "required": True},
                            {"param": "requested_date", "label": "Requested date", "type": "date", "required": True},
                            {"param": "quantity", "label": "Quantity", "type": "number", "required": True},
                        ],
                    }
                }
            },
        },
    )

    cases = client_initialization._assistant_smoke_cases("schema_demo", "generic")
    availability_case = next(case for case in cases if "RUN_CALCULATOR" in case["expected_actions"])

    assert availability_case["schema_enriched"] is True
    assert "primary value: Sample primary value" in availability_case["prompt"]
    assert "secondary value: Sample secondary value" in availability_case["prompt"]
    assert "requested date: 2026-08-15" in availability_case["prompt"]
    assert "quantity: 2" in availability_case["prompt"]


def test_assistant_smoke_cases_skip_credential_based_result_contract(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "vertical_config": {
                "actions": {
                    "FILTER_PRODUCTS": {
                        "type": "form",
                        "form": "form.login",
                        "input": "input[name='email']",
                        "submit": "button.login",
                        "required_fields": ["email", "password"],
                        "required_fields_known": True,
                        "field_schema": [
                            {"param": "email", "label": "Email", "type": "email", "required": True},
                            {"param": "password", "label": "Password", "type": "password", "required": True},
                        ],
                    }
                }
            },
        },
    )

    cases = client_initialization._assistant_smoke_cases("schema_demo", "ecommerce")

    assert all("FILTER_PRODUCTS" not in case["expected_actions"] for case in cases)
    assert [case["name"] for case in cases][:2] == [
        "compare_apple_samsung_phone",
        "sort_phones_low_to_high",
    ]


def test_assistant_smoke_stage_passes_when_expected_actions_return(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "A protective case is a useful accessory to buy with the phone.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        response_text = (
            "Apple and Samsung phones are both available to compare."
            if action == "SHOW_COMPARISON"
            else "Here is a useful source-backed answer."
        )
        return {
            "response_text": response_text,
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "ok"
    assert stage["passed"] == 3
    assert stage["failed"] == 0
    assert stage["tests"][0]["matched_actions"] == ["SHOW_COMPARISON"]
    assert stage["tests"][0]["matched_response_terms_all"] == ["apple", "samsung"]
    assert stage["tests"][0]["display_action_evidence"][0]["id_count"] == 2
    assert stage["tests"][0]["failure_kind"] == ""
    assert stage["tests"][0]["recommended_fix"] == ""
    assert stage["tests"][2]["matched_response_terms"] == ["accessory", "case"]


def test_assistant_smoke_stage_fails_shallow_named_comparison(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "A protective case is a useful accessory to buy with the phone.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        return {
            "response_text": "Here is a useful source-backed comparison.",
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "failed"
    assert stage["tests"][0]["name"] == "compare_apple_samsung_phone"
    assert stage["tests"][0]["failure_kind"] == "missing_response_terms"
    assert stage["tests"][0]["matched_actions"] == ["SHOW_COMPARISON"]
    assert stage["tests"][0]["expected_response_terms_all"] == ["apple", "samsung"]
    assert stage["tests"][0]["matched_response_terms_all"] == []
    assert "missing apple, samsung" in stage["tests"][0]["reason"]


def test_assistant_smoke_stage_fails_display_action_without_ids(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "A protective case is a useful accessory to buy with the phone.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        return {
            "response_text": "Apple and Samsung phones are available to compare.",
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "failed"
    assert stage["tests"][0]["failure_kind"] == "missing_action_ids"
    assert stage["tests"][0]["display_action_evidence"][0]["action"] == "SHOW_COMPARISON"
    assert stage["tests"][0]["display_action_evidence"][0]["id_count"] == 0
    assert "product_ids or entity_ids" in stage["tests"][0]["reason"]
    assert "action params" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_stage_fails_no_records_response(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_run_assistant_turn",
        lambda site_id, prompt: {
            "response_text": "No records found for that request.",
            "intent": "smoke",
            "ui_actions": [{"action": "COMPARE_ENTITIES", "params": {}}],
        },
    )

    stage = client_initialization._assistant_smoke_stage("policy_site", "insurance")

    assert stage["status"] == "failed"
    assert stage["failed"] == 2
    assert stage["tests"][0]["reason"] == "Assistant response used a no-data or no-records fallback."
    assert stage["tests"][0]["failure_kind"] == "no_data_fallback"
    assert "Data storage and Crawl report" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_stage_includes_retrieval_evidence_in_fix(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_run_assistant_turn",
        lambda site_id, prompt: {
            "response_text": "No records found for that request.",
            "intent": "smoke",
            "ui_actions": [{"action": "COMPARE_ENTITIES", "params": {}}],
            "retrieval": {
                "source": "knowledge_items",
                "active_records": 4,
                "missing_embeddings": 0,
                "retrieved_count": 0,
                "issue": "retrieval_returned_zero",
            },
        },
    )

    stage = client_initialization._assistant_smoke_stage("policy_site", "insurance")

    assert stage["tests"][0]["retrieval_evidence"]["source"] == "knowledge_items"
    assert stage["tests"][0]["retrieval_evidence"]["issue"] == "retrieval_returned_zero"
    assert "retrieval returned zero records" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_stage_fails_missing_accessory_recommendation(monkeypatch) -> None:
    from agent import client_initialization

    def fake_turn(site_id: str, prompt: str) -> dict[str, object]:
        if "accessory" in prompt.lower():
            return {
                "response_text": "Here are phones that match the request.",
                "intent": "smoke",
                "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["phone-1"]}}],
            }
        action = "SORT_PRODUCTS" if "low to high" in prompt else "SHOW_COMPARISON"
        response_text = (
            "Apple and Samsung phones are available to compare."
            if action == "SHOW_COMPARISON"
            else "Here is a useful source-backed answer."
        )
        return {
            "response_text": response_text,
            "intent": "smoke",
            "ui_actions": [{"action": action, "params": {"product_ids": ["apple-phone-1", "samsung-phone-1"]} if action == "SHOW_COMPARISON" else {"sort_by": "price_asc"}}],
        }

    monkeypatch.setattr(client_initialization, "_run_assistant_turn", fake_turn)

    stage = client_initialization._assistant_smoke_stage("ai_kart", "ecommerce")

    assert stage["status"] == "failed"
    assert stage["passed"] == 2
    assert stage["failed"] == 1
    assert stage["tests"][2]["name"] == "recommend_phone_accessory"
    assert stage["tests"][2]["matched_actions"] == ["SHOW_PRODUCTS"]
    assert stage["tests"][2]["matched_response_terms"] == []
    assert stage["tests"][2]["failure_kind"] == "missing_response_terms"
    assert "Expected response to mention one of" in stage["tests"][2]["reason"]
    assert "recommendation detail" in stage["tests"][2]["recommended_fix"]


def test_assistant_smoke_stage_fails_when_prompt_has_no_ui_action(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(
        client_initialization,
        "_run_assistant_turn",
        lambda site_id, prompt: {
            "response_text": "I can help with that.",
            "intent": "smoke",
            "ui_actions": [],
        },
    )

    stage = client_initialization._assistant_smoke_stage("travel_site", "travel")

    assert stage["status"] == "failed"
    assert stage["failed"] == 2
    assert stage["tests"][0]["failure_kind"] == "no_ui_action"
    assert "without emitting one of" in stage["tests"][0]["recommended_fix"]


def test_assistant_smoke_cases_do_not_call_external_llm(monkeypatch) -> None:
    from agent import client_initialization

    monkeypatch.setattr(client_initialization.config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(client_initialization, "_action_contract_smoke_cases", lambda site_id: [])

    cases = client_initialization._assistant_smoke_cases("ai_kart", "ecommerce")

    assert [case["name"] for case in cases] == [
        "compare_apple_samsung_phone",
        "sort_phones_low_to_high",
        "recommend_phone_accessory",
    ]


def test_assistant_smoke_result_reports_runtime_filter_failures() -> None:
    from agent import client_initialization

    result = client_initialization._assistant_smoke_result(
        {
            "name": "start_quote",
            "prompt": "Start my quote.",
            "expected_actions": ["START_QUOTE", "HANDOFF_TO_AGENT"],
        },
        {
            "response_text": "I will start the quote.",
            "intent": "quote",
            "ui_actions": [],
            "action_filter": {
                "status": "changed",
                "actions": [],
                "removed_actions": [
                    {
                        "action": "START_QUOTE",
                        "reason": "blocked_by_policy",
                        "message": "START_QUOTE is blocked by this site's safety policy.",
                    }
                ],
            },
        },
    )

    assert result["status"] == "failed"
    assert result["failure_kind"] == "blocked_action_filtered"
    assert result["filtered_actions"][0]["action"] == "START_QUOTE"
    assert "handoff" in result["recommended_fix"].lower()


def test_shopify_variant_id_preserves_large_integer() -> None:
    raw = {
        "id": 123,
        "title": "T Shirt",
        "handle": "t-shirt",
        "options": [{"name": "Color"}],
        "variants": [
            {
                "id": 11111111111111111,
                "title": "Red",
                "option1": "Red",
                "price": "999.00",
                "available": True,
            }
        ],
    }

    variants = ShopifyAdapter().extract_variants(raw, 123, "https://shop.test/products/t-shirt")

    assert variants[0]["id"] == 11111111111111111
    assert variants[0]["cart_id"] == "11111111111111111"


def test_woocommerce_variation_ids_become_variant_rows() -> None:
    raw = {
        "id": 55,
        "name": "Variable Hoodie",
        "prices": {"price": "2500", "currency_minor_unit": 2},
        "is_in_stock": True,
        "variations": [101, 102],
        "attributes": [
            {
                "name": "Size",
                "variation": True,
                "terms": [{"name": "S"}, {"name": "M"}],
            }
        ],
    }

    variants = WooCommerceAdapter().extract_variants(raw, 55, "https://woo.test/product/hoodie")

    assert [variant["id"] for variant in variants] == [101, 102]
    assert [variant["option1_value"] for variant in variants] == ["S", "M"]


def test_llm_extractor_requires_explicit_flag(monkeypatch) -> None:
    monkeypatch.setattr("config.LLM_EXTRACTOR_ENABLED", False)
    monkeypatch.setattr("config.OPENAI_API_KEY", "test-key")

    result = extract_selectors_from_html("<h1>Product</h1>", "site_1")

    assert result is None


def test_action_repair_proposals_include_health_validation_and_candidates() -> None:
    proposals = build_action_repair_proposals(
        vertical_key="construction",
        vertical_config={
            "action_health": {
                "needs_repair": [
                    {
                        "action": "REQUEST_ESTIMATE",
                        "last_reason": "missing selector",
                        "repair_candidate": {
                            "type": "click",
                            "selector": "button.estimate-new",
                            "confidence": 0.9,
                        },
                    }
                ]
            },
            "validation": {
                "actions": {
                    "REQUEST_SITE_VISIT": {
                        "evidence": "replacement found",
                        "repair": {
                            "type": "click",
                            "selector": "button.visit-new",
                            "confidence": 0.82,
                        },
                    }
                }
            },
            "action_candidates": [
                {
                    "action": "OPEN_PROJECTS",
                    "type": "navigate",
                    "path": "/projects",
                    "label": "Projects",
                    "confidence": 0.8,
                }
            ],
        },
    )

    rows = {proposal["action"]: proposal for proposal in proposals}

    assert rows["REQUEST_ESTIMATE"]["kind"] == "runtime_repair"
    assert rows["REQUEST_SITE_VISIT"]["kind"] == "validation_repair"
    assert rows["OPEN_PROJECTS"]["config"]["path"] == "/projects"


def test_tenant_isolation_audit_passes_scoped_runtime_prompt_and_knowledge() -> None:
    audit = build_tenant_isolation_audit(
        site_id="builder_demo",
        client={"site_id": "builder_demo"},
        runtime_config={
            "site_id": "builder_demo",
            "install": {
                "adapter_script": "https://hub.example.com/mayabot-adapter.js?site=builder_demo",
                "widget_script": "https://hub.example.com/mayabot.js?site=builder_demo",
            },
        },
        prompt_profile={
            "profile": {"id": "profile_1", "site_id": "builder_demo"},
            "versions": [{"id": "version_1", "profile_id": "profile_1"}],
        },
        knowledge={
            "stats": {"active_items": 3},
            "items": [{"id": "item_1", "title": "Renovation"}],
        },
    )

    assert audit["status"] == "passed"
    assert audit["summary"]["failed"] == 0


def test_tenant_isolation_audit_fails_cross_site_runtime() -> None:
    audit = build_tenant_isolation_audit(
        site_id="builder_demo",
        client={"site_id": "builder_demo"},
        runtime_config={
            "site_id": "other_site",
            "install": {"adapter_script": "https://hub.example.com/mayabot-adapter.js?site=other_site"},
        },
        prompt_profile={"profile": {"id": "profile_1", "site_id": "builder_demo"}, "versions": []},
        knowledge={"stats": {}, "items": []},
    )

    failed = {row["key"] for row in audit["checks"] if row["status"] == "failed"}

    assert audit["status"] == "failed"
    assert "runtime_site_id" in failed
    assert "install_script_scope" in failed


def test_settings_validation_accepts_model_temperature_update() -> None:
    assert _validated_settings({"LLM_TEMPERATURE": "0.3"}) == {"LLM_TEMPERATURE": "0.3"}


def test_settings_validation_accepts_action_auto_approve_threshold() -> None:
    assert _validated_settings({"ACTION_AUTO_APPROVE_CONFIDENCE": "0.6"}) == {
        "ACTION_AUTO_APPROVE_CONFIDENCE": "0.6",
    }


def test_settings_validation_accepts_openai_provider_usage_settings() -> None:
    assert _validated_settings(
        {
            "OPENAI_ADMIN_KEY": "admin-key",
            "OPENAI_MONTHLY_BUDGET_USD": "250",
            "OPENAI_USAGE_REFRESH_SECONDS": "300",
        }
    ) == {
        "OPENAI_ADMIN_KEY": "admin-key",
        "OPENAI_MONTHLY_BUDGET_USD": "250",
        "OPENAI_USAGE_REFRESH_SECONDS": "300",
    }


def test_settings_validation_rejects_invalid_model_temperature() -> None:
    with pytest.raises(ValueError, match="LLM_TEMPERATURE must be between 0 and 2"):
        _validated_settings({"LLM_TEMPERATURE": "3"})


def test_settings_validation_rejects_invalid_action_auto_approve_threshold() -> None:
    with pytest.raises(ValueError, match="ACTION_AUTO_APPROVE_CONFIDENCE must be between 0 and 1"):
        _validated_settings({"ACTION_AUTO_APPROVE_CONFIDENCE": "1.2"})


def test_settings_validation_rejects_non_integer_ports() -> None:
    with pytest.raises(ValueError, match="PORT must be a whole number"):
        _validated_settings({"PORT": "8585.5"})
