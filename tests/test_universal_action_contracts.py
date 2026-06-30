"""Universal action-contract rules shared by every website vertical."""

from __future__ import annotations

import pytest

from agent.adapter_discovery import ObservedElement, form_sequence_steps, form_submit_mode


RESULT_FORM_ACTIONS = [
    ("START_QUOTE", "Get quotes Age City Show quote results"),
    ("SEARCH_AVAILABILITY", "Search availability Destination Dates Show results"),
    ("CHECK_AVAILABILITY", "Check availability Date Time Show available options"),
    ("CHECK_DELIVERY_AVAILABILITY", "Check delivery availability Pincode Show available slots"),
    ("FILTER_ENTITIES", "Find services Category Location Show results"),
    ("FILTER_PRODUCTS", "Find products Category Budget Show results"),
    ("MATCH_JOBS", "Find matching jobs Role Skills Show results"),
    ("RUN_CALCULATOR", "Calculate EMI Budget Term Show calculator results"),
    ("RUN_AFFORDABILITY_CALCULATOR", "Affordability calculator Budget Income Show results"),
    ("SET_LOCATION", "Set location City Check availability"),
]

FINAL_OR_SENSITIVE_ACTIONS = [
    "ADD_TO_CART",
    "CHECKOUT",
    "CHECKOUT_HANDOFF",
    "START_APPLICATION",
    "START_BOOKING",
    "START_ENROLLMENT",
    "START_TICKET_PURCHASE",
    "REQUEST_APPOINTMENT",
    "REQUEST_CONSULTATION",
    "REQUEST_ESTIMATE",
    "REQUEST_SITE_VISIT",
    "REQUEST_TEST_DRIVE",
    "REQUEST_VIEWING",
    "CAPTURE_LEAD",
    "JOIN_WAITLIST",
    "BOOK_APPOINTMENT_REQUEST",
]


@pytest.mark.parametrize(("action_name", "label"), RESULT_FORM_ACTIONS)
def test_low_sensitivity_result_forms_submit_across_domains(action_name: str, label: str) -> None:
    form = _form(
        label=label,
        fields=(
            {"selector": "select[name='category']", "label": "Category", "type": "select"},
            {"selector": "input[name='city']", "label": "City", "type": "text"},
        ),
    )

    steps = form_sequence_steps(form, action_name)

    assert form_submit_mode(action_name, form) == "submit"
    assert steps[-1] == {"op": "submit", "selector": "button.primary-submit"}


@pytest.mark.parametrize(("action_name", "label"), RESULT_FORM_ACTIONS)
def test_sensitive_result_forms_stay_prepare_only_across_domains(action_name: str, label: str) -> None:
    form = _form(
        label=label,
        fields=(
            {"selector": "input[name='phone']", "label": "Phone", "type": "tel"},
            {"selector": "input[name='email']", "label": "Email", "type": "email"},
        ),
    )

    steps = form_sequence_steps(form, action_name)

    assert form_submit_mode(action_name, form) == "fill_only"
    assert all(step.get("op") != "submit" for step in steps)


@pytest.mark.parametrize("action_name", FINAL_OR_SENSITIVE_ACTIONS)
def test_final_or_lead_forms_stay_prepare_only_even_with_result_words(action_name: str) -> None:
    form = _form(
        label="Show results Continue Confirm Pay Apply Buy Book Now",
        fields=(
            {"selector": "input[name='city']", "label": "City", "type": "text"},
            {"selector": "select[name='category']", "label": "Category", "type": "select"},
        ),
    )

    steps = form_sequence_steps(form, action_name)

    assert form_submit_mode(action_name, form) == "fill_only"
    assert all(step.get("op") != "submit" for step in steps)


@pytest.mark.parametrize("final_term", ["apply", "book now", "checkout", "confirm", "pay", "purchase", "reserve"])
def test_finalization_words_block_result_form_submit(final_term: str) -> None:
    form = _form(label=f"Get quotes Age City Show results {final_term}")

    steps = form_sequence_steps(form, "START_QUOTE")

    assert form_submit_mode("START_QUOTE", form) == "fill_only"
    assert all(step.get("op") != "submit" for step in steps)


def _form(
    *,
    label: str,
    fields: tuple[dict[str, object], ...] = (
        {"selector": "select[name='age']", "label": "Age", "type": "select"},
        {"selector": "input[name='city']", "label": "City", "type": "text"},
    ),
) -> ObservedElement:
    return ObservedElement(
        label=label,
        selector="form.primary",
        input_selector=str(fields[0]["selector"]),
        submit_selector="button.primary-submit",
        fields=fields,
    )
