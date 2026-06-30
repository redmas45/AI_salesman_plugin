"""Jobs and recruiting vertical definition."""

from agent.verticals.base import VerticalDefinition, tabs

VERTICAL = VerticalDefinition(
    key="jobs_recruiting",
    label="Jobs & Recruiting",
    risk_level="high",
    entity_label_singular="job",
    entity_label_plural="jobs",
    default_plan_label="Recruiting plan",
    crm_tabs=tabs(
        ("overview", "Overview"),
        ("readiness", "Readiness"),
        ("catalog", "Jobs"),
        ("leads", "Candidates"),
        ("compliance", "Compliance"),
        ("activity", "Conversations"),
        ("prompt", "Prompt"),
        ("controls", "Controls"),
    ),
    entity_types=("job_posting", "company", "role_family", "skill", "application_flow", "recruiter"),
    readiness_checks=("jobs", "application_flow", "resume_upload", "company_pages", "privacy", "decisioning_guard"),
    action_types=("SHOW_ENTITIES", "SORT_ENTITIES", "MATCH_JOBS", "START_APPLICATION", "CAPTURE_LEAD", "HANDOFF_TO_RECRUITER"),
)
