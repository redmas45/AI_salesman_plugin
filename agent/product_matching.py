"""Product catalog matching services for ecommerce orchestration."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from agent.product_response import normalize_lookup_text, phrase_in_text

ProductLoader = Callable[[str, int], list[dict[str, Any]]]
ProductByIdLoader = Callable[[str, list[int]], list[dict[str, Any]]]

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


class ProductCatalogMatcher:
    """Owns catalog matching, lexical fallback, and history product recovery."""

    def __init__(
        self,
        *,
        load_all_products: ProductLoader,
        load_products_by_ids: ProductByIdLoader,
        recoverable_errors: tuple[type[BaseException], ...],
        logger: logging.Logger,
    ) -> None:
        self._load_all_products = load_all_products
        self._load_products_by_ids = load_products_by_ids
        self._recoverable_errors = recoverable_errors
        self._logger = logger

    def merge(self, primary: list[dict], supplemental: list[dict], limit: int | None = None) -> list[dict]:
        merged: list[dict] = []
        seen: set[str] = set()
        for product in [*(supplemental or []), *(primary or [])]:
            product_id = str(product.get("id", ""))
            if not product_id or product_id in seen:
                continue
            seen.add(product_id)
            merged.append(product)
        return merged[:limit] if limit else merged

    def exact_products_from_query(self, query: str, site_id: str, limit: int = 6) -> list[dict]:
        normalized_query = normalize_lookup_text(query)
        if not normalized_query:
            return []

        try:
            products = self._load_all_products(site_id, 1000)
        except self._recoverable_errors as exc:
            self._logger.warning("PIPELINE | Exact product lookup failed: %s", exc)
            return []

        matches = self._name_matches(products, normalized_query)
        result = [product for _, product in matches[:limit]]
        if len(result) < 2:
            result = self._dedupe(
                [
                    *result,
                    *self._brand_type_products_from_query(normalized_query, products, limit=limit),
                    *self._lexical_products_from_query(normalized_query, products, limit=limit),
                ],
                limit=limit,
            )
        if result:
            self._logger.info(
                "PIPELINE | Exact product lookup added %d products: %s",
                len(result),
                [product.get("name") for product in result],
            )
        return result

    def extract_products_from_history(self, history: list[dict], site_id: str) -> list[dict]:
        last_assistant_message = self._last_assistant_message(history)
        if not last_assistant_message:
            return []

        tagged_ids = self._tagged_product_ids(last_assistant_message)
        mentioned: list[dict[str, Any]] = []
        if tagged_ids:
            mentioned.extend(self._products_from_ids(site_id, tagged_ids))

        if not mentioned:
            mentioned.extend(self._products_named_in_message(site_id, last_assistant_message))

        if mentioned:
            self._logger.info("PIPELINE | Extracted %d previously discussed products from history context", len(mentioned))
        return mentioned

    def matching_inventory_products(self, products: list[dict], item_type: str) -> list[dict]:
        normalized_type = normalize_lookup_text(item_type)
        if not normalized_type:
            return []
        return [
            product
            for product in products
            if normalized_type in self.product_search_text(product)
        ]

    def product_search_text(self, product: dict) -> str:
        values = [
            product.get("name"),
            product.get("title"),
            product.get("brand"),
            product.get("vendor"),
            product.get("category"),
            product.get("category_name"),
            product.get("category_slug"),
            product.get("description"),
            product.get("tags"),
        ]
        return normalize_lookup_text(" ".join(str(value or "") for value in values))

    def available_category_names(self, products: list[dict]) -> list[str]:
        seen: set[str] = set()
        names: list[str] = []
        for product in products:
            category = str(product.get("category_name") or product.get("category") or "").strip()
            if not category:
                continue
            key = category.lower()
            if key in {"product", "products"} or key in seen:
                continue
            seen.add(key)
            names.append(category.replace("-", " ").title())
        return names

    def _name_matches(self, products: list[dict], normalized_query: str) -> list[tuple[int, dict]]:
        matches: list[tuple[int, dict]] = []
        for product in products:
            score = self._product_name_match_score(product, normalized_query)
            if score <= 0:
                continue
            product_copy = dict(product)
            product_copy["_semantic_score"] = max(float(product_copy.get("_semantic_score") or 0.0), 0.98)
            product_copy["_exact_name_match"] = True
            matches.append((score, product_copy))

        matches.sort(
            key=lambda item: (
                -item[0],
                len(normalize_lookup_text(item[1].get("name", ""))),
                str(item[1].get("name", "")),
            )
        )
        return matches

    def _product_name_match_score(self, product: dict, normalized_query: str) -> int:
        name = normalize_lookup_text(product.get("name", ""))
        if not name:
            return 0
        if phrase_in_text(name, normalized_query):
            return 100

        best = 0
        for alias in self._product_aliases(name):
            if not alias or not phrase_in_text(alias, normalized_query):
                continue
            token_count = len(alias.split())
            score = 80 if token_count >= 2 else 35
            best = max(best, score)
        return best

    def _product_aliases(self, normalized_name: str) -> list[str]:
        tokens = normalized_name.split()
        aliases = {normalized_name}
        brand_tokens = {"nova", "acme", "ai", "kart"}
        while tokens and tokens[0] in brand_tokens:
            tokens = tokens[1:]
            if tokens:
                aliases.add(" ".join(tokens))
        if len(tokens) >= 2:
            aliases.add(" ".join(tokens[-2:]))
        elif len(tokens) == 1 and len(tokens[0]) >= 4:
            aliases.add(tokens[0])
        return sorted(aliases, key=lambda item: (-len(item.split()), item))

    def _brand_type_products_from_query(self, normalized_query: str, products: list[dict], limit: int = 6) -> list[dict]:
        requested_types = self._requested_product_type_aliases(normalized_query)
        if not requested_types:
            return []
        requested_brands = self._requested_catalog_brands(normalized_query, products)
        if len(requested_brands) < 2:
            return []

        by_brand: dict[str, list[tuple[int, dict]]] = {brand: [] for brand in requested_brands}
        for product in products:
            brand_key = self._matching_requested_brand(product, requested_brands)
            if not brand_key:
                continue
            search_text = self.product_search_text(product)
            type_score = self._product_type_match_score(search_text, requested_types)
            if type_score <= 0:
                continue
            product_copy = dict(product)
            product_copy["_semantic_score"] = max(float(product_copy.get("_semantic_score") or 0.0), 0.96)
            product_copy["_exact_name_match"] = True
            score = type_score + self._brand_match_score(product, brand_key)
            by_brand[brand_key].append((score, product_copy))

        selected: list[dict] = []
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

    def _lexical_products_from_query(self, normalized_query: str, products: list[dict], limit: int = 6) -> list[dict]:
        query_tokens = self._significant_lookup_tokens(normalized_query)
        requested_types = self._requested_product_type_aliases(normalized_query)
        if not query_tokens and not requested_types:
            return []

        scored: list[tuple[int, str, dict]] = []
        for product in products:
            search_text = self.product_search_text(product)
            score = self._lexical_product_score(search_text, query_tokens, requested_types)
            if score <= 0:
                continue
            product_copy = dict(product)
            product_copy["_semantic_score"] = max(float(product_copy.get("_semantic_score") or 0.0), min(0.9, 0.45 + (score / 100)))
            product_copy["_lexical_query_match"] = True
            scored.append((score + self._stock_score(product), str(product.get("name") or product.get("title") or ""), product_copy))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [product for _score, _name, product in scored[:limit]]

    def _significant_lookup_tokens(self, normalized_query: str) -> set[str]:
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

    def _lexical_product_score(self, search_text: str, query_tokens: set[str], requested_types: set[str]) -> int:
        score = 0
        for alias in requested_types:
            if phrase_in_text(alias, search_text):
                score += 35 if alias in {"android", "ios", "iphone", "galaxy"} else 55
        for token in query_tokens:
            if phrase_in_text(token, search_text):
                score += 18
        return score

    def _stock_score(self, product: dict) -> int:
        try:
            stock = float(product.get("stock") or 0)
        except (TypeError, ValueError):
            stock = 0
        return 5 if bool(product.get("in_stock")) or stock > 0 else 0

    def _requested_product_type_aliases(self, normalized_query: str) -> set[str]:
        phone_aliases = {"phone", "phones", "smartphone", "smartphones", "mobile", "mobiles", "iphone", "galaxy"}
        if any(phrase_in_text(alias, normalized_query) for alias in phone_aliases):
            return phone_aliases | {"android", "ios"}
        return set()

    def _requested_catalog_brands(self, normalized_query: str, products: list[dict]) -> list[str]:
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

    def _matching_requested_brand(self, product: dict, requested_brands: list[str]) -> str:
        requested = set(requested_brands)
        brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
        if brand in requested:
            return brand
        search_text = self.product_search_text(product)
        for requested_brand in requested_brands:
            if phrase_in_text(requested_brand, search_text):
                return requested_brand
        return ""

    def _product_type_match_score(self, search_text: str, requested_types: set[str]) -> int:
        best = 0
        for alias in requested_types:
            if phrase_in_text(alias, search_text):
                if alias in {"phone", "phones", "smartphone", "smartphones", "mobile", "mobiles"}:
                    best = max(best, 50)
                else:
                    best = max(best, 35)
        return best

    def _brand_match_score(self, product: dict, requested_brand: str) -> int:
        score = 40
        brand = normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
        if brand == requested_brand:
            score += 25
        return score + self._stock_score(product)

    def _dedupe(self, products: list[dict], limit: int | None = None) -> list[dict]:
        deduped: list[dict] = []
        seen: set[str] = set()
        for product in products:
            product_id = str(product.get("id", ""))
            if not product_id or product_id in seen:
                continue
            seen.add(product_id)
            deduped.append(product)
            if limit and len(deduped) >= limit:
                break
        return deduped

    def _last_assistant_message(self, history: list[dict]) -> str:
        for message in reversed(history or []):
            if message.get("role") == "assistant" and message.get("content"):
                return str(message["content"])
        return ""

    def _tagged_product_ids(self, message: str) -> list[int]:
        id_tag_match = re.search(r"\[PRODUCT_IDS:\s*([\d,\s]+)\]", message)
        if not id_tag_match:
            return []
        tagged_ids: list[int] = []
        for product_id_text in id_tag_match.group(1).split(","):
            clean_product_id = product_id_text.strip()
            if clean_product_id.isdigit():
                tagged_ids.append(int(clean_product_id))
        if tagged_ids:
            self._logger.info("PIPELINE | Found %d product IDs from history tag: %s", len(tagged_ids), tagged_ids)
        return tagged_ids

    def _products_from_ids(self, site_id: str, tagged_ids: list[int]) -> list[dict[str, Any]]:
        try:
            tagged_products = self._load_products_by_ids(site_id, tagged_ids)
        except self._recoverable_errors as exc:
            self._logger.warning("PIPELINE | History tag product bulk lookup failed: %s", exc)
            return []
        mentioned: list[dict[str, Any]] = []
        for product in tagged_products:
            product_copy = dict(product)
            product_copy["_semantic_score"] = 0.95
            mentioned.append(product_copy)
        return mentioned

    def _products_named_in_message(self, site_id: str, message: str) -> list[dict[str, Any]]:
        try:
            products = self._load_all_products(site_id, 100)
        except self._recoverable_errors as exc:
            self._logger.error("PIPELINE | History product check failed to get all products: %s", exc)
            return []

        mentioned: list[dict[str, Any]] = []
        lowered_message = message.lower()
        for product in products:
            name = product.get("name") or product.get("title") or ""
            product_id = str(product.get("id", ""))
            if not ((name and str(name).lower() in lowered_message) or (product_id and product_id in message)):
                continue
            if any(str(existing.get("id")) == product_id for existing in mentioned):
                continue
            product_copy = dict(product)
            product_copy["_semantic_score"] = 0.95
            mentioned.append(product_copy)
        return mentioned
