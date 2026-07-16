"""Workflow dependency factories for the db.clients compatibility facade."""

from __future__ import annotations

import os
from typing import Any


def lifecycle_workflows(runtime: Any) -> Any:
    return runtime.client_lifecycle.ClientLifecycleWorkflows(
        ensure_default_client_on_startup=runtime.config.ENSURE_DEFAULT_CLIENT_ON_STARTUP,
        current_site_id=runtime.config.CURRENT_SITE_ID,
        default_site_id=runtime.config.DEFAULT_SITE_ID,
        current_url=runtime.config.CURRENT_URL,
        public_api_url=runtime.config.PUBLIC_API_URL,
        deployment_mode=os.getenv("DEPLOYMENT_MODE", runtime.DEFAULT_DEPLOY_MODE),
        default_deploy_mode=runtime.DEFAULT_DEPLOY_MODE,
        default_locale=runtime.DEFAULT_CLIENT_LOCALE,
        default_compliance_mode=runtime.DEFAULT_CLIENT_COMPLIANCE_MODE,
        live_status=runtime.CLIENT_STATUS_LIVE,
        available_status=runtime.CLIENT_STATUS_AVAILABLE,
        deleted_status=runtime.CLIENT_STATUS_DELETED,
        safe_site_id=runtime._safe_site_id,
        first_text=runtime._first_text,
        origin_from_url=runtime._origin_from_url,
        site_id_from_name=runtime._site_id_from_name,
        validated_url=runtime._validated_url,
        required_text=runtime._required_text,
        validated_vertical=runtime._validated_vertical,
        plan_for_vertical=runtime._plan_for_vertical,
        default_client_vertical_key=runtime._default_client_vertical_key,
        default_client_adapter_name=runtime._default_client_adapter_name,
        default_client_name=runtime._default_client_name,
        default_panel_password_hash=runtime._default_panel_password_hash,
        client_upsert_params=runtime._client_upsert_params,
        available_client_upsert_params=runtime._available_client_upsert_params,
        init_admin_schema=runtime.init_admin_schema,
        init_tenant_schema=runtime.init_tenant_schema,
        connect=runtime._connect,
        get_client_detail=runtime.get_client_detail,
        active_client_upsert_sql=runtime.ACTIVE_CLIENT_UPSERT_SQL,
        available_client_upsert_sql=runtime.AVAILABLE_CLIENT_UPSERT_SQL,
        default_client_upsert_sql=runtime.DEFAULT_CLIENT_UPSERT_SQL,
    )


def roster_workflows(runtime: Any) -> Any:
    from db.runtime.quota import _usage_summary, quota_status

    return runtime.client_roster.ClientRosterWorkflows(
        safe_site_id=runtime._safe_site_id,
        visible_client_rows=runtime._visible_client_rows,
        client_vertical=runtime._client_vertical,
        risk_level_text=runtime._risk_level_text,
        json_object=runtime._json_object,
        script_tag_for_site=runtime.script_tag_for_site,
        runtime_status=runtime._runtime_status,
        runtime_status_source_urls=runtime._runtime_status_source_urls,
        safe_catalog_summary=runtime._safe_catalog_summary,
        safe_catalog_preview=runtime._safe_catalog_preview,
        safe_sync_history=runtime._safe_sync_history,
        safe_answer_cache_summary=runtime._safe_answer_cache_summary,
        usage_summary=_usage_summary,
        quota_status=quota_status,
        panel_password_configured=runtime._panel_password_configured,
        panel_password_status=runtime._panel_password_status,
        ensure_default_client=runtime.ensure_default_client,
        init_admin_schema=runtime.init_admin_schema,
        connect=runtime._connect,
        deleted_status=runtime.CLIENT_STATUS_DELETED,
        live_status=runtime.CLIENT_STATUS_LIVE,
        disabled_status=runtime.CLIENT_STATUS_DISABLED,
        available_status=runtime.CLIENT_STATUS_AVAILABLE,
    )


def config_store(runtime: Any) -> Any:
    return runtime.client_config_store.ClientConfigStore(
        safe_site_id=runtime._safe_site_id,
        json_object=runtime._json_object,
        client_row=runtime._client_row,
        init_admin_schema=runtime.init_admin_schema,
        connect=runtime._connect,
        deleted_status=runtime.CLIENT_STATUS_DELETED,
    )


def vertical_update_workflows(runtime: Any) -> Any:
    return runtime.client_vertical_workflows.ClientVerticalUpdateWorkflows(
        safe_site_id=runtime._safe_site_id,
        validated_vertical=runtime._validated_vertical,
        init_schema=runtime.init_admin_schema,
        connect=runtime._connect,
        record_audit_event_safely=runtime._record_audit_event_safely,
        get_client_detail=runtime.get_client_detail,
        deleted_status=runtime.CLIENT_STATUS_DELETED,
    )


