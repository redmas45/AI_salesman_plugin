"""Bound product/cart helper runtime for the voice orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.products import product_turn_responses
from agent.responses import cart_responses
from agent.products.product_matching import ProductCatalogMatcher
from agent.products.product_response import ProductCatalogFormatter, ProductDisplayGrounder, ProductSearchQueryCleaner


@dataclass(frozen=True)
class OrchestratorProductRuntime:
    matcher: ProductCatalogMatcher
    formatter: ProductCatalogFormatter
    query_cleaner: ProductSearchQueryCleaner
    display_grounder: ProductDisplayGrounder

    def merge_products(self, primary: list[dict], supplemental: list[dict], limit: int | None = None) -> list[dict]:
        return self.matcher.merge(primary, supplemental, limit)

    def exact_products_from_query(self, query: str, site_id: str, limit: int = 6) -> list[dict]:
        return self.matcher.exact_products_from_query(query, site_id, limit)

    def ensure_named_comparison_response(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return product_turn_responses.ensure_named_comparison_response(
            response,
            transcript,
            retrieved_products,
            self.formatter,
        )

    def ensure_generic_comparison_response(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_items: list[dict],
    ) -> None:
        return product_turn_responses.ensure_generic_comparison_response(
            response,
            transcript,
            retrieved_items,
            self.formatter,
        )

    def ensure_product_answer_response(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return product_turn_responses.ensure_product_answer_response(
            response,
            transcript,
            retrieved_products,
            self.formatter,
            self.query_cleaner,
        )

    def ensure_product_search_display_action(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return product_turn_responses.ensure_product_search_display_action(
            response,
            transcript,
            retrieved_products,
            self.formatter,
            self.query_cleaner,
        )

    def coerce_recommendation_to_product_search(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return product_turn_responses.coerce_recommendation_to_product_search(
            response,
            transcript,
            retrieved_products,
            self.formatter,
            self.query_cleaner,
        )

    def prevent_false_no_matching_product_claim(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return product_turn_responses.prevent_false_no_matching_product_claim(
            response,
            transcript,
            retrieved_products,
            self.query_cleaner,
        )

    def ensure_product_display_search_queries(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return product_turn_responses.ensure_product_display_search_queries(
            response,
            transcript,
            retrieved_products,
            self.formatter,
            self.query_cleaner,
        )

    def normalized_product_action_search_query(
        self,
        raw_query: Any,
        transcript: str,
        retrieved_products: list[dict],
    ) -> str:
        return product_turn_responses.normalized_product_action_search_query(
            raw_query,
            transcript,
            retrieved_products,
            self.query_cleaner,
        )

    def ground_product_display_response(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return product_turn_responses.ground_product_display_response(
            response,
            transcript,
            retrieved_products,
            self.display_grounder,
        )

    def products_selected_by_display_action(
        self,
        action: dict[str, Any],
        retrieved_products: list[dict],
    ) -> list[dict]:
        return product_turn_responses.products_selected_by_display_action(
            action,
            retrieved_products,
            self.display_grounder,
        )

    def product_search_fallback_text(self, products: list[dict]) -> str:
        return product_turn_responses.product_search_fallback_text(products, self.formatter)

    def display_search_query(self, transcript: str, products: list[dict] | None = None) -> str:
        return product_turn_responses.display_search_query(transcript, self.query_cleaner, products)

    def search_query_words(self, value: Any) -> list[str]:
        return product_turn_responses.search_query_words(value, self.query_cleaner)

    def should_bypass_ecommerce_answer_cache(self, transcript: str) -> bool:
        return product_turn_responses.should_bypass_ecommerce_answer_cache(transcript, self.query_cleaner)

    def display_search_query_from_products(self, products: list[dict]) -> str:
        return product_turn_responses.display_search_query_from_products(products, self.query_cleaner)

    def ensure_entity_answer_response(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_items: list[dict],
    ) -> None:
        return product_turn_responses.ensure_entity_answer_response(
            response,
            transcript,
            retrieved_items,
            self.formatter,
        )

    def answer_target_products(self, transcript: str, products: list[dict]) -> list[dict]:
        return product_turn_responses.answer_target_products(transcript, products, self.formatter)

    def product_answer_fallback_text(self, products: list[dict]) -> str:
        return product_turn_responses.product_answer_fallback_text(products, self.formatter)

    def product_fact_parts(self, product: dict) -> list[str]:
        return product_turn_responses.product_fact_parts(product, self.formatter)

    def product_comparison_fact_text(self, product: dict) -> str:
        return product_turn_responses.product_comparison_fact_text(product, self.formatter)

    def entity_answer_fallback_text(self, items: list[dict]) -> str:
        return product_turn_responses.entity_answer_fallback_text(items, self.formatter)

    def entity_fact_text(self, item: dict) -> str:
        return product_turn_responses.entity_fact_text(item, self.formatter)

    def entity_comparison_fact_text(self, item: dict) -> str:
        return product_turn_responses.entity_comparison_fact_text(item, self.formatter)

    def comparison_fallback_text(self, products: list[dict]) -> str:
        return product_turn_responses.comparison_fallback_text(products, self.formatter)

    def generic_comparison_fallback_text(self, items: list[dict]) -> str:
        return product_turn_responses.generic_comparison_fallback_text(items, self.formatter)

    def ensure_cart_request_response(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
    ) -> None:
        return cart_responses.ensure_cart_request_response(
            response,
            transcript,
            retrieved_products,
            self.formatter,
        )

    def cart_target_product(self, transcript: str, products: list[dict]) -> dict | None:
        return cart_responses.cart_target_product(transcript, products, self.formatter)

    def product_stock(self, product: dict) -> int | None:
        return cart_responses.product_stock(product, self.formatter)

    def product_price(self, product: dict) -> float | None:
        return cart_responses.product_price(product, self.formatter)

    def product_display_name(self, product: dict) -> str:
        return cart_responses.product_display_name(product, self.formatter)

    def cart_confirmation_text(self, product: dict, quantity: int) -> str:
        return cart_responses.cart_confirmation_text(product, quantity, self.formatter)
