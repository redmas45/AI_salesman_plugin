"""Browser-discovered platform and barrier hint normalization."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from agent.flows.flow_barriers import build_flow_barrier_report


class BrowserDiscoveryInput(Protocol):
    site_id: str
    origin: str
    url: str
    title: str
    text_sample: str
    platform_hints: dict[str, Any]
    barrier_hints: dict[str, Any]


def detect_platform(platform_hints: dict[str, Any]) -> str:
    if platform_hints.get("shopify"):
        return "shopify"
    if platform_hints.get("woocommerce"):
        return "woocommerce"
    return "auto"


def browser_barrier_report(data: BrowserDiscoveryInput) -> dict[str, Any]:
    report = build_flow_barrier_report(
        [
            {
                "url": data.url,
                "title": data.title,
                "text_sample": data.text_sample,
                "platform_hints": data.platform_hints,
                "barrier_hints": data.barrier_hints,
            }
        ],
        site_id=data.site_id,
        site_url=data.origin,
    )
    return report.to_dict()


def safe_barrier_hints(value: Any, clean_text: Callable[[Any], str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    hints: dict[str, Any] = {}
    for key in ("iframe_count", "password_inputs", "file_uploads", "date_inputs"):
        hints[key] = safe_count(value.get(key))
    hints["captcha"] = bool(value.get("captcha"))
    for key in (
        "iframe_sources",
        "captcha_providers",
        "payment_providers",
        "calendar_providers",
        "map_providers",
        "external_action_hosts",
    ):
        hints[key] = safe_text_list(value.get(key), 20, 240, clean_text)
    return hints


def safe_count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def safe_text_list(
    value: Any,
    limit: int,
    length: int,
    clean_text: Callable[[Any], str],
) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_text(item)[:length] for item in value[:limit] if clean_text(item)]
