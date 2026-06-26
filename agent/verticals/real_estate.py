"""Real estate vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="real_estate",
    label="Real Estate",
    risk_level="medium",
    entity_label_singular="listing",
    entity_label_plural="listings",
    default_plan_label="Real estate plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Listings"),
        ("leads", "Viewings/Leads"),
        ("compliance", "Compliance"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("property_listing", "development_project", "agent", "locality", "amenity"),
    readiness_checks=("listings", "location", "lead_flow", "maps", "freshness", "compliance"),
    action_types=("SHOW_ENTITIES", "COMPARE_ENTITIES", "REQUEST_VIEWING", "CONTACT_AGENT", "CAPTURE_LEAD"),
)
