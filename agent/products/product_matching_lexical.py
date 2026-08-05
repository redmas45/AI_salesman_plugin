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
# Generic category nouns only. Brand, product-line and OS names are learned
# from the connected tenant catalog, never written into Hub code.
PHONE_ALIASES = {"phone", "phones", "smartphone", "smartphones", "mobile", "mobiles"}


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


# Generic marketing modifiers that carry no product-type meaning; they must never
# be treated as a product type nor admit a product on their own.
GENERIC_MODIFIERS = frozenset(
    {
        "flex", "classic", "active", "pro", "prime", "elite", "signature", "luxe",
        "urban", "smart", "daily", "premium", "budget", "standard", "basic",
        "plus", "max", "ultra", "lite", "new", "best", "casual", "essential",
    }
)

GENERIC_TAXONOMY_TERMS = frozenset(
    {
        "accessories", "beauty", "care", "electronics", "fashion", "fitness",
        "food", "grocery", "home", "kitchen", "men", "personal", "products",
        "sports", "women",
    }
)

# A built-in vocabulary of common e-commerce product-type nouns. This is merged
# with the tenant catalog's own taxonomy so type detection stays grounded in what
# the store actually sells rather than any single site's naming.
BUILTIN_TYPE_NOUNS = frozenset(
    {
        "smartwatch", "watch", "band", "tracker", "laptop", "notebook", "tablet",
        "phone", "smartphone", "mobile", "headphone", "earbud", "earbuds", "earphone",
        "speaker", "soundbar", "tv", "television", "camera", "lens", "drone", "monitor",
        "keyboard", "mouse", "router", "printer", "charger", "cable", "adapter",
        "powerbank", "battery", "case", "cover", "shoe", "sneaker", "sandal", "slipper",
        "boot", "shirt", "tshirt", "tee", "dress", "kurta", "saree", "jeans", "trouser",
        "pant", "jacket", "hoodie", "sweater", "cap", "hat", "sock", "belt", "tie",
        "perfume", "fragrance", "deodorant", "cream", "lotion", "shampoo", "serum",
        "lipstick", "sunscreen", "bag", "backpack", "wallet", "handbag", "luggage",
        "sunglasses", "book", "novel", "diary", "pen", "pencil", "marker", "fryer",
        "airfryer", "mixer", "grinder", "blender", "kettle", "cooker", "toaster", "oven",
        "fan", "iron", "bottle", "cookware", "pan", "mattress", "pillow", "bedsheet",
        "curtain", "dumbbell", "treadmill", "cycle", "racket", "protein", "nuts",
        "fruits", "snack", "chocolate", "coffee", "tea", "juice", "sweater",
    }
)


def product_strong_text(product: Product) -> str:
    """Searchable text WITHOUT the free-text description.

    Brand and type gating runs against strong fields only (name, brand, category,
    subcategory, tags) so a description-only mention can never satisfy an explicit
    brand or type request.
    """
    values = [
        product.get("name"),
        product.get("title"),
        product.get("brand"),
        product.get("vendor"),
        product.get("category"),
        product.get("category_name"),
        product.get("category_slug"),
        product.get("subcategory"),
        product.get("tags"),
    ]
    return normalize_lookup_text(" ".join(str(value or "") for value in values))


def catalog_type_vocabulary(products: list[Product]) -> set[str]:
    """Recognized type tokens = built-in nouns + what THIS catalog actually sells.

    The tenant's own taxonomy and product names are the source of truth for the
    product lines a shopper can name. Learning "galaxy" or "iphone" - or a travel
    site's "maldives", or an insurer's "endowment" - from the connected catalog is
    what keeps one Hub correct for every vertical; writing those words into Hub
    code would fit exactly one store and quietly mis-handle the next one.

    Brand tokens are excluded so a brand is matched as a brand, not as a type.
    """
    vocab: set[str] = set(BUILTIN_TYPE_NOUNS)
    # Every brand in the catalog, so a brand word never counts as a product type -
    # not even when a rival's product name mentions it ("Anker Apple-Compatible
    # Charger" must not make "apple" a type and admit every Apple product).
    catalog_brands = {
        token
        for product in products
        for token in normalize_lookup_text(product.get("brand") or product.get("vendor") or "").split()
    }
    for product in products:
        taxonomy = " ".join(
            str(product.get(field) or "")
            for field in ("category", "category_name", "category_slug", "subcategory")
        )
        product_line = normalize_lookup_text(product.get("name") or product.get("title") or "")
        vocab.update(
            token
            for token in f"{normalize_lookup_text(taxonomy)} {product_line}".split()
            if len(token) >= 3 and token not in catalog_brands
        )
    return vocab - GENERIC_MODIFIERS - GENERIC_TAXONOMY_TERMS


def canonical_type_token(token: str) -> str:
    """Normalize common English plurals for type-vocabulary matching."""
    normalized = normalize_lookup_text(token)
    if normalized in BUILTIN_TYPE_NOUNS:
        return normalized
    if normalized.endswith("ies") and len(normalized) > 4:
        return f"{normalized[:-3]}y"
    if normalized.endswith(("ches", "shes", "sses", "xes", "zes")) and len(normalized) > 5:
        return normalized[:-2]
    if normalized.endswith("s") and not normalized.endswith("ss") and len(normalized) > 3:
        return normalized[:-1]
    return normalized


def requested_type_tokens(normalized_query: str, products: list[Product]) -> set[str]:
    """Type tokens explicitly requested: the phone-family aliases plus any query
    token that is a recognized catalog/built-in type (excluding generic modifiers).
    """
    tokens = set(requested_product_type_aliases(normalized_query))
    vocabulary = catalog_type_vocabulary(products)
    for raw_token in normalized_query.split():
        normalized_token = normalize_lookup_text(raw_token)
        token = normalized_token if normalized_token in vocabulary else canonical_type_token(raw_token)
        if len(token) < 3 or token in LOOKUP_STOPWORDS or token in GENERIC_MODIFIERS:
            continue
        if token in vocabulary:
            tokens.add(token)
    return tokens


