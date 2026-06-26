"""Travel vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="travel",
    label="Travel",
    risk_level="medium",
    entity_label_singular="travel item",
    entity_label_plural="travel items",
    default_plan_label="Travel plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Inventory"),
        ("bookings", "Bookings"),
        ("leads", "Leads"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("destination", "hotel", "room", "flight", "package", "activity", "itinerary"),
    readiness_checks=("inventory", "availability", "booking_handoff", "policies", "lead_capture"),
    action_types=("SHOW_ENTITIES", "SEARCH_AVAILABILITY", "BUILD_ITINERARY", "START_BOOKING", "CAPTURE_LEAD"),
)
