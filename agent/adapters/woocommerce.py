"""
WooCommerce platform adapter.

Handles WooCommerce-specific product normalization, variant/variation
extraction, cart API payloads (Store API), and checkout URLs.
Reuses existing ingestion helpers from agent.ingestion.
"""

from __future__ import annotations

import logging
import hashlib
from typing import Any
from urllib.parse import urljoin

from agent.ingestion import (
    _clean_text,
    _first,
    _image_url_from_value,
    _normalize_product_row,
    _strip_html,
    _term_names,
    _to_float,
    _to_tags,
    _woocommerce_price,
)

logger = logging.getLogger(__name__)

WOO_STORE_API_PRODUCTS = "/wp-json/wc/store/products"
WOO_STORE_API_CART_ADD = "/wp-json/wc/store/cart/add-item"
WOO_STORE_API_CART = "/wp-json/wc/store/cart"
WOO_STORE_API_CART_REMOVE = "/wp-json/wc/store/cart/remove-item"
WOO_STORE_API_CART_UPDATE = "/wp-json/wc/store/cart/update-item"
WOO_CHECKOUT_PATH = "/checkout"
WOO_MAX_PAGE_SIZE = 100
WOO_MAX_PAGES = 20


def _positive_int(value: Any) -> int | None:
    """Parse platform IDs without floating point precision loss."""
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text.isdigit():
        return None
    parsed = int(text)
    return parsed if parsed > 0 else None


def _stable_variant_id(product_id: int, value: str, position: int) -> int:
    seed = f"{product_id}|{value}|{position}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return int(digest, 16) % (2**63 - 1) or 1


