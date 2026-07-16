"""Typed discovery profile model shared by the discovery profile catalog."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerticalDiscoveryProfile:
    """Signals AI Hub uses to classify, crawl, extract, and control a website."""

    key: str
    classification_keywords: tuple[str, ...] = ()
    route_keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)
    route_actions: dict[str, str] = field(default_factory=dict)
    action_labels: dict[str, tuple[str, ...]] = field(default_factory=dict)
    primary_actions: tuple[str, ...] = ()
    form_action: str = "CAPTURE_LEAD"
    discovery_paths: tuple[str, ...] = ()
    high_value_url_keywords: tuple[str, ...] = ()
    jsonld_types: tuple[str, ...] = ()
    text_signals: tuple[str, ...] = ()
    entity_type: str = ""
    category_label: str = ""
    provider_label: str = "Provider"
