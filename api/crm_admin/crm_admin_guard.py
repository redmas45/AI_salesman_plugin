"""CRM admin route guards and maintenance hooks."""

from __future__ import annotations

import hmac
import logging
import os

from fastapi import HTTPException, Request, status

import config
from api.crm_admin.crm_models import ADMIN_TOKEN_HEADER, MIN_ADMIN_TOKEN_LENGTH
from db.admin_domain import admin_facade as admin_db

logger = logging.getLogger(__name__)


def require_admin_token(request: Request) -> None:
    """Require a configured admin token for every CRM admin API request."""
    expected_token = os.getenv("CRM_ADMIN_TOKEN", "").strip()
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM admin token is not configured.",
        )
    if len(expected_token) < MIN_ADMIN_TOKEN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM admin token is configured but too short.",
        )

    provided_token = request.headers.get(ADMIN_TOKEN_HEADER, "").strip()
    if hmac.compare_digest(provided_token, expected_token):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="CRM admin token is required.",
    )


def expire_stale_setup_runs() -> None:
    try:
        expired = admin_db.expire_stale_client_initialization_runs(config.SETUP_RUN_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("CRM stale setup sweep failed: %s", exc)
        return
    if expired:
        logger.warning("CRM marked %s stale setup run(s) as timed out.", expired)
