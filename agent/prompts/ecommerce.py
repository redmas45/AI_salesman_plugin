"""Ecommerce prompt assembly and formatting helpers."""

from __future__ import annotations

import re
from typing import Any

import psycopg

from agent.action_helpers.capabilities import capability_prompt_context
from agent.action_helpers.sales_intake import sales_intake_prompt_context
from db.core.database import get_db


def build_system_prompt(
    *,
    template: str,
    site_id: str,
    product_context: str,
    cart_context: str = "",
    profile_context: str = "",
    page_context: str = "",
) -> str:
    """Inject retrieved product context and cart state into the ecommerce system prompt."""
    categories = _load_categories(site_id)
    category_names = [category["name"] for category in categories]
    category_slugs = [f"category/{category['slug']}" for category in categories]

    system_prompt = _apply_category_placeholders(
        template,
        category_names=category_names,
        category_slugs=category_slugs,
    )
    system_prompt = _append_runtime_context(system_prompt, site_id, page_context)
    return system_prompt.format(
        product_context=_product_context_or_fallback(product_context, category_names),
        cart_context=cart_context.strip() or "The cart is empty.",
        profile_context=profile_context.strip() or "Address: None | Payment Method: None | Preferences: None",
    )


def format_products_for_prompt(
    products: list[dict[str, Any]],
    price_constraints: dict[str, Any] | None = None,
) -> str:
    """Format retrieved product rows into compact, ID-preserving LLM context."""
    if not products:
        return "No matching products found in inventory."

    lines: list[str] = []
    budget_header = _budget_header(price_constraints)
    if budget_header:
        lines.append(budget_header)

    brand_line = _brand_line(products)
    if brand_line:
        lines.append(brand_line)

    lines.extend(_product_line(product) for product in products)
    return "\n".join(lines)


def format_cart_for_prompt(cart_items: list[dict[str, Any]]) -> str:
    """Format cart items into compact, ID-preserving LLM context."""
    if not cart_items:
        return "The cart is empty."

    total = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart_items)
    lines = [f"Cart has {len(cart_items)} item(s), total Rs {total:,.2f}:"]
    for item in cart_items:
        subtotal = item.get("price", 0) * item.get("quantity", 1)
        lines.append(
            f"  - [ID:{item['id']}] {item['name']} x {item['quantity']} = Rs {subtotal:,.2f}"
        )
    return "\n".join(lines)


def _load_categories(site_id: str) -> list[dict[str, str]]:
    try:
        with get_db(site_id) as conn:
            rows = conn.execute("SELECT name, slug FROM categories ORDER BY name ASC").fetchall()
    except psycopg.Error:
        return []
    return [{"name": str(row["name"]), "slug": str(row["slug"])} for row in rows]


def _apply_category_placeholders(template: str, *, category_names: list[str], category_slugs: list[str]) -> str:
    category_list = ", ".join(category_names)
    return (
        template.replace("__CATEGORIES_LIST__", category_list)
        .replace("__CATEGORIES_BOLD_LIST__", _bold_category_list(category_names))
        .replace("__CATEGORIES_NAV_LIST__", ", ".join(category_slugs))
    )


def _append_runtime_context(system_prompt: str, site_id: str, page_context: str) -> str:
    capability_context = capability_prompt_context(site_id)
    if capability_context:
        system_prompt += f"\n\n## Website Capabilities Context\n{capability_context}\n"

    system_prompt += f"\n\n{sales_intake_prompt_context('ecommerce')}\n"
    client_prompt = _client_prompt_context(site_id)
    if client_prompt:
        system_prompt += f"\n\n## Published Client Prompt\n{client_prompt}\n"

    if page_context.strip():
        system_prompt += f"\n\n{page_context.strip()}\n"
    return system_prompt


def _client_prompt_context(site_id: str) -> str:
    try:
        from db.prompting.prompt_profiles import prompt_profile_context

        return prompt_profile_context(site_id)
    except (LookupError, RuntimeError, ValueError, psycopg.Error):
        return ""


def _product_context_or_fallback(product_context: str, category_names: list[str]) -> str:
    if product_context.strip():
        return product_context
    category_list = ", ".join(category_names)
    return (
        f"No matching products were retrieved. We strictly only sell items in: {category_list}. "
        "Do NOT recommend or mention items we do not sell (e.g. flowers, books, electronics). "
        "Instead, apologize warmly and guide the customer to look at one of our available categories."
    )


def _bold_category_list(category_names: list[str]) -> str:
    if len(category_names) > 1:
        return "**" + "**, **".join(category_names[:-1]) + "**, and **" + category_names[-1] + "**"
    if len(category_names) == 1:
        return "**" + category_names[0] + "**"
    return "no categories"


def _budget_header(price_constraints: dict[str, Any] | None) -> str:
    if not price_constraints:
        return ""

    parts = []
    if "max_price" in price_constraints:
        parts.append(f"max budget Rs {int(price_constraints['max_price']):,}")
    if "min_price" in price_constraints:
        parts.append(f"min budget Rs {int(price_constraints['min_price']):,}")
    if not parts:
        return ""
    return f"CUSTOMER BUDGET: {', '.join(parts)}. ONLY recommend products within this budget!\n"


def _brand_line(products: list[dict[str, Any]]) -> str:
    brands = {product.get("brand") for product in products if product.get("brand")}
    if not brands:
        return ""
    return f"Brands available in this list: {', '.join(sorted(brands))}\n"


def _product_line(product: dict[str, Any]) -> str:
    parts = [
        f'[ID:"{product["id"]}"] {product["name"]} by {product["brand"]}',
        f"Category: {product.get('category_name', product.get('category', ''))}",
        f"Color: {product.get('color', 'N/A')}",
        f"Sizes: {_option_text(product.get('size_options')) or 'N/A'}",
        f"Tags: {_option_text(product.get('tags')) or 'None'}",
        f"Price: Rs {int(product['price']):,}{_discount_text(product)}",
        f"Stock: {product.get('stock', 0)}",
        f"Rating: {product.get('rating', 0)}* ({product.get('review_count', 0)} reviews)",
        f"Description: {_clean_description(product.get('description'))[:200]}...",
    ]
    return " | ".join(parts)


def _discount_text(product: dict[str, Any]) -> str:
    original_price = product.get("original_price")
    price = product.get("price")
    if not original_price or original_price <= price:
        return ""
    discount_percent = int((1 - price / original_price) * 100)
    return f" ({discount_percent}% off Rs {int(original_price):,})"


def _option_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, str):
        return value
    return ""


def _clean_description(value: Any) -> str:
    description = re.sub(r"<[^>]+>", " ", str(value or "")).strip()
    return re.sub(r"\s+", " ", description)
