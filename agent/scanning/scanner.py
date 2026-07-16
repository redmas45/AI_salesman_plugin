"""
AI Readiness Scanner — per-client capability report.

Probes a client website to detect platform (Shopify, WooCommerce, custom),
catalog availability, variant support, cart APIs, and checkout capability.
Returns a ReadinessReport with confidence scores for each capability.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

import config

from agent.actions.registry import normalize_action_name
from agent.action_helpers.barrier_policy import build_barrier_action_policy
from agent.site_helpers.local_urls import local_runtime_url_candidates
from agent.scanning.scanner_action_capabilities import (
    action_capability,
    adapter_action_capabilities,
    validated_action_caps,
)
from agent.scanning.scanner_client_hooks import (
    client_hook_capabilities,
    is_client_hook_adapter,
    merge_capability,
)
from agent.scanning.scanner_models import ReadinessReport, SiteCapability
from agent.scanning.scanner_platform import base_url, detect_platform, match_signals
from agent.scanning.scanner_probe_config import (
    GENERIC_CART_PROBES,
    GENERIC_CATALOG_PROBES,
    MAX_PROBE_URLS,
    SCAN_TIMEOUT_SECONDS,
    SHOPIFY_CART_PROBES,
    SHOPIFY_CATALOG_PROBES,
    SHOPIFY_CHECKOUT_PROBES,
    SHOPIFY_SIGNALS,
    WOOCOMMERCE_CART_PROBES,
    WOOCOMMERCE_CATALOG_PROBES,
    WOOCOMMERCE_CHECKOUT_PROBES,
    WOOCOMMERCE_SIGNALS,
)
from agent.scanning.scanner_runtime_capabilities import (
    adapter_action_count,
    barrier_capabilities,
    flow_capabilities,
    regression_capabilities,
    rehearsal_capabilities,
    validated_adapter_action_count,
)
from agent.scanning.scanner_vertical_capabilities import (
    active_knowledge_items,
    active_product_items,
    configured_action_names,
    expected_action_status,
    is_ecommerce_vertical,
    vertical_data_capabilities,
    vertical_expected_action_capabilities,
)
from agent.verticals.registry import get_vertical
from db.core.database import tenant_catalog_stats
from db.knowledge_base.knowledge_items import knowledge_stats

logger = logging.getLogger(__name__)

# Internal helpers

def _base_url(site_url: str) -> str:
    """Normalise to scheme://host with no trailing slash."""
    return base_url(site_url)


async def _probe_url(
    client: httpx.AsyncClient,
    url: str,
    *,
    method: str = "GET",
    accept: str = "application/json",
) -> tuple[int, str, dict[str, str]]:
    """
    Probe a URL, return (status_code, body_text, headers).

    Returns (0, "", {}) on connection/timeout errors.
    """
    try:
        if method == "HEAD":
            resp = await client.head(url, headers={"Accept": accept})
            return resp.status_code, "", dict(resp.headers)
        resp = await client.get(url, headers={"Accept": accept})
        return resp.status_code, resp.text[:50_000], dict(resp.headers)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.debug("Probe failed for %s: %s", url, exc)
        return 0, "", {}


def _match_signals(
    signals: tuple[tuple[str, str, float], ...],
    html: str,
    headers: dict[str, str],
) -> float:
    """Sum signal weights that match the HTML or headers."""
    return match_signals(signals, html, headers)


def _detect_platform(
    html: str,
    headers: dict[str, str],
) -> tuple[str, float]:
    """Detect the ecommerce platform from homepage HTML and headers."""
    return detect_platform(
        html,
        headers,
        shopify_signals=SHOPIFY_SIGNALS,
        woocommerce_signals=WOOCOMMERCE_SIGNALS,
    )


def _is_client_hook_adapter(adapter_name: str, site_id: str) -> bool:
    """Return whether the configured adapter is a verified client hook."""
    return is_client_hook_adapter(adapter_name)


