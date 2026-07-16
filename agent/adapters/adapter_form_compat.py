"""Form-contract compatibility exports for adapter discovery."""

from __future__ import annotations

from typing import Any

from agent.adapters import adapter_form_contracts


def exports() -> dict[str, Any]:
    return {
        "form_sequence_steps": adapter_form_contracts.form_sequence_steps,
        "should_skip_duplicate_checkable_step": adapter_form_contracts.should_skip_duplicate_checkable_step,
        "should_generate_sequence_action": adapter_form_contracts.should_generate_sequence_action,
        "form_field_step": adapter_form_contracts.form_field_step,
        "field_param_name": adapter_form_contracts.field_param_name,
        "field_param_source": adapter_form_contracts.field_param_source,
        "field_is_checkable": adapter_form_contracts.field_is_checkable,
        "looks_like_example_placeholder": adapter_form_contracts.looks_like_example_placeholder,
        "form_action_field_config": adapter_form_contracts.form_action_field_config,
        "field_param_names": adapter_form_contracts.field_param_names,
        "required_field_params": adapter_form_contracts.required_field_params,
        "action_required_field_params": adapter_form_contracts.action_required_field_params,
        "form_field_schema": adapter_form_contracts.form_field_schema,
        "merged_field_schema": adapter_form_contracts.merged_field_schema,
        "merge_field_schema_item": adapter_form_contracts.merge_field_schema_item,
        "merged_field_options": adapter_form_contracts.merged_field_options,
        "form_field_schema_item": adapter_form_contracts.form_field_schema_item,
        "field_required": adapter_form_contracts.field_required,
        "form_submit_mode": adapter_form_contracts.form_submit_mode,
        "safe_result_form_submit": adapter_form_contracts.safe_result_form_submit,
        "form_is_rejected_for_action": adapter_form_contracts.form_is_rejected_for_action,
        "form_requires_prepare_only": adapter_form_contracts.form_requires_prepare_only,
        "form_has_sensitive_fields": adapter_form_contracts.form_has_sensitive_fields,
        "form_has_credential_fields": adapter_form_contracts.form_has_credential_fields,
        "field_has_sensitive_term": adapter_form_contracts.field_has_sensitive_term,
        "normalized_form_text": adapter_form_contracts.normalized_form_text,
        "contains_any_term": adapter_form_contracts.contains_any_term,
        "normalized_text": adapter_form_contracts.normalized_text,
    }
