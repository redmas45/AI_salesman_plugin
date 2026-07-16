"""Lexical product type and brand matching helpers."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from agent.products.product_response import normalize_lookup_text, phrase_in_text

Product = dict[str, Any]
ProductSearchText = Callable[[Product], str]

LOOKUP_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "actually",
        "and",
        "any",
        "ask",
        "asked",
        "asking",
        "best",
        "buy",
        "can",
        "for",
        "from",
        "give",
        "have",
        "help",
        "i",
        "just",
        "me",
        "mean",
        "meant",
        "need",
        "ok",
        "okay",
        "please",
        "recommend",
        "said",
        "say",
        "saying",
        "show",
        "should",
        "so",
        "tell",
        "the",
        "to",
        "uh",
        "um",
        "want",
        "we",
        "what",
        "with",
        "yeah",
        "yep",
        "you",
    }
)
INVENTORY_TYPE_FILLER_TERMS = frozenset(
    {
        "additional",
        "another",
        "any",
        "available",
        "different",
        "else",
        "more",
        "other",
        "right",
        "stock",
    }
)
PHONE_ALIASES = {"phone", "phones", "smartphone", "smartphones", "mobile", "mobiles"}
SPECIFIC_PHONE_ALIASES = {"android", "ios", "iphone", "galaxy"}


def brand_type_products_from_query(
    normalized_query: str,
    products: list[Product],
    *,
    product_search_text: ProductSearchText,
    limit: int = 6,
) -> list[Product]:
    requested_types = requested_product_type_aliases(normalized_query)
    if not requested_types:
        return []
    requested_brands = requested_catalog_brands(normalized_query, products)
    if len(requested_brands) < 2:
        return []

    by_brand: dict[str, list[tuple[int, Product]]] = {brand: [] for brand in requested_brands}
    for product in products:
        brand_key = matching_requested_brand(product, requested_brands, product_search_text=product_search_text)
        if not brand_key:
            continue
        search_text = product_search_text(product)
        type_score = product_type_match_score(search_text, requested_types)
        if type_score <= 0:
            continue
        product_copy = dict(product)
        product_copy["_semantic_score"] = max(float(product_copy.get("_semantic_score") or 0.0), 0.96)
        product_copy["_exact_name_match"] = True
        score = type_score + brand_match_score(product, brand_key)
        by_brand[brand_key].append((score, product_copy))

    selected: list[Product] = []
    for brand in requested_brands:
        candidates = by_brand.get(brand) or []
        if not candidates:
            continue
        candidates.sort(
            key=lambda item: (
                -item[0],
                len(normalize_lookup_text(item[1].get("name", ""))),
                str(item[1].get("name", "")),
            )
        )
        selected.append(candidates[0][1])

    if len(selected) < 2:
        return []
    return selected[:limit]


def lexical_products_from_query(
    normalized_query: str,
    products: list[Product],
    *,
    product_search_text: ProductSearchText,
    limit: int = 6,
) -> list[Product]:
    query_tokens = significant_lookup_tokens(normalized_query)
    requested_types = requested_product_type_aliases(normalized_query)
    if not query_tokens and not requested_types:
        return []

    scored: list[tuple[int, str, Product]] = []
    for product in products:
        search_text = product_search_text(product)
        score = lexical_product_score(search_text, query_tokens, requested_types)
        if score <= 0:
            continue
        product_copy = dict(product)
        product_copy["_semantic_score"] = max(
            float(product_copy.get("_semantic_score") or 0.0),
            min(0.9, 0.45 + (score / 100)),
        )
        product_copy["_lexical_query_match"] = True
        name = str(product.get("name") or product.get("title") or "")
        scored.append((score + stock_score(product), name, product_copy))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [product for _score, _name, product in scored[:limit]]


def matching_inventory_products(
    products: list[Product],
    item_type: str,
    *,
    product_search_text: ProductSearchText,
) -> list[Product]:
    normalized_type = clean_inventory_type(item_type)
    if not normalized_type:
        return []
    requested_types = requested_product_type_aliases(normalized_type)
    query_tokens = significant_lookup_tokens(normalized_type)
    scored: list[tuple[int, int, Product]] = []
    for index, product in enumerate(products):
        search_text = product_search_text(product)
        score = inventory_product_score(product, search_text, normalized_type, requested_types, query_tokens)
        if score <= 0:
            continue
        scored.append((score + stock_score(product), index, product))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [product for _score, _index, product in scored]


def significant_lookup_tokens(normalized_query: str) -> set[str]:
    tokens = {
        token
        for token in normalized_query.split()
        if len(token) >= 3 and token not in LOOKUP_STOPWORDS
    }
    if "phones" in tokens:
        tokens.add("phone")
    if "mobiles" in tokens:
        tokens.add("mobile")
    return tokens


def lexical_product_score(search_text: str, query_tokens: set[str], requested_types: set[str]) -> int:
    score = 0
    for alias in requested_types:
        if phrase_in_text(alias, search_text):
            score += 35 if alias in SPECIFIC_PHONE_ALIASES else 55
    for token in query_tokens:
        if phrase_in_text(token, search_text):
            score += 18
    return score


def clean_inventory_type(item_type: str) -> str:
    normalized = normalize_lookup_text(item_type)
    if not normalized:
        return ""
    tokens = [token for token in normalized.split() if token not in INVENTORY_TYPE_FILLER_TERMS]
    return " ".join(tokens)


def inventory_product_score(
    product: Product,
    search_text: str,
    normalized_type: str,
    requested_types: set[str],
    query_tokens: set[str],
) -> int:
    name = normalize_lookup_text(product.get("name") or product.get("title") or "")
    brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
    score = 0

    if phrase_in_text(normalized_type, name):
        score += 120
        if name.startswith(normalized_type):
            score += 80
    elif phrase_in_text(normalized_type, brand):
        score += 70
    elif phrase_in_text(normalized_type, search_text):
        score += 45

    for alias in requested_types:
        if phrase_in_text(alias, name):
            score += 70
            if name.startswith(alias):
                score += 50
        elif phrase_in_text(alias, brand):
            score += 60
        elif phrase_in_text(alias, search_text):
            score += 35 if alias in SPECIFIC_PHONE_ALIASES else 55

    for token in query_tokens:
        if phrase_in_text(token, name):
            score += 24
        elif phrase_in_text(token, search_text):
            score += 12
    return score


def stock_score(product: Product) -> int:
    try:
        stock = float(product.get("stock") or 0)
    except (TypeError, ValueError):
        stock = 0
    return 5 if bool(product.get("in_stock")) or stock > 0 else 0


def requested_product_type_aliases(normalized_query: str) -> set[str]:
    if any(phrase_in_text(alias, normalized_query) for alias in {"iphone", "iphones", "ios"}):
        return {"iphone", "iphones", "ios"}
    if any(phrase_in_text(alias, normalized_query) for alias in {"galaxy", "samsung galaxy"}):
        return {"galaxy", "samsung", "android"}
    if any(phrase_in_text(alias, normalized_query) for alias in PHONE_ALIASES):
        return PHONE_ALIASES | SPECIFIC_PHONE_ALIASES
    return set()


def requested_catalog_brands(normalized_query: str, products: list[Product]) -> list[str]:
    alias_to_brand: dict[str, str] = {}
    for product in products:
        brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
        if not brand or len(brand) < 2:
            continue
        alias_to_brand[brand] = brand
        if brand == "apple":
            alias_to_brand["iphone"] = brand
            alias_to_brand["ios"] = brand
        elif brand == "samsung":
            alias_to_brand["galaxy"] = brand

    matches: list[tuple[int, str]] = []
    for alias, brand in alias_to_brand.items():
        match = re.search(rf"(?:^|\s){re.escape(alias)}(?:\s|$)", normalized_query)
        if match:
            matches.append((match.start(), brand))

    ordered: list[str] = []
    seen: set[str] = set()
    for _position, brand in sorted(matches, key=lambda item: (item[0], item[1])):
        if brand in seen:
            continue
        seen.add(brand)
        ordered.append(brand)
    return ordered


def matching_requested_brand(
    product: Product,
    requested_brands: list[str],
    *,
    product_search_text: ProductSearchText,
) -> str:
    requested = set(requested_brands)
    brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
    if brand in requested:
        return brand
    search_text = product_search_text(product)
    for requested_brand in requested_brands:
        if phrase_in_text(requested_brand, search_text):
            return requested_brand
    return ""


def product_type_match_score(search_text: str, requested_types: set[str]) -> int:
    best = 0
    for alias in requested_types:
        if phrase_in_text(alias, search_text):
            if alias in PHONE_ALIASES:
                best = max(best, 50)
            else:
                best = max(best, 35)
    return best


def brand_match_score(product: Product, requested_brand: str) -> int:
    score = 40
    brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
    if brand == requested_brand:
        score += 25
    return score + stock_score(product)