def runtime_workflows(runtime: Any) -> Any:
    return runtime.client_runtime_workflows.ClientRuntimeWorkflows(
        safe_site_id=runtime._safe_site_id,
        safe_action_text=runtime._safe_action_text,
        required_text=runtime._required_text,
        validated_vertical=runtime._validated_vertical,
        client_vertical=runtime._client_vertical,
        json_object=runtime._json_object,
        client_row=runtime._client_row,
        client_vertical_config=runtime._client_vertical_config,
        write_client_vertical_config=runtime._write_client_vertical_config,
        get_client_detail=runtime.get_client_detail,
        get_client_vertical_key=runtime.get_client_vertical_key,
        merge_discovery_vertical_config=runtime._merge_discovery_vertical_config,
        validated_action_map=runtime._validated_action_map,
        validated_adapter_validation=runtime._validated_adapter_validation,
        action_candidate_review=runtime._action_candidate_review,
        approve_action_candidate=runtime._approve_action_candidate,
        action_proposal_review=runtime._action_proposal_review,
        approve_action_proposal=runtime._approve_action_proposal,
        flow_repair_review=runtime._flow_repair_review,
        approve_flow_repair_proposal=runtime._approve_flow_repair_proposal,
        merge_action_reviews=runtime._merge_action_reviews,
        apply_validation_repairs=runtime._apply_validation_repairs,
        refresh_action_health=runtime._refresh_action_health,
        refresh_flow_repair_proposals=runtime._refresh_flow_repair_proposals,
        list_client_action_events=runtime.list_client_action_events,
        record_audit_event_safely=runtime._record_audit_event_safely,
        init_admin_schema=runtime.init_admin_schema,
        connect=runtime._connect,
        deleted_status=runtime.CLIENT_STATUS_DELETED,
        action_health_event_window=runtime.ACTION_HEALTH_EVENT_WINDOW,
    )


def report_persistence(runtime: Any) -> Any:
    return runtime.client_report_persistence.ClientReportPersistence(
        safe_site_id=runtime._safe_site_id,
        safe_action_text=runtime._safe_action_text,
        client_vertical_config=runtime._client_vertical_config,
        write_client_vertical_config=runtime._write_client_vertical_config,
        get_client_detail=runtime.get_client_detail,
        record_audit_event_safely=runtime._record_audit_event_safely,
        init_admin_schema=runtime.init_admin_schema,
        connect=runtime._connect,
        deleted_status=runtime.CLIENT_STATUS_DELETED,
        crawl_status_error=runtime.CRAWL_STATUS_ERROR,
        utc_timestamp=runtime._utc_timestamp,
        json_object=runtime._json_object,
        dict_config=runtime._dict_config,
        safe_route_map=runtime._safe_route_map,
        safe_flow_list=runtime._safe_flow_list,
        validated_action_map=runtime._validated_action_map,
        validated_assistant_smoke_report=runtime._validated_assistant_smoke_report,
        validated_barrier_report=runtime._validated_barrier_report,
        validated_flow_report=runtime._validated_flow_report,
        validated_regression_report=runtime._validated_regression_report,
        validated_rehearsal_report=runtime._validated_rehearsal_report,
        merged_initialization_report=runtime._merged_initialization_report,
        setup_cancel_requested=runtime._setup_cancel_requested,
        setup_cancel_update=runtime._setup_cancel_update,
        expired_initialization_update=runtime._expired_initialization_update,
        refresh_flow_repair_proposals=runtime._refresh_flow_repair_proposals,
    )


def event_persistence(runtime: Any) -> Any:
    return runtime.client_event_persistence.ClientEventPersistence(
        safe_site_id=runtime._safe_site_id,
        client_vertical_config=runtime._client_vertical_config,
        write_client_vertical_config=runtime._write_client_vertical_config,
        get_client_detail=runtime.get_client_detail,
        get_client_vertical_key=runtime.get_client_vertical_key,
        validated_policy_event=runtime._validated_policy_event,
        validated_action_event=runtime._validated_action_event,
        validated_interaction_event=runtime._validated_interaction_event,
        enrich_interaction_event=runtime.enrich_interaction_event,
        action_config_from_interaction=runtime.action_config_from_interaction,
        safe_flow_list=runtime._safe_flow_list,
        merge_interaction_candidate=runtime._merge_interaction_candidate,
        merge_learned_action=runtime._merge_learned_action,
        insert_client_action_event=runtime._insert_client_action_event,
        list_client_action_events=runtime.list_client_action_events,
        record_audit_event=runtime.record_audit_event,
        refresh_action_health=runtime._refresh_action_health,
        terminal_statuses=runtime.ACTION_EVENT_TERMINAL_STATUSES,
        action_health_event_window=runtime.ACTION_HEALTH_EVENT_WINDOW,
    )


def panel_password_workflows(runtime: Any) -> Any:
    return runtime.client_panel_password_workflows.ClientPanelPasswordWorkflows(
        safe_site_id=runtime._safe_site_id,
        client_row=runtime._client_row,
        set_default_panel_password=runtime._set_default_panel_password,
        verify_panel_password=runtime._verify_panel_password,
        hash_panel_password=runtime._hash_panel_password,
        get_client_detail=runtime.get_client_detail,
        init_schema=runtime.init_admin_schema,
        connect=runtime._connect,
        record_audit_event_safely=runtime._record_audit_event_safely,
        deleted_status=runtime.CLIENT_STATUS_DELETED,
    )
