"""Static guards for the universal widget/runtime cleanup."""

from __future__ import annotations

from pathlib import Path


PLUGIN_SOURCE_ROOT = Path("plugin/src")
DISCOVERY_PROFILE_SOURCE = Path("agent/verticals/discovery_profiles.py")
API_MAIN_SOURCE = Path("api/main.py")
ECOMMERCE_ROUTE_SOURCE = Path("api/routes/ecommerce.py")
API_CLIENTS_SOURCE = Path("api/routes/clients.py")
ECOMMERCE_PROMPT_SOURCE = Path("agent/prompt.py")
RUNTIME_CAPABILITY_SOURCE = Path("plugin/src/adapter/discovery/runtimeCapabilities.js")
DISCOVERY_ADAPTER_SOURCE = Path("plugin/src/adapter/discovery/discovery.js")
DOCKER_ENTRYPOINT_SOURCE = Path("docker/entrypoint.sh")
ADMIN_SCHEMA_SOURCE = Path("db/core/schema.py")
LEGACY_WIDGET_TOKENS = (
    "window.ShopCart",
    "window.MayaBotConfig",
    "demo.vercel.store",
)
UNIVERSAL_WIDGET_BRAND_TOKENS = (
    "AI-KART",
    "MayaBot",
    "Shopping Assistant",
)


def test_removed_monolithic_widget_action_file_stays_removed() -> None:
    assert not Path("plugin/src/actions.js").exists()


def test_widget_source_has_no_legacy_demo_globals() -> None:
    offenders = _source_token_offenders(PLUGIN_SOURCE_ROOT, LEGACY_WIDGET_TOKENS)

    assert offenders == []


def test_product_resolver_does_not_assume_ai_kart_routes() -> None:
    source = Path("plugin/src/catalog/productResolver.js").read_text(encoding="utf-8")

    assert "AI_KART" not in source
    assert "routePrefixFor" not in source


def test_widget_chrome_is_not_hardcoded_to_ai_kart_or_ecommerce() -> None:
    offenders = _source_token_offenders(PLUGIN_SOURCE_ROOT, UNIVERSAL_WIDGET_BRAND_TOKENS)

    assert offenders == []


def test_runtime_loader_and_ecommerce_prompt_do_not_use_legacy_widget_brand() -> None:
    source = "\n".join(
        (
            API_CLIENTS_SOURCE.read_text(encoding="utf-8"),
            ECOMMERCE_PROMPT_SOURCE.read_text(encoding="utf-8"),
        )
    )

    assert "MayaBot" not in source
    assert "Shopping Assistant" not in source


def test_discovery_profiles_remain_data_driven() -> None:
    source = DISCOVERY_PROFILE_SOURCE.read_text(encoding="utf-8")

    assert "VerticalDiscoveryProfile" in source
    assert "if vertical_key ==" not in source
    assert "elif vertical_key ==" not in source


def test_ecommerce_routes_stay_out_of_core_runtime_app() -> None:
    main_source = API_MAIN_SOURCE.read_text(encoding="utf-8")
    ecommerce_source = ECOMMERCE_ROUTE_SOURCE.read_text(encoding="utf-8")

    assert '@app.get("/v1/products' not in main_source
    assert '@app.post("/v1/cart' not in main_source
    assert '@app.delete("/v1/cart' not in main_source
    assert '@router.get("/v1/products' in ecommerce_source
    assert '@router.post("/v1/cart' in ecommerce_source
    assert "INVOICE_BRAND_NAME" not in ecommerce_source


def test_runtime_capability_probe_does_not_collect_sensitive_values() -> None:
    source = RUNTIME_CAPABILITY_SOURCE.read_text(encoding="utf-8")

    assert "field.value" not in source
    assert ".value" not in source
    assert "password" not in source.lower()
    assert "payment" not in source.lower()


def test_discovery_registration_does_not_use_keepalive_for_large_payloads() -> None:
    source = DISCOVERY_ADAPTER_SOURCE.read_text(encoding="utf-8")

    assert "keepalive" not in source


def test_docker_entrypoint_uses_generic_site_default() -> None:
    source = DOCKER_ENTRYPOINT_SOURCE.read_text(encoding="utf-8")

    assert "${CURRENT_SITE_ID:-site_1}" in source
    assert "${CURRENT_SITE_ID:-ai_kart}" not in source


def test_admin_schema_migrates_setup_lifecycle_columns() -> None:
    source = ADMIN_SCHEMA_SOURCE.read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS last_setup_at TIMESTAMPTZ" in source
    assert "ADD COLUMN IF NOT EXISTS needs_setup BOOLEAN NOT NULL DEFAULT true" in source
    assert "ADD COLUMN IF NOT EXISTS last_crawl_status TEXT NOT NULL DEFAULT 'not_started'" in source


def _source_token_offenders(root: Path, tokens: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []
    for path in sorted(root.rglob("*.js")):
        source = path.read_text(encoding="utf-8")
        for token in tokens:
            if token in source:
                offenders.append(f"{path}:{token}")
    return offenders
