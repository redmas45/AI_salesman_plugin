"""Generic website vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="generic",
    label="Generic",
    risk_level="medium",
    entity_label_singular="item",
    entity_label_plural="items",
    default_plan_label="Generic AI plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Knowledge"),
        ("crawl", "Sources"),
        ("leads", "Leads"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("knowledge_item", "service", "article", "faq", "policy_page", "contact"),
    readiness_checks=("knowledge", "sources", "contact", "policies", "lead_capture"),
    action_types=(
        "SHOW_ENTITIES",
        "SORT_ENTITIES",
        "NAVIGATE_TO",
        "REQUEST_CALLBACK",
        "CAPTURE_LEAD",
        "HANDOFF_TO_HUMAN",
    ),
)
