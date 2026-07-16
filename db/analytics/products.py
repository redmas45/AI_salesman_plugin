"""Product demand matching helpers for analytics snapshots."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import psycopg

from db.core.database import get_all_products

ANALYTICS_CATALOG_PRODUCT_LIMIT = 1000
PRODUCT_FULL_MATCH_WEIGHT = 3
PRODUCT_TOKEN_MATCH_WEIGHT = 1
PRODUCT_COMMON_TOKEN_RATIO = 0.6
PRODUCT_COMMON_TOKEN_MIN_COUNT = 3

ANALYTICS_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "can",
    "could",
    "for",
    "from",
    "have",
    "how",
    "into",
    "like",
    "me",
    "more",
    "need",
    "please",
    "show",
    "that",
    "the",
    "this",
    "what",
    "with",
    "you",
    "your",
}

PRODUCT_TOKEN_STOPWORDS = ANALYTICS_STOPWORDS | {
    "any",
    "best",
    "buy",
    "choice",
    "get",
    "good",
    "great",
    "help",
    "hello",
    "here",
    "interested",
    "looking",
    "might",
    "one",
    "ready",
    "see",
    "some",
    "want",
    "yaar",
}

PRODUCT_TYPE_TOKENS = {
    "bag",
    "bottom",
    "cap",
    "cup",
    "hoodie",
    "jacket",
    "mug",
    "onesie",
    "pant",
    "shirt",
    "shoe",
    "sticker",
    "top",
}


def top_product_mentions(rows: list[dict[str, Any]]) -> Counter[str]:
    products: Counter[str] = Counter()
    matchers_by_site = _product_matchers_by_site({row["site_id"] for row in rows})
    for row in rows:
        matchers = matchers_by_site.get(row["site_id"], [])
        exact_matches = _exact_product_matches(row, matchers)
        if exact_matches:
            products.update(exact_matches)
            continue
        products.update(_fallback_product_matches(row, matchers))
    return products


def _exact_product_matches(row: dict[str, Any], matchers: list[dict[str, Any]]) -> Counter[str]:
    matches: Counter[str] = Counter()
    normalized_text = _normalized_product_text(_conversation_product_text(row))
    for matcher in matchers:
        if matcher["full_text"] and matcher["full_text"] in normalized_text:
            matches[matcher["name"]] += PRODUCT_FULL_MATCH_WEIGHT
    return matches


def _fallback_product_matches(row: dict[str, Any], matchers: list[dict[str, Any]]) -> Counter[str]:
    matches: Counter[str] = Counter()
    text_tokens = set(_normalized_product_tokens(_customer_demand_text(row)))
    for matcher in matchers:
        if matcher["tokens"] & text_tokens:
            matches[matcher["name"]] += PRODUCT_TOKEN_MATCH_WEIGHT
    return matches


def _product_matchers_by_site(site_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    products_by_site = _catalog_product_names(site_ids)
    return {
        site_id: _product_matchers(product_names)
        for site_id, product_names in products_by_site.items()
    }


def _catalog_product_names(site_ids: set[str]) -> dict[str, list[str]]:
    product_names: dict[str, list[str]] = {}
    for site_id in site_ids:
        try:
            products = get_all_products(site_id, limit=ANALYTICS_CATALOG_PRODUCT_LIMIT)
        except psycopg.Error:
            product_names[site_id] = []
            continue
        product_names[site_id] = _unique_product_names(products)
    return product_names


def _unique_product_names(products: list[dict[str, Any]]) -> list[str]:
    names = {
        str(product.get("name") or "").strip()
        for product in products
        if str(product.get("name") or "").strip()
    }
    return sorted(names)


def _product_matchers(product_names: list[str]) -> list[dict[str, Any]]:
    common_tokens = _common_product_tokens(product_names)
    return [
        {
            "name": product_name,
            "full_text": _normalized_product_text(product_name),
            "tokens": _significant_product_tokens(product_name, common_tokens),
        }
        for product_name in product_names
    ]


def _common_product_tokens(product_names: list[str]) -> set[str]:
    token_counts: Counter[str] = Counter()
    for product_name in product_names:
        token_counts.update(set(_normalized_product_tokens(product_name)))
    threshold = max(PRODUCT_COMMON_TOKEN_MIN_COUNT, int(len(product_names) * PRODUCT_COMMON_TOKEN_RATIO))
    return {
        token
        for token, count in token_counts.items()
        if count >= threshold and token not in PRODUCT_TYPE_TOKENS
    }


def _significant_product_tokens(product_name: str, common_tokens: set[str]) -> set[str]:
    tokens = {
        token
        for token in _normalized_product_tokens(product_name)
        if _is_product_signal_token(token, common_tokens)
    }
    if tokens:
        return tokens
    return set(_normalized_product_tokens(product_name)) - common_tokens


def _is_product_signal_token(token: str, common_tokens: set[str]) -> bool:
    if len(token) < 3:
        return False
    if token in PRODUCT_TOKEN_STOPWORDS or token in common_tokens:
        return False
    return True


def _customer_demand_text(row: dict[str, Any]) -> str:
    return str(row.get("transcript") or "")


def _conversation_product_text(row: dict[str, Any]) -> str:
    return f"{row.get('transcript', '')} {row.get('response_text', '')}"


def _normalized_product_text(value: str) -> str:
    return " ".join(_normalized_product_tokens(value))


def _normalized_product_tokens(value: str) -> list[str]:
    text = str(value or "").lower()
    text = re.sub(r"\bt[\s-]?shirts?\b", " t shirt ", text)
    text = re.sub(r"\btees?\b", " t shirt ", text)
    return [_singular_token(token) for token in re.findall(r"[a-z0-9]+", text)]


def _singular_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token
