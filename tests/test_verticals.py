import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from agent.verticals.registry import DEFAULT_VERTICAL_KEY, get_vertical, list_verticals
from api import crm
from api.main import app, _allowed_cors_origins
from db import clients as client_db
from db.clients import _default_client_adapter_name, _default_client_vertical_key
from db.seed import DEFAULT_SEED_SITE_IDS


def test_vertical_registry_lists_core_domains():
    verticals = {vertical.key: vertical for vertical in list_verticals()}

    assert DEFAULT_VERTICAL_KEY == "generic"
    assert verticals["ecommerce"].label == "E-commerce"
    assert verticals["insurance"].risk_level == "high"
    assert verticals["travel"].entity_label_plural == "travel items"
    assert verticals["generic"].default_plan_label == "Generic AI plan"


def test_crm_verticals_exposes_domain_action_contracts(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    res = TestClient(app).get(
        "/v1/admin/verticals",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    verticals = res.json()["verticals"]
    assert len(verticals) >= 14
    for vertical in verticals:
        assert vertical["key"]
        assert vertical["label"]
        assert vertical["entity_label_plural"]
        assert vertical["readiness_checks"], vertical["key"]
        assert vertical["action_types"], vertical["key"]
    ecommerce = next(vertical for vertical in verticals if vertical["key"] == "ecommerce")
    insurance = next(vertical for vertical in verticals if vertical["key"] == "insurance")
    assert "SHOW_COMPARISON" in ecommerce["action_types"]
    assert "START_QUOTE" in insurance["action_types"]


def test_vertical_registry_rejects_unknown_key():
    try:
        get_vertical("unknown-domain")
    except ValueError as exc:
        assert "Unsupported vertical" in str(exc)
    else:
        raise AssertionError("unknown vertical should be rejected")


def test_default_client_seed_is_generic_for_every_site_id():
    assert _default_client_vertical_key("new_policy_site") == "generic"
    assert _default_client_adapter_name("new_policy_site") == "generic_adapter.js"
    assert _default_client_vertical_key("ai_kart") == "generic"
    assert _default_client_adapter_name("ai_kart") == "generic_adapter.js"


def test_seed_defaults_do_not_include_demo_client_ids():
    assert "ai_kart" not in DEFAULT_SEED_SITE_IDS


def test_default_client_seed_can_be_disabled_for_empty_install_tests(monkeypatch):
    calls = []

    monkeypatch.setattr(client_db.config, "ENSURE_DEFAULT_CLIENT_ON_STARTUP", False)
    monkeypatch.setattr(client_db, "init_admin_schema", lambda: calls.append("admin_schema"))
    monkeypatch.setattr(
        client_db,
        "init_tenant_schema",
        lambda site_id: (_ for _ in ()).throw(AssertionError(f"tenant seeded for {site_id}")),
    )
    monkeypatch.setattr(
        client_db,
        "_connect",
        lambda: (_ for _ in ()).throw(AssertionError("default client should not be inserted")),
    )

    client_db.ensure_default_client()

    assert calls == ["admin_schema"]


def test_local_cors_allowlist_uses_hub_dev_origins_not_demo_sites(monkeypatch):
    monkeypatch.setattr(client_db.config, "CORS_ORIGINS", ["*"])
    monkeypatch.setattr(client_db.config, "DEPLOYMENT_MODE", "local")

    origins = _allowed_cors_origins()

    assert "http://127.0.0.1:5174" in origins
    assert "http://127.0.0.1:8585" in origins
    assert "http://127.0.0.1:5175" not in origins
    assert "http://127.0.0.1:5183" not in origins


def test_lifespan_empty_local_startup_does_not_seed_default_client_or_crawl(monkeypatch):
    from api import main as api_main

    calls = []

    monkeypatch.setattr(api_main.config, "ENSURE_DEFAULT_CLIENT_ON_STARTUP", False)
    monkeypatch.setattr(api_main.config, "CRAWL_ON_STARTUP", False)
    monkeypatch.setattr(api_main.config, "CRAWL_PERIODIC_ENABLED", False)
    monkeypatch.setattr(api_main.config, "CURRENT_URL", "https://policy.example.com")
    monkeypatch.setattr("agent.rag.preload", lambda: calls.append("preload"))
    monkeypatch.setattr(api_main.admin_db, "init_admin_schema", lambda: calls.append("schema"))
    monkeypatch.setattr(
        api_main.admin_db,
        "ensure_default_client",
        lambda: (_ for _ in ()).throw(AssertionError("startup must not seed a default client")),
    )
    monkeypatch.setattr(
        api_main.asyncio,
        "create_task",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("startup must not schedule crawler")),
    )

    async def run_lifespan():
        async with api_main.lifespan(api_main.app):
            calls.append("ready")

    asyncio.run(run_lifespan())

    assert calls == ["preload", "schema", "ready"]


def test_lifespan_with_empty_current_url_never_starts_crawler(monkeypatch):
    from api import main as api_main

    calls = []

    monkeypatch.setattr(api_main.config, "ENSURE_DEFAULT_CLIENT_ON_STARTUP", False)
    monkeypatch.setattr(api_main.config, "CRAWL_ON_STARTUP", True)
    monkeypatch.setattr(api_main.config, "CRAWL_PERIODIC_ENABLED", True)
    monkeypatch.setattr(api_main.config, "CURRENT_URL", "")
    monkeypatch.setattr("agent.rag.preload", lambda: calls.append("preload"))
    monkeypatch.setattr(api_main.admin_db, "init_admin_schema", lambda: calls.append("schema"))
    monkeypatch.setattr(
        api_main.admin_db,
        "ensure_default_client",
        lambda: (_ for _ in ()).throw(AssertionError("startup must not seed a default client")),
    )
    monkeypatch.setattr(
        api_main.asyncio,
        "create_task",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("empty CURRENT_URL must not schedule crawler")),
    )

    async def run_lifespan():
        async with api_main.lifespan(api_main.app):
            calls.append("ready")

    asyncio.run(run_lifespan())

    assert calls == ["preload", "schema", "ready"]


