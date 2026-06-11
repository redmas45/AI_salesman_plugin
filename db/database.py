"""
PostgreSQL database connection helpers for AI Hub.
Uses psycopg 3 thread-local connections.
"""

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator
from psycopg import sql

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

import config

# Thread-local storage for connections
_local = threading.local()


class InvalidProductIdError(ValueError):
    """Raised when a product identifier cannot be safely converted."""


class ProductNotFoundError(LookupError):
    """Raised when a cart operation targets a missing product."""


def coerce_product_id(value: int | str) -> int:
    """Return a positive integer product ID or raise a domain-specific error."""
    if isinstance(value, bool):
        raise InvalidProductIdError("Product ID must be a positive integer.")
    try:
        product_id = int(str(value).strip())
    except (TypeError, ValueError):
        raise InvalidProductIdError("Product ID must be a positive integer.") from None
    if product_id <= 0:
        raise InvalidProductIdError("Product ID must be a positive integer.")
    return product_id


def _get_connection() -> psycopg.Connection:
    """Return a thread-local Postgres connection, creating one if needed."""
    if not hasattr(_local, "conn") or _local.conn is None or _local.conn.closed:
        conn = psycopg.connect(config.DATABASE_URL, row_factory=dict_row, connect_timeout=3)
        # Ensure extension exists before registering it
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        # Register pgvector type
        register_vector(conn)
        _local.conn = conn
    return _local.conn


@contextmanager
def get_db(site_id: str) -> Generator[psycopg.Connection, None, None]:
    """Context manager that yields a DB connection and sets search_path."""
    conn = _get_connection()
    try:
        tenant_schema = f"tenant_{site_id}"
        conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(tenant_schema)))
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def init_tenant_schema(site_id: str) -> None:
    """Create schema for a specific tenant and initialize tables."""
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    tenant_schema = f"tenant_{site_id}"
    conn = _get_connection()
    try:
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(tenant_schema)))
        conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(tenant_schema)))
        conn.execute(schema_sql)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_all_products(site_id: str, limit: int = 10000, offset: int = 0) -> list[dict]:
    """Return an even mix of active products across categories."""
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT p.*, c.name AS category_name, c.slug AS category_slug
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER(PARTITION BY category_id ORDER BY RANDOM()) as rn
                FROM products
                WHERE is_active = 1 AND stock > 0
            ) p
            JOIN categories c ON p.category_id = c.id
            WHERE p.rn <= 1000
            ORDER BY RANDOM()
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
    return rows


def get_products_by_ids(site_id: str, ids: list[int]) -> list[dict]:
    """Return products matching given IDs."""
    if not ids:
        return []
    placeholders = ",".join("%s" for _ in ids)
    with get_db(site_id) as conn:
        rows = conn.execute(
            f"""
            SELECT p.*, c.name AS category_name, c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id IN ({placeholders}) AND p.is_active = 1 AND p.stock > 0
            """,
            ids,
        ).fetchall()
    return rows


def get_products_by_category(site_id: str, category_name: str, limit: int = 50) -> list[dict]:
    """Return active products matching the given category name."""
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT p.*, c.name AS category_name, c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE (c.name = %s OR p.tags LIKE %s) AND p.is_active = 1 AND p.stock > 0
            LIMIT %s
            """,
            (category_name, f'%%"{category_name}"%%', limit),
        ).fetchall()
    return rows


def product_exists(site_id: str, product_id: int | str) -> bool:
    """Check whether a product ID exists and is active."""
    try:
        product_id = coerce_product_id(product_id)
    except InvalidProductIdError:
        return False
    with get_db(site_id) as conn:
        row = conn.execute(
            "SELECT 1 FROM products WHERE id = %s AND is_active = 1 AND stock > 0", (product_id,)
        ).fetchone()
    return row is not None


def tenant_catalog_stats(site_id: str) -> dict:
    """Return lightweight catalog stats for a tenant, or zeros if schema is missing."""
    try:
        init_tenant_schema(site_id)
        with get_db(site_id) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_products,
                    COUNT(*) FILTER (WHERE is_active = 1) AS active_products,
                    COUNT(*) FILTER (WHERE embedding IS NULL) AS missing_embeddings
                FROM products
                """
            ).fetchone()
            return dict(row) if row else {"total_products": 0, "active_products": 0, "missing_embeddings": 0}
    except Exception:
        return {"total_products": 0, "active_products": 0, "missing_embeddings": 0}


