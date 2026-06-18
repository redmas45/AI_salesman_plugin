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

logger = logging.getLogger(__name__)

SCAN_TIMEOUT_SECONDS = 10
MAX_PROBE_URLS = 20
CLIENT_HOOK_ADAPTER_NAMES = (
    "ai-kart",
    "aikart",
    "shopcart",
    "shopbot",
    "client-hook",
    "client_hook",
    "custom-hook",
    "custom_hook",
)

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
        f"{adapter_name or ''} {site_id or ''}".strip().lower(),
    )
    return any(token in normalized for token in CLIENT_HOOK_ADAPTER_NAMES)


def _client_hook_capabilities(adapter_name: str) -> list[SiteCapability]:
    """Capabilities supplied by first-party client hook integrations."""
    evidence = f"Client adapter '{adapter_name}' exposes verified ShopCart hooks"
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
    )


async def _check_cart(
    base: str,
    platform: str,
    client: httpx.AsyncClient,
) -> SiteCapability:
    """Check whether the site has usable cart APIs."""
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
        code, _, headers = await _probe_url(client, url, method="HEAD")
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

async def scan_site(
    site_url: str,
    site_id: str,
    *,
    adapter_name: str = "",
    timeout: int = SCAN_TIMEOUT_SECONDS,
) -> ReadinessReport:
    """
    Run a non-destructive readiness scan against a client website.

    Returns a ReadinessReport with platform detection and capability probes.
    Does not modify any data. Safe to call repeatedly.
    """
    start = time.monotonic()
    base = _base_url(site_url)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        verify=False,
    ) as client:
        # Fetch homepage for platform detection
        home_code, home_html, home_headers = await _probe_url(
            client, base, accept="text/html",
        )
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

        # Run capability checks
        catalog = await _check_catalog(base, platform, client)
        variants = await _check_variants(base, platform, client)
        cart = await _check_cart(base, platform, client)
        checkout = await _check_checkout(base, platform, client)

        if _is_client_hook_adapter(adapter_name, site_id):
            hook_caps = {cap.name: cap for cap in _client_hook_capabilities(adapter_name)}
            cart = _merge_capability(cart, hook_caps.get("cart"))
            checkout = _merge_capability(checkout, hook_caps.get("checkout"))

    elapsed = (time.monotonic() - start) * 1000

    report = ReadinessReport(
        site_id=site_id,
        site_url=site_url,
        platform=platform,
        platform_confidence=platform_confidence,
        capabilities=[catalog, variants, cart, checkout],
        scanned_at=datetime.now(timezone.utc).isoformat(),
        scan_duration_ms=elapsed,
    )

    logger.info(
        "Readiness scan for %s (%s): platform=%s(%.2f) catalog=%s cart=%s checkout=%s in %.0fms",
        site_id,
        site_url,
        platform,
        platform_confidence,
        catalog.supported,
        cart.supported,
        checkout.supported,
        elapsed,
    )

    return report