def test_crm_verticals_endpoint(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    res = TestClient(app).get(
        "/v1/admin/verticals",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["default_vertical_key"] == "generic"
    assert any(vertical["key"] == "insurance" for vertical in body["verticals"])


def test_crm_create_client_passes_vertical_key(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_create_client(**kwargs):
        captured.update(kwargs)
        return {
            "site_id": kwargs["site_id"] or "demo_insurance",
            "name": kwargs["name"],
            "store_url": kwargs["store_url"],
            "vertical_key": kwargs["vertical_key"],
            "vertical_label": "Insurance",
            "risk_level": "high",
        }

    monkeypatch.setattr(crm.admin_db, "create_client", fake_create_client)

    res = TestClient(app).post(
        "/v1/admin/clients",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={
            "name": "Demo Insurance",
            "store_url": "https://example.com",
            "site_id": "demo_insurance",
            "deploy_mode": "public-ip",
            "plan": "Insurance plan",
            "adapter_name": "generic_adapter.js",
            "vertical_key": "insurance",
        },
    )

    assert res.status_code == 201
    assert captured["vertical_key"] == "insurance"
    assert res.json()["client"]["vertical_key"] == "insurance"


def test_crm_activate_client_does_not_start_integration(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    activated = {}
    activated_client = {
        "site_id": "demo_policy",
        "name": "Demo Policy",
        "store_url": "https://policy.example.com",
        "vertical_key": "insurance",
        "status": client_db.CLIENT_STATUS_LIVE,
        "last_crawl_status": client_db.CRAWL_STATUS_NOT_STARTED,
    }

    def fake_activate_client(site_id: str):
        activated["site_id"] = site_id
        return activated_client

    monkeypatch.setattr(crm.admin_db, "activate_client", fake_activate_client)
    monkeypatch.setattr(
        crm.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("activation must not start crawl")),
    )
    monkeypatch.setattr(
        crm,
        "run_widget_initialization",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("activation must not start integration")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/demo_policy/activate",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert activated == {"site_id": "demo_policy"}
    body = res.json()
    assert body["status"] == "activated"
    assert body["client"]["status"] == client_db.CLIENT_STATUS_LIVE


def test_crm_crawl_rejects_available_client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://policy.example.com",
            "status": client_db.CLIENT_STATUS_AVAILABLE,
        },
    )
    monkeypatch.setattr(
        crm.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not crawl")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/demo_policy/crawl",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 409
    assert "Move this client to Current" in res.json()["detail"]


def test_crm_auto_integration_rejects_available_client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://policy.example.com",
            "status": client_db.CLIENT_STATUS_AVAILABLE,
        },
    )
    monkeypatch.setattr(
        crm.admin_db,
        "activate_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not auto-activate")),
    )
    monkeypatch.setattr(
        crm.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not auto-integrate")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/demo_policy/auto-integrate",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 409
    assert "Move this client to Current" in res.json()["detail"]


def test_crm_auto_integration_queues_assistant_smoke_tests(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://shop.example.com",
            "status": client_db.CLIENT_STATUS_LIVE,
            "vertical_key": "ecommerce",
        },
    )
    monkeypatch.setattr(crm.admin_db, "update_client_crawl_status", lambda *args, **kwargs: None)

    def fake_run_widget_initialization(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(crm, "run_widget_initialization", fake_run_widget_initialization)

    res = TestClient(app).post(
        "/v1/admin/clients/ai_kart/auto-integrate",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "queued"
    assert "assistant smoke tests" in res.json()["message"]
    assert captured["args"][0] == "ai_kart"
    assert captured["kwargs"]["run_smoke_tests"] is True


def test_crm_assistant_smoke_tests_runs_without_crawl(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://shop.example.com",
            "status": client_db.CLIENT_STATUS_LIVE,
            "vertical_key": "ecommerce",
        },
    )
    monkeypatch.setattr(
        crm,
        "run_assistant_smoke_tests",
        lambda site_id, vertical_key: {
            "source": "crm_assistant_smoke_tests",
            "status": "ok",
            "site_id": site_id,
            "vertical_key": vertical_key,
            "message": "2/2 assistant smoke tests passed.",
            "tests": [],
        },
    )

    def fake_save(site_id: str, report: dict[str, object]):
        saved.update({"site_id": site_id, "report": report})
        return {"site_id": site_id, "vertical_config": {"assistant_smoke_tests": report}}

    monkeypatch.setattr(crm.admin_db, "save_client_assistant_smoke_report", fake_save)
    monkeypatch.setattr(
        crm.admin_db,
        "update_client_crawl_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("smoke tests must not crawl")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/ai_kart/assistant-smoke-tests",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert saved["site_id"] == "ai_kart"
    assert saved["report"]["source"] == "crm_assistant_smoke_tests"


def test_crm_assistant_smoke_tests_rejects_available_client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    monkeypatch.setattr(
        crm.admin_db,
        "get_client_detail",
        lambda site_id: {
            "site_id": site_id,
            "store_url": "https://shop.example.com",
            "status": client_db.CLIENT_STATUS_AVAILABLE,
            "vertical_key": "ecommerce",
        },
    )
    monkeypatch.setattr(
        crm,
        "run_assistant_smoke_tests",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("available client must not run smoke tests")),
    )

    res = TestClient(app).post(
        "/v1/admin/clients/ai_kart/assistant-smoke-tests",
        headers={"x-crm-admin-token": "test-token-strong"},
    )

    assert res.status_code == 409
    assert "Move this client to Current" in res.json()["detail"]


def test_crm_updates_client_vertical(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_TOKEN", "test-token-strong")
    captured = {}

    def fake_update_client_vertical(site_id: str, vertical_key: str):
        captured.update({"site_id": site_id, "vertical_key": vertical_key})
        return {
            "site_id": site_id,
            "vertical_key": vertical_key,
            "vertical_label": "Travel",
            "risk_level": "medium",
        }

    monkeypatch.setattr(crm.admin_db, "update_client_vertical", fake_update_client_vertical)

    res = TestClient(app).patch(
        "/v1/admin/clients/demo/vertical",
        headers={"x-crm-admin-token": "test-token-strong"},
        json={"vertical_key": "travel"},
    )

    assert res.status_code == 200
    assert captured == {"site_id": "demo", "vertical_key": "travel"}
    assert res.json()["client"]["vertical_label"] == "Travel"