def _client_hook_capabilities(adapter_name: str) -> list[SiteCapability]:
    """Capabilities supplied by first-party client hook integrations."""
    return client_hook_capabilities(adapter_name, SiteCapability)


def _merge_capability(
    detected: SiteCapability,
    override: SiteCapability | None,
) -> SiteCapability:
    """Prefer an explicit adapter capability over weaker HTTP probes."""
    return merge_capability(detected, override)


async def _check_catalog(
    base: str,
    platform: str,
    client: httpx.AsyncClient,
) -> SiteCapability:
    """Check whether the site has a usable product catalog API."""
    probes: list[str] = []
    if platform == "shopify":
        probes = [f"{base}{p}" for p in SHOPIFY_CATALOG_PROBES]
    elif platform == "woocommerce":
        probes = [f"{base}{p}" for p in WOOCOMMERCE_CATALOG_PROBES]
    probes.extend(f"{base}{p}" for p in GENERIC_CATALOG_PROBES)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_probes: list[str] = []
    for url in probes:
        if url not in seen:
            seen.add(url)
            unique_probes.append(url)

    for url in unique_probes:
        code, body, _ = await _probe_url(client, url)
        if code == 200 and body.strip().startswith(("{", "[")):
            return SiteCapability(
                name="catalog",
                supported=True,
                confidence=0.9,
                evidence=f"JSON catalog at {url}",
            )
        if code == 200:
            return SiteCapability(
                name="catalog",
                supported=True,
                confidence=0.6,
                evidence=f"Non-JSON 200 at {url}",
            )

    return SiteCapability(
        name="catalog",
        supported=False,
        confidence=0.3,
        evidence="No catalog API found; HTML crawl fallback only",
    )


async def _check_variants(
    base: str,
    platform: str,
    client: httpx.AsyncClient,
) -> SiteCapability:
    """Check whether the site's products include variant data."""
    if platform == "shopify":
        url = f"{base}/products.json?limit=1"
        code, body, _ = await _probe_url(client, url)
        if code == 200 and '"variants"' in body:
            return SiteCapability(
                name="variants",
                supported=True,
                confidence=0.9,
                evidence="Shopify product JSON includes variants array",
            )

    if platform == "woocommerce":
        url = f"{base}/wp-json/wc/store/products?per_page=1"
        code, body, _ = await _probe_url(client, url)
        if code == 200 and ('"variations"' in body or '"attributes"' in body):
            return SiteCapability(
                name="variants",
                supported=True,
                confidence=0.8,
                evidence="WooCommerce product API includes variations/attributes",
            )

    return SiteCapability(
        name="variants",
        supported=False,
        confidence=0.4,
        evidence="No variant data detected in product API responses",
        blocking=False,
    )


async def _check_cart(
    base: str,
    platform: str,
    client: httpx.AsyncClient,
) -> SiteCapability:
    """Check whether the site has usable cart APIs or a same-origin cart page."""
    probes: list[str] = []
    if platform == "shopify":
        probes = [f"{base}{p}" for p in SHOPIFY_CART_PROBES]
    elif platform == "woocommerce":
        probes = [f"{base}{p}" for p in WOOCOMMERCE_CART_PROBES]

    for url in probes:
        code, body, _ = await _probe_url(client, url)
        if code == 200:
            return SiteCapability(
                name="cart",
                supported=True,
                confidence=0.85 if platform == "shopify" else 0.7,
                evidence=f"Cart API responsive at {url}",
            )
        if code in (401, 403):
            return SiteCapability(
                name="cart",
                supported=True,
                confidence=0.5,
                evidence=f"Cart API exists at {url} but requires auth (HTTP {code})",
            )

    page_probes = [f"{base}{p}" for p in GENERIC_CART_PROBES]
    for url in page_probes:
        code, _, _ = await _probe_url(client, url, method="HEAD", accept="text/html")
        if code in (200, 301, 302, 303, 307, 308):
            return SiteCapability(
                name="cart",
                supported=True,
                confidence=0.55 if platform == "custom" else 0.45,
                evidence=f"Cart page at {url} (HTTP {code}); item insertion still depends on adapter action validation.",
            )

    return SiteCapability(
        name="cart",
        supported=False,
        confidence=0.3,
        evidence="No cart API endpoints detected",
    )


