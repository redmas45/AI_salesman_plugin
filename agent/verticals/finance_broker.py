"""Finance broker vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="finance_broker",
    label="Finance Broker",
    risk_level="high",
    entity_label_singular="financial product",
    entity_label_plural="financial products",
    default_plan_label="Finance broker plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Products"),
        ("calculators", "Calculators"),
        ("leads", "Leads"),
        ("compliance", "Compliance"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("financial_product", "loan_product", "rate_table", "calculator", "disclosure", "advisor"),
    readiness_checks=("products", "rates", "calculators", "disclosures", "application_flow", "lead_capture"),
    action_types=(
        "SHOW_ENTITIES",
        "COMPARE_ENTITIES",
        "SORT_ENTITIES",
        "RUN_CALCULATOR",
        "RUN_AFFORDABILITY_CALCULATOR",
        "START_APPLICATION",
        "CAPTURE_LEAD",
        "HANDOFF_TO_ADVISOR",
    ),
)
