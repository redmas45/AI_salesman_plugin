"""
AI Readiness Scanner — per-client capability report.

Probes a client website to detect platform (Shopify, WooCommerce, custom),
catalog availability, variant support, cart APIs, and checkout capability.
Returns a ReadinessReport with confidence scores for each capability.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from agent.actions.registry import normalize_action_name
from agent.barrier_policy import build_barrier_action_policy
from agent.local_urls import local_runtime_url_candidates
from agent.verticals.registry import get_vertical
from db.database import tenant_catalog_stats
from db.knowledge import knowledge_stats

logger = logging.getLogger(__name__)

SCAN_TIMEOUT_SECONDS = 10
MAX_PROBE_URLS = 20
CLIENT_HOOK_ADAPTER_NAMES = (
    "client-hook",
    "client_hook",
    "custom-hook",
    "custom_hook",
    "verified-hook",
    "verified_hook",
)
ENTITY_DISPLAY_ACTIONS = frozenset({"SHOW_ENTITIES", "COMPARE_ENTITIES", "FILTER_ENTITIES", "SORT_ENTITIES"})
PRODUCT_DISPLAY_ACTIONS = frozenset({"SHOW_PRODUCTS", "SHOW_COMPARISON", "FILTER_PRODUCTS", "SORT_PRODUCTS"})

# ── Platform detection signals ──────────────────────────────────────────────

SHOPIFY_SIGNALS = (
    ("meta", r'content=["\']shopify', 0.4),
    ("html", r'cdn\.shopify\.com', 0.3),
    ("html", r'Shopify\.shop', 0.3),
    ("html", r'shopify-section', 0.2),
    ("header", r'x-shopify', 0.4),
)

WOOCOMMERCE_SIGNALS = (
    ("html", r'woocommerce', 0.3),
    ("html", r'wc-block', 0.2),
    ("html", r'wp-content/plugins/woocommerce', 0.4),
    ("html", r'wc_add_to_cart_params', 0.3),
    ("header", r'x-powered-by.*wordpress', 0.2),
)

# ── Probe endpoints ────────────────────────────────────────────────────────

SHOPIFY_CATALOG_PROBES = (
    "/products.json",
    "/collections/all/products.json",
)

WOOCOMMERCE_CATALOG_PROBES = (
    "/wp-json/wc/store/products?per_page=1",
    "/wp-json/wc/store/v1/products?per_page=1",
)

GENERIC_CATALOG_PROBES = (
    "/api/products",
    "/api/products.json",
)

SHOPIFY_CART_PROBES = (
    "/cart.js",
    "/cart/add.js",
)

WOOCOMMERCE_CART_PROBES = (
    "/wp-json/wc/store/cart",
)

GENERIC_CART_PROBES = (
    "/cart",
)

SHOPIFY_CHECKOUT_PROBES = (
    "/checkout",
)

WOOCOMMERCE_CHECKOUT_PROBES = (
    "/checkout",
)


# ── Data models ─────────────────────────────────────────────────────────────

@dataclass
class SiteCapability:
    """One capability detection result."""

    name: str
    supported: bool
    confidence: float
    evidence: str
    blocking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadinessReport:
    """Full readiness scan output for one client site."""

    site_id: str
    site_url: str
    platform: str
    platform_confidence: float
    capabilities: list[SiteCapability] = field(default_factory=list)
    scanned_at: str = ""
    scan_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "site_url": self.site_url,
            "platform": self.platform,
            "platform_confidence": round(self.platform_confidence, 2),
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "scanned_at": self.scanned_at,
            "scan_duration_ms": round(self.scan_duration_ms, 1),
        }

    def capability(self, name: str) -> SiteCapability | None:
        """Lookup a capability by name."""
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None


# ── Internal helpers ────────────────────────────────────────────────────────

def _base_url(site_url: str) -> str:
    """Normalise to scheme://host with no trailing slash."""
    from urllib.parse import urlparse
    parsed = urlparse(site_url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc or parsed.path.split("/")[0]
    return f"{scheme}://{host}"


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
    score = 0.0
    header_blob = " ".join(f"{k}: {v}" for k, v in headers.items()).lower()
    for source, pattern, weight in signals:
        target = html if source in ("html", "meta") else header_blob
        if re.search(pattern, target, re.IGNORECASE):
            score += weight
    return min(score, 1.0)


def _detect_platform(
    html: str,
    headers: dict[str, str],
) -> tuple[str, float]:
    """Detect the ecommerce platform from homepage HTML and headers."""
    shopify_score = _match_signals(SHOPIFY_SIGNALS, html, headers)
    woo_score = _match_signals(WOOCOMMERCE_SIGNALS, html, headers)

    if shopify_score >= 0.4 and shopify_score > woo_score:
        return "shopify", shopify_score
    if woo_score >= 0.4 and woo_score > shopify_score:
        return "woocommerce", woo_score
    if shopify_score > 0 or woo_score > 0:
        best = max(shopify_score, woo_score)
        platform = "shopify" if shopify_score >= woo_score else "woocommerce"
        return platform, best

    return "custom", 0.0


def _is_client_hook_adapter(adapter_name: str, site_id: str) -> bool:
    """Return whether the configured adapter is a verified client hook."""
    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        f"{adapter_name or ''}".strip().lower(),
    )
    return any(token in normalized for token in CLIENT_HOOK_ADAPTER_NAMES)


