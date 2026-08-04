"""Deterministic catalog record queries for aggregate and count operations.

``get_all_products`` deliberately samples: it partitions by category and orders
by ``RANDOM()`` so the assistant sees a varied slice of a large catalog. That is
right for "show me something", and wrong for every question whose answer is a
fact about the whole catalog - the cheapest item, the best rated item, or how
many records match.

These queries are the counterpart: the same tenant scoping and the same hard
filters, but ordered by primary key so repeated calls return the same rows in the
same order, and with a companion ``COUNT``/``SUM`` that measures the entire
matching set rather than a window over it.
"""

from __future__ import annotations

import logging
from typing import Any

from db.core.database import get_db

logger = logging.getLogger(__name__)

# One turn never scans more than this. The caller asks for one row beyond the cap
# so it can tell "exactly N" from "at least N".
CATALOG_SCAN_CAP = 5000

_RECORD_COLUMNS = "p.*, c.name AS category_name, c.slug AS category_slug"
_BASE_FROM = "FROM products p JOIN categories c ON p.category_id = c.id"


def _hard_filter_sql(
    *,
    min_price: float | None,
    max_price: float | None,
    brands: tuple[str, ...],
    category_names: tuple[str, ...],
    in_stock_only: bool,
) -> tuple[str, list[Any]]:
    """Conjunctive WHERE fragment. Every supplied facet must hold."""
    conditions = ["p.is_active = 1"]
    params: list[Any] = []
    if in_stock_only:
        conditions.append("p.stock > 0")
    if max_price is not None:
        conditions.append("p.price <= %s")
        params.append(max_price)
    if min_price is not None:
        conditions.append("p.price >= %s")
        params.append(min_price)
    if brands:
        conditions.append("lower(p.brand) = ANY(%s)")
        params.append([str(brand).strip().lower() for brand in brands])
    if category_names:
        conditions.append("lower(c.name) = ANY(%s)")
        params.append([str(name).strip().lower() for name in category_names])
    return " WHERE " + " AND ".join(conditions), params


def get_catalog_records(
    site_id: str,
    *,
    min_price: float | None = None,
    max_price: float | None = None,
    brands: tuple[str, ...] = (),
    category_names: tuple[str, ...] = (),
    in_stock_only: bool = True,
    limit: int = CATALOG_SCAN_CAP + 1,
) -> list[dict]:
    """Return matching records in a stable primary-key order.

    One row beyond the caller's cap is intentionally returned so a truncated scan
    is detectable and never reported as an exact catalog total.
    """
    where_sql, params = _hard_filter_sql(
        min_price=min_price,
        max_price=max_price,
        brands=tuple(brands),
        category_names=tuple(category_names),
        in_stock_only=in_stock_only,
    )
    query = f"SELECT {_RECORD_COLUMNS} {_BASE_FROM}{where_sql} ORDER BY p.id LIMIT %s"
    with get_db(site_id) as conn:
        return conn.execute(query, (*params, max(1, int(limit)))).fetchall()


def count_catalog_records(
    site_id: str,
    *,
    min_price: float | None = None,
    max_price: float | None = None,
    brands: tuple[str, ...] = (),
    category_names: tuple[str, ...] = (),
    in_stock_only: bool = True,
) -> dict[str, int]:
    """Exact counts over the whole matching set, not over a retrieval window.

    Records, purchasable variants, and stock units are three different numbers
    and are reported separately so a response never confuses them.
    """
    where_sql, params = _hard_filter_sql(
        min_price=min_price,
        max_price=max_price,
        brands=tuple(brands),
        category_names=tuple(category_names),
        in_stock_only=in_stock_only,
    )
    query = (
        "SELECT COUNT(*) AS matching_records, "
        "COUNT(DISTINCT p.variant_id) AS variant_count, "
        "COALESCE(SUM(p.stock), 0) AS stock_units "
        f"{_BASE_FROM}{where_sql}"
    )
    with get_db(site_id) as conn:
        row = conn.execute(query, params).fetchone() or {}
    return {
        "matching_records": int(row.get("matching_records") or 0),
        "variant_count": int(row.get("variant_count") or 0),
        "stock_units": int(row.get("stock_units") or 0),
    }
