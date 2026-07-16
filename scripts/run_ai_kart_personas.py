"""Run the final AI-KART buyer-persona and session-cache acceptance matrix."""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

HUB_URL = "http://localhost:5176"
SITE_ID = "ai_kart"
ORIGIN = "http://localhost:5175"
REQUEST_TIMEOUT_SECONDS = 90
REPORT_PATH = Path("test-results/aihub-final-persona-test.json")
UNSUPPORTED_SCOPE = "unsupported_or_offsite"

PAGE_CONTEXT = {
    "url": f"{ORIGIN}/",
    "title": "AI-KART",
    "routes": {
        "home": "/",
        "shop": "/shop",
        "beauty": "/shop?category=beauty-personal-care",
        "shipping-and-returns": "/shipping-and-returns",
        "about": "/about",
        "cart": "/cart",
        "checkout": "/checkout",
    },
}


@dataclass(frozen=True)
class TurnSpec:
    question: str
    expected_action: str = ""
    expected_page: str = ""
    expect_unsupported: bool = False
    minimum_comparison_products: int = 0
    maximum_comparison_products: int = 0
    maximum_product_price: float = 0
    required_product_terms: tuple[str, ...] = ()
    required_response_terms: tuple[str, ...] = ()
    expect_no_product_action: bool = False


@dataclass
class TurnResult:
    persona: str
    turn: int
    question: str
    status_code: int
    response_text: str
    answer_scope: str
    intent: str
    actions: list[dict[str, Any]]
    retrieval: dict[str, Any]
    failures: list[str]


