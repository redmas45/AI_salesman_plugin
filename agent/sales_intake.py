"""Vertical-aware sales intake guidance for universal website assistants."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agent.verticals.registry import DEFAULT_VERTICAL_KEY, get_vertical

MAX_INTAKE_QUESTIONS = 6
MAX_INTAKE_FIELD_LENGTH = 240


@dataclass(frozen=True)
class IntakeQuestion:
    """One safe question the assistant can ask before starting a website flow."""

    key: str
    label: str
    question: str
    why: str
    actions: tuple[str, ...] = ()
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


INTAKE_QUESTIONS_BY_VERTICAL: dict[str, tuple[IntakeQuestion, ...]] = {
    "ecommerce": (
        IntakeQuestion("need", "Need", "What are you looking for, and who is it for?", "Narrows product discovery.", ("FILTER_PRODUCTS", "SHOW_PRODUCTS"), True),
        IntakeQuestion("budget", "Budget", "What budget range should I stay within?", "Filters unsuitable products.", ("FILTER_PRODUCTS",)),
        IntakeQuestion("preference", "Preferences", "Any brand, size, color, feature, or delivery preference?", "Avoids irrelevant suggestions.", ("FILTER_PRODUCTS", "SHOW_COMPARISON")),
        IntakeQuestion("decision", "Decision criteria", "What matters most: price, quality, speed, reviews, or availability?", "Ranks recommendations.", ("SHOW_COMPARISON",)),
    ),
    "insurance": (
        IntakeQuestion("coverage_need", "Coverage need", "What type of cover are you comparing, and who needs coverage?", "Determines plan category.", ("START_QUOTE", "COMPARE_ENTITIES"), True),
        IntakeQuestion("life_stage", "Life stage", "What broad age band and family situation should I consider?", "Supports safe, non-underwriting guidance.", ("START_QUOTE",)),
        IntakeQuestion("budget", "Premium budget", "What monthly or annual premium range feels comfortable?", "Filters plan options.", ("START_QUOTE", "COMPARE_ENTITIES")),
        IntakeQuestion("priorities", "Priorities", "Which matters more: lower premium, higher cover, claim support, renewability, or add-ons?", "Ranks plans without deciding eligibility.", ("COMPARE_ENTITIES",)),
        IntakeQuestion("handoff", "Advisor handoff", "Would you like a licensed advisor to review exact eligibility or documents?", "High-risk decisions need handoff.", ("HANDOFF_TO_LICENSED_AGENT", "HANDOFF_TO_AGENT")),
    ),
    "travel": (
        IntakeQuestion("destination", "Destination", "Where do you want to go, and from where?", "Starts destination or route search.", ("SEARCH_AVAILABILITY", "BUILD_ITINERARY"), True),
        IntakeQuestion("dates", "Dates", "What dates or date flexibility should I use?", "Controls availability and pricing.", ("SEARCH_AVAILABILITY", "START_BOOKING"), True),
        IntakeQuestion("travelers", "Travelers", "How many travelers are going, and are there children or seniors?", "Affects tickets, rooms, and policies.", ("SEARCH_AVAILABILITY",)),
        IntakeQuestion("style", "Trip style", "Do you prefer budget, comfort, premium, family, adventure, or relaxed options?", "Guides recommendations.", ("BUILD_ITINERARY",)),
        IntakeQuestion("constraints", "Constraints", "Any visa, accessibility, luggage, cancellation, or timing constraints?", "Prevents bad-fit bookings.", ("START_BOOKING",)),
    ),
    "finance_broker": (
        IntakeQuestion("goal", "Finance goal", "What are you trying to finance or compare?", "Selects product type.", ("START_APPLICATION", "RUN_CALCULATOR"), True),
        IntakeQuestion("amount", "Amount", "What loan or investment amount range should I use?", "Feeds calculators and filters.", ("RUN_CALCULATOR",)),
        IntakeQuestion("timeline", "Timeline", "How soon do you need this, and for how long?", "Matches terms and urgency.", ("START_APPLICATION",)),
        IntakeQuestion("risk", "Risk comfort", "Do you prefer lower monthly payment, faster payoff, lower risk, or flexibility?", "Avoids unsuitable options.", ("HANDOFF_TO_ADVISOR",)),
    ),
    "healthcare": (
        IntakeQuestion("care_need", "Care need", "What kind of care or specialist are you looking for?", "Routes to the right department.", ("REQUEST_APPOINTMENT", "SHOW_ENTITIES"), True),
        IntakeQuestion("urgency", "Urgency", "Is this routine, soon, urgent, or an emergency?", "Determines safe next step.", ("REQUEST_APPOINTMENT", "SHOW_EMERGENCY_NOTICE"), True),
        IntakeQuestion("location", "Location", "Which location, clinic, or appointment mode works for you?", "Filters providers and slots.", ("CHECK_APPOINTMENT_AVAILABILITY",)),
        IntakeQuestion("timing", "Timing", "What days or time windows work best?", "Supports scheduling.", ("REQUEST_APPOINTMENT",)),
    ),
    "food": (
        IntakeQuestion("location", "Delivery location", "Where should I check delivery, pickup, or table availability?", "Controls serviceability.", ("SET_LOCATION",), True),
        IntakeQuestion("meal", "Meal need", "What are you hungry for or planning to order?", "Narrows menu search.", ("SHOW_ENTITIES",)),
        IntakeQuestion("diet", "Diet", "Any diet, allergy, spice, cuisine, or portion preference?", "Avoids unsuitable items.", ("FILTER_ENTITIES",)),
        IntakeQuestion("time", "Timing", "Do you need it now, scheduled, pickup, delivery, or reservation?", "Selects the right flow.", ("SCHEDULE_ORDER", "CHECKOUT_HANDOFF")),
    ),
    "real_estate": (
        IntakeQuestion("intent", "Intent", "Are you looking to buy, rent, sell, or schedule a viewing?", "Routes the flow.", ("SHOW_ENTITIES", "REQUEST_VIEWING"), True),
        IntakeQuestion("location", "Location", "Which city, neighborhood, or commute area should I search?", "Filters listings.", ("SHOW_ENTITIES",), True),
        IntakeQuestion("budget", "Budget", "What budget range and property type should I use?", "Filters bad-fit listings.", ("SHOW_ENTITIES", "RUN_AFFORDABILITY_CALCULATOR")),
        IntakeQuestion("must_haves", "Must-haves", "How many bedrooms and which features are must-haves?", "Ranks listings.", ("COMPARE_ENTITIES",)),
    ),
    "education": (
        IntakeQuestion("goal", "Learning goal", "What skill, course, degree, or outcome are you aiming for?", "Finds relevant programs.", ("SHOW_ENTITIES", "BUILD_LEARNING_PATH"), True),
        IntakeQuestion("level", "Current level", "What is your current level or background?", "Avoids unsuitable programs.", ("CHECK_PREREQUISITES",)),
        IntakeQuestion("schedule", "Schedule", "Do you prefer self-paced, weekday, weekend, online, or classroom learning?", "Filters delivery formats.", ("START_ENROLLMENT",)),
        IntakeQuestion("budget", "Budget", "What budget or financing range should I consider?", "Filters options.", ("SHOW_ENTITIES",)),
    ),
    "automotive": (
        IntakeQuestion("vehicle_need", "Vehicle need", "What type of vehicle and use case are you shopping for?", "Narrows inventory.", ("SHOW_ENTITIES",), True),
        IntakeQuestion("budget", "Budget", "What purchase or monthly payment range should I use?", "Feeds finance filters.", ("RUN_CALCULATOR",)),
        IntakeQuestion("preferences", "Preferences", "Any brand, fuel type, body style, mileage, or feature must-haves?", "Improves matches.", ("SHOW_ENTITIES", "COMPARE_ENTITIES")),
        IntakeQuestion("visit", "Visit timing", "When would you like a test drive or dealer callback?", "Supports lead flow.", ("REQUEST_TEST_DRIVE", "CONTACT_AGENT")),
    ),
    "legal_services": (
        IntakeQuestion("matter", "Legal matter", "What type of legal matter or practice area do you need help with?", "Routes to the right service.", ("REQUEST_CONSULTATION", "START_INTAKE"), True),
        IntakeQuestion("jurisdiction", "Location", "Which city, state, or jurisdiction is involved?", "Legal services are location-sensitive.", ("START_INTAKE",)),
        IntakeQuestion("timeline", "Timeline", "Is there a deadline, hearing date, notice, or urgent timeline?", "Determines urgency.", ("REQUEST_CONSULTATION",)),
        IntakeQuestion("handoff", "Lawyer handoff", "Would you like the firm to review details directly?", "Avoids legal conclusions in chat.", ("HANDOFF_TO_LAWYER",)),
    ),
    "jobs_recruiting": (
        IntakeQuestion("role", "Target role", "What role, skill area, or job title are you targeting?", "Matches jobs.", ("MATCH_JOBS",), True),
        IntakeQuestion("location", "Location", "Which location or remote preference should I use?", "Filters jobs.", ("MATCH_JOBS",)),
        IntakeQuestion("experience", "Experience", "What experience level and key skills should I match?", "Improves fit.", ("MATCH_JOBS",)),
        IntakeQuestion("availability", "Availability", "When can you start, and do you prefer full-time, part-time, contract, or internship?", "Supports application flow.", ("START_APPLICATION",)),
    ),
    "events_ticketing": (
        IntakeQuestion("event", "Event interest", "What event, artist, team, venue, or date are you interested in?", "Finds events.", ("SHOW_ENTITIES", "CHECK_AVAILABILITY"), True),
        IntakeQuestion("party", "Party size", "How many tickets do you need?", "Controls availability.", ("CHECK_AVAILABILITY",)),
        IntakeQuestion("budget", "Budget", "What budget range per ticket should I use?", "Filters options.", ("SHOW_ENTITIES",)),
        IntakeQuestion("seat", "Seat preference", "Any seating, accessibility, or timing preference?", "Prevents bad-fit purchases.", ("START_TICKET_PURCHASE",)),
    ),
    "construction": (
        IntakeQuestion("project", "Project scope", "What construction, renovation, repair, or remodeling work do you need?", "Routes to services.", ("REQUEST_ESTIMATE", "OPEN_SERVICES"), True),
        IntakeQuestion("property", "Property details", "What type of property and approximate project size should I consider?", "Improves estimate context.", ("REQUEST_ESTIMATE",)),
        IntakeQuestion("location", "Location", "Where is the project or service area?", "Checks serviceability.", ("REQUEST_SITE_VISIT",), True),
        IntakeQuestion("timeline", "Timeline", "When do you want the work assessed or started?", "Supports site visit flow.", ("REQUEST_SITE_VISIT",)),
        IntakeQuestion("budget", "Budget", "Do you have a rough budget range or priority tradeoff?", "Helps qualify options.", ("REQUEST_ESTIMATE",)),
    ),
    DEFAULT_VERTICAL_KEY: (
        IntakeQuestion("goal", "Goal", "What are you trying to compare, choose, book, or request?", "Identifies intent.", ("SHOW_ENTITIES", "CAPTURE_LEAD"), True),
        IntakeQuestion("constraints", "Constraints", "What budget, timing, location, or preference should I consider?", "Narrows recommendations.", ("SHOW_ENTITIES",)),
        IntakeQuestion("next_step", "Next step", "Would you like information, a comparison, contact, or help starting the website flow?", "Selects the safest action.", ("CAPTURE_LEAD", "OPEN_CONTACT")),
    ),
}


def intake_questions_for(vertical_key: str | None, *, limit: int = MAX_INTAKE_QUESTIONS) -> list[dict[str, Any]]:
    """Return JSON-ready intake questions for a vertical."""
    safe_limit = max(1, min(int(limit or MAX_INTAKE_QUESTIONS), MAX_INTAKE_QUESTIONS))
    vertical = _safe_vertical_key(vertical_key)
    questions = INTAKE_QUESTIONS_BY_VERTICAL.get(vertical) or INTAKE_QUESTIONS_BY_VERTICAL[DEFAULT_VERTICAL_KEY]
    return [question.to_dict() for question in questions[:safe_limit]]


def sanitize_intake_questions(value: Any, *, limit: int = MAX_INTAKE_QUESTIONS) -> list[dict[str, Any]]:
    """Validate intake questions before storing or exposing runtime config."""
    if not isinstance(value, list):
        return []
    rows = [_sanitize_intake_question(item) for item in value[:limit] if isinstance(item, dict)]
    return [row for row in rows if row]


def sales_intake_prompt_context(vertical_key: str | None) -> str:
    """Build compact prompt instructions for pre-action sales discovery."""
    vertical = get_vertical(_safe_vertical_key(vertical_key))
    questions = intake_questions_for(vertical.key)
    lines = [
        "## Sales Intake Plan",
        f"Use these {vertical.label} intake questions to qualify the user's need before starting quote, booking, checkout, application, appointment, or lead-capture actions.",
        "Before asking a question, extract and reuse facts from the current user message, conversation history, session profile, and live page context.",
        "Do not ask for a value the user already gave. Ask only the exact missing field needed for the next supported website action.",
        "Ask one missing question at a time. Do not ask for passwords, OTPs, card numbers, full medical records, or sensitive documents in chat.",
    ]
    if vertical.risk_level == "high":
        lines.append("For this high-risk vertical, explain that final advice, eligibility, approval, diagnosis, or legal conclusions require the appropriate human/professional handoff.")
    lines.extend(_question_line(question) for question in questions)
    return "\n".join(lines)


def _safe_vertical_key(vertical_key: str | None) -> str:
    try:
        return get_vertical(vertical_key).key
    except ValueError:
        return DEFAULT_VERTICAL_KEY


def _question_line(question: dict[str, Any]) -> str:
    marker = "required" if question.get("required") else "optional"
    actions = ", ".join(question.get("actions") or [])
    action_text = f" Actions: {actions}." if actions else ""
    return f"- {question['label']} ({marker}): {question['question']} Why: {question['why']}.{action_text}"


def _sanitize_intake_question(value: dict[str, Any]) -> dict[str, Any]:
    key = _clean_text(value.get("key"), 80)
    question = _clean_text(value.get("question"), MAX_INTAKE_FIELD_LENGTH)
    if not key or not question:
        return {}
    return {
        "key": key,
        "label": _clean_text(value.get("label"), 120) or key.replace("_", " ").title(),
        "question": question,
        "why": _clean_text(value.get("why"), MAX_INTAKE_FIELD_LENGTH),
        "actions": _clean_text_list(value.get("actions"), 12),
        "required": bool(value.get("required") is True),
    }


def _clean_text(value: Any, limit: int) -> str:
    return str(value or "").replace("\x00", "").replace("\n", " ").strip()[:limit]


def _clean_text_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_clean_text(item, 80) for item in value[:limit] if _clean_text(item, 80)]
