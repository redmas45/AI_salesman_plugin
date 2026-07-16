"""Pydantic models and validation constants for widget client routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

import config

MAX_DISCOVERY_ELEMENTS = 80
MAX_DISCOVERY_TEXT_LENGTH = 3000
MAX_DISCOVERY_HTML_LENGTH = 6000
MAX_DISCOVERY_LABEL_LENGTH = 160
MAX_DISCOVERY_SELECTOR_LENGTH = 260
MAX_DISCOVERY_HREF_LENGTH = 600
MAX_RUNTIME_CAPABILITY_TEXT_LENGTH = 240
MAX_RUNTIME_CAPABILITY_NUMBER = 10000
RUNTIME_CAPABILITY_BOOL_KEYS = frozenset({
    "script_loaded",
    "secure_context",
    "top_level_window",
    "fetch_api",
    "permissions_api",
    "media_devices_api",
    "get_user_media_api",
    "cookies_enabled",
    "shadow_dom_api",
    "custom_elements_api",
    "mutation_observer_api",
})
RUNTIME_CAPABILITY_TEXT_KEYS = frozenset({
    "reported_at",
    "origin",
    "url",
    "protocol",
    "document_ready_state",
    "microphone_permission",
    "session_storage",
    "local_storage",
    "language",
    "user_agent",
})
RUNTIME_CAPABILITY_NUMBER_KEYS = frozenset({"iframe_count"})

DISCOVERY_ELEMENT_FIELD_LIMITS = {
    "label": MAX_DISCOVERY_LABEL_LENGTH,
    "selector": MAX_DISCOVERY_SELECTOR_LENGTH,
    "href": MAX_DISCOVERY_HREF_LENGTH,
    "input_selector": MAX_DISCOVERY_SELECTOR_LENGTH,
    "submit_selector": MAX_DISCOVERY_SELECTOR_LENGTH,
}


class DiscoveryElement(BaseModel):
    label: str = Field(default="", max_length=MAX_DISCOVERY_LABEL_LENGTH)
    selector: str = Field(default="", max_length=MAX_DISCOVERY_SELECTOR_LENGTH)
    href: str = Field(default="", max_length=MAX_DISCOVERY_HREF_LENGTH)
    input_selector: str = Field(default="", max_length=MAX_DISCOVERY_SELECTOR_LENGTH)
    submit_selector: str = Field(default="", max_length=MAX_DISCOVERY_SELECTOR_LENGTH)
    fields: list[dict[str, Any]] = Field(default_factory=list, max_length=20)

    @field_validator("label", "selector", "href", "input_selector", "submit_selector", mode="before")
    @classmethod
    def trim_browser_discovery_text(cls, value: Any, info: Any) -> str:
        limit = DISCOVERY_ELEMENT_FIELD_LIMITS.get(info.field_name, MAX_DISCOVERY_LABEL_LENGTH)
        return str(value or "").strip()[:limit]


class WidgetRegisterRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    title: str = Field(default="", max_length=180)
    text_sample: str = Field(default="", max_length=MAX_DISCOVERY_TEXT_LENGTH)
    html_sample: str = Field(default="", max_length=MAX_DISCOVERY_HTML_LENGTH)
    buttons: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    links: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    forms: list[DiscoveryElement] = Field(default_factory=list, max_length=MAX_DISCOVERY_ELEMENTS)
    platform_hints: dict[str, Any] = Field(default_factory=dict)
    barrier_hints: dict[str, Any] = Field(default_factory=dict)
    runtime_capabilities: dict[str, Any] = Field(default_factory=dict)


class WidgetActionValidationRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    validated_at: str = Field(default="", max_length=80)
    actions: dict[str, Any] = Field(default_factory=dict)


class WidgetPolicyEventRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    occurred_at: str = Field(default="", max_length=80)
    action: str = Field(..., min_length=1, max_length=80)
    status: str = Field(default="blocked", max_length=40)
    reason: str = Field(default="", max_length=240)
    policy: dict[str, Any] = Field(default_factory=dict)


class WidgetActionExecutionEventRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    occurred_at: str = Field(default="", max_length=80)
    request_id: str = Field(default="", max_length=80)
    turn_id: str = Field(default="", max_length=80)
    sequence: int = Field(default=0, ge=0, le=100)
    action: str = Field(..., min_length=1, max_length=80)
    status: str = Field(default="unknown", max_length=40)
    stage: str = Field(default="", max_length=80)
    reason: str = Field(default="", max_length=240)
    duration_ms: float = Field(default=0.0, ge=0)
    param_keys: list[str] = Field(default_factory=list, max_length=20)
    requested_url: str = Field(default="", max_length=600)
    final_url: str = Field(default="", max_length=600)
    evidence: dict[str, Any] = Field(default_factory=dict)


class WidgetInteractionEventRequest(BaseModel):
    site_id: str = Field(default=config.DEFAULT_SITE_ID, min_length=1, max_length=80)
    origin: str = Field(..., min_length=1, max_length=240)
    url: str = Field(..., min_length=1, max_length=600)
    occurred_at: str = Field(default="", max_length=80)
    event_type: str = Field(..., min_length=1, max_length=40)
    label: str = Field(default="", max_length=180)
    selector: str = Field(default="", max_length=260)
    tag: str = Field(default="", max_length=40)
    href: str = Field(default="", max_length=600)
    form: dict[str, Any] = Field(default_factory=dict)
