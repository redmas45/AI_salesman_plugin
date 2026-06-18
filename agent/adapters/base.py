"""
Base adapter protocol for platform-specific ecommerce integration.

All platform adapters (Shopify, WooCommerce, custom) implement this
protocol so the Hub can normalize products, variants, and cart
operations consistently.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol that all platform adapters must implement."""

    platform: str  # "shopify", "woocommerce", "generic"

    def normalize_product(
        self,
        raw: dict[str, Any],
        source_url: str,
    ) -> dict[str, Any] | None:
        """Normalize a raw product dict into the Hub product schema."""
        ...

    def extract_variants(
        self,
        raw: dict[str, Any],
        product_id: int,
        source_url: str,
    ) -> list[dict[str, Any]]:
        """Extract variant rows from a raw product dict."""
        ...

    def cart_add_payload(
        self,
        variant_id: str,
        quantity: int,
    ) -> dict[str, Any]:
        """Build the JSON body for adding an item to cart."""
        ...

    def cart_api_url(self, base_url: str) -> str:
        """Return the cart add endpoint URL."""
        ...

    def checkout_url(self, base_url: str) -> str:
        """Return the checkout page URL."""
        ...


def select_adapter(platform: str) -> PlatformAdapter:
    """Return the correct adapter for a detected platform."""
    if platform == "shopify":
        from agent.adapters.shopify import ShopifyAdapter
        return ShopifyAdapter()
    if platform == "woocommerce":
        from agent.adapters.woocommerce import WooCommerceAdapter
        return WooCommerceAdapter()

    # Generic fallback — import inline to avoid circular deps
    from agent.adapters.shopify import ShopifyAdapter
    return ShopifyAdapter()  # Shopify adapter is most capable as generic fallback
