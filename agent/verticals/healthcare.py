"""Healthcare vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="healthcare",
    label="Healthcare",
    risk_level="high",
    entity_label_singular="provider",
    entity_label_plural="providers",
    default_plan_label="Healthcare plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Providers"),
        ("appointments", "Appointments"),
        ("leads", "Leads"),
        ("compliance", "Compliance"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("doctor", "clinic", "specialty", "service_line", "lab_test", "health_article"),
    readiness_checks=("providers", "specialties", "appointments", "locations", "privacy", "emergency_notice"),
    action_types=(
        "SHOW_ENTITIES",
        "SORT_ENTITIES",
        "CHECK_APPOINTMENT_AVAILABILITY",
        "REQUEST_APPOINTMENT",
        "CAPTURE_LEAD",
        "HANDOFF_TO_CLINIC",
    ),
)