def tenant_inventory_summary(site_id: str) -> dict[str, Any]:
    """Return inventory counts for customer-facing status questions."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        catalog = conn.execute(
            """
            SELECT
                COUNT(*) AS total_products,
                COUNT(*) FILTER (WHERE is_active = 1) AS active_products,
                COUNT(*) FILTER (WHERE is_active = 1 AND stock > 0) AS in_stock_products,
                COALESCE(SUM(stock) FILTER (WHERE is_active = 1), 0) AS total_units,
                COUNT(*) FILTER (WHERE embedding IS NULL) AS missing_embeddings
            FROM products
            """
        ).fetchone()
        categories = conn.execute(
            """
            SELECT COUNT(*) AS total_categories
            FROM categories
            """
        ).fetchone()
        cart = conn.execute(
            """
            SELECT COUNT(*) AS cart_rows
            FROM cart
            """
        ).fetchone()

    result = dict(catalog or {})
    result.update(dict(categories or {}))
    result.update(dict(cart or {}))
    return result


def catalog_source_stats(site_id: str) -> list[dict[str, Any]]:
    """Return per-source snapshot counts for a tenant."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT
                source_name,
                COUNT(*) AS total_products,
                COUNT(*) FILTER (WHERE is_active = 1) AS active_products,
                MAX(last_seen_at)::TEXT AS last_seen_at
            FROM catalog_source_products
            GROUP BY source_name
            ORDER BY source_name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def catalog_source_preview(site_id: str, source_name: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return a small product preview from a source snapshot."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT product_id, name, brand, category, price, stock, image_url, is_active
            FROM catalog_source_products
            WHERE source_name = %s
            ORDER BY last_seen_at DESC, name ASC
            LIMIT %s
            """,
            (source_name, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def catalog_sync_history(site_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent catalog sync runs for an admin/status surface."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                source_name,
                source_count,
                changed_count,
                deactivated_count,
                vectorized_count,
                created_at::TEXT AS created_at
            FROM catalog_sync_runs
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def tenant_catalog_preview(site_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return a small preview from the active vectorized catalog table."""
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT
                p.id AS product_id,
                p.name,
                p.brand,
                c.name AS category,
                p.price,
                p.stock,
                p.image_url,
                p.is_active,
                CASE WHEN p.embedding IS NULL THEN 0 ELSE 1 END AS has_embedding
            FROM products p
            JOIN categories c ON p.category_id = c.id
            ORDER BY p.is_active DESC, p.name ASC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


# Cart Helpers


def get_cart_items(site_id: str) -> list[dict]:
    """Return all items in the cart with product details."""
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
    return rows


def add_to_cart(site_id: str, product_id: int | str, quantity: int = 1) -> int:
    """Add a product to the cart or increment quantity if it exists."""
    product_id = coerce_product_id(product_id)
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    if not product_exists(site_id, product_id):
        raise ProductNotFoundError(f"Product {product_id} was not found.")
    with get_db(site_id) as conn:
        row = conn.execute(
            "SELECT id, quantity FROM cart WHERE product_id = %s", (product_id,)
        ).fetchone()
        if row:
            new_qty = row["quantity"] + quantity
            conn.execute(
                "UPDATE cart SET quantity = %s WHERE id = %s", (new_qty, row["id"])
            )
            return row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO cart (product_id, quantity) VALUES (%s, %s) RETURNING id",
                (product_id, quantity),
            )
            return cur.fetchone()["id"]


def update_cart_quantity(site_id: str, product_id: int | str, quantity: int) -> bool:
    """Update quantity of a product in the cart. Remove if <= 0."""
    try:
        product_id = coerce_product_id(product_id)
    except InvalidProductIdError:
        return False
    with get_db(site_id) as conn:
        row = conn.execute(
            "SELECT id FROM cart WHERE product_id = %s", (product_id,)
        ).fetchone()
        if not row:
            return False

        if quantity <= 0:
            cur = conn.execute(
                "DELETE FROM cart WHERE id = %s", (row["id"],)
            )
        else:
            cur = conn.execute(
                "UPDATE cart SET quantity = %s WHERE id = %s",
                (quantity, row["id"]),
            )
        return cur.rowcount > 0


def remove_from_cart(site_id: str, cart_id: int) -> bool:
    """Remove a specific cart entry by ID."""
    with get_db(site_id) as conn:
        cursor = conn.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
        return cursor.rowcount > 0


def clear_cart(site_id: str) -> None:
    """Remove all items from the cart."""
    with get_db(site_id) as conn:
        conn.execute("DELETE FROM cart")


def checkout_cart(site_id: str) -> None:
    """Process checkout: deduct stock, mark inactive if out of stock, clear cart."""
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
                (row["quantity"], row["quantity"], row["product_id"])
            )
        conn.execute("DELETE FROM cart")


# User Profile Helpers


def get_user_profile(site_id: str) -> dict:
    """Get the user profile. If none exists, return empty structure."""
    with get_db(site_id) as conn:
        row = conn.execute(
            "SELECT address, payment_method, preferences FROM user_profile LIMIT 1"
        ).fetchone()
        if row:
            return dict(row)
        return {"address": None, "payment_method": None, "preferences": None}


def update_user_profile(site_id: str, address: str, payment_method: str) -> None:
    """Update user's address and payment method."""
    with get_db(site_id) as conn:
        row = conn.execute("SELECT id FROM user_profile LIMIT 1").fetchone()
        if row:
            conn.execute(
                "UPDATE user_profile SET address = %s, payment_method = %s",
                (address, payment_method),
            )
        else:
            conn.execute(
                "INSERT INTO user_profile (address, payment_method) VALUES (%s, %s)",
                (address, payment_method),
            )


def update_user_preferences(site_id: str, preferences: str) -> None:
    """Update user's inferred preferences (from chat)."""
    with get_db(site_id) as conn:
        row = conn.execute("SELECT id FROM user_profile LIMIT 1").fetchone()
        if row:
            conn.execute(
                "UPDATE user_profile SET preferences = %s",
                (preferences,),
            )
        else:
            conn.execute(
                "INSERT INTO user_profile (preferences) VALUES (%s)",
                (preferences,),
            )