class WooCommerceAdapter:
    """WooCommerce-specific platform adapter."""

    platform: str = "woocommerce"

    def normalize_product(
        self,
        raw: dict[str, Any],
        source_url: str,
    ) -> dict[str, Any] | None:
        """Normalize a WooCommerce Store API product into Hub schema."""
        prices = raw.get("prices") if isinstance(raw.get("prices"), dict) else {}
        category_names = _term_names(raw.get("categories"))
        tag_names = _term_names(raw.get("tags"))
        in_stock = _first(raw.get("is_in_stock"), raw.get("in_stock"), default=True)
        stock = _first(raw.get("stock_quantity"), raw.get("stock"), default=None)
        if stock in (None, ""):
            stock = 100 if in_stock is not False else 0

        price = _woocommerce_price(prices, "price", "sale_price", "regular_price")
        if price <= 0:
            price = _to_float(_first(raw.get("price"), raw.get("sale_price"), raw.get("regular_price"), 0))

        regular_price = _woocommerce_price(prices, "regular_price", "price")
        if regular_price <= 0:
            regular_price = _to_float(_first(raw.get("regular_price"), price))

        return _normalize_product_row(
            {
                "id": _first(raw.get("id"), raw.get("sku"), raw.get("slug"), default=None),
                "name": _first(raw.get("name"), raw.get("title"), raw.get("slug")),
                "description": _first(
                    _strip_html(raw.get("description")),
                    _strip_html(raw.get("short_description")),
                    raw.get("name"),
                ),
                "category": _first(
                    category_names[0] if category_names else None,
                    raw.get("category"),
                    "Products",
                ),
                "brand": _first(raw.get("brand"), raw.get("vendor"), "Unknown Brand"),
                "price": price,
                "original_price": regular_price,
                "image": _image_url_from_value(raw.get("images")),
                "stock": stock,
                "tags": tag_names,
                "rating": raw.get("average_rating"),
                "review_count": raw.get("review_count"),
                "is_active": 1 if in_stock is not False and int(_to_float(stock)) > 0 else 0,
            },
            fallback_category=_clean_text(
                _first(category_names[0] if category_names else None, "Products")
            ),
            source_url=source_url,
        )

    def extract_variants(
        self,
        raw: dict[str, Any],
        product_id: int,
        source_url: str,
    ) -> list[dict[str, Any]]:
        """Extract WooCommerce variation/attribute data as variant rows."""
        # WooCommerce variations are separate product objects
        raw_variations = raw.get("variations")
        if not isinstance(raw_variations, list) or not raw_variations:
            # Try to use attributes as variant-like data
            return self._variants_from_attributes(raw, product_id)

        results: list[dict[str, Any]] = []
        for idx, variation in enumerate(raw_variations):
            if isinstance(variation, (int, str)):
                variant_id = _positive_int(variation)
                if variant_id is None:
                    continue
                results.append(self._variant_stub_from_id(raw, product_id, variant_id, idx))
                continue

            if not isinstance(variation, dict):
                continue

            variation_id = _positive_int(variation.get("id"))
            if variation_id is None:
                continue

            attributes = variation.get("attributes") or []
            option_pairs: list[tuple[str, str]] = []
            for attr in attributes:
                if isinstance(attr, dict):
                    attr_name = str(attr.get("name") or attr.get("attribute") or "")
                    attr_value = str(attr.get("value") or attr.get("option") or "")
                    if attr_name and attr_value:
                        option_pairs.append((attr_name, attr_value))

            prices = variation.get("prices") if isinstance(variation.get("prices"), dict) else {}
            price = _woocommerce_price(prices, "price", "sale_price", "regular_price")
            if price <= 0:
                price = _to_float(_first(variation.get("price"), 0))

            compare_price = _woocommerce_price(prices, "regular_price", "price")
            stock_val = _first(variation.get("stock_quantity"), variation.get("stock"), default=100)
            available = variation.get("is_in_stock", True) is not False

            title_parts = [p[1] for p in option_pairs[:3]]
            title = _clean_text(" / ".join(title_parts)) or "Default"

            variant_row: dict[str, Any] = {
                "id": variation_id,
                "product_id": product_id,
                "sku": _clean_text(variation.get("sku") or ""),
                "title": title,
                "option1_name": option_pairs[0][0] if len(option_pairs) > 0 else None,
                "option1_value": option_pairs[0][1] if len(option_pairs) > 0 else None,
                "option2_name": option_pairs[1][0] if len(option_pairs) > 1 else None,
                "option2_value": option_pairs[1][1] if len(option_pairs) > 1 else None,
                "option3_name": option_pairs[2][0] if len(option_pairs) > 2 else None,
                "option3_value": option_pairs[2][1] if len(option_pairs) > 2 else None,
                "price": price,
                "compare_at_price": compare_price if compare_price > 0 else None,
                "stock": int(_to_float(stock_val)),
                "available": available,
                "image_url": _image_url_from_value(variation.get("image")),
                "cart_id": str(variation_id),
                "position": idx,
            }
            results.append(variant_row)

        return results

    def _variant_stub_from_id(
        self,
        raw: dict[str, Any],
        product_id: int,
        variation_id: int,
        position: int,
    ) -> dict[str, Any]:
        """Create a conservative variant row when Woo only returns variation IDs."""
        option_name, option_value = self._option_for_position(raw, position)
        prices = raw.get("prices") if isinstance(raw.get("prices"), dict) else {}
        price = _woocommerce_price(prices, "price", "sale_price", "regular_price")
        title = option_value or f"Variation {variation_id}"
        return {
            "id": variation_id,
            "product_id": product_id,
            "sku": "",
            "title": title,
            "option1_name": option_name,
            "option1_value": option_value,
            "option2_name": None,
            "option2_value": None,
            "option3_name": None,
            "option3_value": None,
            "price": price,
            "compare_at_price": None,
            "stock": 100 if raw.get("is_in_stock", True) is not False else 0,
            "available": raw.get("is_in_stock", True) is not False,
            "image_url": _image_url_from_value(raw.get("images")),
            "cart_id": str(variation_id),
            "position": position,
        }

    def _option_for_position(
        self,
        raw: dict[str, Any],
        position: int,
    ) -> tuple[str | None, str | None]:
        """Map a variation ID position to the first variation attribute term when possible."""
        attributes = raw.get("attributes")
        if not isinstance(attributes, list):
            return None, None
        for attr in attributes:
            if not isinstance(attr, dict) or not attr.get("variation", False):
                continue
            terms = attr.get("terms") or attr.get("options") or []
            if position >= len(terms):
                return str(attr.get("name") or "") or None, None
            term = terms[position]
            value = str(term.get("name") or term) if isinstance(term, dict) else str(term)
            return str(attr.get("name") or "") or None, value or None
        return None, None

    def _variants_from_attributes(
        self,
        raw: dict[str, Any],
        product_id: int,
    ) -> list[dict[str, Any]]:
        """Create pseudo-variant rows from WooCommerce product attributes."""
        attributes = raw.get("attributes")
        if not isinstance(attributes, list) or not attributes:
            return []

        # Only create variants from variation-type attributes
        variant_attrs = [
            attr for attr in attributes
            if isinstance(attr, dict) and attr.get("variation", False)
        ]
        if not variant_attrs:
            return []

        # Simple case: one variant attribute with terms
        if len(variant_attrs) == 1:
            attr = variant_attrs[0]
            attr_name = str(attr.get("name") or "")
            terms = attr.get("terms") or attr.get("options") or []
            results: list[dict[str, Any]] = []
            for idx, term in enumerate(terms):
                term_value = str(term.get("name") or term) if isinstance(term, dict) else str(term)
                results.append({
                    "id": _stable_variant_id(product_id, term_value, idx),
                    "product_id": product_id,
                    "sku": "",
                    "title": term_value,
                    "option1_name": attr_name,
                    "option1_value": term_value,
                    "option2_name": None,
                    "option2_value": None,
                    "option3_name": None,
                    "option3_value": None,
                    "price": 0.0,
                    "compare_at_price": None,
                    "stock": 0,
                    "available": True,
                    "image_url": None,
                    "cart_id": None,
                    "position": idx,
                })
            return results

        return []

    def cart_add_payload(
        self,
        variant_id: str,
        quantity: int,
    ) -> dict[str, Any]:
        """Build WooCommerce Store API cart add payload."""
        return {
            "id": int(variant_id),
            "quantity": max(1, quantity),
        }

    def cart_api_url(self, base_url: str) -> str:
        """Return WooCommerce Store API cart add endpoint."""
        return urljoin(base_url.rstrip("/") + "/", WOO_STORE_API_CART_ADD.lstrip("/"))

    def checkout_url(self, base_url: str) -> str:
        """Return WooCommerce checkout URL."""
        return urljoin(base_url.rstrip("/") + "/", WOO_CHECKOUT_PATH.lstrip("/"))

    def catalog_pages_url(self, base_url: str, page: int) -> str:
        """Return WooCommerce paginated product list URL."""
        return urljoin(
            base_url.rstrip("/") + "/",
            f"{WOO_STORE_API_PRODUCTS.lstrip('/')}?per_page={WOO_MAX_PAGE_SIZE}&page={page}",
        )
