"""Automotive vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="automotive",
    label="Automotive",
    risk_level="medium",
    entity_label_singular="vehicle",
    entity_label_plural="vehicles",
    default_plan_label="Automotive plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Vehicles"),
        ("calculators", "Finance"),
        ("leads", "Test Drives"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("vehicle_listing", "vehicle_model", "trim", "dealer", "finance_offer", "test_drive_slot"),
    readiness_checks=("vehicles", "specs", "dealer_contact", "test_drive", "finance", "freshness"),
    action_types=("SHOW_ENTITIES", "COMPARE_ENTITIES", "REQUEST_TEST_DRIVE", "RUN_CALCULATOR", "CAPTURE_LEAD"),
)
