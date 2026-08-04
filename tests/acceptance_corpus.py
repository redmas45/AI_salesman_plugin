"""Multi-turn acceptance corpus for e-commerce, travel, and policy.

Each entry is one whole conversation, not one utterance, because almost every
reported defect was a *continuity* failure: a budget that survived one turn and
vanished on the next, a correction that was ignored, a superlative answered from
the previous topic's records, a page question answered with a fresh search.

Turn expectations are asserted keys only. A key that is absent is not checked,
so a scenario states exactly what it is about and nothing more.

Supported keys
    operation   the resolved TurnOperation value
    off_topic   whether the turn is small talk rather than a shopping request
    aggregate   the resolved superlative ("cheapest" / "most_expensive" / "best_rated")
    max_price   the ceiling in force on this turn (None asserts no ceiling)
    min_price   the floor in force on this turn
    brands      brands the turn is scoped to
    types       item/entity types the turn is scoped to
    recipient   who the purchase is for
    ids         record ids the deterministic selection must return, in order
    categories  category labels the turn resolved from tenant data
    cacheable   whether the answer may be replayed
    navigation  whether the customer asked to be taken somewhere
    referents   record ids inherited from the screen or from history
    clarify     whether the turn is still under-determined
"""

from __future__ import annotations

# --- Tenant fixtures. Neutral invented names, so the assertions prove generic
# behaviour rather than one demo store's taxonomy. ---------------------------

ECOMMERCE_CATALOG = [
    {"id": "e1", "name": "Aster Slim Kurta", "brand": "Aster", "category_name": "Fashion Women",
     "price": 499.0, "rating": 4.2, "review_count": 18, "stock": 5, "variant_id": 901},
    {"id": "e2", "name": "Aster Cotton Top", "brand": "Aster", "category_name": "Fashion Women",
     "price": 1299.0, "rating": 4.8, "review_count": 9, "stock": 3, "variant_id": 902},
    {"id": "e3", "name": "Borel Steel Bottle", "brand": "Borel", "category_name": "Home Kitchen",
     "price": 199.0, "rating": 4.9, "review_count": 40, "stock": 12, "variant_id": 903},
    {"id": "e4", "name": "Corvi Smartphone X1", "brand": "Corvi", "category_name": "Electronics",
     "price": 42999.0, "rating": 4.4, "review_count": 120, "stock": 2, "variant_id": 904},
    {"id": "e5", "name": "Corvi Smartphone X9", "brand": "Corvi", "category_name": "Electronics",
     "price": 72999.0, "rating": 4.7, "review_count": 80, "stock": 4, "variant_id": 905},
    {"id": "e6", "name": "Delta Smartphone Lite", "brand": "Delta", "category_name": "Electronics",
     "price": 18999.0, "rating": 4.1, "review_count": 55, "stock": 9, "variant_id": 906},
    {"id": "e7", "name": "Delta Laptop Air", "brand": "Delta", "category_name": "Electronics",
     "price": 64999.0, "rating": 4.6, "review_count": 33, "stock": 6, "variant_id": 907},
    {"id": "e8", "name": "Aster Sold Out Dress", "brand": "Aster", "category_name": "Fashion Women",
     "price": 149.0, "rating": 4.9, "review_count": 30, "stock": 0, "variant_id": 908},
]
ECOMMERCE_BRANDS = ("aster", "borel", "corvi", "delta")

TRAVEL_CATALOG = [
    {"id": "t1", "name": "Coastal Rail Pass", "brand": "Merova", "category_name": "Rail Journeys",
     "price": 7400.0, "rating": 4.5, "review_count": 61, "stock": 20, "variant_id": 701},
    {"id": "t2", "name": "Merova Island Flight", "brand": "Merova", "category_name": "Flights",
     "price": 18900.0, "rating": 4.2, "review_count": 140, "stock": 8, "variant_id": 702},
    {"id": "t3", "name": "Highland Lodge Stay", "brand": "Kelvar", "category_name": "Hotels",
     "price": 5200.0, "rating": 4.8, "review_count": 95, "stock": 4, "variant_id": 703},
    {"id": "t4", "name": "Kelvar City Hotel", "brand": "Kelvar", "category_name": "Hotels",
     "price": 3100.0, "rating": 4.0, "review_count": 210, "stock": 15, "variant_id": 704},
    {"id": "t5", "name": "Unlisted Charter Flight", "brand": "Merova", "category_name": "Flights",
     "price": 42000.0, "rating": 5.0, "review_count": 0, "stock": 2, "variant_id": 705},
]
TRAVEL_BRANDS = ("merova", "kelvar")
TRAVEL_TYPES = ("flight", "hotel", "lodge", "rail pass", "pass")

