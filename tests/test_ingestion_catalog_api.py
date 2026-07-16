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


def test_safe_console_print_replaces_unencodable_crawler_text(monkeypatch):
    fake_stdout = _Cp1252Stdout()
    monkeypatch.setattr(ingestion.sys, "stdout", fake_stdout)

    ingestion._safe_console_print("Health plan \U0001F3E5")

    assert "Health plan ?" in "".join(fake_stdout.output)


def test_sanitize_site_id_normalizes_urlish_input():
    assert ingestion.sanitize_site_id("ai_kart") == "ai_kart"
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


def test_generic_api_product_preserves_reviews_specs_and_buying_options():
    product = ingestion._normalize_api_catalog_product(
        {
            "id": "phone-1",
            "name": "Example Phone",
            "description": "A practical everyday phone.",
            "category": "electronics",
            "subcategory": "Electronics > Mobiles",
            "brand": "Example",
            "price": 49999,
            "stock": 8,
            "rating": 4.7,
            "review_count": 321,
            "tags": ["phone", "5g"],
            "specs": {
                "chipset": "Example X1",
                "battery": "5000 mAh",
                "sizes_available": ["128 GB", "256 GB"],
            },
            "variants": [
                {"type": "size", "name": "128 GB", "in_stock": True},
                {"type": "color", "name": "Midnight", "in_stock": True},
            ],
            "highlights": ["Two-year warranty"],
            "url": "/product/phone-1/",
        },
        "https://shop.example.test/api/products",
    )

    assert product["rating"] == 4.7
    assert product["review_count"] == 321
    assert "chipset: Example X1" in product["description"]
    assert "battery: 5000 mAh" in product["description"]
    assert "Highlights: Two-year warranty" in product["description"]
    assert product["size_options"] == '["128 GB", "256 GB"]'
    assert product["color"] == "Midnight"
    assert product["specs"]["chipset"] == "Example X1"
    assert product["url"] == "/product/phone-1/"


def test_generic_api_variants_do_not_trigger_shopify_normalization():
    raw = {
        "id": "phone-2",
        "handle": "phone-2",
        "name": "Generic API Phone",
        "vendor": "Example",
        "price": 30000,
        "rating": 4.6,
        "review_count": 90,
        "variants": [{"type": "color", "name": "Blue", "in_stock": True}],
    }

    assert not ingestion._looks_like_shopify_product(raw)
    assert ingestion._normalize_api_catalog_product(raw, "https://example.test/api/products")["rating"] == 4.6


def test_catalog_endpoints_include_common_platform_routes():
    endpoints = ingestion._catalog_endpoints_for("https://shop.example.test/start")

    assert "https://shop.example.test/api/products" in endpoints
    assert "https://shop.example.test/api/policies" in endpoints
    assert "https://shop.example.test/api/products.json" in endpoints
    assert "https://shop.example.test/products.json" in endpoints
    assert "https://shop.example.test/collections/all/products.json" in endpoints
    assert "https://shop.example.test/wp-json/wc/store/products?per_page=100" in endpoints
    assert len(endpoints) == len(set(endpoints))


def test_catalog_seed_candidates_include_docker_host_alias_for_localhost():
    candidates = ingestion._catalog_seed_candidates("http://127.0.0.1:5183/insurance/health")

    assert candidates == [
        "http://127.0.0.1:5183/insurance/health",
        "http://host.docker.internal:5183/insurance/health",
    ]


def test_policy_api_catalog_normalization_preserves_plan_details():
    product = ingestion._normalize_api_catalog_product(
        {
            "id": "H001",
            "category_id": "health",
            "name": "IndividualCare Plan",
            "insurer": "InsureMax Health",
            "type": "Individual",
            "premium_monthly": 899,
            "premium_annual": 9999,
            "sum_insured": 500000,
            "features": ["5 Lakh cover", "Cashless at 6000+ hospitals"],
            "rating": 4.5,
            "review_count": 2341,
            "claim_process": "Cashless / Reimbursement",
            "waiting_period": "30 days general, 2 years pre-existing",
            "renewability": "Lifelong",
            "tax_benefit": "Section 80D",
            "age_min": 18,
            "age_max": 65,
        },
        "https://policy.example.test/api/policies",
    )

    assert product["name"] == "IndividualCare Plan"
    assert product["brand"] == "InsureMax Health"
    assert product["category"] == "Health Insurance"
    assert product["price"] == 899
    assert product["original_price"] == 9999
    assert product["rating"] == 4.5
    assert product["review_count"] == 2341
    assert "Cashless at 6000+ hospitals" in product["description"]
    assert "age 18 to 65" in product["description"]
    assert "Health Insurance" in product["tags"]
    assert product["policy_json"]["age_min"] == 18
    assert product["policy_json"]["age_max"] == 65
    assert product["policy_json"]["sum_insured"] == 500000
    assert product["pricing_json"]["premium_monthly"] == 899
    assert "regulated_insurance" in product["risk_tags"]
    assert "health_cover" in product["risk_tags"]