def _client_hook_capabilities(adapter_name: str) -> list[SiteCapability]:
    """Capabilities supplied by first-party client hook integrations."""
    evidence = f"Client adapter '{adapter_name}' exposes verified first-party hooks"
    return [
        SiteCapability("cart", True, 0.95, evidence),
        SiteCapability("checkout", True, 0.9, evidence),
    ]


def _merge_capability(
    detected: SiteCapability,
    override: SiteCapability | None,
) -> SiteCapability:
    """Prefer an explicit adapter capability over weaker HTTP probes."""
    if override is None:
        return detected
    if override.supported and not detected.supported:
        return override
    if override.supported and override.confidence > detected.confidence:
        return override
    return detected


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
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict) or not actions:
        return []

    validation = vertical_config.get("validation")
    validation_actions = validation.get("actions") if isinstance(validation, dict) else {}
    if not isinstance(validation_actions, dict):
        validation_actions = {}

    capabilities = [
        SiteCapability(
            name="adapter_action_map",
            supported=True,
            confidence=0.85,
            evidence=f"Generated adapter exposes {len(actions)} action(s).",
        )
    ]
    capabilities.extend(_validated_action_caps(actions, validation_actions))
    return capabilities


def _validated_action_caps(actions: dict[str, Any], validation_actions: dict[str, Any]) -> list[SiteCapability]:
    capabilities: list[SiteCapability] = []
    for action_name, action_config in actions.items():
        evidence = validation_actions.get(action_name)
        capabilities.append(_action_capability(action_name, action_config, evidence))
    return capabilities


def _action_capability(action_name: str, action_config: Any, evidence: Any) -> SiteCapability:
    if isinstance(evidence, dict):
        supported = bool(evidence.get("supported") or evidence.get("repair"))
        confidence = float(evidence.get("confidence") or 0.55)
        note = str(evidence.get("evidence") or evidence.get("status") or "Browser validation evidence saved.")
        return SiteCapability(f"action:{action_name}", supported, min(max(confidence, 0.0), 1.0), note)

    action_type = action_config.get("type") if isinstance(action_config, dict) else "unknown"
    return SiteCapability(
        name=f"action:{action_name}",
        supported=True,
        confidence=0.6,
        evidence=f"Generated adapter config has a {action_type} target; browser validation is pending.",
    )


def _flow_capabilities(vertical_config: dict[str, Any]) -> list[SiteCapability]:
    flow = vertical_config.get("flow")
    if not isinstance(flow, dict):
        return []
    summary = flow.get("summary") if isinstance(flow.get("summary"), dict) else {}
    pages = int(summary.get("pages") or 0)
    actions = int(summary.get("actions") or 0)
    prompts = len(flow.get("prompt_suggestions") or [])
    engine = str(flow.get("engine") or "unknown")
    adapter_actions = _adapter_action_count(vertical_config)
    graph_supported = pages > 0 and (actions > 0 or adapter_actions > 0)
    graph_confidence = 0.85 if pages > 0 and actions > 0 else 0.75 if graph_supported else 0.35
    if pages > 0 and actions == 0 and adapter_actions > 0:
        graph_evidence = (
            f"{engine} discovery mapped {pages} page(s) and 0 static action candidate(s); "
            f"generated adapter exposes {adapter_actions} runtime action(s) for the JS app."
        )
    else:
        graph_evidence = f"{engine} discovery mapped {pages} page(s) and {actions} action candidate(s)."
    return [
        SiteCapability(
            "flow_graph",
            graph_supported,
            graph_confidence,
            graph_evidence,
        ),
        SiteCapability(
            "flow_prompt_suggestions",
            prompts > 0,
            0.8 if prompts > 0 else 0.25,
            f"Flow discovery generated {prompts} customer prompt suggestion(s).",
        ),
    ]


