"""Bound navigation and sort runtime for orchestrator turns."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from agent.responses import navigation_intent


@dataclass(frozen=True)
class OrchestratorNavigationRuntime:
    recoverable_errors: tuple[type[BaseException], ...]
    get_client_detail: Callable[[str], dict[str, Any]]
    get_client_vertical_key: Callable[[str], str]
    is_ecommerce_site: Callable[[str], bool]
    lead_flow_action_from_transcript_func: Callable[[str, str], str]
    synthesize_b64: Callable[[str], str]
    ai_log: Callable[[str, Any], None]
    elapsed_ms: Callable[[float], float]
    logger: logging.Logger

    def navigation_intent_response(
        self,
        site_id: str,
        transcript: str,
        safe_transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
        page_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return navigation_intent.navigation_intent_response(
            site_id,
            transcript,
            safe_transcript,
            skip_tts,
            timings,
            start_time,
            page_context,
            page_from_transcript=self.navigation_page_from_transcript,
            synthesize_b64=self.synthesize_b64,
            ai_log=self.ai_log,
            elapsed_ms=self.elapsed_ms,
            logger=self.logger,
        )

    def sort_intent_response(
        self,
        site_id: str,
        transcript: str,
        safe_transcript: str,
        ecommerce_runtime: bool,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any] | None:
        return navigation_intent.sort_intent_response(
            site_id,
            transcript,
            safe_transcript,
            ecommerce_runtime,
            skip_tts,
            timings,
            start_time,
            vertical_entity_plural=self.vertical_entity_plural,
            synthesize_b64=self.synthesize_b64,
            ai_log=self.ai_log,
            elapsed_ms=self.elapsed_ms,
            logger=self.logger,
        )

    def vertical_entity_plural(self, site_id: str) -> str:
        try:
            from agent.verticals.registry import get_vertical

            vertical = get_vertical(self.get_client_vertical_key(site_id))
            return vertical.entity_label_plural
        except self.recoverable_errors as exc:
            self.logger.warning("PIPELINE | vertical entity label unavailable for %s: %s", site_id, exc)
            return "options"

    def navigation_page_from_transcript(
        self,
        site_id: str,
        transcript: str,
        page_context: dict[str, Any] | None = None,
        *,
        require_specific_match: bool = False,
    ) -> str:
        return navigation_intent.navigation_page_from_transcript(
            site_id,
            transcript,
            page_context,
            require_specific_match=require_specific_match,
            route_map=self.client_navigation_route_map,
            is_ecommerce_site=self.is_ecommerce_site,
            lead_flow_action_from_transcript=self.lead_flow_action_from_transcript_func,
        )

    def lead_flow_should_own_navigation_text(self, text: str, site_id: str) -> bool:
        return navigation_intent.lead_flow_should_own_navigation_text(
            text,
            site_id,
            lead_flow_action_from_transcript=self.lead_flow_action_from_transcript_func,
        )

    def navigation_route_terms(
        self,
        site_id: str,
        page_context: dict[str, Any] | None = None,
    ) -> list[tuple[str, str]]:
        return navigation_intent.navigation_route_terms(
            site_id,
            page_context,
            route_map=self.client_navigation_route_map,
        )

    def client_navigation_route_map(
        self,
        site_id: str,
        page_context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        return navigation_intent.client_navigation_route_map(
            site_id,
            page_context,
            get_client_detail=self.get_client_detail,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def navigation_unavailable_text(
        self,
        site_id: str,
        transcript: str,
        page_context: dict[str, Any] | None = None,
    ) -> str:
        return navigation_intent.navigation_unavailable_text(
            site_id,
            transcript,
            page_context,
            route_map=self.client_navigation_route_map,
        )

    def available_navigation_labels(
        self,
        site_id: str,
        page_context: dict[str, Any] | None = None,
    ) -> list[str]:
        return navigation_intent.available_navigation_labels(
            site_id,
            page_context,
            route_map=self.client_navigation_route_map,
        )