POLICY_CATALOG = [
    {"id": "p1", "name": "Vantis Term Cover", "brand": "Vantis", "category_name": "Life Insurance",
     "price": 8400.0, "rating": 4.3, "review_count": 74, "stock": 100, "variant_id": 601},
    {"id": "p2", "name": "Vantis Family Health Plan", "brand": "Vantis", "category_name": "Health Insurance",
     "price": 15600.0, "rating": 4.6, "review_count": 52, "stock": 100, "variant_id": 602},
    {"id": "p3", "name": "Orlen Motor Shield", "brand": "Orlen", "category_name": "Motor Insurance",
     "price": 4200.0, "rating": 4.1, "review_count": 180, "stock": 100, "variant_id": 603},
    {"id": "p4", "name": "Orlen Health Essential", "brand": "Orlen", "category_name": "Health Insurance",
     "price": 9900.0, "rating": 4.4, "review_count": 31, "stock": 100, "variant_id": 604},
    {"id": "p5", "name": "Withdrawn Legacy Plan", "brand": "Orlen", "category_name": "Life Insurance",
     "price": 2000.0, "rating": 4.9, "review_count": 12, "stock": 0, "variant_id": 605},
]
POLICY_BRANDS = ("vantis", "orlen")
POLICY_TYPES = (
    "term cover", "health plan", "motor shield", "plan", "cover",
    "life insurance", "health insurance", "motor insurance",
)

VERTICALS = {
    "ecommerce": {"catalog": ECOMMERCE_CATALOG, "brands": ECOMMERCE_BRANDS, "types": ()},
    "travel": {"catalog": TRAVEL_CATALOG, "brands": TRAVEL_BRANDS, "types": TRAVEL_TYPES},
    "policy": {"catalog": POLICY_CATALOG, "brands": POLICY_BRANDS, "types": POLICY_TYPES},
}

# A screen showing two electronics records, used by page-relative scenarios.
ELECTRONICS_SCREEN = {
    "visible_entities": [
        {"id": "e4", "entity_type": "product", "label": "Corvi Smartphone X1", "facts": {"price": "42999"}},
        {"id": "e6", "entity_type": "product", "label": "Delta Smartphone Lite", "facts": {"price": "18999"}},
    ],
    "route": {"path": "/electronics", "search": ""},
    "filters": {"category": "electronics"},
    "sort": "",
}


# --- Conversations ----------------------------------------------------------
# (name, vertical, [(utterance, expectations), ...])

