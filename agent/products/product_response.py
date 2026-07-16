"""Product response formatting and grounding services for ecommerce turns."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from api.contracts.models import ACTION_SHOW_COMPARISON, ACTION_SHOW_PRODUCTS, PRODUCT_IDS_PARAM
from agent.products.product_response_text import (
    concise_text,
    normalize_lookup_text,
    numeric_value,
    phrase_in_text,
    plain_text,
)


class ProductSearchQueryCleaner:
    """Build short host-site search queries from noisy speech transcripts."""

    _stopwords = frozenset(
        {
            "a",
            "about",
            "actually",
            "again",
            "alright",
            "am",
            "an",
            "and",
            "any",
            "are",
            "ask",
            "asked",
            "asking",
            "best",
            "better",
            "bro",
            "budget",
            "below",
            "buy",
            "buying",
            "can",
            "carries",
            "carry",
            "compare",
            "comparison",
            "cost",
            "could",
            "did",
            "difference",
            "differences",
            "do",
            "does",
            "don",
            "dont",
            "find",
            "for",
            "get",
            "give",
            "have",
            "hello",
            "help",
            "hey",
            "hi",
            "i",
            "im",
            "in",
            "inr",
            "interest",
            "interested",
            "instead",
            "is",
            "it",
            "just",
            "know",
            "like",
            "looking",
            "man",
            "me",
            "mean",
            "meant",
            "need",
            "not",
            "ok",
            "okay",
            "of",
            "on",
            "only",
            "option",
            "options",
            "please",
            "price",
            "pricing",
            "product",
            "products",
            "purchase",
            "q",
            "query",
            "range",
            "recommend",
            "result",
            "results",
            "rs",
            "rupee",
            "rupees",
            "said",
            "say",
            "saying",
            "search",
            "sell",
            "sells",
            "show",
            "shop",
            "should",
            "so",
            "some",
            "something",
            "t",
            "tell",
            "that",
            "the",
            "than",
            "this",
            "to",
            "uh",
            "um",
            "under",
            "versus",
            "vs",
            "want",
            "wanna",
            "wanted",
            "we",
            "what",
            "which",
            "with",
            "why",
            "would",
            "yeah",
            "yep",
            "yes",
            "you",
            "your",
        }
    )

    def display_search_query(self, transcript: str, products: list[dict] | None = None) -> str:
        words = self.search_query_words(transcript)
        if words:
            return " ".join(words[:4])
        return self.display_search_query_from_products(products or [])

    def search_query_words(self, value: Any) -> list[str]:
        text = self._remove_negative_corrections(normalize_lookup_text(value))
        budget_context = self._is_budget_context(text)
        words: list[str] = []
        seen: set[str] = set()
        for word in text.split():
            canonical = self._canonical_query_word(word)
            if budget_context and canonical.isdigit():
                continue
            if canonical in self._stopwords or (len(canonical) <= 1 and not canonical.isdigit()):
                continue
            if canonical in seen:
                continue
            seen.add(canonical)
            words.append(canonical)
        return words

    def _remove_negative_corrections(self, text: str) -> str:
        return re.sub(r"\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b", " ", text)

    def _canonical_query_word(self, word: str) -> str:
        if word in {"phone", "phones", "mobile", "mobiles", "smartphone", "smartphones"}:
            return "phone"
        if word in {"book", "books"}:
            return "books"
        return word

    def _is_budget_context(self, text: str) -> bool:
        return bool(
            re.search(
                r"\b(budget|rupees?|rs|inr|under|below|less than|price|pricing|cost)\b",
                text,
            )
        )

    def should_bypass_ecommerce_answer_cache(self, transcript: str) -> bool:
        text = normalize_lookup_text(transcript)
        if not text:
            return True
        if any(
            phrase_in_text(phrase, text)
            for phrase in (
                "asked for",
                "i asked",
                "i said",
                "i meant",
                "not this",
                "not that",
                "wrong",
            )
        ):
            return True

        words = self.search_query_words(text)

        # These turns depend on the current session state or previous result set.
        # Replaying a cached answer for "the cheaper one" or "any other one" is
        # worse than spending an LLM/RAG turn.
        if re.search(
            r"\b(other|another|more|else|these|those|this one|that one|it|them|same|"
            r"cheaper|cheapest|lowest|least expensive|second|third|fourth|one|two|three|four)\b",
            text,
        ):
            return True

        if self._is_budget_context(text) and not words:
            return True

        if self._is_direct_purchase_turn(text):
            return True

        return bool(
            re.search(
                r"\b(start|open|go|checkout|check out|pay|payment)\b",
                text,
            )
        )

    def _is_direct_purchase_turn(self, text: str) -> bool:
        if re.search(r"\b(recommend|suggest|advice|advise|options|which|what|why|how)\b", text):
            return False
        return bool(re.search(r"\b(buy|purchase|order|take this|get this|i want this)\b", text))

    def display_search_query_from_products(self, products: list[dict]) -> str:
        for product in products:
            for key in ("subcategory", "category_name", "category", "name", "title", "brand"):
                words = self.search_query_words(product.get(key))
                if words:
                    return " ".join(words[:3])
        return "products"


class ProductCatalogFormatter:
    """Format source-backed product facts without inventing missing data."""

    def answer_text(self, products: list[dict]) -> str:
        if len(products) == 1:
            product = products[0]
            details = self.fact_parts(product)
            detail_text = " ".join(details) if details else "I found it in the catalog."
            return f"Based on the catalog, {self.display_name(product)} is worth considering. {detail_text}"

        bullets = [
            f"- {self.display_name(product)}: {' '.join(self.fact_parts(product)) or 'catalog item'}"
            for product in products[:3]
        ]
        return "Here are source-backed options to consider:\n" + "\n".join(bullets)

    def search_text(self, products: list[dict]) -> str:
        shown = products[:3]
        prefix = (
            "I found this matching product:"
            if len(products) == 1
            else f"I found {len(products)} matching products:"
        )
        bullets = [
            f"- {self.display_name(product)}: {' '.join(self.search_fact_parts(product)) or 'catalog item'}"
            for product in shown
        ]
        if len(products) > len(shown):
            bullets.append("I can show more options too.")
        return prefix + "\n" + "\n".join(bullets)

    def with_accessory_recommendation(self, text: str, products: list[dict]) -> str:
        product = products[0] if products else {}
        product_name = self.display_name(product)
        return (
            f"{text} For the accessory, I would add a protective case with {product_name}; "
            "it protects the phone and is the safest first add-on."
        )

    def comparison_text(self, products: list[dict]) -> str:
        names = " and ".join(self.display_name(product) for product in products[:2])
        bullets = [
            f"- {self.display_name(product)}: {self.comparison_fact_text(product)}"
            for product in products[:4]
        ]
        return f"I found {names}. Here is a source-backed comparison:\n" + "\n".join(bullets)

    def comparison_fact_text(self, product: dict) -> str:
        parts = self.fact_parts(product)
        if self.price(product) is None:
            parts.append("Price not published in retrieved data.")
        return " ".join(parts) if parts else "Only basic catalog data is published for this item."

    def search_fact_parts(self, product: dict) -> list[str]:
        parts: list[str] = []
        brand = str(product.get("brand") or product.get("vendor") or "").strip()
        price = self.price(product)
        stock = self.stock(product)
        if brand:
            parts.append(f"Brand: {brand}.")
        if price is not None and price > 0:
            parts.append(f"Price: {price:g}.")
        if stock is not None:
            parts.append("In stock." if stock > 0 else "Sold out.")
        rating_text = self.rating_text(product)
        if rating_text:
            parts.append(rating_text)
        return parts

    def fact_parts(self, product: dict) -> list[str]:
        parts: list[str] = []
        brand = str(product.get("brand") or product.get("vendor") or "").strip()
        category = str(product.get("category_name") or product.get("category") or product.get("subcategory") or "").strip()
        description = concise_text(plain_text(product.get("description") or product.get("summary") or ""))
        price = self.price(product)
        stock = self.stock(product)
        if brand:
            parts.append(f"Brand: {brand}.")
        if category:
            parts.append(f"Category: {category}.")
        if price is not None and price > 0:
            parts.append(f"Price: {price:g}.")
        if stock is not None:
            parts.append("In stock." if stock > 0 else "Currently sold out.")
        rating_text = self.rating_text(product)
        if rating_text:
            parts.append(rating_text)
        if description:
            parts.append(description[:140])
        return parts

    def rating_text(self, product: dict) -> str:
        rating = numeric_value(product.get("rating"))
        review_count = numeric_value(product.get("review_count"))
        if rating is None or rating <= 0:
            return ""
        if review_count is not None and review_count > 0:
            return f"Rating: {rating:g}/5 ({int(review_count)} reviews)."
        return f"Rating: {rating:g}/5."

    def stock(self, product: dict) -> int | None:
        raw_stock = product.get("stock")
        if raw_stock is None:
            return None
        try:
            return max(0, int(float(raw_stock)))
        except (TypeError, ValueError):
            return None

    def price(self, product: dict) -> float | None:
        candidates = [
            product.get("price"),
            product.get("amount"),
            product.get("cost"),
            product.get("premium"),
        ]
        for container_key in ("pricing", "attributes"):
            container = product.get(container_key)
            if not isinstance(container, dict):
                continue
            candidates.extend(
                [
                    container.get("price"),
                    container.get("amount"),
                    container.get("cost"),
                    container.get("premium"),
                    container.get("premium_min"),
                    container.get("monthly_premium"),
                    container.get("annual_premium"),
                    container.get("min_price"),
                    container.get("starting_price"),
                    container.get("fare"),
                    container.get("fee"),
                    container.get("rate"),
                ]
            )
        for value in candidates:
            number = numeric_value(value)
            if number is not None:
                return number
        return None

    def display_name(self, product: dict) -> str:
        return str(product.get("name") or product.get("title") or "That item")

    def cart_confirmation_text(self, product: dict, quantity: int) -> str:
        name = self.display_name(product)
        if quantity > 1:
            return f"I'll try to add {quantity} x {name} to your cart now."
        return f"I'll try to add {name} to your cart now."


class ProductDisplayGrounder:
    """Rewrite product display responses from selected retrieved rows."""

    def __init__(self, formatter: ProductCatalogFormatter) -> None:
        self._formatter = formatter

    def ground_response(
        self,
        response: dict[str, Any],
        transcript: str,
        retrieved_products: list[dict],
        *,
        wants_comparison: Callable[[str], bool],
        wants_source_answer: Callable[[str], bool],
    ) -> None:
        actions = response.get("ui_actions")
        if not isinstance(actions, list):
            return

        display_action, display_action_name = self._first_display_action(actions)
        if not display_action:
            return

        selected = self.products_selected_by_display_action(display_action, retrieved_products)
        if not selected:
            return

        if display_action_name == ACTION_SHOW_COMPARISON or wants_comparison(transcript):
            response["intent"] = "product_compare"
            response["response_text"] = self._comparison_response_text(selected, transcript)
            return

        if len(selected) == 1 and wants_source_answer(transcript):
            response["intent"] = "product_detail"
            response_text = self._formatter.answer_text(selected)
            if self._wants_accessory_recommendation(transcript):
                response_text = self._formatter.with_accessory_recommendation(response_text, selected)
            response["response_text"] = response_text
            return

        if str(response.get("intent") or "") not in {"product_detail", "product_compare"}:
            response["intent"] = "product_search"
        response_text = self._formatter.search_text(selected)
        if self._wants_accessory_recommendation(transcript):
            response_text = self._formatter.with_accessory_recommendation(response_text, selected)
        response["response_text"] = response_text

    def products_selected_by_display_action(
        self,
        action: dict[str, Any],
        retrieved_products: list[dict],
    ) -> list[dict]:
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        requested_ids = params.get(PRODUCT_IDS_PARAM)
        if not isinstance(requested_ids, list):
            requested_ids = []

        by_id = {
            str(product.get("id")): product
            for product in retrieved_products
            if product.get("id") is not None
        }
        selected = [
            by_id[str(product_id)]
            for product_id in requested_ids
            if str(product_id) in by_id
        ]
        if selected:
            return selected

        action_name = str(action.get("action") or "").upper()
        fallback_limit = 4 if action_name == ACTION_SHOW_COMPARISON else 6
        return [product for product in retrieved_products if product.get("id") is not None][:fallback_limit]

    def _first_display_action(self, actions: list[Any]) -> tuple[dict[str, Any] | None, str]:
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_name = str(action.get("action") or "").upper()
            if action_name in {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON}:
                return action, action_name
        return None, ""

    def _wants_accessory_recommendation(self, transcript: str) -> bool:
        text = normalize_lookup_text(transcript)
        return bool(re.search(r"\b(accessory|accessories|case|cover|screen protector|charger|add on|addon)\b", text))

    def _comparison_response_text(self, products: list[dict], transcript: str) -> str:
        response_text = self._formatter.comparison_text(products)
        if not self._buyer_is_undecided(transcript):
            return response_text
        return (
            response_text
            + "\nWhat matters most to you: budget, camera, battery life, software experience, or long-term support?"
        )

    def _buyer_is_undecided(self, transcript: str) -> bool:
        text = normalize_lookup_text(transcript)
        return bool(
            re.search(
                r"\b(confused|undecided|not sure|cannot decide|can't decide|which direction|suits me)\b",
                text,
            )
        )
