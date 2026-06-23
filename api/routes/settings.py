"""Settings and diagnostics routes for the Voice Shopping Agent API."""

from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import logging

from fastapi import APIRouter

import config
from api.models import HealthResponse

logger = logging.getLogger(__name__)

CRAWLER_SOURCE_NAME = "custom_url_crawler"

router = APIRouter(tags=["Utility"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Check API and model configuration health."""
    return HealthResponse(
        status="ok",
        models={
            "stt": f"{config.STT_PROVIDER}:{config.GROQ_STT_MODEL if config.STT_PROVIDER == 'groq' else config.STT_MODEL}",
            "llm": config.LLM_MODEL,
            "tts": (
                f"groq:{config.GROQ_TTS_MODEL} / {config.GROQ_TTS_VOICE}"
                if config.TTS_PROVIDER == "groq"
                else f"openai:{config.TTS_MODEL} / {config.TTS_VOICE}"
            ),
            "embedding": config.EMBEDDING_MODEL,
        },
    )


@router.post("/v1/catalog/crawler/run")
async def trigger_crawler() -> dict[str, str]:
    """Manually trigger the crawler."""
    from agent.ingestion import sync_web_crawl

    target_url = config.CURRENT_URL
    site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if not target_url:
        return {"status": "error", "message": "No CURRENT_URL configured."}

    logger.info("Manual crawler trigger requested for %s...", target_url)

    def run_sync() -> None:
        try:
            sync_web_crawl(
                target_url,
                max_pages=config.CRAWL_MAX_PAGES,
                max_depth=config.CRAWL_MAX_DEPTH,
                site_id=site_id,
                reconcile_missing=True,
                source_name=CRAWLER_SOURCE_NAME,
            )
        except (RuntimeError, OSError, ValueError) as exc:
            logger.error("Manual crawl failed: %s", exc)

    loop = asyncio.get_running_loop()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, run_sync)

    return {"status": "ok", "message": "Crawler started in background."}
