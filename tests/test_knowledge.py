import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import get_db, init_tenant_schema
from db.knowledge import knowledge_preview, knowledge_stats, sync_products_to_knowledge


def test_products_sync_into_knowledge_items():
    site_id = "knowledge_test"
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        conn.execute("DELETE FROM knowledge_items WHERE id = %s", ("product:441002",))
        conn.execute(
            """
            INSERT INTO categories (id, name, slug)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, slug = EXCLUDED.slug
            """,
            (441001, "Insurance Plans", "insurance-plans"),
        )
        conn.execute(
            """
            INSERT INTO products
                (id, name, brand, category_id, description, price, stock, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                brand = EXCLUDED.brand,
                category_id = EXCLUDED.category_id,
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                stock = EXCLUDED.stock,
                is_active = EXCLUDED.is_active
            """,
            (441002, "Term Life Protect", "DemoInsure", 441001, "Term insurance plan.", 499.0, 8, 1),
        )

    changed = sync_products_to_knowledge(site_id, "unit_test_catalog")
    stats = knowledge_stats(site_id)
    preview = knowledge_preview(site_id, limit=10)

    assert changed >= 1
    assert stats["active_items"] >= 1
    assert any(item["id"] == "product:441002" for item in preview)
