"""Cheap, TTL-cached tenant vocabulary for constraint resolution.

Resolving a turn needs to know which words in it are real brands for THIS tenant.
Loading the catalog on every turn would be wasteful, so this module keeps a small
per-tenant brand list behind a short TTL. Only distinct brand strings are read --
never product rows -- so the query stays small and independent of catalog size.

Failures are non-fatal: an empty vocabulary simply means brand words are not
recognised on this turn, which degrades to the previous behaviour.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

BRAND_CACHE_TTL_SECONDS = 300
MAX_CATALOG_BRANDS = 400
MIN_BRAND_LENGTH = 2

_BRAND_CACHE: dict[str, tuple[float, tuple[str, ...]]] = {}


def catalog_brand_vocabulary(site_id: str) -> tuple[str, ...]:
    """Return the tenant's distinct lower-cased brand names (TTL-cached)."""
    key = str(site_id or "").strip()
    if not key:
        return ()

    now = time.monotonic()
    cached = _BRAND_CACHE.get(key)
    if cached and (now - cached[0]) < BRAND_CACHE_TTL_SECONDS:
        return cached[1]

    try:
        from db.core.database import get_db

        with get_db(key) as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT brand
                FROM products
                WHERE is_active = 1 AND brand IS NOT NULL AND brand <> ''
                LIMIT %s
                """,
                (MAX_CATALOG_BRANDS,),
            ).fetchall()
        brands = tuple(
            sorted(
                {
                    str(row["brand"]).strip().lower()
                    for row in rows
                    if str(row["brand"] or "").strip() and len(str(row["brand"]).strip()) >= MIN_BRAND_LENGTH
                }
            )
        )
    except Exception as exc:
        # Never fail a customer turn because the vocabulary could not be read.
        logger.warning("Brand vocabulary lookup failed for %s: %s", key, exc)
        brands = cached[1] if cached else ()

    _BRAND_CACHE[key] = (now, brands)
    return brands


def reset_brand_vocabulary_cache() -> None:
    """Clear the cache (used by tests and after a catalog re-ingest)."""
    _BRAND_CACHE.clear()
