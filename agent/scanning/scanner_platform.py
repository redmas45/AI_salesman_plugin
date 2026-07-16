"""Platform URL normalization and signal matching for readiness scans."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def base_url(site_url: str) -> str:
    parsed = urlparse(site_url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc or parsed.path.split("/")[0]
    return f"{scheme}://{host}"


def match_signals(
    signals: tuple[tuple[str, str, float], ...],
    html: str,
    headers: dict[str, str],
) -> float:
    score = 0.0
    header_blob = " ".join(f"{key}: {value}" for key, value in headers.items()).lower()
    for source, pattern, weight in signals:
        target = html if source in {"html", "meta"} else header_blob
        if re.search(pattern, target, re.IGNORECASE):
            score += weight
    return min(score, 1.0)


def detect_platform(
    html: str,
    headers: dict[str, str],
    *,
    shopify_signals: tuple[tuple[str, str, float], ...],
    woocommerce_signals: tuple[tuple[str, str, float], ...],
) -> tuple[str, float]:
    shopify_score = match_signals(shopify_signals, html, headers)
    woocommerce_score = match_signals(woocommerce_signals, html, headers)

    if shopify_score >= 0.4 and shopify_score > woocommerce_score:
        return "shopify", shopify_score
    if woocommerce_score >= 0.4 and woocommerce_score > shopify_score:
        return "woocommerce", woocommerce_score
    if shopify_score > 0 or woocommerce_score > 0:
        best_score = max(shopify_score, woocommerce_score)
        platform = "shopify" if shopify_score >= woocommerce_score else "woocommerce"
        return platform, best_score

    return "custom", 0.0
