"""Action compatibility wrappers installed into agent.orchestrator."""

from __future__ import annotations

from typing import Any

from agent.action_helpers import action_response_filters
from agent.orchestration import orchestrator_action_enrichment, orchestrator_runtime_factories


def exports(runtime: Any) -> dict[str, Any]:
    def action_runtime() -> Any:
        return orchestrator_runtime_factories.action_runtime(runtime._pipeline_runtime())

    def add_variant_ids_to_cart_actions(
        site_id: str,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return runtime._action_runtime().add_variant_ids_to_cart_actions(site_id, actions)

    def enrich_action_params_from_context(
        site_id: str,
        transcript: str,
        conversation_history: list,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return runtime._action_runtime().enrich_action_params_from_context(
            site_id,
            transcript,
            conversation_history,
            actions,
        )

    def action_configs_for_site(site_id: str) -> dict[str, dict[str, Any]]:
        return runtime._action_runtime().action_configs_for_site(site_id)

    def apply_capability_filter(
        site_id: str,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return runtime._apply_capability_filter_result(site_id, actions)["actions"]

    def apply_capability_filter_result(
        site_id: str,
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return runtime._action_runtime().apply_capability_filter_result(site_id, actions)

    def align_response_with_action_filter(response_text: str, filter_report: dict[str, Any]) -> str:
        return runtime._action_runtime().align_response_with_action_filter(response_text, filter_report)

    def align_response_with_enriched_action_params(response_text: str, actions: list[dict[str, Any]]) -> str:
        return runtime._action_runtime().align_response_with_enriched_action_params(response_text, actions)

    def neutralize_pending_action_claims(response_text: str, actions: list[dict[str, Any]]) -> str:
        return action_response_filters.neutralize_pending_action_claims(response_text, actions)

    def align_response_when_actions_removed(
        response: dict[str, Any],
        transcript: str,
        site_id: str,
        original_actions: list[str],
        page_context: dict[str, Any] | None = None,
    ) -> None:
        return runtime._action_runtime().align_response_when_actions_removed(
            response,
            transcript,
            site_id,
            original_actions,
            page_context,
        )

    def suppress_lead_recovery_after_removed_navigation(
        response: dict[str, Any],
        transcript: str,
        original_actions: list[str],
    ) -> bool:
        return runtime._action_runtime().suppress_lead_recovery_after_removed_navigation(
            response,
            transcript,
            original_actions,
        )

    def response_promises_website_action(response_text: str) -> bool:
        return runtime._action_runtime().response_promises_website_action(response_text)

    def response_asks_for_known_action_param(response_text: str, known_params: list[str]) -> bool:
        return runtime._action_runtime().response_asks_for_known_action_param(response_text, known_params)

    return {
        "_action_runtime": action_runtime,
        "_add_variant_ids_to_cart_actions": add_variant_ids_to_cart_actions,
        "_enrich_action_params_from_context": enrich_action_params_from_context,
        "_action_configs_for_site": action_configs_for_site,
        "_legacy_extract_money_like_value": orchestrator_action_enrichment.legacy_extract_money_like_value,
        "_apply_capability_filter": apply_capability_filter,
        "_apply_capability_filter_result": apply_capability_filter_result,
        "_align_response_with_action_filter": align_response_with_action_filter,
        "_align_response_with_enriched_action_params": align_response_with_enriched_action_params,
        "_neutralize_pending_action_claims": neutralize_pending_action_claims,
        "_align_response_when_actions_removed": align_response_when_actions_removed,
        "_suppress_lead_recovery_after_removed_navigation": suppress_lead_recovery_after_removed_navigation,
        "_response_promises_website_action": response_promises_website_action,
        "_response_asks_for_known_action_param": response_asks_for_known_action_param,
        "_merged_action_filter_response": action_response_filters.merged_action_filter_response,
    }
