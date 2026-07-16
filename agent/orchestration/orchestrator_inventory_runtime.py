"""Bound inventory and simple response runtime for orchestrator turns."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from agent.responses import inventory_responses, turn_runtime_responses


@dataclass(frozen=True)
class OrchestratorInventoryRuntime:
    recoverable_errors: tuple[type[BaseException], ...]
    load_products: Callable[[str, int], list[dict[str, Any]]]
    matching_inventory_products: Callable[[list[dict[str, Any]], str], list[dict[str, Any]]]
    available_category_names: Callable[[list[dict[str, Any]]], list[str]]
    inventory_summary: Callable[[str], dict[str, Any]]
    synthesize_b64: Callable[[str], str]
    guardrail_audio: Callable[[str, bool], str]
    ai_log: Callable[[str, Any], None]
    elapsed_ms: Callable[[float], float]
    logger: logging.Logger

    def greeting_response(
        self,
        transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any]:
        return inventory_responses.greeting_response(
            transcript,
            skip_tts,
            timings,
            start_time,
            synthesize_b64=self.synthesize_b64,
            ai_log=self.ai_log,
            elapsed_ms=self.elapsed_ms,
            logger=self.logger,
        )

    def inventory_type_count_response(
        self,
        site_id: str,
        transcript: str,
        item_type: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any]:
        return inventory_responses.inventory_type_count_response(
            site_id,
            transcript,
            item_type,
            skip_tts,
            timings,
            start_time,
            load_products=self.load_products,
            matching_products=self.matching_inventory_products,
            available_categories=self.available_category_names,
            synthesize_b64=self.synthesize_b64,
            ai_log=self.ai_log,
            elapsed_ms=self.elapsed_ms,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def inventory_stats_response(
        self,
        site_id: str,
        transcript: str,
        skip_tts: bool,
        timings: dict[str, float],
        start_time: float,
    ) -> dict[str, Any]:
        return inventory_responses.inventory_stats_response(
            site_id,
            transcript,
            skip_tts,
            timings,
            start_time,
            inventory_summary=self.inventory_summary,
            synthesize_b64=self.synthesize_b64,
            elapsed_ms=self.elapsed_ms,
            recoverable_errors=self.recoverable_errors,
            logger=self.logger,
        )

    def error_response(self, message: str, timings: dict) -> dict[str, Any]:
        return turn_runtime_responses.error_response(message, timings)

    def guardrail_response(
        self,
        message: str,
        transcript: str,
        skip_tts: bool,
        timings: dict,
    ) -> dict[str, Any]:
        return turn_runtime_responses.guardrail_response(
            message,
            transcript,
            skip_tts,
            timings,
            guardrail_audio=self.guardrail_audio,
        )
