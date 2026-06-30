"""Education vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="education",
    label="Education",
    risk_level="low",
    entity_label_singular="course",
    entity_label_plural="courses",
    default_plan_label="Education plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Courses"),
        ("leads", "Leads"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("course", "program", "certificate", "instructor", "learning_path", "cohort"),
    readiness_checks=("courses", "syllabus", "pricing", "enrollment", "lead_capture", "policies"),
    action_types=(
        "SHOW_ENTITIES",
        "SORT_ENTITIES",
        "BUILD_LEARNING_PATH",
        "CHECK_PREREQUISITES",
        "START_ENROLLMENT",
        "REQUEST_COUNSELOR_CALLBACK",
        "CAPTURE_LEAD",
    ),
)
