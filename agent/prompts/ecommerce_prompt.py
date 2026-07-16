"""
System prompt and few-shot examples for the ecommerce vertical.
The prompt is assembled dynamically with retrieved product context injected.
"""

from typing import Any

from agent.prompts import ecommerce
from agent.prompts.ecommerce_template import SYSTEM_PROMPT_TEMPLATE


ACTIVE_SYSTEM_PROMPT = None
ACTIVE_FALLBACK_CONTEXT = None


def build_system_prompt(
    site_id: str,
    product_context: str,
    cart_context: str = "",
    profile_context: str = "",
    page_context: str = "",
) -> str:
    """
    Inject retrieved product context and cart state into the system prompt dynamically per tenant.
    """
    return ecommerce.build_system_prompt(
        template=SYSTEM_PROMPT_TEMPLATE,
        site_id=site_id,
        product_context=product_context,
        cart_context=cart_context,
        profile_context=profile_context,
        page_context=page_context,
    )


def format_products_for_prompt(
    products: list[dict[str, Any]],
    price_constraints: dict[str, Any] | None = None,
) -> str:
    """
    Format a list of product dicts into a compact, LLM-readable string.

    Args:
        products:           List of product dicts from the database.
        price_constraints:  Optional dict with 'max_price' and/or 'min_price' extracted from query.

    Returns:
        Formatted multi-line string.
    """
    return ecommerce.format_products_for_prompt(products, price_constraints)


def format_cart_for_prompt(cart_items: list[dict[str, Any]]) -> str:
    """Format cart items into a compact string for the LLM."""
    return ecommerce.format_cart_for_prompt(cart_items)
