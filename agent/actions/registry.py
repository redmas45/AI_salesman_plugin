"""Typed registry for AI-to-website actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

ActionFamily = Literal["discovery", "navigation", "commerce", "lead", "tool", "session"]


@dataclass(frozen=True)
class ActionDefinition:
    """One structured action the assistant may emit."""

    name: str
    label: str
    family: ActionFamily
    requires_product_ids: bool = False
    requires_product_id: bool = False
    requires_cart: bool = False
    requires_checkout: bool = False
    open_params: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


_ACTIONS: tuple[ActionDefinition, ...] = (
    ActionDefinition("SHOW_PRODUCTS", "Show products", "discovery", requires_product_ids=True),
    ActionDefinition("SHOW_COMPARISON", "Compare products", "discovery", requires_product_ids=True),
    ActionDefinition("FILTER_PRODUCTS", "Filter products", "discovery"),
    ActionDefinition("NAVIGATE_TO", "Navigate", "navigation"),
    ActionDefinition("SORT_PRODUCTS", "Sort products", "discovery"),
    ActionDefinition("ADD_TO_CART", "Add to cart", "commerce", requires_product_id=True, requires_cart=True),
    ActionDefinition("REMOVE_FROM_CART", "Remove from cart", "commerce", requires_product_id=True, requires_cart=True),
    ActionDefinition("SHOW_PRODUCT_DETAIL", "Product detail", "discovery", requires_product_id=True),
    ActionDefinition("CLEAR_FILTERS", "Clear filters", "discovery"),
    ActionDefinition("CLEAR_CART", "Clear cart", "commerce", requires_cart=True),
    ActionDefinition("CHECKOUT", "Checkout", "commerce", requires_checkout=True),
    ActionDefinition("UPDATE_CART_QUANTITY", "Update quantity", "commerce", requires_product_id=True, requires_cart=True),
    ActionDefinition("CLEAR_HISTORY", "Clear history", "session"),
    ActionDefinition("UPDATE_PREFERENCES", "Update preferences", "session"),
    ActionDefinition("SHOW_ENTITIES", "Show entities", "discovery"),
    ActionDefinition("COMPARE_ENTITIES", "Compare entities", "discovery"),
    ActionDefinition("FILTER_ENTITIES", "Filter entities", "discovery"),
    ActionDefinition("SORT_ENTITIES", "Sort entities", "discovery"),
    ActionDefinition("OPEN_ENTITY_DETAIL", "Open detail", "navigation"),
    ActionDefinition("OPEN_POLICY", "Open policy", "navigation"),
    ActionDefinition("OPEN_MAP", "Open map", "navigation"),
    ActionDefinition("OPEN_CONTACT", "Open contact", "navigation"),
    ActionDefinition("START_QUOTE", "Start quote", "lead"),
    ActionDefinition("START_BOOKING", "Start booking", "lead"),
    ActionDefinition("START_APPLICATION", "Start application", "lead"),
    ActionDefinition("REQUEST_APPOINTMENT", "Request appointment", "lead"),
    ActionDefinition("REQUEST_TEST_DRIVE", "Request test drive", "lead"),
    ActionDefinition("REQUEST_VIEWING", "Request viewing", "lead"),
    ActionDefinition("CONTACT_AGENT", "Contact agent", "lead"),
    ActionDefinition("START_INTAKE", "Start intake", "lead"),
    ActionDefinition("REQUEST_CONSULTATION", "Request consultation", "lead"),
    ActionDefinition("REQUEST_ESTIMATE", "Request estimate", "lead"),
    ActionDefinition("REQUEST_SITE_VISIT", "Request site visit", "lead"),
    ActionDefinition("START_TICKET_PURCHASE", "Start ticket purchase", "lead"),
    ActionDefinition("START_ENROLLMENT", "Start enrollment", "lead"),
    ActionDefinition("CAPTURE_LEAD", "Capture lead", "lead"),
    ActionDefinition("CAPTURE_PATIENT_LEAD", "Capture patient lead", "lead"),
    ActionDefinition("REQUEST_CALLBACK", "Request callback", "lead"),
    ActionDefinition("HANDOFF_TO_HUMAN", "Human handoff", "lead"),
    ActionDefinition("HANDOFF_TO_AGENT", "Agent handoff", "lead"),
    ActionDefinition("HANDOFF_TO_LICENSED_AGENT", "Licensed agent handoff", "lead"),
    ActionDefinition("HANDOFF_TO_ADVISOR", "Advisor handoff", "lead"),
    ActionDefinition("HANDOFF_TO_CLINIC", "Clinic handoff", "lead"),
    ActionDefinition("HANDOFF_TO_LAWYER", "Lawyer handoff", "lead"),
    ActionDefinition("HANDOFF_TO_RECRUITER", "Recruiter handoff", "lead"),
    ActionDefinition("RUN_CALCULATOR", "Run calculator", "tool"),
    ActionDefinition("RUN_AFFORDABILITY_CALCULATOR", "Run affordability calculator", "tool"),
    ActionDefinition("RUN_DOM_SEQUENCE", "Run website operation sequence", "tool"),
    ActionDefinition("BUILD_ITINERARY", "Build itinerary", "tool"),
    ActionDefinition("BUILD_LEARNING_PATH", "Build learning path", "tool"),
    ActionDefinition("CHECK_AVAILABILITY", "Check availability", "tool"),
    ActionDefinition("SEARCH_AVAILABILITY", "Search availability", "tool"),
    ActionDefinition("CHECK_ELIGIBILITY_SOFT", "Soft eligibility check", "tool"),
    ActionDefinition("CHECK_APPOINTMENT_AVAILABILITY", "Check appointment availability", "tool"),
    ActionDefinition("CHECK_PREREQUISITES", "Check prerequisites", "tool"),
    ActionDefinition("SET_LOCATION", "Set location", "tool"),
    ActionDefinition("SCHEDULE_ORDER", "Schedule order", "commerce"),
    ActionDefinition("CHECKOUT_HANDOFF", "Checkout handoff", "commerce"),
    ActionDefinition("CHECK_DELIVERY_AVAILABILITY", "Check delivery availability", "tool"),
    ActionDefinition("JOIN_WAITLIST", "Join waitlist", "lead"),
    ActionDefinition("MATCH_JOBS", "Match jobs", "tool"),
    ActionDefinition("SAVE_SEARCH", "Save search", "session"),
    ActionDefinition("OPEN_CLAIM_FLOW", "Open claim flow", "navigation"),
    ActionDefinition("OPEN_RENEWAL_FLOW", "Open renewal flow", "navigation"),
    ActionDefinition("OPEN_DISCLOSURE", "Open disclosure", "navigation"),
    ActionDefinition("OPEN_PROJECTS", "Open projects", "navigation"),
    ActionDefinition("OPEN_SERVICES", "Open services", "navigation"),
    ActionDefinition("OPEN_SYLLABUS", "Open syllabus", "navigation"),
    ActionDefinition("OPEN_LOCATION", "Open location", "navigation"),
    ActionDefinition("OPEN_TELECONSULT", "Open teleconsult", "navigation"),
    ActionDefinition("SHOW_EMERGENCY_NOTICE", "Show emergency notice", "navigation"),
    ActionDefinition("BOOK_APPOINTMENT_REQUEST", "Book appointment request", "lead"),
    ActionDefinition("REQUEST_COUNSELOR_CALLBACK", "Counselor callback", "lead"),
)

_ACTION_BY_NAME = {action.name: action for action in _ACTIONS}


def normalize_action_name(value: str) -> str:
    return str(value or "").strip().upper()


def get_action(action_name: str) -> ActionDefinition | None:
    return _ACTION_BY_NAME.get(normalize_action_name(action_name))


def is_supported_action(action_name: str) -> bool:
    return get_action(action_name) is not None


def list_actions() -> list[ActionDefinition]:
    return list(_ACTIONS)


def list_action_names() -> set[str]:
    return set(_ACTION_BY_NAME)


def product_list_actions() -> set[str]:
    return {action.name for action in _ACTIONS if action.requires_product_ids}


def product_id_actions() -> set[str]:
    return {action.name for action in _ACTIONS if action.requires_product_id}
