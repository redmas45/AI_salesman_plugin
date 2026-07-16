"""FastAPI startup and shutdown lifecycle for the runtime API."""

from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

import config
from db.admin_domain import admin_facade as admin_db

CRAWLER_SOURCE_NAME = "custom_url_crawler"
CRAWLER_POLL_INTERVAL_SECONDS = 120

logger = logging.getLogger(__name__)


@asynccontextmanager
async def runtime_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise database, seed data, preload RAG, and manage crawler task."""
    print("\n" + "=" * 60, flush=True)
    print(" INITIALIZING AI MODELS (May take 1-3 minutes on first boot)", flush=True)
    print("    Downloading/Loading embedding weights from HuggingFace...", flush=True)
    print("=" * 60 + "\n", flush=True)

    logger.info("Starting AI Hub Runtime API...")

    from agent import rag

    rag.preload()
    if config.ENSURE_DEFAULT_CLIENT_ON_STARTUP:
        admin_db.ensure_default_client()
    else:
        admin_db.init_admin_schema()
        logger.info("Default client startup seed disabled; keeping existing client list unchanged.")
    if config.CLEAN_SYNTHETIC_DEMO_CLIENTS_ON_STARTUP:
        removed_demo_clients = admin_db.cleanup_synthetic_demo_clients()
        if removed_demo_clients:
            logger.info("Removed %d stale synthetic example-domain install(s).", removed_demo_clients)

    startup_target_url = config.CURRENT_URL
    startup_site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if startup_target_url and config.CRAWL_ON_STARTUP:
        await run_crawl_once(startup_target_url, startup_site_id, initial=True)
    elif config.CRAWL_ON_STARTUP:
        logger.info("Startup crawl enabled but CURRENT_URL is empty; skipping crawl.")
    else:
        logger.info("Startup crawl disabled.")

    crawler_task = None
    if config.CRAWL_PERIODIC_ENABLED and config.CURRENT_URL:
        crawler_task = asyncio.create_task(periodic_crawl())
    elif config.CRAWL_PERIODIC_ENABLED:
        logger.info("Periodic crawl enabled but CURRENT_URL is empty; skipping crawler task.")
    else:
        logger.info("Periodic crawl disabled.")

    logger.info("Startup complete. API ready.")
    yield

    if crawler_task:
        crawler_task.cancel()
    logger.info("Shutting down AI Hub Runtime API.")


async def run_crawl_once(target_url: str, site_id: str, *, initial: bool = False) -> None:
    from agent.ingestion_helpers.ingestion_facade import sync_web_crawl

    phase = "startup" if initial else "periodic"
    logger.info("Starting %s crawl for %s...", phase, target_url)
    try:
        loop = asyncio.get_running_loop()
        func = functools.partial(
            sync_web_crawl,
            target_url,
            max_pages=config.CRAWL_MAX_PAGES,
            max_depth=config.CRAWL_MAX_DEPTH,
            site_id=site_id,
            reconcile_missing=True,
            source_name=CRAWLER_SOURCE_NAME,
        )
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(executor, func)
        logger.info("%s crawl completed for %s.", phase.capitalize(), target_url)
    except (RuntimeError, OSError, ValueError) as exc:
        logger.error("%s crawl failed: %s", phase.capitalize(), exc)


async def periodic_crawl() -> None:
    target_url = config.CURRENT_URL
    site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if target_url:
        while True:
            await asyncio.sleep(CRAWLER_POLL_INTERVAL_SECONDS)
            await run_crawl_once(target_url, site_id)