async def _check_checkout(
    base: str,
    platform: str,
    client: httpx.AsyncClient,
) -> SiteCapability:
    """Check whether the site has a usable checkout page."""
    probes: list[str] = []
    if platform == "shopify":
        probes = [f"{base}{p}" for p in SHOPIFY_CHECKOUT_PROBES]
    elif platform == "woocommerce":
        probes = [f"{base}{p}" for p in WOOCOMMERCE_CHECKOUT_PROBES]
    else:
        probes = [f"{base}/checkout"]

    for url in probes:
        code, _, headers = await _probe_url(client, url, method="HEAD", accept="text/html")
        if code in (200, 301, 302, 303, 307, 308):
            return SiteCapability(
                name="checkout",
                supported=True,
                confidence=0.7 if platform in ("shopify", "woocommerce") else 0.4,
                evidence=f"Checkout page at {url} (HTTP {code})",
            )

    return SiteCapability(
        name="checkout",
        supported=False,
        confidence=0.3,
        evidence="No checkout page detected",
    )


# ── Public API ──────────────────────────────────────────────────────────────

def _adapter_action_capabilities(vertical_config: dict[str, Any]) -> list[SiteCapability]:
    """Return capabilities from generated adapter actions and browser validation."""
    return adapter_action_capabilities(vertical_config, SiteCapability)


def _validated_action_caps(actions: dict[str, Any], validation_actions: dict[str, Any]) -> list[SiteCapability]:
    return validated_action_caps(actions, validation_actions, SiteCapability)


def _action_capability(action_name: str, action_config: Any, evidence: Any) -> SiteCapability:
    return action_capability(action_name, action_config, evidence, SiteCapability)


def _flow_capabilities(vertical_config: dict[str, Any]) -> list[SiteCapability]:
    return flow_capabilities(vertical_config, SiteCapability)


def _rehearsal_capabilities(vertical_config: dict[str, Any]) -> list[SiteCapability]:
    return rehearsal_capabilities(vertical_config, SiteCapability)


def _adapter_action_count(vertical_config: dict[str, Any]) -> int:
    return adapter_action_count(vertical_config)


def _validated_adapter_action_count(vertical_config: dict[str, Any]) -> int:
    return validated_adapter_action_count(vertical_config)


def _regression_capabilities(vertical_config: dict[str, Any]) -> list[SiteCapability]:
    return regression_capabilities(vertical_config, SiteCapability)


def _barrier_capabilities(vertical_config: dict[str, Any], vertical_key: str) -> list[SiteCapability]:
    return barrier_capabilities(vertical_config, vertical_key, SiteCapability, build_barrier_action_policy)


def _is_ecommerce_vertical(vertical_key: str) -> bool:
    return is_ecommerce_vertical(vertical_key)


def _vertical_data_capabilities(site_id: str, vertical_key: str) -> list[SiteCapability]:
    return vertical_data_capabilities(site_id, vertical_key, SiteCapability, get_vertical, knowledge_stats, logger)


def _vertical_expected_action_capabilities(
    site_id: str,
    vertical_key: str,
    vertical_config: dict[str, Any],
    commerce_capabilities: list[SiteCapability] | None = None,
) -> list[SiteCapability]:
    """Compare a vertical's expected action contract with this client's generated runtime config."""
    return vertical_expected_action_capabilities(
        site_id,
        vertical_key,
        vertical_config,
        commerce_capabilities,
        SiteCapability,
        get_vertical,
        normalize_action_name,
        knowledge_stats,
        tenant_catalog_stats,
        logger,
    )


def _configured_action_names(vertical_config: dict[str, Any]) -> set[str]:
    return configured_action_names(vertical_config, normalize_action_name)


def _active_knowledge_items(site_id: str) -> int:
    return active_knowledge_items(site_id, knowledge_stats, logger)


