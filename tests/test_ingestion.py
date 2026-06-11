import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import ingestion


def test_sanitize_site_id_normalizes_urlish_input():
    assert ingestion.sanitize_site_id("ai_kart_main") == "ai_kart_main"
    assert ingestion.sanitize_site_id("https://vercelclonedwebsite.vercel.app/") == "https_vercelclonedwebsite_vercel_app"


def test_sync_web_crawl_rejects_missing_host():
    with pytest.raises(ValueError, match="must include a host"):
        ingestion.sync_web_crawl("/relative/path")


def test_api_catalog_product_id_stays_stable_when_name_changes():
    first = ingestion._normalize_api_catalog_product(
        {
            "id": "nova-mug",
            "name": "NOVA Mug",
            "description": "Ceramic mug",
            "category": "drinkware",
            "brand": "NOVA",
            "price": 15,
            "in_stock": True,
        },
        "https://example.test/api/products.json",
    )
    renamed = ingestion._normalize_api_catalog_product(
        {
            "id": "nova-mug",
            "name": "NOVA Premium Mug",
            "description": "Ceramic mug",
            "category": "drinkware",
            "brand": "NOVA",
            "price": 15,
            "in_stock": True,
        },
        "https://example.test/api/products.json",
    )

    assert first["id"] == renamed["id"]
    assert first["name"] == "NOVA Mug"
    assert renamed["name"] == "NOVA Premium Mug"
