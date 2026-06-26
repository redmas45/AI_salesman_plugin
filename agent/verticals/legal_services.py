"""Legal and professional services vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="legal_services",
    label="Legal Services",
    risk_level="high",
    entity_label_singular="service",
    entity_label_plural="services",
    default_plan_label="Legal services plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Services"),
        ("documents", "Documents"),
        ("leads", "Intake/Leads"),
        ("compliance", "Compliance"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("legal_service", "lawyer", "practice_area", "document_template", "jurisdiction"),
    readiness_checks=("services", "attorneys", "jurisdictions", "consultation", "disclaimers", "pricing"),
    action_types=("SHOW_ENTITIES", "START_INTAKE", "REQUEST_CONSULTATION", "CAPTURE_LEAD", "HANDOFF_TO_LAWYER"),
)
