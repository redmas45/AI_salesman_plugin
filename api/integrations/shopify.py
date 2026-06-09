import httpx
import re
import hashlib
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    cleaner = re.compile('<.*?>')
    return re.sub(cleaner, '', raw_html)

def hash_category(name: str) -> int:
    """Generate a consistent BIGINT from a string name."""
    if not name:
        name = "Uncategorized"
    h = hashlib.sha256(name.lower().encode('utf-8')).hexdigest()
    # Convert to big int, keep it within Postgres BIGINT bounds (64-bit signed)
    return int(h[:15], 16) % (2**63 - 1)

import asyncio

async def fetch_shopify_catalog(store_domain: str, access_token: str) -> Dict[str, Any]:
    """
    Fetch all products from a Shopify store using the Admin API with pagination.
    Returns a normalized dictionary containing {"categories": [...], "products": [...]}.
    """
    if not store_domain.startswith("http"):
        store_domain = f"https://{store_domain}"
        
    url = f"{store_domain}/admin/api/2024-01/products.json?limit=250"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    products_data = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while url:
            for attempt in range(5):
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        print(f"Rate limited (429)! Sleeping for {2 ** attempt}s...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise
                except httpx.ReadTimeout:
                    if attempt == 4:
                        raise
                    print(f"ReadTimeout fetching {url}. Retrying ({attempt+1}/5)...")
                    await asyncio.sleep(2)
            
            data = response.json()
            products_data.extend(data.get("products", []))
            print(f"Fetched {len(products_data)} products so far...")
            
            # Respect Shopify's REST API rate limit (2 requests per second)
            await asyncio.sleep(0.6)
            
            # Check for next page in Link header
            link_header = response.headers.get("Link")
            url = None
            if link_header:
                links = link_header.split(",")
                for link in links:
                    if 'rel="next"' in link:
                        url = link[link.find("<")+1:link.find(">")]
                        break

    categories_map = {}
    normalized_products = []

    for item in products_data:
        # Resolve category (product_type)
        cat_name = item.get("product_type") or "Uncategorized"
        cat_id = hash_category(cat_name)
        
        if cat_id not in categories_map:
            categories_map[cat_id] = {
                "id": cat_id,
                "name": cat_name,
                "slug": cat_name.lower().replace(" ", "-")
            }

        # Resolve price/stock from first variant
        variants = item.get("variants", [])
        price = 0.0
        original_price = None
        stock = 100
        variant_id = None
        
        if variants:
            v = variants[0]
            variant_id = v.get("id")
            price = float(v.get("price") or 0.0)
            orig = v.get("compare_at_price")
            original_price = float(orig) if orig else None
            stock = v.get("inventory_quantity", 100)
            
        # Resolve Image
        image_url = None
        if item.get("image"):
            image_url = item["image"].get("src")

        is_active = 1 if item.get("status") == "active" else 0

        p = {
            "id": item["id"],
            "variant_id": variant_id,
            "name": item["title"],
            "brand": item.get("vendor", "Unknown Brand"),
            "category_id": cat_id,
            "description": clean_html(item.get("body_html", "")),
            "price": price,
            "original_price": original_price,
            "color": None,
            "size_options": "[]",
            "tags": str(item.get("tags", "")).split(", "),
            "rating": 5.0,
            "review_count": 0,
            "stock": stock,
            "image_url": image_url,
            "is_active": is_active
        }
        normalized_products.append(p)

    return {
        "categories": list(categories_map.values()),
        "products": normalized_products
    }
