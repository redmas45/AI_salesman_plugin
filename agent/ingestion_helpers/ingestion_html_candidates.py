"""HTML and framework payload extraction for catalog ingestion."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

from agent.ingestion_helpers import ingestion_catalog_normalizers, ingestion_nextjs_payloads
from agent.ingestion_helpers.ingestion_normalization import (
    clean_text,
    first,
    is_present,
    looks_like_noise_name,
    normalized_candidate_name,
    parse_price,
    stable_id,
    to_float,
)
from agent.ingestion_helpers.ingestion_product_rows import derive_category_from_url, normalize_product_row, to_tags
from agent.verticals.discovery_profiles import get_discovery_profile, high_value_url_keywords_for
from agent.verticals.registry import DEFAULT_VERTICAL_KEY


class HtmlHarvest(HTMLParser):
    BLOCK_TAGS = {"title", "h1", "h2", "h3", "p", "li", "section", "article"}
    IGNORE_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.links: list[str] = []
        self._stack: list[str] = []
        self._buffers: list[list[str]] = []
        self._ignore_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.IGNORE_TAGS:
            self._ignore_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self._stack.append(tag)
            self._buffers.append([])
        if tag == "a":
            href = dict(attrs).get("href")
            if href and not href.startswith("javascript:") and href != "#":
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.IGNORE_TAGS:
            self._ignore_depth = max(0, self._ignore_depth - 1)
            return
        if tag in self.BLOCK_TAGS and self._stack and self._stack[-1] == tag:
            idx = len(self._buffers) - 1
            if idx >= 0:
                text = clean_text(" ".join(self._buffers[idx]))
                if text:
                    self.blocks.append(text)
                self._buffers.pop()
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._ignore_depth:
            return
        text = data.strip()
        if not text:
            return
        for buffer in self._buffers:
            buffer.append(text)


def build_candidates_from_html(
    url: str,
    html_text: str,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
) -> list[dict[str, Any]]:
    profile = get_discovery_profile(vertical_key)
    parser = HtmlHarvest()
    parser.feed(html_text)

    all_products: list[dict[str, Any]] = []
    all_products.extend(extract_jsonld_products(html_text, url, vertical_key=vertical_key))
    all_products.extend(extract_nextjs_flight_products(html_text, url))
    all_products.extend(
        ingestion_catalog_normalizers.extract_embedded_json_products(
            html_text,
            url,
            dedupe_products=dedupe_products,
        )
    )

    category_hint = derive_category_from_url(url)
    for block in parser.blocks:
        text = clean_text(block)
        if len(text) < 45:
            continue
        lowered = text.lower()
        has_price_signal = parse_price(text) > 0
        has_shop_signal = any(token in lowered for token in ("add to cart", "buy", "price", "₹", "rs", "inr", "$"))
        has_vertical_signal = _has_vertical_signal(text, url, vertical_key=profile.key)
        if not has_price_signal and not has_shop_signal and not has_vertical_signal:
            continue

        fallback_category = profile.category_label if has_vertical_signal else category_hint
        matched_signals = _matched_vertical_signals(text, url, vertical_key=profile.key)
        row = normalize_product_row(
            {
                "name": candidate_title_from_block(text, vertical_key=vertical_key),
                "description": text,
                "category": fallback_category,
                "brand": profile.provider_label if has_vertical_signal else "Unknown Brand",
                "price": parse_price(text),
                "tags": matched_signals if has_vertical_signal else [],
            },
            fallback_category=fallback_category,
            source_url=url,
        )
        if row:
            all_products.append(row)

    unique: dict[int, dict[str, Any]] = {}
    for item in all_products:
        if isinstance(item, dict):
            unique[int(item["id"])] = item
    return dedupe_products(list(unique.values()))


def extract_nextjs_flight_products(html_text: str, source_url: str) -> list[dict[str, Any]]:
    return ingestion_nextjs_payloads.extract_nextjs_flight_products(html_text, source_url)


def extract_jsonld_products(
    html_text: str,
    source_url: str,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
) -> list[dict[str, Any]]:
    profile = get_discovery_profile(vertical_key)
    profile_types = {item.lower() for item in profile.jsonld_types}
    raw_json = re.findall(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    results: list[dict[str, Any]] = []
    for entry in raw_json:
        try:
            payload = json.loads(entry.strip())
        except json.JSONDecodeError:
            continue

        queue: list[Any] = [payload] if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])
        while queue:
            item = queue.pop()
            if not isinstance(item, dict):
                continue
            item_types = jsonld_type_texts(item.get("@type"))
            if "product" in item_types and profile.key == "ecommerce":
                row = normalize_jsonld_item(item, source_url)
                if row:
                    results.append(row)
            elif item_types & profile_types:
                row = normalize_generic_jsonld_item(item, source_url, vertical_key=profile.key)
                if row:
                    results.append(row)

            graph = item.get("@graph")
            if isinstance(graph, list):
                queue.extend(graph)
            elif isinstance(graph, dict):
                queue.append(graph)
    return results


def jsonld_type_text(value: Any) -> str:
    if isinstance(value, list):
        return clean_text(first(*value, default=""))
    return clean_text(value)


def jsonld_type_texts(value: Any) -> set[str]:
    values = value if isinstance(value, list) else [value]
    result: set[str] = set()
    for item in values:
        text = clean_text(item)
        if not text:
            continue
        result.add(text)
        result.add(text.rsplit("/", 1)[-1])
    return {item.lower() for item in result if item}


def normalize_jsonld_item(raw: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    name = clean_text(first(raw.get("name"), raw.get("headline"), default=""))
    if not name:
        return None

    description = clean_text(first(raw.get("description"), raw.get("summary"), default=name))
    category = clean_text(first(raw.get("category"), "Products"))
    brand = raw.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")

    offers = _first_offer(raw.get("offers"))
    rating = 0.0
    review_count = 0
    aggregate = raw.get("aggregateRating")
    if isinstance(aggregate, dict):
        rating = to_float(aggregate.get("ratingValue"))
        review_count = int(to_float(aggregate.get("reviewCount")))

    availability = clean_text(first(raw.get("availability"), offers.get("availability"), default="")).lower()
    stock = 100 if ("in stock" in availability or availability == "instock") else 100

    return normalize_product_row(
        {
            "id": first(raw.get("product_id"), raw.get("sku"), stable_id(source_url, name, description)),
            "name": name,
            "brand": first(brand, "Unknown Brand"),
            "category": first(category, "Products"),
            "description": description,
            "price": to_float(first(offers.get("price"), offers.get("lowPrice"), offers.get("highPrice"), 0)),
            "original_price": to_float(first(offers.get("highPrice"), offers.get("price"), offers.get("lowPrice"), 0)),
            "color": first(raw.get("color"), default=None),
            "size_options": first(raw.get("size"), raw.get("size_options"), "[]"),
            "tags": to_tags(raw.get("keywords")),
            "rating": rating,
            "review_count": review_count,
            "stock": stock,
            "image": first(raw.get("image"), default=None),
            "is_active": 1,
        },
        fallback_category="Products",
        source_url=source_url,
    )


def normalize_generic_jsonld_item(
    raw: dict[str, Any],
    source_url: str,
    *,
    vertical_key: str,
) -> dict[str, Any] | None:
    profile = get_discovery_profile(vertical_key)
    name = clean_text(first(raw.get("name"), raw.get("headline"), raw.get("serviceType"), raw.get("title"), default=""))
    if not name:
        return None

    description = clean_text(first(raw.get("description"), raw.get("summary"), default=name))
    provider = raw.get("provider") or raw.get("brand") or raw.get("seller") or raw.get("organizer")
    if isinstance(provider, dict):
        provider = provider.get("name")

    offers = _first_offer(raw.get("offers"))
    tags = to_tags(first(raw.get("keywords"), raw.get("areaServed"), raw.get("serviceType"), raw.get("@type"), default=[]))
    for tag in profile.text_signals[:4]:
        if tag not in tags:
            tags.append(tag)

    return normalize_product_row(
        {
            "id": first(raw.get("identifier"), raw.get("sku"), stable_id(source_url, name, description)),
            "name": name,
            "brand": first(provider, profile.provider_label),
            "category": first(raw.get("category"), profile.category_label),
            "description": description,
            "price": first(offers.get("price"), offers.get("lowPrice"), 0),
            "original_price": first(offers.get("highPrice"), offers.get("price"), 0),
            "image": first(raw.get("image"), default=None),
            "tags": tags,
            "stock": 100,
            "is_active": 1,
        },
        fallback_category=profile.category_label or "Knowledge",
        source_url=source_url,
    )


def candidate_title_from_block(text: str, vertical_key: str = DEFAULT_VERTICAL_KEY) -> str:
    clean = clean_text(text)
    if vertical_key == "ecommerce":
        return clean.split(".")[0][:90]

    for separator in (".", ":", "|", "-", ","):
        first_chunk = clean.split(separator)[0].strip()
        if 8 <= len(first_chunk) <= 90:
            return first_chunk
    words = clean.split()
    return " ".join(words[:10])[:90]


def dedupe_products(products: list[dict[str, Any]], *, merge_same_name: bool = True) -> list[dict[str, Any]]:
    if not merge_same_name:
        unique_by_id: dict[int, dict[str, Any]] = {}
        for item in products:
            if looks_like_noise_name(str(item.get("name") or "")):
                continue
            unique_by_id[int(item["id"])] = item
        return list(unique_by_id.values())

    merged_by_name: dict[str, dict[str, Any]] = {}
    for item in products:
        if looks_like_noise_name(str(item.get("name") or "")):
            continue
        normalized_name = normalized_candidate_name(str(item.get("name") or ""))
        if not normalized_name:
            merged_by_name[str(item["id"])] = item
            continue
        existing = merged_by_name.get(normalized_name)
        merged_by_name[normalized_name] = merge_product_candidates(existing, item) if existing else item
    return list(merged_by_name.values())


def merge_product_candidates(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    preferred = incoming if candidate_score(incoming) > candidate_score(existing) else existing
    other = existing if preferred is incoming else incoming
    merged = dict(preferred)

    if float(merged.get("price") or 0.0) <= 0 and float(other.get("price") or 0.0) > 0:
        merged["price"] = other["price"]
        merged["original_price"] = other.get("original_price", other["price"])
    if not is_present(merged.get("image_url")) and is_present(other.get("image_url")):
        merged["image_url"] = other["image_url"]
    if clean_text(merged.get("brand")) in {"", "Unknown Brand"} and clean_text(other.get("brand")) not in {"", "Unknown Brand"}:
        merged["brand"] = other["brand"]
    if clean_text(merged.get("category")) in {"", "Products", "Uncategorized"} and clean_text(other.get("category")) not in {"", "Products", "Uncategorized"}:
        merged["category"] = other["category"]
    if len(clean_text(other.get("description"))) > len(clean_text(merged.get("description"))):
        merged["description"] = other["description"]
    if not merged.get("variants") and other.get("variants"):
        merged["variants"] = other["variants"]

    preferred_name = clean_text(merged.get("name"))
    other_name = clean_text(other.get("name"))
    if normalized_candidate_name(other_name) == normalized_candidate_name(preferred_name) and len(other_name) < len(preferred_name):
        merged["name"] = other_name
    return merged


def candidate_score(product: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        1 if float(product.get("price") or 0.0) > 0 else 0,
        1 if is_present(product.get("image_url")) else 0,
        1 if clean_text(product.get("brand")) not in {"", "Unknown Brand"} else 0,
        1 if clean_text(product.get("category")) not in {"", "Products", "Uncategorized"} else 0,
        len(clean_text(product.get("description"))),
    )


def _decode_next_script_payload(raw: str) -> Any | None:
    return ingestion_nextjs_payloads.decode_next_script_payload(raw)


def decode_next_payload(raw: str) -> Any | None:
    return ingestion_nextjs_payloads.decode_next_payload(raw)


def _extract_product_from_react_payload(node: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    return ingestion_nextjs_payloads.extract_product_from_react_payload(node, source_url)


def _best_react_candidate_name(candidate_names: list[str]) -> str:
    return ingestion_nextjs_payloads.best_react_candidate_name(candidate_names)


def _collect_react_node_texts(node: Any, texts: list[str], images: list[str], prices: list[float]) -> None:
    ingestion_nextjs_payloads.collect_react_node_texts(node, texts, images, prices)


def _has_vertical_signal(text: str, url: str, *, vertical_key: str) -> bool:
    if vertical_key == "ecommerce":
        return False
    matched = _matched_vertical_signals(text, url, vertical_key=vertical_key)
    return len(matched) >= 2 or any(token in url.lower() for token in high_value_url_keywords_for(vertical_key))


def _matched_vertical_signals(text: str, url: str, *, vertical_key: str) -> list[str]:
    profile = get_discovery_profile(vertical_key)
    lowered = f"{text} {url}".lower()
    return [token for token in profile.text_signals if token in lowered]


def _first_offer(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value:
        value = value[0]
    return value if isinstance(value, dict) else {}
