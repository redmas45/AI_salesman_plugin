"""Next.js and React payload extraction for catalog ingestion."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from agent.ingestion_helpers.ingestion_normalization import (
    clean_text,
    parse_price,
)
from agent.ingestion_helpers.ingestion_product_rows import derive_category_from_url, normalize_product_row

logger = logging.getLogger(__name__)

NEXT_FLIGHT_SCRIPT_RE = re.compile(
    r"self\.__next_f\.push\(\[\s*1,\s*(\"(?:\\.|[^\"\\])+\")\s*\]\)",
    flags=re.IGNORECASE | re.DOTALL,
)
NEXT_DATA_SCRIPT_RE = re.compile(
    r"<script[^>]*id=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>",
    flags=re.IGNORECASE | re.DOTALL,
)


def extract_nextjs_flight_products(html_text: str, source_url: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    def collect_from_payload(payload: Any) -> None:
        if not isinstance(payload, (dict, list)):
            return
        stack: list[Any] = [payload]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                product = extract_product_from_react_payload(item, source_url)
                if product:
                    product_id = int(product["id"])
                    if product_id not in seen_ids:
                        seen_ids.add(product_id)
                        results.append(product)
                for value in item.values():
                    if isinstance(value, (dict, list)):
                        stack.append(value)
            elif isinstance(item, list):
                for value in item:
                    if isinstance(value, (dict, list)):
                        stack.append(value)

    for match in NEXT_FLIGHT_SCRIPT_RE.finditer(html_text):
        payload = decode_next_script_payload(match.group(1))
        if payload is not None:
            collect_from_payload(payload)

    for match in NEXT_DATA_SCRIPT_RE.finditer(html_text):
        payload = decode_next_script_payload(match.group(1))
        if payload is not None:
            collect_from_payload(payload)

    return results


def decode_next_script_payload(raw: str) -> Any | None:
    decoded = decode_next_payload(raw)
    if decoded is None:
        return None
    if isinstance(decoded, str) and ":" in decoded[:40]:
        decoded = decoded.split(":", 1)[1]
    elif isinstance(decoded, str) and not decoded.startswith("["):
        return None
    if isinstance(decoded, str):
        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            return None
    return decoded


def decode_next_payload(raw: str) -> Any | None:
    if not raw:
        return None

    candidate = raw.strip()
    if not candidate:
        return None

    attempts: list[str] = [candidate]
    if (candidate.startswith('"') and candidate.endswith('"')) or (
        candidate.startswith("'") and candidate.endswith("'")
    ):
        attempts.append(candidate[1:-1])
        try:
            attempts.append(bytes(candidate[1:-1], "utf-8").decode("unicode_escape"))
        except UnicodeDecodeError as exc:
            logger.debug("Embedded JSON unicode escape decode failed: %s", exc)

    for attempt in attempts:
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return None


def extract_product_from_react_payload(
    node: dict[str, Any],
    source_url: str,
) -> dict[str, Any] | None:
    if not isinstance(node, dict):
        return None

    href = node.get("href")
    if not (isinstance(href, str) and "/product/" in href.lower()):
        return None

    texts: list[str] = []
    images: list[str] = []
    prices: list[float] = []
    collect_react_node_texts(node, texts, images, prices)

    if not texts:
        return None

    candidate_names = [
        text for text in texts if not text.startswith("$$") and len(clean_text(text).split()) >= 2
    ]
    if not candidate_names:
        return None

    name = best_react_candidate_name(candidate_names)
    description = clean_text(" | ".join(texts[:10])) or name
    price = max(prices) if prices else 0.0
    if price <= 0:
        price = next((value for value in (parse_price(item) for item in texts) if value > 0), 0.0)
    if not href.startswith("http"):
        href = urljoin(source_url, href)

    return normalize_product_row(
        {
            "name": name,
            "description": description,
            "price": price,
            "image": clean_text(images[0]) if images else None,
            "category": derive_category_from_url(href),
            "brand": "Unknown Brand",
        },
        fallback_category=derive_category_from_url(href),
        source_url=source_url,
    )


def best_react_candidate_name(candidate_names: list[str]) -> str:
    for item in candidate_names:
        lowered = item.lower()
        if "acme store" not in lowered and "shop" not in lowered and "search" not in lowered:
            return item
    return candidate_names[0]


def collect_react_node_texts(
    node: Any,
    texts: list[str],
    images: list[str],
    prices: list[float],
) -> None:
    if isinstance(node, str):
        text = clean_text(node)
        if not text:
            return
        texts.append(text)
        value = parse_price(text)
        if value > 0:
            prices.append(value)
        return

    if isinstance(node, list):
        for item in node:
            collect_react_node_texts(item, texts, images, prices)
        return

    if isinstance(node, dict):
        for key, value in node.items():
            if key == "src" and isinstance(value, str):
                value_clean = value.strip()
                if value_clean.startswith("http://") or value_clean.startswith("https://"):
                    images.append(value_clean)
                continue
            if key == "children":
                collect_react_node_texts(value, texts, images, prices)
                continue
            if key in {"name", "alt", "title"} and isinstance(value, str):
                texts.append(clean_text(value))
                continue
            collect_react_node_texts(value, texts, images, prices)
