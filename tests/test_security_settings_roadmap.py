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


def test_settings_validation_accepts_azure_timeout_update() -> None:
    assert _validated_settings({"AZURE_OPENAI_TIMEOUT_SECONDS": "30"}) == {
        "AZURE_OPENAI_TIMEOUT_SECONDS": "30"
    }


def test_settings_validation_accepts_action_auto_approve_threshold() -> None:
    assert _validated_settings({"ACTION_AUTO_APPROVE_CONFIDENCE": "0.6"}) == {
        "ACTION_AUTO_APPROVE_CONFIDENCE": "0.6",
    }


def test_settings_validation_accepts_azure_provider_settings() -> None:
    assert _validated_settings(
        {
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_BASE_URL": "https://example.openai.azure.com/openai/v1/",
            "AZURE_OPENAI_REASONING_EFFORT": "none",
        }
    ) == {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_BASE_URL": "https://example.openai.azure.com/openai/v1/",
        "AZURE_OPENAI_REASONING_EFFORT": "none",
    }


def test_settings_validation_rejects_invalid_azure_timeout() -> None:
    with pytest.raises(ValueError, match="AZURE_OPENAI_TIMEOUT_SECONDS must be between 1 and 300"):
        _validated_settings({"AZURE_OPENAI_TIMEOUT_SECONDS": "0"})


def test_settings_validation_rejects_full_chat_completions_url() -> None:
    with pytest.raises(RuntimeError, match="must end with /openai/v1/"):
        _validated_settings(
            {
                "AZURE_OPENAI_BASE_URL": (
                    "https://example.openai.azure.com/openai/v1/chat/completions"
                )
            }
        )


def test_settings_validation_rejects_invalid_action_auto_approve_threshold() -> None:
    with pytest.raises(ValueError, match="ACTION_AUTO_APPROVE_CONFIDENCE must be between 0 and 1"):
        _validated_settings({"ACTION_AUTO_APPROVE_CONFIDENCE": "1.2"})


def test_settings_validation_rejects_non_integer_ports() -> None:
    with pytest.raises(ValueError, match="PORT must be a whole number"):
        _validated_settings({"PORT": "8585.5"})
