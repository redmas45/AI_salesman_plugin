"""Food and grocery vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="food",
    label="Food",
    risk_level="low",
    entity_label_singular="menu item",
    entity_label_plural="menu items",
    default_plan_label="Food ordering plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Menu"),
        ("crawl", "Sources"),
        ("leads", "Orders/Leads"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("restaurant", "menu_item", "grocery_item", "cuisine", "offer", "delivery_zone"),
    readiness_checks=("menu", "location", "delivery_zone", "cart", "checkout", "dietary_data"),
    action_types=("SHOW_ENTITIES", "SET_LOCATION", "ADD_TO_CART", "CHECKOUT_HANDOFF", "CAPTURE_LEAD"),
)