@pytest.mark.asyncio
async def test_fetch_policy_api_catalog_endpoint_reads_wrapped_policy_rows():
    client = _CatalogClient(
        [
            {
                "data": [
                    {
                        "id": "H001",
                        "category_id": "health",
                        "name": "IndividualCare Plan",
                        "insurer": "InsureMax Health",
                        "type": "Individual",
                        "premium_monthly": 899,
                        "premium_annual": 9999,
                        "sum_insured": 500000,
                        "features": ["Cashless hospitalization", "Claim support"],
                        "claim_process": "Cashless / Reimbursement",
                        "waiting_period": "30 days general",
                    }
                ]
            }
        ]
    )

    products = await ingestion._fetch_catalog_endpoint_pages(
        client,
        "https://policy.example.test/api/policies",
    )

    assert client.urls == ["https://policy.example.test/api/policies"]
    assert [product["name"] for product in products] == ["IndividualCare Plan"]
    assert products[0]["category"] == "Health Insurance"
    assert products[0]["policy_json"]["claim_process"] == "Cashless / Reimbursement"


def test_generic_api_products_endpoint_uses_aikart_pagination_params():
    urls = ingestion._catalog_page_urls("https://shop.example.test/api/products")

    assert urls[0] == "https://shop.example.test/api/products?page=1&per_page=96"
    assert urls[1] == "https://shop.example.test/api/products?page=2&per_page=96"
    assert len(urls) == ingestion.GENERIC_API_CATALOG_MAX_PAGES


@pytest.mark.asyncio
async def test_fetch_catalog_endpoint_pages_follows_fastapi_meta_total_pages():
    client = _CatalogClient(
        [
            {
                "data": [
                    {
                        "id": "p1",
                        "name": "Product One",
                        "description": "One",
                        "category": "Products",
                        "price": 10,
                        "in_stock": True,
                    }
                ],
                "meta": {"page": 1, "per_page": 96, "total": 2, "total_pages": 2},
            },
            {
                "data": [
                    {
                        "id": "p2",
                        "name": "Product Two",
                        "description": "Two",
                        "category": "Products",
                        "price": 20,
                        "in_stock": True,
                    }
                ],
                "meta": {"page": 2, "per_page": 96, "total": 2, "total_pages": 2},
            },
            {
                "data": [
                    {
                        "id": "p3",
                        "name": "Product Three",
                        "description": "Three",
                        "category": "Products",
                        "price": 30,
                        "in_stock": True,
                    }
                ],
                "meta": {"page": 3, "per_page": 96, "total": 3, "total_pages": 3},
            },
        ]
    )

    products = await ingestion._fetch_catalog_endpoint_pages(
        client,
        "https://shop.example.test/api/products",
    )

    assert [product["name"] for product in products] == ["Product One", "Product Two"]
    assert len(client.urls) == 2


@pytest.mark.asyncio
async def test_fetch_catalog_endpoint_pages_stops_when_generic_api_repeats_first_page():
    repeated = {
        "data": [
            {
                "id": "p1",
                "name": "Product One",
                "description": "One",
                "category": "Products",
                "price": 10,
                "in_stock": True,
            }
        ]
    }
    client = _CatalogClient([repeated, repeated, repeated])

    products = await ingestion._fetch_catalog_endpoint_pages(
        client,
        "https://shop.example.test/api/products",
    )

    assert [product["name"] for product in products] == ["Product One"]
    assert len(client.urls) == 2


@pytest.mark.asyncio
async def test_fetch_catalog_endpoint_pages_keeps_distinct_generic_products_with_same_name():
    client = _CatalogClient(
        [
            {
                "data": [
                    {
                        "id": "p1",
                        "name": "NOVA Plain T-Shirt",
                        "description": "First color",
                        "category": "shirts",
                        "brand": "NOVA",
                        "price": 20,
                        "in_stock": True,
                    }
                ],
                "meta": {"page": 1, "per_page": 96, "total": 2, "total_pages": 2},
            },
            {
                "data": [
                    {
                        "id": "p2",
                        "name": "NOVA Plain T-Shirt",
                        "description": "Second color",
                        "category": "shirts",
                        "brand": "NOVA",
                        "price": 20,
                        "in_stock": True,
                    }
                ],
                "meta": {"page": 2, "per_page": 96, "total": 2, "total_pages": 2},
            },
        ]
    )

    products = await ingestion._fetch_catalog_endpoint_pages(
        client,
        "https://shop.example.test/api/products",
    )

    assert len(products) == 2
