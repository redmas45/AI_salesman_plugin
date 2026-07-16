"""Public knowledge lookup routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
import psycopg

import config
from api.contracts.models import KnowledgeItemResponse
from api.routes.knowledge_helpers import public_knowledge

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/v1/knowledge", tags=["Knowledge"])
async def list_knowledge(site_id: str = config.DEFAULT_SITE_ID, limit: int = 50) -> dict[str, Any]:
    """Return generic knowledge rows for a tenant."""
    try:
        from db.knowledge_base.knowledge_items import knowledge_preview, knowledge_stats

        safe_limit = max(1, min(int(limit), 500))
        return {
            "site_id": site_id,
            "stats": knowledge_stats(site_id),
            "items": knowledge_preview(site_id, limit=safe_limit),
        }
    except psycopg.Error as exc:
        logger.error("GET /v1/knowledge failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge items.") from exc


@router.get("/v1/knowledge/by-ids", response_model=list[KnowledgeItemResponse], tags=["Knowledge"])
async def list_knowledge_by_ids(ids: str, site_id: str = config.DEFAULT_SITE_ID) -> list[KnowledgeItemResponse]:
    """Fetch public knowledge records by exact IDs for widget-side entity rendering."""
    requested_ids = public_knowledge.parse_public_knowledge_ids(ids)
    if not requested_ids:
        return []
    try:
        from db.knowledge_base.knowledge_items import get_knowledge_items_by_ids

        items = get_knowledge_items_by_ids(site_id, requested_ids)
        public_items = public_knowledge.public_knowledge_items(items, requested_ids)
        return [KnowledgeItemResponse(**item) for item in public_items]
    except psycopg.Error as exc:
        logger.error("GET /v1/knowledge/by-ids failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge items by IDs.") from exc
