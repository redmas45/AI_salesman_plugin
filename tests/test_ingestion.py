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


def test_catalog_endpoints_include_common_platform_routes():
    endpoints = ingestion._catalog_endpoints_for("https://shop.example.test/start")

    assert "https://shop.example.test/api/products.json" in endpoints
    assert "https://shop.example.test/products.json" in endpoints
    assert "https://shop.example.test/collections/all/products.json" in endpoints
    assert "https://shop.example.test/wp-json/wc/store/products?per_page=100" in endpoints
    assert len(endpoints) == len(set(endpoints))


def test_shopify_products_json_normalization():
    products = ingestion._normalize_catalog_payload(
        {
            "products": [
                {
                    "id": 101,
                    "title": "NOVA Cap",
                    "body_html": "<p>Peach washed cotton cap.</p>",
                    "vendor": "NOVA",
                    "product_type": "Headwear",
                    "handle": "nova-cap",
                    "tags": "cap, black",
                    "variants": [
                        {
                            "id": 201,
                            "price": "20.00",
                            "compare_at_price": "25.00",
                            "inventory_quantity": 7,
                            "available": True,
                        }
                    ],
                    "images": [{"src": "https://cdn.example.test/nova-cap.png"}],
                }
            ]
        },
        "https://shop.example.test/products.json",
    )

    assert len(products) == 1
    product = products[0]
    assert product["id"] == 101
    assert product["variant_id"] == 201
    assert product["name"] == "NOVA Cap"
    assert product["brand"] == "NOVA"
    assert product["category"] == "Headwear"
    assert product["price"] == 20.0
    assert product["stock"] == 7
    assert product["image_url"] == "https://cdn.example.test/nova-cap.png"


def test_woocommerce_store_api_normalization():
    products = ingestion._normalize_catalog_payload(
        [
            {
                "id": 501,
                "name": "NOVA Mug",
                "description": "<p>Ceramic mug.</p>",
                "categories": [{"name": "Drinkware"}],
                "tags": [{"name": "coffee"}],
                "prices": {
                    "price": "2500",
                    "regular_price": "3000",
                    "currency_minor_unit": 2,
                },
                "images": [{"src": "https://cdn.example.test/nova-mug.png"}],
                "is_in_stock": True,
                "stock_quantity": 12,
                "average_rating": "4.8",
                "review_count": 9,
            }
        ],
        "https://shop.example.test/wp-json/wc/store/products?per_page=100",
    )

    assert len(products) == 1
    product = products[0]
    assert product["id"] == 501
    assert product["name"] == "NOVA Mug"
    assert product["category"] == "Drinkware"
    assert product["price"] == 25.0
    assert product["original_price"] == 30.0
    assert product["stock"] == 12
    assert product["rating"] == 4.8


def test_embedded_json_products_are_extracted_from_app_state():
    html = """
    <html><body>
      <script>
        window.__APP_STATE__ = {
          "catalog": {
            "items": [
              {
                "product_id": "nova-bag",
                "name": "NOVA Bag",
                "description": "Canvas tote",
                "category": "Bags",
                "price": "18.50",
                "image_url": "https://cdn.example.test/bag.png",
                "url": "/products/nova-bag"
              }
            ]
          }
        };
      </script>
    </body></html>
    """

    products = ingestion._extract_embedded_json_products(html, "https://shop.example.test/")

    assert len(products) == 1
    assert products[0]["name"] == "NOVA Bag"
    assert products[0]["category"] == "Bags"
    assert products[0]["price"] == 18.5


def test_nested_catalog_payload_falls_back_to_json_tree_extraction():
    products = ingestion._normalize_catalog_payload(
        {
            "data": {
                "catalog": {
                    "items": [
                        {
                            "sku": "nova-wallet",
                            "title": "NOVA Wallet",
                            "description": "Slim leather wallet",
                            "category": "Accessories",
                            "price": "32",
                            "image": "https://cdn.example.test/wallet.png",
                            "url": "/products/nova-wallet",
                        }
                    ]
                }
            }
        },
        "https://shop.example.test/catalog.json",
    )

    assert len(products) == 1
    assert products[0]["name"] == "NOVA Wallet"
    assert products[0]["category"] == "Accessories"


def test_sitemap_locations_are_ranked_toward_product_pages():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://shop.example.test/about</loc></url>
      <url><loc>https://shop.example.test/products/nova-cap</loc></url>
      <url><loc>https://shop.example.test/store</loc></url>
    </urlset>
    """

    ranked = ingestion._ranked_unique_urls(ingestion._extract_sitemap_locations(xml))

    assert ranked[0] == "https://shop.example.test/products/nova-cap"
    assert ranked[-1] == "https://shop.example.test/about"


def test_crawl_url_filter_skips_cart_without_blocking_cartoon_products():
    assert not ingestion._is_allowed_crawl_url("https://shop.example.test/cart", "shop.example.test")
    assert ingestion._is_allowed_crawl_url("https://shop.example.test/cartoon-products", "shop.example.test")
