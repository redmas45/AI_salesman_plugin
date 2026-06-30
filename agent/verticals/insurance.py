"""Insurance vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="insurance",
    label="Insurance",
    risk_level="high",
    entity_label_singular="plan",
    entity_label_plural="plans",
    default_plan_label="Insurance plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Plans"),
        ("quote_flows", "Quotes"),
        ("leads", "Leads"),
        ("compliance", "Compliance"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("insurance_plan", "insurer", "coverage_feature", "claim_flow", "document_requirement"),
    readiness_checks=("plans", "quote_flow", "claims", "renewals", "disclosures", "lead_capture"),
    action_types=(
        "SHOW_ENTITIES",
        "COMPARE_ENTITIES",
        "SORT_ENTITIES",
        "START_QUOTE",
        "REQUEST_CALLBACK",
        "CAPTURE_LEAD",
        "HANDOFF_TO_AGENT",
        "HANDOFF_TO_LICENSED_AGENT",
    ),
)
