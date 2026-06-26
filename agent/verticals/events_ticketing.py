"""Events and ticketing vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="events_ticketing",
    label="Events & Ticketing",
    risk_level="low",
    entity_label_singular="event",
    entity_label_plural="events",
    default_plan_label="Events plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Events"),
        ("bookings", "Ticketing"),
        ("leads", "Waitlists/Leads"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("event", "venue", "performer", "ticket_type", "showtime", "organizer"),
    readiness_checks=("events", "date_location", "ticket_handoff", "venue_maps", "policies", "organizer_contact"),
    action_types=("SHOW_ENTITIES", "CHECK_AVAILABILITY", "START_TICKET_PURCHASE", "JOIN_WAITLIST", "CAPTURE_LEAD"),
)
