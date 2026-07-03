"""Check product columns + sample iPad row + variant data."""
import psycopg
from psycopg.rows import dict_row

DB = "postgresql://shopbot:shopbot_password@localhost:5434/shopping_db"
conn = psycopg.connect(DB, row_factory=dict_row)
conn.execute("SET search_path TO tenant_ai_kart, public")

# Product columns
cols = conn.execute(
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='products' AND table_schema='tenant_ai_kart' ORDER BY ordinal_position"
).fetchall()
print("=== PRODUCT COLUMNS ===")
for c in cols:
    print(f"  {c['column_name']}: {c['data_type']}")

# Sample iPad row (all fields except embedding)
row = conn.execute("SELECT * FROM products WHERE name ILIKE '%iPad%' LIMIT 1").fetchone()
print("\n=== SAMPLE IPAD ROW ===")
for k, v in dict(row).items():
    if k == 'embedding':
        print(f"  {k}: [vector]")
    else:
        print(f"  {k}: {str(v)[:300]}")

# Check variants for iPads
ipad_ids = conn.execute("SELECT id FROM products WHERE name ILIKE '%iPad%'").fetchall()
print(f"\n=== VARIANTS FOR {len(ipad_ids)} iPad PRODUCTS ===")
for ipad in ipad_ids:
    variants = conn.execute(
        "SELECT * FROM product_variants WHERE product_id = %s ORDER BY position",
        (ipad['id'],)
    ).fetchall()
    if variants:
        print(f"\n  Product ID {ipad['id']}: {len(variants)} variants")
        for v in variants:
            print(f"    {dict(v)}")
    else:
        print(f"  Product ID {ipad['id']}: no variants")

# Check knowledge_items for iPads
print("\n=== KNOWLEDGE ITEMS FOR iPads ===")
ki = conn.execute("SELECT * FROM knowledge_items WHERE title ILIKE '%iPad%' OR title ILIKE '%tablet%' LIMIT 5").fetchall()
for k in ki:
    d = dict(k)
    for key, val in d.items():
        if key == 'embedding':
            d[key] = '[vector]'
        elif isinstance(val, str) and len(val) > 200:
            d[key] = val[:200] + '...'
    print(f"  {d}")
if not ki:
    print("  (none)")

conn.close()
