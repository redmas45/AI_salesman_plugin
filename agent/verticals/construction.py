"""Construction and contracting vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="construction",
    label="Construction",
    risk_level="medium",
    entity_label_singular="service",
    entity_label_plural="services",
    default_plan_label="Construction plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Services"),
        ("leads", "Estimates"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("construction_service", "project", "service_area", "estimate_flow", "contractor", "warranty"),
    readiness_checks=("services", "projects", "estimate_flow", "contact", "service_area", "lead_capture"),
    action_types=(
        "SHOW_ENTITIES",
        "SORT_ENTITIES",
        "REQUEST_ESTIMATE",
        "REQUEST_SITE_VISIT",
        "OPEN_PROJECTS",
        "OPEN_SERVICES",
        "CAPTURE_LEAD",
    ),
)
