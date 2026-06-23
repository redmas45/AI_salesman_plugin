"""Analytics and logs routes for the Voice Shopping Agent API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MAX_LOG_FIELD_CHARS = 80
MAX_LOG_VALUE_CHARS = 300

router = APIRouter(tags=["Utility"])


class ClientLogRequest(BaseModel):
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/v1/client-log")
async def client_log(req: ClientLogRequest) -> dict[str, str]:
    """Receive browser-side diagnostics from the injected widget."""
    safe_event = str(req.event)[:MAX_LOG_FIELD_CHARS]
    safe_payload = {
        str(key)[:MAX_LOG_FIELD_CHARS]: str(value)[:MAX_LOG_VALUE_CHARS]
        for key, value in (req.payload or {}).items()
    }
    logger.info("CLIENT | %s | %s", safe_event, safe_payload)
    return {"status": "ok"}