def _rehearsal_capabilities(vertical_config: dict[str, Any]) -> list[SiteCapability]:
    rehearsal = vertical_config.get("rehearsal")
    if not isinstance(rehearsal, dict):
        return []
    summary = rehearsal.get("summary") if isinstance(rehearsal.get("summary"), dict) else {}
    total = int(summary.get("total") or 0)
    supported = int(summary.get("supported") or 0)
    blocked = int(summary.get("blocked") or 0)
    needs_confirmation = int(summary.get("needs_confirmation") or 0)
    engine = str(rehearsal.get("engine") or "unknown")
    adapter_actions = _adapter_action_count(vertical_config)
    validated_actions = _validated_adapter_action_count(vertical_config)
    fallback_supported = total == 0 and adapter_actions > 0 and validated_actions > 0
    if fallback_supported:
        rehearsal_supported = True
        rehearsal_confidence = 0.75
        rehearsal_evidence = (
            f"{engine} rehearsal had no generated flow targets; "
            f"browser validation supports {validated_actions}/{adapter_actions} adapter action(s)."
        )
        confirmation_supported = True
        confirmation_confidence = 0.6
        confirmation_evidence = (
            "No generated flow targets required confirmation; runtime adapter actions remain governed by action policy."
        )
    else:
        rehearsal_supported = total > 0 and supported > 0 and supported >= max(1, total - blocked)
        rehearsal_confidence = 0.9 if total > 0 and blocked == 0 else 0.7 if supported > 0 else 0.25
        rehearsal_evidence = f"{engine} rehearsal verified {supported}/{total} generated flow target(s); {blocked} blocked."
        confirmation_supported = total > 0
        confirmation_confidence = 0.8 if total > 0 else 0.2
        confirmation_evidence = f"{needs_confirmation} rehearsed action(s) require user confirmation before final completion."
    return [
        SiteCapability(
            "flow_rehearsal",
            rehearsal_supported,
            rehearsal_confidence,
            rehearsal_evidence,
        ),
        SiteCapability(
            "flow_confirmation_policy",
            confirmation_supported,
            confirmation_confidence,
            confirmation_evidence,
        ),
    ]


def _adapter_action_count(vertical_config: dict[str, Any]) -> int:
    actions = vertical_config.get("actions")
    return len(actions) if isinstance(actions, dict) else 0


def _validated_adapter_action_count(vertical_config: dict[str, Any]) -> int:
    validation = vertical_config.get("validation")
    validation_actions = validation.get("actions") if isinstance(validation, dict) else {}
    if not isinstance(validation_actions, dict):
        return 0
    return sum(
        1
        for evidence in validation_actions.values()
        if isinstance(evidence, dict) and (evidence.get("supported") or evidence.get("repair"))
    )


def _regression_capabilities(vertical_config: dict[str, Any]) -> list[SiteCapability]:
    regression = vertical_config.get("regression")
    if not isinstance(regression, dict):
        return []
    summary = regression.get("summary") if isinstance(regression.get("summary"), dict) else {}
    status = str(regression.get("status") or "unknown")
    high = int(summary.get("high") or 0)
    medium = int(summary.get("medium") or 0)
    changes = int(summary.get("changes") or 0)
    supported = status in {"baseline", "stable"} or high == 0
    confidence = 0.9 if status in {"baseline", "stable"} else 0.65 if high == 0 else 0.25
    return [
        SiteCapability(
            "flow_regression",
            supported,
            confidence,
            f"Flow regression status is {status}; {changes} change(s), {high} high severity, {medium} medium severity.",
        )
    ]