def products_matching_query_facets(products: list[Product], query: str) -> list[Product]:
    """Filter a candidate pool by explicit brand/type facets from the query.

    This is the shared retrieval-boundary equivalent of the fast inventory
    matcher. It prevents semantic/fuzzy candidates from bypassing brand+type
    conjunction on recommendation, comparison, and other non-browse phrasings.
    """
    normalized_query = normalize_lookup_text(query)
    if not normalized_query or not products:
        return products

    brands = requested_catalog_brands(normalized_query, products)
    type_tokens = requested_type_tokens(normalized_query, products)
    if not brands and not type_tokens:
        return products

    matches: list[Product] = []
    for product in products:
        strong_text = product_strong_text(product)
        name = normalize_lookup_text(product.get("name") or product.get("title") or "")
        brand_ok = _brand_matches_on_strong(product, brands, strong_text) if brands else True
        type_ok = _type_matches_on_strong(type_tokens, strong_text, name) if type_tokens else True
        if brand_ok and type_ok:
            matches.append(product)
    return matches


def _brand_matches_on_strong(product: Product, brands: list[str], strong_text: str) -> bool:
    brand_field = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
    if brand_field:
        return any(brand_field == brand or phrase_in_text(brand, brand_field) for brand in brands)
    return any(phrase_in_text(brand, strong_text) for brand in brands)


def _type_matches_on_strong(type_tokens: set[str], strong_text: str, name: str) -> bool:
    return any(phrase_in_text(token, name) or phrase_in_text(token, strong_text) for token in type_tokens)


def matching_inventory_products(
    products: list[Product],
    item_type: str,
    *,
    product_search_text: ProductSearchText,
) -> list[Product]:
    """Field-aware, conjunctive product matching.

    When the query names both a brand and a product type, a product must match
    BOTH on strong fields (brand+type conjunction). A single explicit facet must
    match that facet; a query with no recognized facet falls back to token overlap
    on strong fields (never description-only). Ranking reuses the existing weighted
    scorer for backward-compatible ordering.
    """
    normalized_type = clean_inventory_type(item_type)
    if not normalized_type:
        return []

    brands = requested_catalog_brands(normalized_type, products)
    type_tokens = requested_type_tokens(normalized_type, products)
    query_tokens = significant_lookup_tokens(normalized_type)
    ranking_aliases = requested_product_type_aliases(normalized_type)
    conjunctive = bool(brands and type_tokens)

    scored: list[tuple[int, int, Product]] = []
    for index, product in enumerate(products):
        strong_text = product_strong_text(product)
        name = normalize_lookup_text(product.get("name") or product.get("title") or "")

        brand_ok = _brand_matches_on_strong(product, brands, strong_text) if brands else False
        type_ok = _type_matches_on_strong(type_tokens, strong_text, name) if type_tokens else False

        if conjunctive:
            if not (brand_ok and type_ok):
                continue
        elif brands:
            if not brand_ok:
                continue
        elif type_tokens:
            if not type_ok:
                continue
        elif not any(phrase_in_text(token, strong_text) for token in query_tokens):
            # No recognized facet at all: require a plain token match on a strong
            # field so bare nouns ("cap") still work, but description-only cannot.
            continue

        search_text = product_search_text(product)
        score = inventory_product_score(product, search_text, normalized_type, ranking_aliases, query_tokens)
        scored.append((max(score, 1) + stock_score(product), index, product))

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
            score += 55
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
            score += 55

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
    """Generic product-type nouns the query names.

    Only ordinary category nouns belong here. Product lines and model names are
    NOT listed: they differ per tenant, so they are learned from the connected
    catalog's own product names (see `catalog_type_vocabulary`) rather than being
    written into Hub code, which would only ever fit one store.
    """
    if any(phrase_in_text(alias, normalized_query) for alias in PHONE_ALIASES):
        return set(PHONE_ALIASES)
    return set()


MIN_BRAND_ALIAS_LENGTH = 3


def brand_alias_index(products: list[Product]) -> dict[str, str]:
    """Map every name a shopper might use for a brand to that brand.

    Shoppers name product lines, not brands ("the iPhone", "a Galaxy"). Which
    words those are differs per tenant, so they are learned here instead of being
    listed in Hub code: a token appearing in the product names of exactly ONE
    brand is that brand's line. A token shared by several brands is ambiguous and
    is deliberately left unmapped rather than guessed at.
    """
    alias_to_brand: dict[str, str] = {}
    brands_by_line_token: dict[str, set[str]] = {}
    for product in products:
        brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
        if not brand or len(brand) < 2:
            continue
        alias_to_brand[brand] = brand
        for token in normalize_lookup_text(product.get("name") or product.get("title") or "").split():
            if len(token) < MIN_BRAND_ALIAS_LENGTH or token.isdigit():
                continue
            if token in GENERIC_MODIFIERS or token in GENERIC_TAXONOMY_TERMS or token in BUILTIN_TYPE_NOUNS:
                continue
            brands_by_line_token.setdefault(token, set()).add(brand)

    for token, owning_brands in brands_by_line_token.items():
        if len(owning_brands) == 1 and token not in alias_to_brand:
            alias_to_brand[token] = next(iter(owning_brands))
    return alias_to_brand


def requested_catalog_brands(normalized_query: str, products: list[Product]) -> list[str]:
    alias_to_brand = brand_alias_index(products)

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