def _active_product_items(site_id: str) -> int:
    return active_product_items(site_id, tenant_catalog_stats, logger)


def _expected_action_status(
    action: str,
    configured_actions: set[str],
    active_items: int,
    entity_label_plural: str,
    commerce_caps: dict[str, SiteCapability] | None = None,
) -> tuple[bool, float, str]:
    return expected_action_status(action, configured_actions, active_items, entity_label_plural, commerce_caps)


async def scan_site(
    site_url: str,
    site_id: str,
    *,
    adapter_name: str = "",
    vertical_key: str = "",
    vertical_config: dict[str, Any] | None = None,
    timeout: int = SCAN_TIMEOUT_SECONDS,
) -> ReadinessReport:
    """
    Run a non-destructive readiness scan against a client website.

    Returns a ReadinessReport with platform detection and capability probes.
    Does not modify any data. Safe to call repeatedly.
    """
    start = time.monotonic()
    base_candidates = local_runtime_url_candidates(_base_url(site_url))

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        verify=config.CLIENT_TLS_VERIFY,
    ) as client:
        # Fetch homepage for platform detection
        base = base_candidates[0] if base_candidates else _base_url(site_url)
        home_code = 0
        home_html = ""
        home_headers: dict[str, str] = {}
        for candidate_base in base_candidates or [base]:
            home_code, home_html, home_headers = await _probe_url(
                client, candidate_base, accept="text/html",
            )
            if home_code:
                base = candidate_base
                break
        if home_code == 0:
            elapsed = (time.monotonic() - start) * 1000
            return ReadinessReport(
                site_id=site_id,
                site_url=site_url,
                platform="unreachable",
                platform_confidence=0.0,
                capabilities=[],
                scanned_at=datetime.now(timezone.utc).isoformat(),
                scan_duration_ms=elapsed,
            )

        platform, platform_confidence = _detect_platform(home_html, home_headers)

        commerce_caps: list[SiteCapability] = []
        if _is_ecommerce_vertical(vertical_key):
            catalog = await _check_catalog(base, platform, client)
            variants = await _check_variants(base, platform, client)
            cart = await _check_cart(base, platform, client)
            checkout = await _check_checkout(base, platform, client)

            if _is_client_hook_adapter(adapter_name, site_id):
                hook_caps = {cap.name: cap for cap in _client_hook_capabilities(adapter_name)}
                cart = _merge_capability(cart, hook_caps.get("cart"))
                checkout = _merge_capability(checkout, hook_caps.get("checkout"))
            commerce_caps = [catalog, variants, cart, checkout]

    elapsed = (time.monotonic() - start) * 1000
    data_caps = _vertical_data_capabilities(site_id, vertical_key) if not _is_ecommerce_vertical(vertical_key) else []
    adapter_caps = _adapter_action_capabilities(vertical_config or {})
    expected_action_caps = _vertical_expected_action_capabilities(site_id, vertical_key, vertical_config or {}, commerce_caps)
    flow_caps = _flow_capabilities(vertical_config or {})
    barrier_caps = _barrier_capabilities(vertical_config or {}, vertical_key)
    rehearsal_caps = _rehearsal_capabilities(vertical_config or {})
    regression_caps = _regression_capabilities(vertical_config or {})

    report = ReadinessReport(
        site_id=site_id,
        site_url=site_url,
        platform=platform,
        platform_confidence=platform_confidence,
        capabilities=[
            *commerce_caps,
            *data_caps,
            *adapter_caps,
            *expected_action_caps,
            *flow_caps,
            *barrier_caps,
            *rehearsal_caps,
            *regression_caps,
        ],
        scanned_at=datetime.now(timezone.utc).isoformat(),
        scan_duration_ms=elapsed,
    )

    logger.info(
        "Readiness scan for %s (%s): platform=%s(%.2f) capabilities=%d in %.0fms",
        site_id,
        site_url,
        platform,
        platform_confidence,
        len(report.capabilities),
        elapsed,
    )

    return report