PERSONAS: dict[str, list[TurnSpec]] = {
    "very_eager_buyer": [
        TurnSpec("I am ready to buy a phone today, but should I choose iPhone or Android? Show me strong options."),
        TurnSpec("From those choices, narrow it to the best two for camera, battery, and five-year use under INR 90,000.", minimum_comparison_products=2),
        TurnSpec("At a practical buying level, how do Apple A-series chips and Snapdragon phones differ for me?"),
        TurnSpec("Now compare their CPU microarchitecture, transistor design, and instruction pipelines in depth.", expect_unsupported=True),
        TurnSpec("Choose the better of those two under my budget and add it to the cart.", expected_action="ADD_TO_CART"),
    ],
    "time_wasting_buyer": [
        TurnSpec("I might buy a beauty gift, or maybe not. Show a few well-rated skincare options."),
        TurnSpec("Actually maybe a phone instead. Show some reliable mid-range choices."),
        TurnSpec("Before that, what is the weather in Delhi today?", expect_unsupported=True),
        TurnSpec(
            "Back to the gift: show beauty products below INR 2,000 with good ratings.",
            expected_action="SHOW_PRODUCTS",
            maximum_product_price=2_000,
            required_product_terms=("beauty", "skin", "eye", "lip", "moistur", "serum", "sunscreen"),
        ),
        TurnSpec("Open the Beauty section so I can browse it myself.", expected_action="NAVIGATE_TO", expected_page="shop?category=beauty-personal-care"),
    ],
    "just_checking_buyer": [
        TurnSpec(
            "I am only checking. What phones do you list below INR 20,000?",
            expected_action="SHOW_PRODUCTS",
            maximum_product_price=20_000,
            required_product_terms=("phone", "smartphone", "android", "iphone", "5g"),
        ),
        TurnSpec(
            "Compare the best two of those by price, battery, camera, rating, and reviews.",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            maximum_product_price=20_000,
            required_product_terms=("phone", "smartphone", "android", "iphone", "5g"),
            required_response_terms=("rating", "reviews"),
        ),
        TurnSpec("Take me to your returns information.", expected_action="NAVIGATE_TO", expected_page="shipping-and-returns"),
        TurnSpec("Who is the prime minister of India?", expect_unsupported=True),
        TurnSpec("Open the cheaper phone from that comparison so I can inspect it.", expected_action="SHOW_PRODUCT_DETAIL"),
    ],
    "curious_buyer": [
        TurnSpec("My skin is dry. Show suitable moisturisers or serums from this store."),
        TurnSpec(
            "Compare two good choices using ingredients, listed specs, price, rating, and review count.",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            required_product_terms=("beauty", "skin", "moistur", "serum"),
            required_response_terms=("rating", "reviews"),
        ),
        TurnSpec("Explain the molecular chemistry and receptor pathways of every ingredient in depth.", expect_unsupported=True),
        TurnSpec(
            "Which of the compared products is in stock and better rated according to the store?",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            required_product_terms=("beauty", "skin", "moistur", "serum"),
            required_response_terms=("rating", "reviews"),
        ),
        TurnSpec("Open the cheaper of those compared beauty products.", expected_action="SHOW_PRODUCT_DETAIL"),
    ],
    "skeptical_buyer": [
        TurnSpec(
            "I do not trust generic recommendations. Show college laptops under INR 60,000 from the actual catalog.",
            expected_action="SHOW_PRODUCTS",
            maximum_product_price=60_000,
            required_product_terms=("laptop", "student", "budget", "notebook"),
        ),
        TurnSpec("Why should I trust these choices? Use only listed price, stock, rating, reviews, and specifications."),
        TurnSpec(
            "Compare the two strongest value options and be direct about the tradeoffs.",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            maximum_product_price=60_000,
            required_product_terms=("laptop", "student", "budget", "notebook"),
        ),
        TurnSpec("What is the capital of France?", expect_unsupported=True),
        TurnSpec("Open the cheaper laptop from that comparison so I can verify it myself.", expected_action="SHOW_PRODUCT_DETAIL"),
    ],
    "decisive_budget_buyer": [
        TurnSpec(
            "Show me in-stock phones under INR 20,000 and keep strictly to that limit.",
            expected_action="SHOW_PRODUCTS",
            maximum_product_price=20_000,
            required_product_terms=("phone", "smartphone", "android", "iphone", "5g"),
        ),
        TurnSpec(
            "Compare exactly the best two by price, rating, review count, battery, and camera.",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            maximum_product_price=20_000,
            required_product_terms=("phone", "smartphone", "android", "iphone", "5g"),
            required_response_terms=("rating", "reviews"),
        ),
        TurnSpec(
            "Which of those two gives better battery value based only on the listed specifications?",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            maximum_product_price=20_000,
            required_product_terms=("phone", "smartphone", "android", "iphone", "5g"),
        ),
        TurnSpec("Pick the better-rated one and add it to my cart.", expected_action="ADD_TO_CART"),
        TurnSpec("Before checkout, explain quantum tunnelling in semiconductor fabrication.", expect_unsupported=True),
    ],
    "review_driven_beauty_buyer": [
        TurnSpec(
            "Show well-rated sunscreens or moisturisers under INR 1,500 from this store.",
            expected_action="SHOW_PRODUCTS",
            maximum_product_price=1_500,
            required_product_terms=("beauty", "skin", "sunscreen", "moistur"),
            required_response_terms=("rating", "reviews"),
        ),
        TurnSpec(
            "Compare exactly two of those using price, rating, reviews, and listed product details.",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            maximum_product_price=1_500,
            required_product_terms=("beauty", "skin", "sunscreen", "moistur"),
            required_response_terms=("rating", "reviews"),
        ),
        TurnSpec(
            "Which of the compared two is better rated and still in stock?",
            minimum_comparison_products=2,
            maximum_comparison_products=2,
            required_product_terms=("beauty", "skin", "sunscreen", "moistur"),
        ),
        TurnSpec("Open the cheaper one from that comparison.", expected_action="SHOW_PRODUCT_DETAIL"),
        TurnSpec("What is the capital of Japan?", expect_unsupported=True),
    ],
    "category_switching_buyer": [
        TurnSpec("Show office chairs under INR 20,000 from the catalog.", expect_no_product_action=True),
        TurnSpec("Actually switch to college laptops under INR 60,000.", expected_action="SHOW_PRODUCTS", maximum_product_price=60_000, required_product_terms=("laptop", "student", "budget", "notebook")),
        TurnSpec("Compare the best two laptop choices.", minimum_comparison_products=2, maximum_comparison_products=2, maximum_product_price=60_000, required_product_terms=("laptop", "student", "budget", "notebook")),
        TurnSpec("Now return to chairs and show options below INR 15,000.", expect_no_product_action=True),
        TurnSpec("Open the Shop section so I can browse myself.", expected_action="NAVIGATE_TO", expected_page="shop"),
    ],
    "navigation_focused_buyer": [
        TurnSpec("Take me to shipping and returns information.", expected_action="NAVIGATE_TO", expected_page="shipping-and-returns"),
        TurnSpec("Open the Beauty section so I can browse the category.", expected_action="NAVIGATE_TO", expected_page="shop?category=beauty-personal-care"),
        TurnSpec("Now show me moisturiser products rather than just the section.", expected_action="SHOW_PRODUCTS", required_product_terms=("beauty", "skin", "moistur")),
        TurnSpec("Open my cart.", expected_action="NAVIGATE_TO", expected_page="cart"),
        TurnSpec("What will Delhi weather be tomorrow?", expect_unsupported=True),
    ],
    "careful_book_buyer": [
        TurnSpec("Show self-help or business books under INR 1,000.", expected_action="SHOW_PRODUCTS", maximum_product_price=1_000, required_product_terms=("book", "self-help", "business", "fiction")),
        TurnSpec("Compare exactly two of those by price, rating, and reviews.", minimum_comparison_products=2, maximum_comparison_products=2, maximum_product_price=1_000, required_product_terms=("book", "self-help", "business", "fiction"), required_response_terms=("rating", "reviews")),
        TurnSpec("Which compared book is better rated according to store data?", minimum_comparison_products=2, maximum_comparison_products=2, required_product_terms=("book", "self-help", "business", "fiction")),
        TurnSpec("Open the cheaper compared book.", expected_action="SHOW_PRODUCT_DETAIL"),
        TurnSpec("Add that book to my cart.", expected_action="ADD_TO_CART"),
    ],
}


