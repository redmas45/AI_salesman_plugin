"""Regression tests for slice 6: inventory-count vs product-browse intent.

Reproduces the reported failures where a *browse* phrase was answered as an
inventory *count* and a brand was pluralized into a product type:
  - "I'm looking for Apple products" -> "I found 18 apples in stock"
  - "I'm interested in Apple Flex smartwatches" -> "I found 66 ... in stock"

After the fix a brand is never pluralized ("apples"), browse phrases are a
product_search intent, and only genuine count questions keep the "in stock"
count wording.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.responses.inventory_responses import (  # noqa: E402
    is_browse_search_phrase,
    pluralize,
)
from agent.runtime_helpers.retrieval_runtime import products_for_explicit_request  # noqa: E402

ECOMMERCE_TEST_SITE_ID = "ecommerce_site"


def test_browse_phrases_are_detected():
    for phrase in (
        "I'm looking for Apple products",
        "I am interested in Apple Flex smartwatches",
        "I want to buy a laptop",
        "I need a gift",
    ):
        assert is_browse_search_phrase(phrase), phrase


def test_count_questions_are_not_browse():
    for phrase in (
        "How many caps do you have?",
        "Do you have iPhone?",
        "Is iPhone available?",
    ):
        assert not is_browse_search_phrase(phrase), phrase


def test_pluralize_never_invents_a_brand_plural_for_count_of_one():
    # Guards the "1 iphone" grammar; brand-guarding itself is covered end-to-end below.
    assert pluralize("iphone", 1) == "iphone"


def _run(monkeypatch, products, text):
    from agent import orchestrator

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )
    events = list(orchestrator.run_stream(site_id=ECOMMERCE_TEST_SITE_ID, text_input=text, skip_tts=True))
    response = next(event for event in events if event["event"] == "response")
    return response["data"]["response_text"]


APPLE_CATALOG = [
    {"id": "a1", "name": "iPhone 17 Pro", "brand": "Apple", "category_name": "Electronics", "stock": 9},
    {"id": "a2", "name": "iPad Air", "brand": "Apple", "category_name": "Electronics", "stock": 4},
    {"id": "a3", "name": "MacBook Air", "brand": "Apple", "category_name": "Electronics", "stock": 3},
]


def test_looking_for_apple_products_does_not_say_apples(monkeypatch):
    text = _run(monkeypatch, APPLE_CATALOG, "I'm looking for Apple products")
    assert "apples" not in text.lower()
    assert "in stock" not in text.lower()
    assert "matching product" in text.lower()


def test_brand_count_question_does_not_pluralize_brand(monkeypatch):
    text = _run(monkeypatch, APPLE_CATALOG, "Do you have any Apple?")
    assert "apples" not in text.lower()
    assert "matching product" in text.lower()


# --- Slice 5: field-aware conjunctive matching ------------------------------

CONJUNCTIVE_CATALOG = [
    {"id": "sw", "name": "Apple Watch Series 10", "brand": "Apple",
     "category_name": "Wearables", "tags": ["smartwatch", "watch"], "stock": 5},
    {"id": "df", "name": "NOVA Flex Dry Fruits Mix", "brand": "NOVA",
     "category_name": "Food", "tags": ["dry fruits", "snacks"], "stock": 9},
    {"id": "tab", "name": "Apple iPad Air", "brand": "Apple",
     "category_name": "Electronics", "tags": ["tablet"], "stock": 4},
    {"id": "nova-sw", "name": "NOVA Active Smartwatch", "brand": "NOVA",
     "category_name": "Wearables", "tags": ["smartwatch"], "stock": 7},
]


def _run_actions(monkeypatch, products, text):
    from agent import orchestrator

    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: products)
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator.llm,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )
    events = list(orchestrator.run_stream(site_id=ECOMMERCE_TEST_SITE_ID, text_input=text, skip_tts=True))
    actions = next(event for event in events if event["event"] == "actions")
    response = next(event for event in events if event["event"] == "response")
    ids = actions["data"]["ui_actions"][0]["params"]["product_ids"] if actions["data"]["ui_actions"] else []
    return ids, response["data"]["response_text"]


def test_apple_smartwatch_excludes_dry_fruits_and_tablets(monkeypatch):
    # Brand+type conjunction: only the Apple *smartwatch* qualifies.
    ids, text = _run_actions(monkeypatch, CONJUNCTIVE_CATALOG, "I'm interested in Apple Flex smartwatches")
    assert ids == ["sw"]
    assert "dry fruits" not in text.lower()
    assert "ipad" not in text.lower()


def test_smartwatch_only_returns_all_smartwatches(monkeypatch):
    # Single facet (type only): both smartwatches, no tablet/dry-fruits.
    ids, _text = _run_actions(monkeypatch, CONJUNCTIVE_CATALOG, "I'm looking for a smartwatch")
    assert set(ids) == {"sw", "nova-sw"}


def test_recommendation_path_enforces_brand_and_type_conjunction():
    matches = products_for_explicit_request(
        CONJUNCTIVE_CATALOG,
        "Can you recommend an Apple smartwatch?",
    )
    assert [product["id"] for product in matches] == ["sw"]


def test_recommendation_path_normalizes_plural_product_types():
    matches = products_for_explicit_request(
        CONJUNCTIVE_CATALOG,
        "Recommend smartwatches",
    )
    assert {product["id"] for product in matches} == {"sw", "nova-sw"}


def test_explicit_brand_uses_brand_field_not_compatibility_text():
    catalog = [
        *CONJUNCTIVE_CATALOG,
        {
            "id": "compatible",
            "name": "Anker Apple-Compatible Watch Charger",
            "brand": "Anker",
            "category_name": "Wearables",
            "tags": ["apple", "smartwatch", "charger"],
        },
    ]
    matches = products_for_explicit_request(catalog, "Recommend an Apple smartwatch")
    assert [product["id"] for product in matches] == ["sw"]