ECOMMERCE_CONVERSATIONS = [
    ("eager_budgeted_phone", "ecommerce", [
        ("I'm looking for a Corvi smartphone", {"brands": {"corvi"}, "types": {"smartphone"}}),
        ("under 50000", {"max_price": 50000.0, "ids": ["e4"]}),
    ]),
    ("budget_correction_raises_ceiling", "ecommerce", [
        ("show me a smartphone under 20000", {"max_price": 20000.0, "ids": ["e6"]}),
        ("but I said 50,000", {"max_price": 50000.0, "cacheable": False}),
    ]),
    ("budget_correction_lowers_ceiling", "ecommerce", [
        ("a smartphone under 80000", {"max_price": 80000.0}),
        ("actually 20000", {"max_price": 20000.0, "cacheable": False}),
    ]),
    ("gift_recipient_needs_detail", "ecommerce", [
        ("something for my girlfriend under 3000", {"recipient": "girlfriend", "max_price": 3000.0,
                                                    "operation": "recommend", "types": set()}),
    ]),
    ("gift_then_category", "ecommerce", [
        ("a gift for my mom", {"recipient": "mom", "clarify": True}),
        ("something from Fashion Women under 1500", {"max_price": 1500.0, "categories": ("Fashion Women",),
                                                     "ids": ["e1", "e2"]}),
    ]),
    ("cheapest_in_category", "ecommerce", [
        ("what is the cheapest item in Fashion Women?", {"operation": "aggregate", "aggregate": "cheapest",
                                                         "categories": ("Fashion Women",), "ids": ["e1"]}),
    ]),
    ("cheapest_overall", "ecommerce", [
        ("which is your cheapest product?", {"aggregate": "cheapest", "ids": ["e3"]}),
    ]),
    ("most_expensive_scoped_to_type", "ecommerce", [
        ("what is the most expensive smartphone?", {"aggregate": "most_expensive", "ids": ["e5"]}),
    ]),
    ("best_rated_needs_review_evidence", "ecommerce", [
        ("which item has the best rating?", {"aggregate": "best_rated", "ids": ["e3"]}),
    ]),
    ("aggregate_plus_navigation", "ecommerce", [
        ("show the cheapest smartphone and take me there", {"aggregate": "cheapest", "navigation": True,
                                                            "cacheable": False, "ids": ["e6"]}),
    ]),
    ("inventory_count_is_not_a_browse", "ecommerce", [
        ("how many smartphones do you have?", {"operation": "inventory_count", "ids": ["e4", "e5", "e6"]}),
    ]),
    ("brand_browse_is_not_pluralised", "ecommerce", [
        ("do you have Aster?", {"brands": {"aster"}, "ids": ["e1", "e2"]}),
    ]),
    ("out_of_stock_never_offered", "ecommerce", [
        ("show me Aster dresses under 200", {"max_price": 200.0, "ids": []}),
    ]),
    ("topic_change_drops_stale_brand", "ecommerce", [
        ("Corvi smartphones please", {"brands": {"corvi"}}),
        ("actually show me Home Kitchen", {"categories": ("Home Kitchen",), "ids": ["e3"]}),
    ]),
    ("page_question_uses_the_screen", "ecommerce", [
        ("which of these results is cheapest?", {"referents": ("e4", "e6"), "cacheable": False},
         ELECTRONICS_SCREEN),
    ]),
    ("page_question_never_navigates", "ecommerce", [
        ("what is showing on this page?", {"operation": "page_question", "cacheable": False,
                                           "referents": ("e4", "e6")}, ELECTRONICS_SCREEN),
    ]),
    ("sort_is_not_a_search", "ecommerce", [
        ("sort them by price low to high", {"operation": "sort", "cacheable": False}),
    ]),
    ("navigation_only", "ecommerce", [
        ("take me to the offers page", {"operation": "navigate", "navigation": True, "cacheable": False}),
    ]),
    ("comparison_of_two", "ecommerce", [
        ("compare the Corvi Smartphone X1 and the Delta Smartphone Lite", {"operation": "compare"}),
    ]),
    ("time_waster_gets_one_clarification", "ecommerce", [
        ("I'm just browsing", {"clarify": True}),
        ("what should I buy?", {"clarify": True}),
    ]),
    ("nonsense_is_clarified_not_searched", "ecommerce", [
        ("It's raining air. What should I buy? I'm not decided.", {"clarify": True, "types": set()}),
    ]),
    ("checking_only_availability", "ecommerce", [
        ("is the Delta Laptop Air available?", {"brands": {"delta"}}),
    ]),
    ("curious_category_exploration", "ecommerce", [
        ("I'm interested in laptops", {"types": {"laptop"}, "ids": ["e7"]}),
    ]),
    ("floor_and_ceiling_together", "ecommerce", [
        ("smartphones between 20000 and 60000", {"min_price": 20000.0, "max_price": 60000.0, "ids": ["e4"]}),
    ]),
    ("cart_turn_is_never_replayed", "ecommerce", [
        ("add that one to my cart", {"cacheable": False}),
    ]),
    ("off_topic_question", "ecommerce", [
        ("what is the weather like today?", {"off_topic": True, "types": set()}),
    ]),
    ("budget_survives_a_follow_up", "ecommerce", [
        ("smartphones under 50000", {"max_price": 50000.0}),
        ("any from Corvi?", {"brands": {"corvi"}, "max_price": 50000.0, "ids": ["e4"]}),
    ]),
    ("exclusion_is_a_hard_constraint", "ecommerce", [
        ("show me a smartphone under 50000", {"max_price": 50000.0}),
    ]),
]

