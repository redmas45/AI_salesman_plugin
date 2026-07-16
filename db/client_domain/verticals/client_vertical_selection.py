"""Client vertical selection and presentation helpers."""

from __future__ import annotations

from typing import Any, Callable

from agent.verticals.base import VerticalDefinition
from agent.verticals.registry import get_vertical, list_verticals as registry_list_verticals


def list_verticals() -> list[dict[str, Any]]:
    return [vertical.to_dict() for vertical in registry_list_verticals()]


def get_vertical_detail(vertical_key: str, default_key: str) -> dict[str, Any]:
    return validated_vertical(vertical_key, default_key).to_dict()


def get_client_vertical_key(
    site_id: str,
    *,
    client_row: Callable[[str], dict[str, Any] | None],
    default_key: str,
) -> str:
    client = client_row(site_id)
    if not client:
        return default_key
    return client_vertical(client.get("vertical_key"), default_key).key


def validated_vertical(vertical_key: str | None, default_key: str) -> VerticalDefinition:
    try:
        return get_vertical(vertical_key or default_key)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def client_vertical(vertical_key: str | None, default_key: str) -> VerticalDefinition:
    try:
        return get_vertical(vertical_key or default_key)
    except ValueError:
        return get_vertical(default_key)


def plan_for_vertical(plan: str, vertical: VerticalDefinition, *, default_plan: str) -> str:
    clean_plan = str(plan or "").strip()
    if not clean_plan:
        raise ValueError("Plan is required.")
    if clean_plan == default_plan and vertical.default_plan_label != default_plan:
        return vertical.default_plan_label
    return clean_plan


def risk_level_text(value: str | None, fallback: str) -> str:
    clean_value = str(value or "").strip().lower()
    return clean_value if clean_value in {"low", "medium", "high"} else fallback
