"""Product variant persistence helpers."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Callable

import psycopg

DbContext = Callable[[str], AbstractContextManager[psycopg.Connection]]


def upsert_variants(
    site_id: str,
    product_id: int,
    variants: list[dict[str, Any]],
    *,
    db_context: DbContext,
) -> int:
    """Upsert product variants, return count of changed rows."""
    if not variants:
        return 0

    changed = 0
    with db_context(site_id) as conn:
        for variant in variants:
            variant_id = variant.get("id")
            if variant_id is None:
                continue

            row = conn.execute(
                """
                INSERT INTO product_variants
                  (id, product_id, sku, title, option1_name, option1_value,
                   option2_name, option2_value, option3_name, option3_value,
                   price, compare_at_price, stock, available, image_url,
                   cart_id, position)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  sku = EXCLUDED.sku,
                  title = EXCLUDED.title,
                  option1_name = EXCLUDED.option1_name,
                  option1_value = EXCLUDED.option1_value,
                  option2_name = EXCLUDED.option2_name,
                  option2_value = EXCLUDED.option2_value,
                  option3_name = EXCLUDED.option3_name,
                  option3_value = EXCLUDED.option3_value,
                  price = EXCLUDED.price,
                  compare_at_price = EXCLUDED.compare_at_price,
                  stock = EXCLUDED.stock,
                  available = EXCLUDED.available,
                  image_url = EXCLUDED.image_url,
                  cart_id = EXCLUDED.cart_id,
                  position = EXCLUDED.position
                WHERE product_variants.sku IS DISTINCT FROM EXCLUDED.sku
                   OR product_variants.title IS DISTINCT FROM EXCLUDED.title
                   OR product_variants.price IS DISTINCT FROM EXCLUDED.price
                   OR product_variants.stock IS DISTINCT FROM EXCLUDED.stock
                   OR product_variants.available IS DISTINCT FROM EXCLUDED.available
                RETURNING id
                """,
                (
                    variant_id,
                    product_id,
                    variant.get("sku") or "",
                    variant.get("title") or "Default",
                    variant.get("option1_name"),
                    variant.get("option1_value"),
                    variant.get("option2_name"),
                    variant.get("option2_value"),
                    variant.get("option3_name"),
                    variant.get("option3_value"),
                    float(variant.get("price") or 0),
                    float(variant.get("compare_at_price") or 0) or None,
                    int(variant.get("stock") or 0),
                    bool(variant.get("available", True)),
                    variant.get("image_url"),
                    variant.get("cart_id"),
                    int(variant.get("position") or 0),
                ),
            ).fetchone()
            if row:
                changed += 1

    return changed


def get_product_variants(
    site_id: str,
    product_id: int,
    *,
    db_context: DbContext,
) -> list[dict[str, Any]]:
    """Return all variants for a product, ordered by position."""
    with db_context(site_id) as conn:
        rows = conn.execute(
            """
            SELECT id, product_id, sku, title,
                   option1_name, option1_value,
                   option2_name, option2_value,
                   option3_name, option3_value,
                   price, compare_at_price, stock, available,
                   image_url, cart_id, position
            FROM product_variants
            WHERE product_id = %s
            ORDER BY position ASC
            """,
            (product_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_variant_by_id(
    site_id: str,
    variant_id: int,
    *,
    db_context: DbContext,
) -> dict[str, Any] | None:
    """Return a single variant by its ID, or None."""
    with db_context(site_id) as conn:
        row = conn.execute(
            """
            SELECT id, product_id, sku, title,
                   option1_name, option1_value,
                   option2_name, option2_value,
                   option3_name, option3_value,
                   price, compare_at_price, stock, available,
                   image_url, cart_id, position
            FROM product_variants
            WHERE id = %s
            """,
            (variant_id,),
        ).fetchone()
    return dict(row) if row else None
