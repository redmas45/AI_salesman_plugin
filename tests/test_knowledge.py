import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import get_db, init_tenant_schema
from db.knowledge import knowledge_preview, knowledge_stats, sync_products_to_knowledge
from agent.retrieval.generic_rag import _knowledge_item_to_text, _rank_lexical_items, vectorize_missing_knowledge


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


def test_policy_source_payload_syncs_structured_knowledge_fields():
    site_id = "knowledge_policy_payload_test"
    source_name = "policy_api"
    product_id = 441003
    init_tenant_schema(site_id)
    raw_product = {
        "policy_json": {
            "category": "Health Insurance",
            "category_id": "health",
            "policy_type": "Individual",
            "sum_insured": 500000,
            "age_min": 18,
            "age_max": 65,
            "claim_process": "Cashless / Reimbursement",
        },
        "pricing_json": {
            "premium_monthly": 899,
            "premium_annual": 9999,
            "currency": "INR",
        },
        "risk_tags": ["regulated_insurance", "health_cover"],
    }
    with get_db(site_id) as conn:
        conn.execute("DELETE FROM knowledge_items WHERE id = %s", (f"product:{product_id}",))
        conn.execute(
            """
            INSERT INTO categories (id, name, slug)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, slug = EXCLUDED.slug
            """,
            (441004, "Health Insurance", "health-insurance"),
        )
        conn.execute(
            """
            INSERT INTO products
                (id, name, brand, category_id, description, price, original_price, stock, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                brand = EXCLUDED.brand,
                category_id = EXCLUDED.category_id,
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                original_price = EXCLUDED.original_price,
                stock = EXCLUDED.stock,
                is_active = EXCLUDED.is_active
            """,
            (
                product_id,
                "IndividualCare Plan",
                "InsureMax Health",
                441004,
                "Health insurance plan with cashless hospitalization.",
                899.0,
                9999.0,
                100,
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO catalog_source_products
                (source_name, source_product_id, product_id, name, brand, category, price, stock, raw_product, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            ON CONFLICT (source_name, source_product_id) DO UPDATE SET
                product_id = EXCLUDED.product_id,
                raw_product = EXCLUDED.raw_product,
                is_active = 1
            """,
            (
                source_name,
                str(product_id),
                product_id,
                "IndividualCare Plan",
                "InsureMax Health",
                "Health Insurance",
                899.0,
                100,
                json.dumps(raw_product),
            ),
        )

    changed = sync_products_to_knowledge(
        site_id,
        source_name,
        entity_type="insurance_plan",
        source_type="website_crawl",
    )

    with get_db(site_id) as conn:
        row = conn.execute(
            """
            SELECT id, entity_type, title, subtitle, summary, body,
                   attributes_json, pricing_json, policy_json, risk_tags_json
            FROM knowledge_items
            WHERE id = %s
            """,
            (f"product:{product_id}",),
        ).fetchone()

    assert changed >= 1
    assert row is not None
    policy = json.loads(row["policy_json"])
    pricing = json.loads(row["pricing_json"])
    risk_tags = json.loads(row["risk_tags_json"])
    assert policy["age_min"] == 18
    assert policy["age_max"] == 65
    assert policy["sum_insured"] == 500000
    assert pricing["premium_monthly"] == 899
    assert "health_cover" in risk_tags

    text = _knowledge_item_to_text(dict(row))
    assert "age_min" in text
    assert "premium_monthly" in text
    ranked = _rank_lexical_items(
        "compare health insurance for me, I am 20 year old",
        [dict(row)],
        limit=5,
    )
    assert [item["id"] for item in ranked] == [f"product:{product_id}"]


def test_vectorize_missing_knowledge_drains_more_than_one_batch(monkeypatch):
    site_id = "knowledge_vectorize_batch_test"
    init_tenant_schema(site_id)
    with get_db(site_id) as conn:
        conn.execute("DELETE FROM knowledge_items WHERE id LIKE 'bulk:%%'")
        conn.execute(
            """
            INSERT INTO knowledge_sources (id, source_type, source_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET source_name = EXCLUDED.source_name
            """,
            ("source:bulk_test", "test", "bulk_test"),
        )
        for index in range(5):
            conn.execute(
                """
                INSERT INTO knowledge_items
                    (id, external_id, entity_type, title, source_id, is_active, embedding)
                VALUES (%s, %s, %s, %s, %s, 1, NULL)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    is_active = 1,
                    embedding = NULL
                """,
                (
                    f"bulk:{index}",
                    str(index),
                    "test_item",
                    f"Bulk item {index}",
                    "source:bulk_test",
                ),
            )

    batch_sizes: list[int] = []

    def fake_embed(texts):
        batch_sizes.append(len(texts))
        return [[0.01] * 384 for _ in texts]

    monkeypatch.setattr("agent.retrieval.generic_rag.VECTORIZE_BATCH_SIZE", 2)
    monkeypatch.setattr("agent.retrieval.generic_rag._embed", fake_embed)

    vectorized = vectorize_missing_knowledge(site_id)
    stats = knowledge_stats(site_id)

    assert vectorized >= 5
    assert batch_sizes[:3] == [2, 2, 1]
    assert stats["missing_embeddings"] == 0


def test_knowledge_item_text_includes_policy_specific_fields():
    text = _knowledge_item_to_text(
        {
            "title": "IndividualCare Plan",
            "subtitle": "Health Insurance",
            "entity_type": "insurance_plan",
            "summary": "Health policy with cashless hospitalization.",
            "pricing_json": '{"premium_monthly": 899, "currency": "INR"}',
            "policy_json": '{"age_min": 18, "age_max": 65, "sum_insured": 500000}',
            "risk_tags_json": '["regulated_insurance", "health_cover"]',
        }
    )

    assert "Health Insurance" in text
    assert "premium_monthly" in text
    assert "age_min" in text
    assert "regulated_insurance" in text


def test_lexical_rank_prioritizes_health_insurance_for_age_query():
    rows = [
        {
            "id": "product:H001",
            "entity_type": "insurance_plan",
            "title": "IndividualCare Plan",
            "subtitle": "InsureMax Health | Health Insurance",
            "summary": "Health Insurance insurance plan priced at INR 9,999.",
            "body": "Cashless hospitalization, OPD, critical illness, claim support.",
            "pricing_json": '{"premium_monthly": 899, "premium_annual": 9999}',
            "policy_json": '{"age_min": 18, "age_max": 65, "sum_insured": 500000}',
        },
        {
            "id": "product:M001",
            "entity_type": "insurance_plan",
            "title": "ComprehensiveCar Shield",
            "subtitle": "InsureMax General | Motor Insurance",
            "summary": "Motor insurance policy for cars.",
            "body": "Garage claim support and third party liability.",
            "pricing_json": '{"premium_monthly": 799, "premium_annual": 8999}',
            "policy_json": '{"age_min": 18, "age_max": 70}',
        },
    ]

    ranked = _rank_lexical_items(
        "compare health insurance for me, I am 20 year old",
        rows,
        limit=5,
    )

    assert [item["id"] for item in ranked] == ["product:H001", "product:M001"]
    assert ranked[0]["_semantic_score"] > 0
