"""Compatibility exports consumed by the db.clients facade."""

from __future__ import annotations

from db.client_domain.actions.client_action_configs import (
    ADAPTER_ACTION_TYPES,
    ADAPTER_FORM_SUBMIT_MODES,
    ADAPTER_SEQUENCE_OPERATIONS,
    MAX_ADAPTER_SEQUENCE_STEPS,
    repair_config as _repair_config,
    safe_wait_ms as _safe_wait_ms,
    validated_action_config as _validated_action_config,
    validated_action_map as _validated_action_map,
    validated_action_evidence as _validated_action_evidence,
    validated_adapter_sequence as _validated_adapter_sequence,
    validated_adapter_sequence_step as _validated_adapter_sequence_step,
    validated_adapter_validation as _validated_adapter_validation,
    validated_field_option as _validated_field_option,
    validated_field_options as _validated_field_options,
    validated_field_schema as _validated_field_schema,
    validated_field_schema_item as _validated_field_schema_item,
    validation_summary as _validation_summary,
)
from db.client_domain.dashboard.client_dashboard import (
    category_count as _category_count,
    empty_catalog_summary as _empty_catalog_summary,
    health_snapshot as _health_snapshot,
    latest_sync as _latest_sync,
    postgres_health as _postgres_health,
    recent_usage_events as _recent_usage_events,
    safe_answer_cache_summary as _safe_answer_cache_summary,
    safe_catalog_preview as _safe_catalog_preview,
    safe_catalog_summary as _safe_catalog_summary,
    safe_sync_history as _safe_sync_history,
)
from db.client_domain.runtime.client_discovery_config import (
    DISCOVERY_DIRECT_KEYS,
    DISCOVERY_PRESERVED_KEYS,
    action_auto_approve_confidence as _action_auto_approve_confidence,
    action_candidate_key as _action_candidate_key,
    action_candidate_review as _action_candidate_review,
    action_config_from_candidate as _action_config_from_candidate,
    action_proposal_key as _action_proposal_key,
    action_proposal_review as _action_proposal_review,
    approve_action_candidate as _approve_action_candidate,
    approve_action_proposal as _approve_action_proposal,
    approve_flow_repair_proposal as _approve_flow_repair_proposal,
    barrier_severity_count as _barrier_severity_count,
    barrier_summary as _barrier_summary,
    existing_candidate_config as _existing_candidate_config,
    flow_repair_proposal_key as _flow_repair_proposal_key,
    flow_repair_review as _flow_repair_review,
    merge_action_reviews as _merge_action_reviews,
    merge_discovery_actions as _merge_discovery_actions,
    merge_discovery_barriers as _merge_discovery_barriers,
    merge_discovery_rows as _merge_discovery_rows,
    merge_discovery_texts as _merge_discovery_texts,
    merge_discovery_vertical_config as _merge_discovery_vertical_config,
    merge_intake_questions as _merge_intake_questions,
    safe_candidate_path as _safe_candidate_path,
    validated_flow_repair_patch as _validated_flow_repair_patch,
)
from db.client_domain.events.client_events import (
    safe_action_status as _safe_action_status,
    validated_action_event as _validated_action_event,
    validated_interaction_event as _validated_interaction_event,
    validated_interaction_fields as _validated_interaction_fields,
    validated_interaction_form as _validated_interaction_form,
    validated_policy_event as _validated_policy_event,
)
from db.client_domain.events.client_event_store import (
    insert_client_action_event as _insert_client_action_event,
    list_client_action_events,
    record_audit_event,
    record_audit_event_safely as _record_audit_event_safely,
)
from db.client_domain.core.client_identity import (
    origin_from_url as _origin_from_url,
    required_text as _required_text,
    safe_session_id as _safe_session_id,
    safe_site_id as _safe_site_id,
    site_id_from_name as _site_id_from_name,
    validated_url as _validated_url,
)
from db.client_domain.lifecycle.client_listing import (
    auto_client_origin_key as _auto_client_origin_key,
    auto_client_sort_key as _auto_client_sort_key,
    canonical_origin_key as _canonical_origin_key,
    client_origin_key as _client_origin_key,
    visible_client_rows as _visible_client_rows,
)
from db.client_domain.panel.client_passwords import (
    GENERATED_PANEL_PASSWORD_BYTES,
    MIN_CLIENT_PANEL_PASSWORD_LENGTH,
    PANEL_PASSWORD_DISABLED,
    PANEL_PASSWORD_ITERATIONS,
    PANEL_PASSWORD_SALT_BYTES,
    b64 as _password_b64,
    unb64 as _password_unb64,
)
from db.client_domain.reports.client_reports import (
    validated_assistant_smoke_report as _validated_assistant_smoke_report,
    validated_barrier_report as _validated_barrier_report,
    validated_flow_report as _validated_flow_report,
    validated_regression_report as _validated_regression_report,
    validated_rehearsal_report as _validated_rehearsal_report,
)
from db.client_domain.runtime.client_runtime_config import (
    apply_validation_repairs as _apply_validation_repairs_impl,
    merge_interaction_candidate as _merge_interaction_candidate,
    merge_learned_action as _merge_learned_action,
    refresh_flow_repair_proposals as _refresh_flow_repair_proposals_impl,
    should_apply_repair as _should_apply_repair,
)
from db.client_domain.runtime.client_runtime_status import (
    RUNTIME_STATUS_CACHE_SECONDS,
    RUNTIME_STATUS_OFFLINE,
    RUNTIME_STATUS_ONLINE,
    RUNTIME_STATUS_TIMEOUT_SECONDS,
    RUNTIME_STATUS_UNKNOWN,
    probe_runtime_status as _probe_runtime_status,
    runtime_status as _runtime_status,
    runtime_status_candidates as _runtime_status_candidates,
    runtime_status_source_urls as _runtime_status_source_urls,
    runtime_status_url as _runtime_status_url,
    runtime_status_urls as _runtime_status_urls,
)
from db.client_domain.core.client_serialization import (
    dict_config as _dict_config,
    json_object as _json_object,
    safe_action_page_path as _safe_action_page_path,
    safe_action_stage as _safe_action_stage,
    safe_action_text as _safe_action_text,
    safe_confidence as _safe_confidence,
    safe_duration_ms as _safe_duration_ms,
    safe_flow_list as _safe_flow_list,
    safe_int as _safe_int,
    safe_json_value as _safe_json_value,
    safe_route_map as _safe_route_map,
    safe_text_list as _safe_text_list,
)
from db.client_domain.reports.client_setup_runs import (
    expired_initialization_update as _expired_initialization_update,
    merged_initialization_report as _merged_initialization_report,
    setup_cancel_requested as _setup_cancel_requested,
    setup_cancel_update as _setup_cancel_update,
)

__all__ = [name for name in globals() if not name.startswith("__")]
