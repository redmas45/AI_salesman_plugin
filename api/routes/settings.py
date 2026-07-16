"""Settings and diagnostics routes for the Voice Shopping Agent API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends

import config
from api.contracts.models import HealthResponse
from api.crm_admin.crm_admin_guard import require_admin_token

logger = logging.getLogger(__name__)

CRAWLER_SOURCE_NAME = "custom_url_crawler"

router = APIRouter(tags=["Utility"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Check API and model configuration health."""
    return HealthResponse(
        status="ok",
        models={
            "stt": f"azure:{config.AZURE_OPENAI_STT_DEPLOYMENT}",
            "llm": f"azure:{config.AZURE_OPENAI_CHAT_DEPLOYMENT}",
            "tts": f"azure:{config.AZURE_OPENAI_TTS_DEPLOYMENT} / {config.AZURE_OPENAI_TTS_VOICE}",
            "embedding": config.EMBEDDING_MODEL,
        },
    )


@router.post("/v1/catalog/crawler/run", dependencies=[Depends(require_admin_token)])
async def trigger_crawler(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Manually trigger the crawler."""
    from agent.ingestion_helpers.ingestion_facade import sync_web_crawl

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

    background_tasks.add_task(run_sync)

    return {"status": "ok", "message": "Crawler started in background."}
