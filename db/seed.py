"""
Seed the SQLite databases with products for the 4 Host Websites.
Run: python -m db.seed
"""

import json
import random
import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

def seed():
    """Read products.json and seed the SQLite database for 4 sites."""
    json_path = Path(__file__).parent.parent / "data" / "products.json"
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
    random.shuffle(all_categories)
    
    site_config = {
        "Site_1": all_categories[0:5],
        "Site_2": all_categories[5:10],
        "Site_3": all_categories[10:15],
        "Site_4": all_categories[15:20],
    }

    base_dir = Path(__file__).parent.parent / "websites"

    for site_id, categories in site_config.items():
        print(f"--- Seeding {site_id} ---")
        
        db_path = base_dir / site_id / "shop.db"
        
        # Delete existing DB
        if db_path.exists():
            db_path.unlink()
            
        conn = sqlite3.connect(db_path)
        
        # Init schema
        schema_path = base_dir / site_id / "db" / "schema.sql"
        if schema_path.exists():
            conn.executescript(schema_path.read_text(encoding="utf-8"))
        else:
            print(f"Schema not found for {site_id}")
            continue

        cat_id_map = {}
        for cat_slug in categories:
            cat_name = format_category_name(cat_slug)
            conn.execute(
                "INSERT OR IGNORE INTO categories (name, slug) VALUES (?, ?)",
                (cat_name, cat_slug),
            )
            row = conn.execute(
                "SELECT id FROM categories WHERE name = ?", (cat_name,)
            ).fetchone()
            cat_id_map[cat_slug] = row[0]

        # Get base products for this site's categories
        base_site_products = [p for p in all_products if p["category"] in categories]
        if not base_site_products:
            print(f"Warning: No base products found for {site_id} categories.")
            continue
            
        target_count = 200
        synthetic_products = generate_synthetic_catalog(base_site_products, target_count)
        print(f"Generated {len(synthetic_products)} products for {site_id}.")

        for p in synthetic_products:
            cat_id = cat_id_map[p["category"]]
            img_list = p.get("images", [])
            img_url = json.dumps(img_list) if img_list else ""
            
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

            conn.execute(
                """
                INSERT INTO products
                  (name, brand, category_id, description, price, original_price,
                   color, size_options, tags, rating, review_count, stock, image_url, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
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

        conn.commit()
        conn.close()

    print("\n[+] Successfully seeded SQLite databases for 4 sites.")

if __name__ == "__main__":
    seed()
