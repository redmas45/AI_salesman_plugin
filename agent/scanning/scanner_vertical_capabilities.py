"""Readiness capability builders for vertical data and expected actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent.scanning.scanner_runtime_capabilities import CapabilityFactory

ENTITY_DISPLAY_ACTIONS = frozenset({"SHOW_ENTITIES", "COMPARE_ENTITIES", "FILTER_ENTITIES", "SORT_ENTITIES"})
PRODUCT_DISPLAY_ACTIONS = frozenset({"SHOW_PRODUCTS", "SHOW_COMPARISON", "FILTER_PRODUCTS", "SORT_PRODUCTS"})

VerticalResolver = Callable[[str], Any]
StatsProvider = Callable[[str], dict[str, Any]]
ActionNormalizer = Callable[[str], str]


def is_ecommerce_vertical(vertical_key: str) -> bool:
    return str(vertical_key or "").strip().lower().replace("-", "_") == "ecommerce"


def vertical_data_capabilities(
    site_id: str,
    vertical_key: str,
    capability: CapabilityFactory,
    get_vertical: VerticalResolver,
    knowledge_stats: StatsProvider,
    logger: Any,
) -> list[Any]:
    try:
        vertical = get_vertical(vertical_key)
    except ValueError:
        vertical = get_vertical("generic")
    try:
        stats = knowledge_stats(site_id)
    except Exception as exc:
        logger.warning("Knowledge stats unavailable during readiness scan for %s: %s", site_id, exc)
        stats = {}

    active_items = int(stats.get("active_items") or 0)
    entity_types = int(stats.get("entity_types") or 0)
    missing_embeddings = int(stats.get("missing_embeddings") or 0)
    entity_name = vertical.entity_label_plural.replace(" ", "_")
    readable_entity = vertical.entity_label_plural
    return [
        capability(
            entity_name,
            active_items > 0,
            0.9 if active_items > 0 else 0.25,
            f"{active_items} active {readable_entity} indexed in AI Hub data storage.",
        ),
        capability(
            "groups",
            entity_types > 0,
            0.85 if entity_types > 0 else 0.25,
            f"{entity_types} source group(s) detected across loaded {readable_entity}.",
        ),
        capability(
            "vectors",
            active_items > 0 and missing_embeddings == 0,
            0.9 if active_items > 0 and missing_embeddings == 0 else 0.35,
            f"{missing_embeddings} active {readable_entity} still need vector embeddings.",
        ),
    ]


def vertical_expected_action_capabilities(
    site_id: str,
    vertical_key: str,
    vertical_config: dict[str, Any],
    commerce_capabilities: list[Any] | None,
    capability: CapabilityFactory,
    get_vertical: VerticalResolver,
    normalize_action_name: ActionNormalizer,
    knowledge_stats: StatsProvider,
    tenant_catalog_stats: StatsProvider,
    logger: Any,
) -> list[Any]:
    try:
        vertical = get_vertical(vertical_key)
    except ValueError:
        vertical = get_vertical("generic")

    expected_actions = [normalize_action_name(action) for action in vertical.action_types]
    expected_actions = [action for action in dict.fromkeys(expected_actions) if action]
    if not expected_actions:
        return []

    configured_actions = configured_action_names(vertical_config, normalize_action_name)
    active_items = (
        active_product_items(site_id, tenant_catalog_stats, logger)
        if is_ecommerce_vertical(vertical.key)
        else active_knowledge_items(site_id, knowledge_stats, logger)
    )
    commerce_caps = {cap.name: cap for cap in commerce_capabilities or []}
    rows: list[Any] = []
    supported_count = 0

    for action in expected_actions:
        supported, confidence, evidence = expected_action_status(
            action,
            configured_actions,
            active_items,
            vertical.entity_label_plural,
            commerce_caps,
        )
        if supported:
            supported_count += 1
        rows.append(capability(f"expected_action:{action}", supported, confidence, evidence))

    total = len(expected_actions)
    rows.insert(
        0,
        capability(
            "domain_action_coverage",
            supported_count == total,
            0.9 if supported_count == total else 0.55 if supported_count else 0.25,
            (
                f"{supported_count}/{total} expected {vertical.label} action(s) are covered. "
                f"Missing: {', '.join(action for action in expected_actions if not expected_action_status(action, configured_actions, active_items, vertical.entity_label_plural, commerce_caps)[0]) or 'none'}."
            ),
        ),
    )
    return rows


def configured_action_names(
    vertical_config: dict[str, Any],
    normalize_action_name: ActionNormalizer,
) -> set[str]:
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict):
        return set()
    return {normalize_action_name(action) for action in actions if normalize_action_name(str(action))}


def active_knowledge_items(site_id: str, knowledge_stats: StatsProvider, logger: Any) -> int:
    try:
        stats = knowledge_stats(site_id)
    except Exception as exc:
        logger.warning("Knowledge stats unavailable during domain action scan for %s: %s", site_id, exc)
        return 0
    return int(stats.get("active_items") or 0)


def active_product_items(site_id: str, tenant_catalog_stats: StatsProvider, logger: Any) -> int:
    try:
        stats = tenant_catalog_stats(site_id)
    except Exception as exc:
        logger.warning("Catalog stats unavailable during domain action scan for %s: %s", site_id, exc)
        return 0
    return int(stats.get("active_products") or 0)


def expected_action_status(
    action: str,
    configured_actions: set[str],
    active_items: int,
    entity_label_plural: str,
    commerce_caps: dict[str, Any] | None = None,
) -> tuple[bool, float, str]:
    if action in configured_actions:
        return True, 0.85, f"{action} is mapped in generated adapter actions."
    if action == "CHECKOUT":
        checkout = (commerce_caps or {}).get("checkout")
        if checkout and checkout.supported:
            return True, max(0.65, checkout.confidence), f"CHECKOUT can use detected checkout capability. {checkout.evidence}"
    if action in ENTITY_DISPLAY_ACTIONS and active_items > 0:
        return True, 0.8, f"{action} can use AI Hub entity rendering with {active_items} active {entity_label_plural}."
    if action in PRODUCT_DISPLAY_ACTIONS and active_items > 0:
        return True, 0.8, f"{action} can use AI Hub product rendering with {active_items} active {entity_label_plural}."
    if action in ENTITY_DISPLAY_ACTIONS:
        return False, 0.3, f"{action} needs active {entity_label_plural} in AI Hub data storage."
    if action in PRODUCT_DISPLAY_ACTIONS:
        return False, 0.3, f"{action} needs active {entity_label_plural} in AI Hub data storage."
    return False, 0.25, f"{action} is expected for this vertical but is not mapped in generated adapter actions yet."
