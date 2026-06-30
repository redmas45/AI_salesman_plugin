"""E-commerce vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="ecommerce",
    label="E-commerce",
    risk_level="low",
    entity_label_singular="product",
    entity_label_plural="products",
    default_plan_label="Commerce plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Catalog"),
        ("crawl", "Crawl"),
        ("activity", "Activity"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("product", "category", "brand", "variant", "offer", "policy_page"),
    readiness_checks=("catalog", "variants", "cart", "checkout"),
    action_types=(
        "SHOW_PRODUCTS",
        "SHOW_COMPARISON",
        "FILTER_PRODUCTS",
        "SORT_PRODUCTS",
        "ADD_TO_CART",
        "CHECKOUT",
    ),
)
