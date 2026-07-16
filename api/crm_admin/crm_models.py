"""Request models for CRM admin routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from db.admin_domain import admin_facade as admin_db

ADMIN_TOKEN_HEADER = "x-crm-admin-token"
MAX_CLIENT_NAME_LENGTH = 120
MAX_SITE_ID_LENGTH = 80
MAX_URL_LENGTH = 500
MAX_ADAPTER_NAME_LENGTH = 160
MAX_PLAN_LENGTH = 80
MAX_VERTICAL_KEY_LENGTH = 80
MIN_ADMIN_TOKEN_LENGTH = 12


class ClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_CLIENT_NAME_LENGTH)
    store_url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)
    site_id: str | None = Field(default=None, max_length=MAX_SITE_ID_LENGTH)
    deploy_mode: str = Field(default=admin_db.DEFAULT_DEPLOY_MODE, max_length=40)
    plan: str = Field(default=admin_db.DEFAULT_PLAN, max_length=MAX_PLAN_LENGTH)
    vertical_key: str = Field(
        default=admin_db.DEFAULT_CLIENT_VERTICAL_KEY,
        max_length=MAX_VERTICAL_KEY_LENGTH,
    )
    adapter_name: str = Field(
        default=admin_db.DEFAULT_ADAPTER_NAME,
        max_length=MAX_ADAPTER_NAME_LENGTH,
    )


class ClientVerticalRequest(BaseModel):
    vertical_key: str = Field(..., min_length=1, max_length=MAX_VERTICAL_KEY_LENGTH)


class PromptProfileSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    system_prompt: str = Field(..., min_length=1, max_length=12000)
    developer_rules: str = Field(default="", max_length=12000)
    publish: bool = False
    changelog: str = Field(default="", max_length=500)


class AdapterActionsSaveRequest(BaseModel):
    actions: dict[str, Any] = Field(default_factory=dict)


class AdapterActionReviewRequest(BaseModel):
    candidate: dict[str, Any] = Field(default_factory=dict)
    decision: str = Field(..., min_length=1, max_length=20)
    action_name: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=500)


class AdapterActionProposalReviewRequest(BaseModel):
    proposal: dict[str, Any] = Field(default_factory=dict)
    decision: str = Field(..., min_length=1, max_length=20)
    note: str = Field(default="", max_length=500)


class FlowRepairProposalReviewRequest(BaseModel):
    proposal: dict[str, Any] = Field(default_factory=dict)
    decision: str = Field(..., min_length=1, max_length=20)
    note: str = Field(default="", max_length=500)


class FlowDiscoveryRequest(BaseModel):
    max_pages: int = Field(default=6, ge=1, le=20)


class FlowRehearsalRequest(BaseModel):
    max_steps: int = Field(default=24, ge=1, le=80)


class ClientStatusRequest(BaseModel):
    enabled: bool


class ClientTokenLimitsRequest(BaseModel):
    token_limit: int = Field(..., ge=1, le=admin_db.MAX_CLIENT_TOKEN_LIMIT)
    session_token_limit: int = Field(..., ge=1, le=admin_db.MAX_SESSION_TOKEN_LIMIT)


class ClientPanelPasswordRequest(BaseModel):
    password: str | None = Field(
        default=None,
        min_length=admin_db.MIN_CLIENT_PANEL_PASSWORD_LENGTH,
        max_length=160,
    )
    auto_generate: bool = False


class SettingsUpdateRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class AnalyticsSummaryRequest(BaseModel):
    range: str = Field(default=admin_db.ANALYTICS_DEFAULT_RANGE, max_length=20)
    site_id: str = Field(default="", max_length=MAX_SITE_ID_LENGTH)
