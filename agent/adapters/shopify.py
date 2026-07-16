"""
Shopify platform adapter.

Handles Shopify-specific product normalization, variant extraction,
cart API payloads, and checkout URLs. Reuses existing ingestion helpers.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

from agent.ingestion_helpers.ingestion_facade import (
    _clean_text,
    _first,
    _image_url_from_value,
    _normalize_product_row,
    _strip_html,
    _to_float,
    _to_tags,
)

logger = logging.getLogger(__name__)

SHOPIFY_CART_ADD_ENDPOINT = "/cart/add.js"
SHOPIFY_CART_ENDPOINT = "/cart.js"
SHOPIFY_CHECKOUT_PATH = "/checkout"
SHOPIFY_PRODUCTS_PATH = "/collections/all/products.json"
SHOPIFY_MAX_PAGE_SIZE = 250
SHOPIFY_MAX_PAGES = 20


def _positive_int(value: Any) -> int | None:
    """Parse platform IDs without floating point precision loss."""
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text.isdigit():
        return None
    parsed = int(text)
    return parsed if parsed > 0 else None


class ShopifyAdapter:
    """Shopify-specific platform adapter."""

    platform: str = "shopify"

    def normalize_product(
        self,
        raw: dict[str, Any],
        source_url: str,
    ) -> dict[str, Any] | None:
        """Normalize a Shopify product JSON into Hub product schema."""
        variants = raw.get("variants") if isinstance(raw.get("variants"), list) else []
        selected_variant: dict[str, Any] = {}
        for variant in variants:
            if isinstance(variant, dict) and variant.get("available") is not False:
                selected_variant = variant
                break
        if not selected_variant and variants and isinstance(variants[0], dict):
            selected_variant = variants[0]

        image = _image_url_from_value(
            _first(raw.get("image"), raw.get("images"), raw.get("featured_image"), default=None)
        )
        available = _first(selected_variant.get("available"), raw.get("available"), default=True)
        stock = _first(selected_variant.get("inventory_quantity"), raw.get("stock"), default=None)
        if stock in (None, ""):
            stock = 100 if available is not False else 0

        variant_id = _positive_int(selected_variant.get("id"))

        return _normalize_product_row(
            {
                "id": _first(raw.get("id"), raw.get("handle"), raw.get("sku"), default=None),
                "variant_id": variant_id,
                "name": _first(raw.get("title"), raw.get("name"), raw.get("handle")),
                "description": _first(
                    _strip_html(raw.get("body_html")),
                    raw.get("description"),
                    raw.get("title"),
                ),
                "category": _first(raw.get("product_type"), raw.get("category"), "Products"),
                "brand": _first(raw.get("vendor"), raw.get("brand"), "Unknown Brand"),
                "price": _first(selected_variant.get("price"), raw.get("price"), 0),
                "original_price": _first(
                    selected_variant.get("compare_at_price"),
                    raw.get("compare_at_price"),
                    selected_variant.get("price"),
                    raw.get("price"),
                    0,
                ),
                "image": image,
                "stock": stock,
                "tags": _to_tags(raw.get("tags")),
                "is_active": 1 if available is not False and int(_to_float(stock)) > 0 else 0,
            },
            fallback_category=_clean_text(_first(raw.get("product_type"), "Products")),
            source_url=source_url,
        )

    def extract_variants(
        self,
        raw: dict[str, Any],
        product_id: int,
        source_url: str,
    ) -> list[dict[str, Any]]:
        """Extract all Shopify variants for a product."""
        raw_variants = raw.get("variants")
        if not isinstance(raw_variants, list) or not raw_variants:
            return []

        options = raw.get("options") or []
        option_names: list[str] = []
        for opt in options:
            if isinstance(opt, dict):
                option_names.append(str(opt.get("name") or ""))
            elif isinstance(opt, str):
                option_names.append(opt)

        results: list[dict[str, Any]] = []
        for idx, variant in enumerate(raw_variants):
            if not isinstance(variant, dict):
                continue

            variant_id = _positive_int(variant.get("id"))
            if variant_id is None:
                continue

            title = _clean_text(variant.get("title") or "Default")
            available = variant.get("available")
            stock = variant.get("inventory_quantity")
            if stock in (None, ""):
                stock = 100 if available is not False else 0

            variant_row: dict[str, Any] = {
                "id": variant_id,
                "product_id": product_id,
                "sku": _clean_text(variant.get("sku") or ""),
                "title": title,
                "option1_name": option_names[0] if len(option_names) > 0 else None,
                "option1_value": _clean_text(variant.get("option1") or ""),
                "option2_name": option_names[1] if len(option_names) > 1 else None,
                "option2_value": _clean_text(variant.get("option2") or ""),
                "option3_name": option_names[2] if len(option_names) > 2 else None,
                "option3_value": _clean_text(variant.get("option3") or ""),
                "price": _to_float(variant.get("price") or 0),
                "compare_at_price": _to_float(variant.get("compare_at_price") or 0) or None,
                "stock": int(_to_float(stock)),
                "available": available is not False,
                "image_url": _image_url_from_value(variant.get("featured_image")),
                "cart_id": str(variant_id),
                "position": idx,
            }
            results.append(variant_row)

        return results

    def cart_add_payload(
        self,
        variant_id: str,
        quantity: int,
    ) -> dict[str, Any]:
        """Build Shopify /cart/add.js JSON payload."""
        return {
            "items": [
                {
                    "id": int(variant_id),
                    "quantity": max(1, quantity),
                }
            ],
        }

    def cart_api_url(self, base_url: str) -> str:
        """Return Shopify cart add endpoint."""
        return urljoin(base_url.rstrip("/") + "/", SHOPIFY_CART_ADD_ENDPOINT.lstrip("/"))

    def checkout_url(self, base_url: str) -> str:
        """Return Shopify checkout URL."""
        return urljoin(base_url.rstrip("/") + "/", SHOPIFY_CHECKOUT_PATH.lstrip("/"))

    def product_url(self, base_url: str, handle: str) -> str:
        """Return Shopify product page URL."""
        return urljoin(base_url.rstrip("/") + "/", f"products/{handle}")

    def catalog_pages_url(self, base_url: str, page: int) -> str:
        """Return Shopify paginated products.json URL."""
        return urljoin(
            base_url.rstrip("/") + "/",
            f"{SHOPIFY_PRODUCTS_PATH.lstrip('/')}?limit={SHOPIFY_MAX_PAGE_SIZE}&page={page}",
        )
