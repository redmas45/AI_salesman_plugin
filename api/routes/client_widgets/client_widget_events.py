"""Widget browser-runtime event processors."""

from __future__ import annotations

from typing import Any, Callable, Protocol
from urllib.parse import urlparse

from fastapi import HTTPException

from api.routes.client_widgets.client_models import (
    WidgetActionExecutionEventRequest,
    WidgetActionValidationRequest,
    WidgetInteractionEventRequest,
    WidgetPolicyEventRequest,
)


class ClientEventStore(Protocol):
    def get_client_detail(self, site_id: str) -> dict[str, Any]: ...

    def save_adapter_validation_report(self, site_id: str, report: dict[str, Any]) -> Any: ...

    def save_client_policy_event(self, site_id: str, event: dict[str, Any]) -> Any: ...

    def save_client_action_event(self, site_id: str, event: dict[str, Any]) -> Any: ...

    def save_client_interaction_event(self, site_id: str, event: dict[str, Any]) -> Any: ...


SiteIdSanitizer = Callable[[str], str]
OriginSanitizer = Callable[[str], str]
ClientDetailLoader = Callable[[str], dict[str, Any]]
DictValue = Callable[[dict[str, Any], str], dict[str, Any]]


def process_action_validation_report(
    req: WidgetActionValidationRequest,
    *,
    client_store: ClientEventStore,
    safe_site_id: SiteIdSanitizer,
    safe_script_base_url: OriginSanitizer,
    safe_client_detail: ClientDetailLoader,
    dict_value: DictValue,
) -> dict[str, Any]:
    safe_site = safe_site_id(req.site_id)
    origin = safe_script_base_url(req.origin)
    if not origin:
        raise HTTPException(status_code=400, detail="Validation origin must be http or https.")
    client = safe_client_detail(safe_site)
    allowed_origin = safe_script_base_url(str(client.get("allowed_origin") or ""))
    if allowed_origin and allowed_origin != origin:
        raise HTTPException(status_code=403, detail="Validation origin is not allowed for this client.")
    report = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "validated_at": req.validated_at,
        "actions": req.actions,
    }
    client_store.save_adapter_validation_report(safe_site, report)
    validation = dict_value(client_store.get_client_detail(safe_site).get("vertical_config") or {}, "validation")
    return {
        "site_id": safe_site,
        "summary": validation.get("summary") or {},
    }


def process_policy_event(
    req: WidgetPolicyEventRequest,
    *,
    client_store: ClientEventStore,
    safe_site_id: SiteIdSanitizer,
    safe_script_base_url: OriginSanitizer,
    safe_client_detail: ClientDetailLoader,
) -> dict[str, Any]:
    safe_site = safe_site_id(req.site_id)
    origin = allowed_event_origin(req.origin, safe_site, "Policy event", safe_script_base_url, safe_client_detail)
    event = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "occurred_at": req.occurred_at,
        "action": req.action,
        "status": req.status,
        "reason": req.reason,
        "policy": req.policy,
    }
    client_store.save_client_policy_event(safe_site, event)
    return {"site_id": safe_site, "status": "ok"}


def process_action_execution_event(
    req: WidgetActionExecutionEventRequest,
    *,
    client_store: ClientEventStore,
    safe_site_id: SiteIdSanitizer,
    safe_script_base_url: OriginSanitizer,
    safe_client_detail: ClientDetailLoader,
) -> dict[str, Any]:
    safe_site = safe_site_id(req.site_id)
    origin = allowed_event_origin(req.origin, safe_site, "Action event", safe_script_base_url, safe_client_detail)
    event = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "occurred_at": req.occurred_at,
        "request_id": req.request_id,
        "turn_id": req.turn_id,
        "sequence": req.sequence,
        "action": req.action,
        "status": req.status,
        "stage": req.stage,
        "reason": req.reason,
        "duration_ms": req.duration_ms,
        "param_keys": req.param_keys,
        "requested_url": same_origin_public_url(req.requested_url, origin) if req.requested_url else "",
        "final_url": same_origin_public_url(req.final_url, origin) if req.final_url else "",
        "evidence": req.evidence,
    }
    client_store.save_client_action_event(safe_site, event)
    return {"site_id": safe_site, "status": "ok"}


def process_interaction_event(
    req: WidgetInteractionEventRequest,
    *,
    client_store: ClientEventStore,
    safe_site_id: SiteIdSanitizer,
    safe_script_base_url: OriginSanitizer,
    safe_client_detail: ClientDetailLoader,
) -> dict[str, Any]:
    safe_site = safe_site_id(req.site_id)
    origin = allowed_event_origin(req.origin, safe_site, "Interaction", safe_script_base_url, safe_client_detail)
    event = {
        "source": "browser_runtime",
        "origin": origin,
        "url": same_origin_public_url(req.url, origin),
        "occurred_at": req.occurred_at,
        "event_type": req.event_type,
        "label": req.label,
        "selector": req.selector,
        "tag": req.tag,
        "href": req.href,
        "form": req.form,
    }
    client_store.save_client_interaction_event(safe_site, event)
    return {"site_id": safe_site, "status": "ok"}


def allowed_event_origin(
    raw_origin: str,
    safe_site: str,
    event_label: str,
    safe_script_base_url: OriginSanitizer,
    safe_client_detail: ClientDetailLoader,
) -> str:
    origin = safe_script_base_url(raw_origin)
    if not origin:
        raise HTTPException(status_code=400, detail=f"{event_label} origin must be http or https.")
    client = safe_client_detail(safe_site)
    allowed_origin = safe_script_base_url(str(client.get("allowed_origin") or ""))
    if allowed_origin and allowed_origin != origin:
        raise HTTPException(status_code=403, detail=f"{event_label} origin is not allowed for this client.")
    return origin


def same_origin_public_url(url: str, origin: str) -> str:
    clean_url = str(url or "").strip()[:600]
    try:
        parsed = urlparse(clean_url)
    except ValueError:
        return origin
    if not parsed.scheme or not parsed.netloc:
        return origin
    if f"{parsed.scheme}://{parsed.netloc}" != origin:
        return origin
    return clean_url
