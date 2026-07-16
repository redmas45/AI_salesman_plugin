"""Tenant cart persistence helpers."""

from __future__ import annotations

from typing import Any


def get_cart_items(site_id: str) -> list[dict[str, Any]]:
    """Return all items in the cart with product details."""
    from db.core.database import get_db

    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT c.id as cart_id, c.quantity, CAST(c.added_at AS TEXT) as added_at, p.*, cat.name AS category_name, cat.slug AS category_slug
            FROM cart c
            JOIN products p ON c.product_id = p.id
            JOIN categories cat ON p.category_id = cat.id
            ORDER BY c.added_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def add_to_cart(site_id: str, product_id: int | str, quantity: int = 1) -> int:
    """Add a product to the cart or increment quantity if it exists."""
    from db.core.database import ProductNotFoundError, coerce_product_id, get_db, product_exists

    clean_product_id = coerce_product_id(product_id)
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    if not product_exists(site_id, clean_product_id):
        raise ProductNotFoundError(f"Product {clean_product_id} was not found.")
    with get_db(site_id) as conn:
        row = conn.execute(
            "SELECT id, quantity FROM cart WHERE product_id = %s", (clean_product_id,)
        ).fetchone()
        if row:
            new_quantity = row["quantity"] + quantity
            conn.execute(
                "UPDATE cart SET quantity = %s WHERE id = %s", (new_quantity, row["id"])
            )
            return int(row["id"])

        cursor = conn.execute(
            "INSERT INTO cart (product_id, quantity) VALUES (%s, %s) RETURNING id",
            (clean_product_id, quantity),
        )
        return int(cursor.fetchone()["id"])


def update_cart_quantity(site_id: str, product_id: int | str, quantity: int) -> bool:
    """Update quantity of a product in the cart. Remove if <= 0."""
    from db.core.database import InvalidProductIdError, coerce_product_id, get_db

    try:
        clean_product_id = coerce_product_id(product_id)
    except InvalidProductIdError:
        return False
    with get_db(site_id) as conn:
        row = conn.execute(
            "SELECT id FROM cart WHERE product_id = %s", (clean_product_id,)
        ).fetchone()
        if not row:
            return False

        if quantity <= 0:
            cursor = conn.execute(
                "DELETE FROM cart WHERE id = %s", (row["id"],)
            )
        else:
            cursor = conn.execute(
                "UPDATE cart SET quantity = %s WHERE id = %s",
                (quantity, row["id"]),
            )
        return cursor.rowcount > 0


def remove_from_cart(site_id: str, cart_id: int) -> bool:
    """Remove a specific cart entry by ID."""
    from db.core.database import get_db

    with get_db(site_id) as conn:
        cursor = conn.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
        return cursor.rowcount > 0


def clear_cart(site_id: str) -> None:
    """Remove all items from the cart."""
    from db.core.database import get_db

    with get_db(site_id) as conn:
        conn.execute("DELETE FROM cart")


def checkout_cart(site_id: str) -> None:
    """Process checkout: deduct stock, mark inactive if out of stock, clear cart."""
    from db.core.database import get_db

    with get_db(site_id) as conn:
        rows = conn.execute("SELECT product_id, quantity FROM cart").fetchall()
        for row in rows:
            conn.execute(
                """
                UPDATE products
                SET stock = GREATEST(stock - %s, 0),
                    is_active = CASE WHEN (stock - %s) <= 0 THEN 0 ELSE is_active END
                WHERE id = %s
                """,
                (row["quantity"], row["quantity"], row["product_id"]),
            )
        conn.execute("DELETE FROM cart")
