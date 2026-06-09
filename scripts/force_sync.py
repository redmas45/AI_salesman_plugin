import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from db.database import get_global_db, init_tenant_schema, get_db
from api.integrations.shopify import fetch_shopify_catalog
import json

async def force_sync(shop_domain: str):
    site_id = shop_domain.replace("https://", "").replace("http://", "").replace(".", "_").replace("-", "_")
    
    # 1. Retrieve the access token from the database
    access_token = None
    with get_global_db() as conn:
        result = conn.execute(
            "SELECT access_token FROM shopify_installations WHERE shop_domain = %s",
            (shop_domain,)
        ).fetchone()
        if result:
            access_token = result["access_token"]
            
    if not access_token:
        print(f"❌ Error: No access token found for store '{shop_domain}'. Is the app installed?")
        sys.exit(1)

    print(f"Fetching catalog for {shop_domain}... This may take a moment for 5,000 products!")
    catalog = await fetch_shopify_catalog(shop_domain, access_token)
    
    print(f"Fetched {len(catalog['products'])} products and {len(catalog['categories'])} categories from Shopify!")
    
    with get_db(site_id) as conn:
        conn.execute("DROP TABLE IF EXISTS products CASCADE")
        conn.commit()

    init_tenant_schema(site_id)
    
    print("Inserting into PostgreSQL database...")
    with get_db(site_id) as conn:
        conn.execute("TRUNCATE categories CASCADE")
        
        for c in catalog['categories']:
            conn.execute("INSERT INTO categories (id, name, slug) VALUES (%s, %s, %s)", (c['id'], c['name'], c['slug']))
            
        for p in catalog['products']:
            conn.execute(
                "INSERT INTO products (id, variant_id, name, brand, category_id, description, price, original_price, color, size_options, tags, rating, review_count, stock, image_url, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (p['id'], p['variant_id'], p['name'], p['brand'], p['category_id'], p['description'], p['price'], p['original_price'], p['color'], p['size_options'], json.dumps(p['tags']), p['rating'], p['review_count'], p['stock'], p['image_url'], p['is_active'])
            )
            
    print("Insertion complete! Now starting background vectorization...")
    # Trigger vectorization synchronously for the test
    from api.main import vectorize_site_catalog
    vectorize_site_catalog(site_id)
    print("✅ Full sync and vectorization complete!")

if __name__ == "__main__":
    asyncio.run(force_sync("pisszq-ay.myshopify.com"))