TRAVEL_CONVERSATIONS = [
    ("travel_budgeted_hotel", "travel", [
        ("I want a Kelvar hotel under 4000", {"brands": {"kelvar"}, "max_price": 4000.0, "ids": ["t4"]}),
    ]),
    ("travel_cheapest_in_category", "travel", [
        ("what is the cheapest Hotels option?", {"aggregate": "cheapest", "categories": ("Hotels",),
                                                 "ids": ["t4"]}),
    ]),
    ("travel_best_rated_requires_reviews", "travel", [
        ("which trip is best rated?", {"aggregate": "best_rated", "ids": ["t3"]}),
    ]),
    ("travel_most_expensive", "travel", [
        ("what is your most expensive option?", {"aggregate": "most_expensive", "ids": ["t5"]}),
    ]),
    ("travel_budget_correction", "travel", [
        ("flights under 15000", {"max_price": 15000.0}),
        ("but I said 20,000", {"max_price": 20000.0, "cacheable": False}),
    ]),
    ("travel_count", "travel", [
        ("how many hotels do you have?", {"operation": "inventory_count"}),
    ]),
    ("travel_navigation", "travel", [
        ("take me to the bookings page", {"operation": "navigate", "cacheable": False}),
    ]),
    ("travel_aggregate_plus_navigation", "travel", [
        ("show the cheapest hotel and take me there", {"aggregate": "cheapest", "navigation": True,
                                                       "cacheable": False}),
    ]),
    ("travel_sort", "travel", [
        ("sort these by price", {"operation": "sort", "cacheable": False}),
    ]),
    ("travel_topic_change", "travel", [
        ("Merova flights", {"brands": {"merova"}}),
        ("actually show me Kelvar", {"brands": {"kelvar"}}),
    ]),
    ("travel_clarification", "travel", [
        ("I'm not sure where to go", {"clarify": True}),
    ]),
    ("travel_comparison", "travel", [
        ("compare the Highland Lodge Stay and the Kelvar City Hotel", {"operation": "compare"}),
    ]),
    ("travel_floor_price", "travel", [
        ("anything above 10000?", {"min_price": 10000.0}),
    ]),
    ("travel_brand_scoped_follow_up", "travel", [
        ("hotels under 6000", {"max_price": 6000.0}),
        ("any from Kelvar?", {"brands": {"kelvar"}, "max_price": 6000.0}),
    ]),
    ("travel_page_question", "travel", [
        ("which of these is cheapest?", {"cacheable": False}),
    ]),
    ("travel_out_of_stock_excluded", "travel", [
        ("show me every flight", {"types": {"flight"}}),
    ]),
]

POLICY_CONVERSATIONS = [
    ("policy_route_interest", "policy", [
        ("I'm interested in life insurance", {"clarify": False}),
    ]),
    ("policy_budgeted_health_plan", "policy", [
        ("a Vantis health plan under 20000", {"brands": {"vantis"}, "max_price": 20000.0, "ids": ["p2"]}),
    ]),
    ("policy_cheapest_in_category", "policy", [
        ("what is the cheapest Health Insurance option?", {"aggregate": "cheapest",
                                                           "categories": ("Health Insurance",), "ids": ["p4"]}),
    ]),
    ("policy_best_rated", "policy", [
        ("which plan is best rated?", {"aggregate": "best_rated", "ids": ["p2"]}),
    ]),
    ("policy_most_expensive", "policy", [
        ("what is the most expensive plan?", {"aggregate": "most_expensive", "ids": ["p2"]}),
    ]),
    ("policy_withdrawn_plan_never_offered", "policy", [
        ("show me life insurance under 3000", {"max_price": 3000.0, "ids": []}),
    ]),
    ("policy_budget_correction", "policy", [
        ("cover under 5000", {"max_price": 5000.0}),
        ("actually 10000", {"max_price": 10000.0, "cacheable": False}),
    ]),
    ("policy_count", "policy", [
        ("how many plans do you have?", {"operation": "inventory_count"}),
    ]),
    ("policy_navigation", "policy", [
        ("take me to the claims page", {"operation": "navigate", "cacheable": False}),
    ]),
    ("policy_sort", "policy", [
        ("sort them by price low to high", {"operation": "sort", "cacheable": False}),
    ]),
    ("policy_comparison", "policy", [
        ("compare the Vantis Term Cover and the Orlen Motor Shield", {"operation": "compare"}),
    ]),
    ("policy_clarification", "policy", [
        ("I have no idea what I need", {"clarify": True}),
    ]),
    ("policy_topic_change", "policy", [
        ("Vantis plans", {"brands": {"vantis"}}),
        ("actually show me Orlen", {"brands": {"orlen"}}),
    ]),
    ("policy_brand_scoped_follow_up", "policy", [
        ("health insurance under 20000", {"max_price": 20000.0}),
        ("any from Orlen?", {"brands": {"orlen"}, "max_price": 20000.0, "ids": ["p4"]}),
    ]),
    ("policy_page_question", "policy", [
        ("what is displayed right now?", {"operation": "page_question", "cacheable": False}),
    ]),
    ("policy_unsupported_technical_depth", "policy", [
        ("what is the reinsurance treaty structure behind this?", {"clarify": False}),
    ]),
]

CONVERSATIONS = ECOMMERCE_CONVERSATIONS + TRAVEL_CONVERSATIONS + POLICY_CONVERSATIONS
