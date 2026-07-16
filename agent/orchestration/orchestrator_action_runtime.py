"""Bound action enrichment and filtering runtime for orchestrator turns."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from agent.action_helpers import action_params, action_response_filters
from agent.orchestration import orchestrator_action_enrichment


@dataclass(frozen=True)
class OrchestratorActionRuntime:
    recoverable_errors: tuple[type[BaseException], ...]
    capability_filter_skipped: str
    get_db: Callable[[str], Any]
    get_client_detail: Callable[[str], dict[str, Any]]
    lead_flow_fallback_text: Callable[[str], str]
    normalize_lookup_text: Callable[[Any], str]
    normalize_navigation_text: Callable[[str], str]
    navigation_unavailable_text: Callable[[str, str, dict[str, Any] | None], str]
    logger: logging.Logger

    def add_variant_ids_to_cart_actions(
        self,
        site_id: str,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return orchestrator_action_enrichment.add_variant_ids_to_cart_actions(
            site_id,
            actions,
            get_db=self.get_db,
            logger=self.logger,
        )

    def enrich_action_params_from_context(
        self,
        site_id: str,
        transcript: str,
        conversation_history: list,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return orchestrator_action_enrichment.enrich_action_params_from_context(
            site_id,
            transcript,
            conversation_history,
            actions,
            get_client_detail=self.get_client_detail,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def action_configs_for_site(self, site_id: str) -> dict[str, dict[str, Any]]:
        return orchestrator_action_enrichment.action_configs_for_site(
            site_id,
            get_client_detail=self.get_client_detail,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def apply_capability_filter_result(
        self,
        site_id: str,
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return action_response_filters.apply_capability_filter_result(
            site_id,
            actions,
            recoverable_errors=self.recoverable_errors,
            skipped_status=self.capability_filter_skipped,
            logger=self.logger,
        )

    def align_response_with_action_filter(self, response_text: str, filter_report: dict[str, Any]) -> str:
        return action_response_filters.align_response_with_action_filter(
            response_text,
            filter_report,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def align_response_with_enriched_action_params(
        self,
        response_text: str,
        actions: list[dict[str, Any]],
    ) -> str:
        return action_response_filters.align_response_with_enriched_action_params(
            response_text,
            actions,
            action_param_has_value=action_params.action_param_has_value,
            lead_flow_fallback_text=self.lead_flow_fallback_text,
            normalize_lookup_text=self.normalize_lookup_text,
        )

    def align_response_when_actions_removed(
        self,
        response: dict[str, Any],
        transcript: str,
        site_id: str,
        original_actions: list[str],
        page_context: dict[str, Any] | None = None,
    ) -> None:
        return action_response_filters.align_response_when_actions_removed(
            response,
            transcript,
            site_id,
            original_actions,
            page_context,
            navigation_unavailable_text=self.navigation_unavailable_text,
        )

    def suppress_lead_recovery_after_removed_navigation(
        self,
        response: dict[str, Any],
        transcript: str,
        original_actions: list[str],
    ) -> bool:
        return action_response_filters.suppress_lead_recovery_after_removed_navigation(
            response,
            transcript,
            original_actions,
            normalize_navigation_text=self.normalize_navigation_text,
        )

    def response_promises_website_action(self, response_text: str) -> bool:
        return action_response_filters.response_promises_website_action(
            response_text,
            normalize_lookup_text=self.normalize_lookup_text,
        )

    def response_asks_for_known_action_param(self, response_text: str, known_params: list[str]) -> bool:
        return action_response_filters.response_asks_for_known_action_param(
            response_text,
            known_params,
            self.normalize_lookup_text,
        )