def _barrier_capabilities(vertical_config: dict[str, Any], vertical_key: str) -> list[SiteCapability]:
    barriers = vertical_config.get("barriers")
    if not isinstance(barriers, dict):
        return []
    summary = barriers.get("summary") if isinstance(barriers.get("summary"), dict) else {}
    total = int(summary.get("total") or 0)
    high = int(summary.get("high") or 0)
    medium = int(summary.get("medium") or 0)
    keys = summary.get("keys") if isinstance(summary.get("keys"), list) else []
    action_policy = build_barrier_action_policy(vertical_config, vertical_key)
    managed = high > 0 and bool(action_policy.get("handoff_flows"))
    supported = high == 0 or managed
    confidence = 0.9 if total == 0 else 0.75 if managed else 0.65 if high == 0 else 0.2
    handoffs = action_policy.get("handoff_actions") if isinstance(action_policy.get("handoff_actions"), list) else []
    suffix = f" Managed by handoff policy: {', '.join(handoffs[:4])}." if managed and handoffs else ""
    return [
        SiteCapability(
            "flow_barriers",
            supported,
            confidence,
            f"Discovery detected {total} hard-flow barrier(s): {high} high, {medium} medium. {', '.join(str(key) for key in keys[:6])}.{suffix}",
            blocking=not managed,
        )
    ]


def _is_ecommerce_vertical(vertical_key: str) -> bool:
    return str(vertical_key or "").strip().lower().replace("-", "_") == "ecommerce"


def _vertical_data_capabilities(site_id: str, vertical_key: str) -> list[SiteCapability]:
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
        SiteCapability(
            entity_name,
            active_items > 0,
            0.9 if active_items > 0 else 0.25,
            f"{active_items} active {readable_entity} indexed in AI Hub data storage.",
        ),
        SiteCapability(
            "groups",
            entity_types > 0,
            0.85 if entity_types > 0 else 0.25,
            f"{entity_types} source group(s) detected across loaded {readable_entity}.",
        ),
        SiteCapability(
            "vectors",
            active_items > 0 and missing_embeddings == 0,
            0.9 if active_items > 0 and missing_embeddings == 0 else 0.35,
            f"{missing_embeddings} active {readable_entity} still need vector embeddings.",
        ),
    ]


def _vertical_expected_action_capabilities(
    site_id: str,
    vertical_key: str,
    vertical_config: dict[str, Any],
    commerce_capabilities: list[SiteCapability] | None = None,
) -> list[SiteCapability]:
    """Compare a vertical's expected action contract with this client's generated runtime config."""
    try:
        vertical = get_vertical(vertical_key)
    except ValueError:
        vertical = get_vertical("generic")

    expected_actions = [normalize_action_name(action) for action in vertical.action_types]
    expected_actions = [action for action in dict.fromkeys(expected_actions) if action]
    if not expected_actions:
        return []

    configured_actions = _configured_action_names(vertical_config)
    active_items = _active_product_items(site_id) if _is_ecommerce_vertical(vertical.key) else _active_knowledge_items(site_id)
    commerce_caps = {cap.name: cap for cap in commerce_capabilities or []}
    rows: list[SiteCapability] = []
    supported_count = 0

    for action in expected_actions:
        supported, confidence, evidence = _expected_action_status(
            action,
            configured_actions,
            active_items,
            vertical.entity_label_plural,
            commerce_caps,
        )
        if supported:
            supported_count += 1
        rows.append(
            SiteCapability(
                f"expected_action:{action}",
                supported,
                confidence,
                evidence,
            )
        )

    total = len(expected_actions)
    rows.insert(
        0,
        SiteCapability(
            "domain_action_coverage",
            supported_count == total,
            0.9 if supported_count == total else 0.55 if supported_count else 0.25,
            (
                f"{supported_count}/{total} expected {vertical.label} action(s) are covered. "
                f"Missing: {', '.join(action for action in expected_actions if not _expected_action_status(action, configured_actions, active_items, vertical.entity_label_plural, commerce_caps)[0]) or 'none'}."
            ),
        ),
    )
    return rows


def _configured_action_names(vertical_config: dict[str, Any]) -> set[str]:
    actions = vertical_config.get("actions")
    if not isinstance(actions, dict):
        return set()
    return {normalize_action_name(action) for action in actions if normalize_action_name(str(action))}


def _active_knowledge_items(site_id: str) -> int:
    try:
        stats = knowledge_stats(site_id)
    except Exception as exc:
        logger.warning("Knowledge stats unavailable during domain action scan for %s: %s", site_id, exc)
        return 0
    return int(stats.get("active_items") or 0)


def _active_product_items(site_id: str) -> int:
    try:
        stats = tenant_catalog_stats(site_id)
    except Exception as exc:
        logger.warning("Catalog stats unavailable during domain action scan for %s: %s", site_id, exc)
        return 0
    return int(stats.get("active_products") or 0)


def _expected_action_status(
    action: str,
    configured_actions: set[str],
    active_items: int,
    entity_label_plural: str,
    commerce_caps: dict[str, SiteCapability] | None = None,
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
        verify=False,
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
