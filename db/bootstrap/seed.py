"""
Seed the PostgreSQL database with products for Host Websites.
Run: python -m db.seed
"""

import json
import random
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_SEED_SITE_IDS = ("site_1", "site_2", "site_3", "site_4")

def format_category_name(slug: str) -> str:
    mapping = {
        "beauty": "Beauty",
        "fragrances": "Fragrances",
        "furniture": "Furniture",
        "groceries": "Groceries",
        "home-decoration": "Home Decor",
        "kitchen-accessories": "Kitchen Accessories",
        "laptops": "Laptops",
        "mens-shirts": "Men's Shirts",
        "mens-shoes": "Men's Shoes",
        "mens-watches": "Men's Watches",
        "mobile-accessories": "Mobile Accessories",
        "motorcycle": "Motorcycle Accessories",
        "skin-care": "Skin Care",
        "smartphones": "Smartphones",
        "sports-accessories": "Sports Accessories",
        "sunglasses": "Sunglasses",
        "tablets": "Tablets",
        "tops": "Women's Tops",
        "vehicle": "Automotive",
        "womens-bags": "Women's Bags",
        "womens-dresses": "Women's Dresses",
        "womens-jewellery": "Women's Jewellery",
        "womens-shoes": "Women's Shoes",
        "womens-watches": "Women's Watches",
    }
    return mapping.get(slug, slug.replace("-", " ").title())

def generate_synthetic_catalog(base_products, target_count):
    """Generate a larger catalog by slightly mutating base products."""
    adjectives = ["Premium", "Essential", "Classic", "Modern", "Luxury", "Standard", "Pro", "Ultra", "Max", "Lite", "Basic", "Advanced", "Signature", "Elite"]
    colors = ["Red", "Blue", "Black", "White", "Silver", "Gold", "Green", "Pink", "Purple", "Grey"]
    
    synthetic = []
    while len(synthetic) < target_count:
        base = random.choice(base_products)
        new_p = dict(base)
        adj = random.choice(adjectives)
        col = random.choice(colors)
        
        # Mutate
        new_p["title"] = f"{adj} {base['title']} - {col} Edition"
        new_p["price"] = round(base.get("price", 10.0) * random.uniform(0.7, 1.5), 2)
        new_p["rating"] = round(random.uniform(3.5, 5.0), 1)
        new_p["brand"] = f"{base.get('brand', 'BrandX')} {adj}"
        
        synthetic.append(new_p)
        
    return synthetic


def get_or_create_category_id(conn, category_id, name: str, slug: str) -> int:
    """Return a category ID, reusing existing rows when unique keys already exist."""
    existing = conn.execute(
        "SELECT id FROM categories WHERE name = %s OR slug = %s LIMIT 1",
        (name, slug),
    ).fetchone()
    if existing:
        return existing["id"]

    row = conn.execute(
        """
        INSERT INTO categories (id, name, slug)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name,
            slug = EXCLUDED.slug
        RETURNING id
        """,
        (category_id, name, slug),
    ).fetchone()
    return row["id"]

def seed(site_ids=None):
    """Read products.json and seed the PostgreSQL database for the configured sites."""
    from db.core.database import get_db, init_tenant_schema
    from agent.ingestion_helpers.ingestion_facade import _stable_id, _vectorize

    if site_ids is None:
        site_ids = list(DEFAULT_SEED_SITE_IDS)

    json_path = Path(__file__).resolve().parents[2] / "data" / "products.json"
    if not json_path.exists():
        print(f"Error: {json_path} does not exist.")
        sys.exit(1)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error reading JSON file: {exc}")
        sys.exit(1)

    all_products = data.get("products", [])
    if not all_products:
        print("No products found in the JSON file.")
        sys.exit(1)

    print(f"Retrieved {len(all_products)} base products.")

    all_categories = list(set(p["category"] for p in all_products))
    # Seed random state to have deterministic categories for tests
    random.seed(42)
    random.shuffle(all_categories)
    
    # Explicitly assign test categories to site_1 to pass RAG tests
    test_categories = ["groceries", "mens-shoes", "mobile-accessories", "laptops", "smartphones"]
    
    site_config = {}
    site_config["site_1"] = test_categories
    
    remaining_categories = [c for c in all_categories if c not in test_categories]
    for idx, site_id in enumerate(site_ids):
        if site_id == "site_1":
            continue
        start_cat = (idx * 5) % len(remaining_categories)
        end_cat = start_cat + 5
        site_config[site_id] = remaining_categories[start_cat:end_cat]

    for site_id, categories in site_config.items():
        print(f"--- Seeding PostgreSQL schema for {site_id} ---")
        try:
            init_tenant_schema(site_id)
        except Exception as exc:
            print(f"Error initializing schema for {site_id}: {exc}")
            continue

        with get_db(site_id) as conn:
            # Clean up tables
            conn.execute("DELETE FROM cart")
            conn.execute("DELETE FROM products")
            conn.execute("DELETE FROM categories")

            cat_id_map = {}
            for cat_slug in categories:
                cat_name = format_category_name(cat_slug)
                cat_id = _stable_id(site_id, cat_name, cat_slug)
                cat_id_map[cat_slug] = get_or_create_category_id(conn, cat_id, cat_name, cat_slug)

            # Get base products for this site's categories
            base_site_products = [p for p in all_products if p["category"] in categories]
            if not base_site_products:
                print(f"Warning: No base products found for {site_id} categories.")
                continue
                
            target_count = 50
            synthetic_products = generate_synthetic_catalog(base_site_products, target_count)
            print(f"Generated {len(synthetic_products)} products for {site_id}.")

            seen_ids = set()
            for p in synthetic_products:
                cat_id = cat_id_map[p["category"]]
                img_list = p.get("images", [])
                img_url = img_list[0] if img_list else ""
                
                item_tags = p.get("tags", [])
                if p["category"] not in item_tags:
                    item_tags.append(p["category"])
                tags_str = json.dumps(item_tags)

                usd_price = p.get("price", 0.0)
                inr_price = round(usd_price * 80, 2)
                original_price = round(inr_price * random.uniform(1.1, 1.5), 2)
                rating = p.get("rating", 4.0)
                review_count = random.randint(5, 500)
                stock = random.randint(10, 500)
                brand = p.get("brand", "Generic")
                
                product_id = _stable_id(site_id, p["title"], p["description"])
                if product_id in seen_ids:
                    salt = 1
                    while product_id in seen_ids:
                        product_id = _stable_id(site_id, p["title"], p["description"] + f"_{salt}")
                        salt += 1
                seen_ids.add(product_id)

                conn.execute(
                    """
                    INSERT INTO products
                      (id, name, brand, category_id, description, price, original_price,
                       color, size_options, tags, rating, review_count, stock, image_url, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """,
                    (
                        product_id,
                        p["title"],
                        brand,
                        cat_id,
                        p["description"],
                        inr_price,
                        original_price,
                        "",
                        "[]",
                        tags_str,
                        rating,
                        review_count,
                        stock,
                        img_url,
                    ),
                )

        # Vectorize using pgvector helper
        try:
            v_count = _vectorize(site_id)
            print(f"Vectorized {v_count} products for {site_id}.")
        except Exception as exc:
            print(f"Failed to vectorize schema for {site_id}: {exc}")

    print("\n[+] Successfully seeded PostgreSQL database.")

if __name__ == "__main__":
    seed()