def post_turn(session_id: str, question: str, history: list[dict[str, str]]) -> requests.Response:
    return requests.post(
        f"{HUB_URL}/v1/shop",
        headers={"Origin": ORIGIN},
        data={
            "site_id": SITE_ID,
            "text": question,
            "skip_tts": "true",
            "session_id": session_id,
            "conversation_history": json.dumps(history),
            "page_context": json.dumps(PAGE_CONTEXT),
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def action_names(actions: list[dict[str, Any]]) -> list[str]:
    return [str(action.get("action") or "").upper() for action in actions]


def validate_turn(
    spec: TurnSpec,
    payload: dict[str, Any],
    catalog_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    response_text = str(payload.get("response_text") or "").strip()
    answer_scope = str(payload.get("answer_scope") or "")
    actions = payload.get("ui_actions") if isinstance(payload.get("ui_actions"), list) else []
    names = action_names(actions)

    if not response_text:
        failures.append("empty response")
    if "SHOW_PRODUCTS" in names and "NAVIGATE_TO" in names:
        failures.append("conflicting product overlay and page navigation")
    if spec.expect_unsupported:
        if answer_scope != UNSUPPORTED_SCOPE:
            failures.append(f"expected unsupported scope, got {answer_scope or 'empty'}")
        if actions:
            failures.append("unsupported question emitted a website action")
    elif answer_scope == UNSUPPORTED_SCOPE:
        failures.append("shopping question was incorrectly rejected")
    if spec.expected_action and spec.expected_action not in names:
        failures.append(f"missing {spec.expected_action} action")
    if spec.expect_no_product_action and set(names) & {"SHOW_PRODUCTS", "SHOW_COMPARISON", "SHOW_PRODUCT_DETAIL"}:
        failures.append("unavailable product request emitted a product action")
    if spec.expected_page:
        pages = [str(action.get("params", {}).get("page") or "") for action in actions]
        if not any(spec.expected_page in page for page in pages):
            failures.append(f"navigation did not target {spec.expected_page}")
    if spec.minimum_comparison_products:
        comparison_sizes = [
            len(action.get("params", {}).get("product_ids") or [])
            for action in actions
            if str(action.get("action") or "").upper() == "SHOW_COMPARISON"
        ]
        if not comparison_sizes or max(comparison_sizes) < spec.minimum_comparison_products:
            failures.append("comparison did not contain at least two products")
    if spec.maximum_comparison_products:
        comparison_sizes = [
            len(action.get("params", {}).get("product_ids") or [])
            for action in actions
            if str(action.get("action") or "").upper() == "SHOW_COMPARISON"
        ]
        if not comparison_sizes or max(comparison_sizes) > spec.maximum_comparison_products:
            failures.append(f"comparison exceeded {spec.maximum_comparison_products} products")
    selected_products = products_selected_by_actions(actions, catalog_by_id)
    if spec.maximum_product_price:
        invalid_prices = [
            f"{product.get('name')}={product.get('price')}"
            for product in selected_products
            if float(product.get("price") or 0) > spec.maximum_product_price
        ]
        if invalid_prices:
            failures.append(f"products exceed price limit: {', '.join(invalid_prices)}")
    if spec.required_product_terms:
        unrelated = [
            str(product.get("name") or product.get("id"))
            for product in selected_products
            if not product_matches_terms(product, spec.required_product_terms)
        ]
        if unrelated:
            failures.append(f"unrelated products returned: {', '.join(unrelated)}")
    response_lower = response_text.lower()
    for term in spec.required_response_terms:
        if term.lower() not in response_lower:
            failures.append(f"response omitted {term} evidence")
    for action in actions:
        if str(action.get("action") or "").upper() in {"ADD_TO_CART", "SHOW_PRODUCT_DETAIL"}:
            if not action.get("params", {}).get("product_id"):
                failures.append(f"{action.get('action')} is missing product_id")
    return failures


def products_selected_by_actions(
    actions: list[dict[str, Any]],
    catalog_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action in actions:
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        product_ids = params.get("product_ids") if isinstance(params.get("product_ids"), list) else []
        if params.get("product_id") is not None:
            product_ids = [*product_ids, params["product_id"]]
        for product_id in product_ids:
            key = str(product_id)
            if key in seen or key not in catalog_by_id:
                continue
            seen.add(key)
            selected.append(catalog_by_id[key])
    return selected


def product_matches_terms(product: dict[str, Any], terms: tuple[str, ...]) -> bool:
    searchable = " ".join(
        str(product.get(key) or "")
        for key in ("name", "brand", "category", "category_name", "description", "tags")
    ).lower()
    return any(term.lower() in searchable for term in terms)


def run_personas(catalog_by_id: dict[str, dict[str, Any]]) -> list[TurnResult]:
    results: list[TurnResult] = []
    run_id = uuid.uuid4().hex[:10]
    for persona, specs in PERSONAS.items():
        session_id = f"final-{run_id}-{persona}"
        history: list[dict[str, str]] = []
        for turn_number, spec in enumerate(specs, start=1):
            response = post_turn(session_id, spec.question, history)
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            failures = [] if response.status_code == 200 else [f"HTTP {response.status_code}"]
            if response.status_code == 200:
                failures.extend(validate_turn(spec, payload, catalog_by_id))
            result = TurnResult(
                persona=persona,
                turn=turn_number,
                question=spec.question,
                status_code=response.status_code,
                response_text=str(payload.get("response_text") or response.text)[:1000],
                answer_scope=str(payload.get("answer_scope") or ""),
                intent=str(payload.get("intent") or ""),
                actions=payload.get("ui_actions") if isinstance(payload.get("ui_actions"), list) else [],
                retrieval=payload.get("retrieval") if isinstance(payload.get("retrieval"), dict) else {},
                failures=failures,
            )
            results.append(result)
            history.extend(
                (
                    {"role": "user", "content": spec.question},
                    {"role": "assistant", "content": result.response_text},
                )
            )
            print(f"{persona} T{turn_number}: {'PASS' if not failures else 'FAIL'}")
    return results


def load_catalog() -> list[dict[str, Any]]:
    response = requests.get(
        f"{HUB_URL}/v1/products",
        params={"site_id": SITE_ID, "limit": 2_000},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def catalog_checks(products: list[dict[str, Any]]) -> dict[str, Any]:
    status_response = requests.get(
        f"{HUB_URL}/v1/catalog/status",
        params={"site_id": SITE_ID},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    status_response.raise_for_status()
    status = status_response.json()
    sample = products[:100]
    return {
        "status": status,
        "loaded_product_count": len(products),
        "sample_size": len(sample),
        "sample_with_ratings": sum(float(product.get("rating") or 0) > 0 for product in sample),
        "sample_with_reviews": sum(int(product.get("review_count") or 0) > 0 for product in sample),
        "sample_with_specs_in_description": sum("Specifications:" in str(product.get("description") or "") for product in sample),
    }


def cache_checks() -> dict[str, Any]:
    question = "Explain the practical tradeoffs between iOS and Android for a phone buyer."
    similar_question = "What are the practical iOS versus Android tradeoffs for a phone buyer?"
    session_a = f"cache-a-{uuid.uuid4().hex}"
    session_b = f"cache-b-{uuid.uuid4().hex}"
    first = post_turn(session_a, question, []).json()
    history = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": str(first.get("response_text") or "")},
    ]
    repeated = post_turn(session_a, question, history).json()
    similar = post_turn(session_a, similar_question, []).json()
    isolated = post_turn(session_b, question, []).json()
    repeated_retrieval = repeated.get("retrieval") or {}
    similar_retrieval = similar.get("retrieval") or {}
    isolated_retrieval = isolated.get("retrieval") or {}
    return {
        "first_cache_hit": bool((first.get("retrieval") or {}).get("cache_hit")),
        "repeat_cache_hit": bool(repeated_retrieval.get("cache_hit")),
        "repeat_match_type": str(repeated_retrieval.get("match_type") or ""),
        "similar_cache_hit": bool(similar_retrieval.get("cache_hit")),
        "similar_match_type": str(similar_retrieval.get("match_type") or ""),
        "similar_match_score": float(similar_retrieval.get("match_score") or 0.0),
        "other_session_cache_hit": bool(isolated_retrieval.get("cache_hit")),
        "passed": bool(repeated_retrieval.get("cache_hit"))
        and str(repeated_retrieval.get("match_type") or "") == "exact"
        and bool(similar_retrieval.get("cache_hit"))
        and str(similar_retrieval.get("match_type") or "") == "semantic"
        and not bool(isolated_retrieval.get("cache_hit")),
    }


def main() -> int:
    products = load_catalog()
    catalog_by_id = {str(product["id"]): product for product in products}
    catalog = catalog_checks(products)
    results = run_personas(catalog_by_id)
    cache = cache_checks()
    failed_turns = [result for result in results if result.failures]
    catalog_passed = (
        int(((catalog.get("status") or {}).get("catalog") or {}).get("active_products") or 0) == 572
        and int(catalog.get("sample_with_ratings") or 0) > 0
        and int(catalog.get("sample_with_reviews") or 0) > 0
        and int(catalog.get("sample_with_specs_in_description") or 0) > 0
    )
    report = {
        "site_id": SITE_ID,
        "origin": ORIGIN,
        "catalog": catalog,
        "catalog_passed": catalog_passed,
        "cache": cache,
        "turn_count": len(results),
        "failed_turn_count": len(failed_turns),
        "passed": not failed_turns and catalog_passed and bool(cache.get("passed")),
        "turns": [asdict(result) for result in results],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report: {REPORT_PATH.resolve()}")
    print(f"Result: {'PASS' if report['passed'] else 'FAIL'} ({len(results) - len(failed_turns)}/{len(results)} persona turns)")
    if failed_turns:
        for result in failed_turns:
            print(f"- {result.persona} T{result.turn}: {', '.join(result.failures)}")
    if not catalog_passed:
        print("- catalog evidence check failed")
    if not cache.get("passed"):
        print(f"- session cache check failed: {cache}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
