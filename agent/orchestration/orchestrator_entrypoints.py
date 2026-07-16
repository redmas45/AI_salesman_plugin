"""Public pipeline entrypoint helpers for the orchestrator facade."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

from agent.orchestration import orchestrator_logging, orchestrator_pipeline

RuntimeProvider = Callable[[], Any]


def exports(
    *,
    runtime_provider: RuntimeProvider,
    logger: Any,
    default_audio_filename: str,
) -> dict[str, Any]:
    def safe_print(*args: Any, **kwargs: Any) -> None:
        orchestrator_logging.safe_print(*args, **kwargs)

    def ai_log(label: str, value: Any) -> None:
        orchestrator_logging.ai_log(logger, safe_print, label, value)

    def run(
        site_id: str,
        audio_bytes: bytes | None = None,
        text_input: str | None = None,
        audio_filename: str = default_audio_filename,
        skip_tts: bool = False,
        conversation_history: list | None = None,
        page_context: dict[str, Any] | None = None,
        session_summary: str = "",
        session_id: str = "",
    ) -> dict[str, Any]:
        return orchestrator_pipeline.run_pipeline(
            runtime_provider(),
            site_id=site_id,
            audio_bytes=audio_bytes,
            text_input=text_input,
            audio_filename=audio_filename,
            skip_tts=skip_tts,
            conversation_history=conversation_history,
            page_context=page_context,
            session_summary=session_summary,
            session_id=session_id,
        )

    def run_stream(
        site_id: str,
        audio_bytes: bytes | None = None,
        text_input: str | None = None,
        audio_filename: str = default_audio_filename,
        skip_tts: bool = False,
        conversation_history: list | None = None,
        page_context: dict[str, Any] | None = None,
        session_summary: str = "",
        session_id: str = "",
    ) -> Generator[dict[str, Any], None, None]:
        yield from orchestrator_pipeline.run_stream_pipeline(
            runtime_provider(),
            site_id=site_id,
            audio_bytes=audio_bytes,
            text_input=text_input,
            audio_filename=audio_filename,
            skip_tts=skip_tts,
            conversation_history=conversation_history,
            page_context=page_context,
            session_summary=session_summary,
            session_id=session_id,
        )

    def stream_final_result(result: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        yield from orchestrator_pipeline.stream_final_result(result)

    return {
        "print": safe_print,
        "_ai_log": ai_log,
        "run": run,
        "run_stream": run_stream,
        "_stream_final_result": stream_final_result,
        "_ms": orchestrator_logging.elapsed_ms,
    }
