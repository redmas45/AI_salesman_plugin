"""Shared vertical definition types."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CrmTabDefinition:
    """One CRM client workspace tab exposed by a vertical."""

    id: str
    label: str


@dataclass(frozen=True)
class VerticalDefinition:
    """Runtime metadata that changes AI Hub behavior for one client domain."""

    key: str
    label: str
    risk_level: RiskLevel
    entity_label_singular: str
    entity_label_plural: str
    default_plan_label: str
    crm_tabs: tuple[CrmTabDefinition, ...]
    entity_types: tuple[str, ...]
    readiness_checks: tuple[str, ...]
    action_types: tuple[str, ...]

    def to_dict(self) -> dict:
        """Return a JSON-ready representation for CRM APIs."""
        return asdict(self)


def tabs(*items: tuple[str, str]) -> tuple[CrmTabDefinition, ...]:
    """Build tab definitions without repeating dataclass names in vertical modules."""
    return tuple(CrmTabDefinition(id=tab_id, label=label) for tab_id, label in items)
