import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import ingestion
from agent.verticals.registry import DEFAULT_VERTICAL_KEY


class _CatalogResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _CatalogClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.urls = []

    async def get(self, url, headers=None):
        self.urls.append(url)
        if not self.payloads:
            return _CatalogResponse({"data": [], "meta": {"page": len(self.urls), "total_pages": len(self.urls)}})
        return _CatalogResponse(self.payloads.pop(0))


class _Cp1252Stdout:
    encoding = "cp1252"

    def __init__(self):
        self.output = []

    def write(self, value):
        value.encode(self.encoding)
        self.output.append(value)

    def flush(self):
        return None


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


def test_aikart_fastapi_products_payload_normalization():
    products = ingestion._normalize_catalog_payload(
        {
            "data": [
                {
                    "id": "acme-dog-sweater",
                    "handle": "acme-dog-sweater",
                    "title": "NOVA Dog Sweater",
                    "name": "NOVA Dog Sweater",
                    "description": "Warm fleece dog sweater",
                    "category": "pets",
                    "categories": ["pets"],
                    "brand": "NOVA",
                    "vendor": "NOVA",
                    "price": 20.0,
                    "currency": "USD",
                    "stock": None,
                    "in_stock": True,
                    "image_url": "https://cdn.example.test/dog-sweater.png",
                    "url": "/product/acme-dog-sweater/",
                }
            ]
        },
        "https://shop.example.test/api/products",
    )

    assert len(products) == 1
    product = products[0]
    assert product["name"] == "NOVA Dog Sweater"
    assert product["category"] == "pets"
    assert product["price"] == 20.0
    assert product["stock"] == 100


def test_sitemap_locations_are_ranked_toward_product_pages():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://shop.example.test/about</loc></url>
      <url><loc>https://shop.example.test/products/nova-cap</loc></url>
      <url><loc>https://shop.example.test/store</loc></url>
    </urlset>
    """

    ranked = ingestion._ranked_unique_urls(ingestion._extract_sitemap_locations(xml), vertical_key="ecommerce")

    assert ranked[0] == "https://shop.example.test/products/nova-cap"
    assert ranked[-1] == "https://shop.example.test/about"


def test_crawler_vertical_fallback_is_generic(monkeypatch):
    def fail_lookup(site_id: str) -> str:
        raise RuntimeError("db unavailable")

    monkeypatch.setattr("db.clients.get_client_vertical_key", fail_lookup)

    assert ingestion._crawl_vertical_key("unknown_site") == DEFAULT_VERTICAL_KEY


def test_default_html_candidate_extraction_is_not_ecommerce_biased():
    html = """
    <html><body>
      <p>
        Roofing consultation, construction site visit, project estimate,
        renovation planning, contractor support, and concrete repair services.
      </p>
    </body></html>
    """

    rows = ingestion._build_candidates_from_html("https://builder.example.test/services", html)

    assert rows
    assert rows[0]["category"] != "Products"


def test_crawl_url_filter_skips_cart_without_blocking_cartoon_products():
    assert not ingestion._is_allowed_crawl_url("https://shop.example.test/cart", "shop.example.test")
    assert ingestion._is_allowed_crawl_url("https://shop.example.test/cartoon-products", "shop.example.test")

