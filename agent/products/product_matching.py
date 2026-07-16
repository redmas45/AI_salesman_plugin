"""Product catalog matching services for ecommerce orchestration."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from agent.products import product_matching_lexical
from agent.products.product_response import normalize_lookup_text, phrase_in_text

ProductLoader = Callable[[str, int], list[dict[str, Any]]]
ProductByIdLoader = Callable[[str, list[int]], list[dict[str, Any]]]

LOOKUP_STOPWORDS = product_matching_lexical.LOOKUP_STOPWORDS
INVENTORY_TYPE_FILLER_TERMS = product_matching_lexical.INVENTORY_TYPE_FILLER_TERMS


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

    def extract_products_from_history(
        self,
        history: list[dict],
        site_id: str,
        expected_count: int | None = None,
    ) -> list[dict]:
        for message in self._recent_assistant_messages(history):
            tagged_ids = self._tagged_product_ids(message)
            mentioned = (
                self._products_from_ids(site_id, tagged_ids)
                if tagged_ids
                else self._products_named_in_message(site_id, message)
            )
            if not mentioned or (expected_count and len(mentioned) != expected_count):
                continue
            for product in mentioned:
                product["_history_context"] = True
            self._logger.info(
                "PIPELINE | Extracted %d previously discussed products from history context",
                len(mentioned),
            )
            return mentioned
        return []

    def matching_inventory_products(self, products: list[dict], item_type: str) -> list[dict]:
        return product_matching_lexical.matching_inventory_products(
            products,
            item_type,
            product_search_text=self.product_search_text,
        )

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
        return product_matching_lexical.brand_type_products_from_query(
            normalized_query,
            products,
            product_search_text=self.product_search_text,
            limit=limit,
        )

    def _lexical_products_from_query(self, normalized_query: str, products: list[dict], limit: int = 6) -> list[dict]:
        return product_matching_lexical.lexical_products_from_query(
            normalized_query,
            products,
            product_search_text=self.product_search_text,
            limit=limit,
        )

    def _significant_lookup_tokens(self, normalized_query: str) -> set[str]:
        return product_matching_lexical.significant_lookup_tokens(normalized_query)

    def _lexical_product_score(self, search_text: str, query_tokens: set[str], requested_types: set[str]) -> int:
        return product_matching_lexical.lexical_product_score(search_text, query_tokens, requested_types)

    def _clean_inventory_type(self, item_type: str) -> str:
        return product_matching_lexical.clean_inventory_type(item_type)

    def _inventory_product_score(
        self,
        product: dict,
        search_text: str,
        normalized_type: str,
        requested_types: set[str],
        query_tokens: set[str],
    ) -> int:
        return product_matching_lexical.inventory_product_score(
            product,
            search_text,
            normalized_type,
            requested_types,
            query_tokens,
        )

    def _stock_score(self, product: dict) -> int:
        return product_matching_lexical.stock_score(product)

    def _requested_product_type_aliases(self, normalized_query: str) -> set[str]:
        return product_matching_lexical.requested_product_type_aliases(normalized_query)

    def _requested_catalog_brands(self, normalized_query: str, products: list[dict]) -> list[str]:
        return product_matching_lexical.requested_catalog_brands(normalized_query, products)

    def _matching_requested_brand(self, product: dict, requested_brands: list[str]) -> str:
        return product_matching_lexical.matching_requested_brand(
            product,
            requested_brands,
            product_search_text=self.product_search_text,
        )

    def _product_type_match_score(self, search_text: str, requested_types: set[str]) -> int:
        return product_matching_lexical.product_type_match_score(search_text, requested_types)

    def _brand_match_score(self, product: dict, requested_brand: str) -> int:
        return product_matching_lexical.brand_match_score(product, requested_brand)

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

    def _recent_assistant_messages(self, history: list[dict]) -> list[str]:
        messages: list[str] = []
        for message in reversed(history or []):
            if message.get("role") != "assistant" or not message.get("content"):
                continue
            messages.append(str(message["content"]))
            if len(messages) >= 8:
                break
        return messages

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
            products = self._load_all_products(site_id, 1000)
        except self._recoverable_errors as exc:
            self._logger.error("PIPELINE | History product check failed to get all products: %s", exc)
            return []

        positioned: list[tuple[int, dict[str, Any]]] = []
        lowered_message = message.lower()
        for product in products:
            name = product.get("name") or product.get("title") or ""
            product_id = str(product.get("id", ""))
            name_position = lowered_message.find(str(name).lower()) if name else -1
            id_position = message.find(product_id) if product_id else -1
            positions = [position for position in (name_position, id_position) if position >= 0]
            if not positions:
                continue
            if any(str(existing.get("id")) == product_id for _, existing in positioned):
                continue
            product_copy = dict(product)
            product_copy["_semantic_score"] = 0.95
            positioned.append((min(positions), product_copy))
        positioned.sort(key=lambda item: item[0])
        return [product for _, product in positioned]
