"""Multi-domain website discovery fixtures for universal adapter onboarding."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from agent.adapter_discovery import build_discovery


DOMAIN_CASES = [
    (
        "fashion_store",
        "ecommerce",
        "NOVA Fashion store with clothing, apparel, size guide, cart, checkout, sale, and product catalog.",
        "Add to bag",
        "button.add-bag",
        [("Shop", "/collections/all"), ("Sale", "/sale"), ("Cart", "/cart")],
        {"ADD_TO_CART", "FILTER_PRODUCTS"},
    ),
    (
        "travel_tours",
        "travel",
        "Dubai things to do, tours, attraction tickets, activities, destination booking, and availability.",
        "Book Now",
        "button.book-now",
        [("Things To Do", "/things-to-do"), ("Tickets", "/tickets"), ("Destinations", "/destinations")],
        {"START_BOOKING", "SEARCH_AVAILABILITY"},
    ),
    (
        "policy_site",
        "insurance",
        "Health insurance policy coverage, premium quote, claim support, renewal, riders, and plans.",
        "Get Quote",
        "button.get-quote",
        [("Claims", "/claims"), ("Renewal", "/renewal"), ("Plans", "/plans")],
        {"START_QUOTE", "OPEN_CLAIM_FLOW"},
    ),
    (
        "finance_broker",
        "finance_broker",
        "Mortgage broker, loan rates, EMI calculator, eligibility, finance products, and application support.",
        "Apply Now",
        "button.apply",
        [("Loans", "/loans"), ("Calculator", "/calculator"), ("Apply", "/apply")],
        {"START_APPLICATION", "RUN_CALCULATOR"},
    ),
    (
        "clinic_site",
        "healthcare",
        "Doctor clinic appointments, hospital specialists, patient treatment, consultation, and departments.",
        "Book Appointment",
        "button.appointment",
        [("Doctors", "/doctors"), ("Treatments", "/treatments"), ("Appointments", "/appointments")],
        {"REQUEST_APPOINTMENT", "SHOW_ENTITIES"},
    ),
    (
        "food_delivery",
        "food",
        "Restaurant menu, cuisine, dishes, delivery, takeaway, order food, reservation, and grocery items.",
        "Order Now",
        "button.order",
        [("Menu", "/menu"), ("Delivery", "/delivery"), ("Reservations", "/reservation")],
        {"CHECKOUT_HANDOFF", "SHOW_ENTITIES"},
    ),
    (
        "realty_site",
        "real_estate",
        "Real estate property listings, apartment rent, buy home, bedroom, location, and viewing.",
        "Book Viewing",
        "button.viewing",
        [("Properties", "/properties"), ("Listings", "/listings"), ("Schedule Viewing", "/schedule-viewing")],
        {"REQUEST_VIEWING", "SHOW_ENTITIES"},
    ),
    (
        "learning_site",
        "education",
        "Online course programs, learning classes, syllabus, curriculum, certificate, admission, and enroll.",
        "Enroll",
        "button.enroll",
        [("Courses", "/courses"), ("Syllabus", "/syllabus"), ("Admissions", "/admissions")],
        {"START_ENROLLMENT", "OPEN_SYLLABUS"},
    ),
    (
        "auto_dealer",
        "automotive",
        "Car dealer vehicle inventory, auto model trim, service, finance calculator, and test drive.",
        "Book Test Drive",
        "button.test-drive",
        [("Vehicles", "/vehicles"), ("Models", "/models"), ("Service", "/service")],
        {"REQUEST_TEST_DRIVE", "SHOW_ENTITIES"},
    ),
    (
        "law_firm",
        "legal_services",
        "Legal services, lawyer attorney consultation, case review, intake, and practice areas.",
        "Request Consultation",
        "button.consult",
        [("Practice Areas", "/practice-areas"), ("Consultation", "/consultation"), ("Attorneys", "/attorneys")],
        {"REQUEST_CONSULTATION", "SHOW_ENTITIES"},
    ),
    (
        "jobs_board",
        "jobs_recruiting",
        "Job careers, recruiting, resume, hiring, vacancy, role salary, skills, and apply now.",
        "Apply Now",
        "button.apply-job",
        [("Jobs", "/jobs"), ("Careers", "/careers"), ("Apply", "/apply")],
        {"START_APPLICATION", "MATCH_JOBS"},
    ),
    (
        "events_site",
        "events_ticketing",
        "Event tickets, concert venue, showtime, seat availability, festival, and booking.",
        "Buy Tickets",
        "button.tickets",
        [("Events", "/events"), ("Tickets", "/tickets"), ("Venues", "/venues")],
        {"START_TICKET_PURCHASE", "SHOW_ENTITIES"},
    ),
    (
        "builder_site",
        "construction",
        "Construction contractor renovation, remodeling, builder, roofing, concrete, estimate, and site visit.",
        "Request Estimate",
        "button.estimate",
        [("Services", "/services"), ("Projects", "/projects"), ("Estimate", "/estimate")],
        {"REQUEST_ESTIMATE", "OPEN_PROJECTS"},
    ),
    (
        "generic_site",
        "generic",
        "Company overview, resources, support, contact, articles, and help center.",
        "Contact Team",
        "button.contact",
        [("Resources", "/resources"), ("Contact", "/contact")],
        {"OPEN_CONTACT", "SHOW_ENTITIES"},
    ),
]


@pytest.mark.parametrize(
    ("site_id", "expected_vertical", "text_sample", "button_label", "button_selector", "links", "expected_actions"),
    DOMAIN_CASES,
)
def test_domain_fixture_generates_vertical_specific_runtime(
    site_id: str,
    expected_vertical: str,
    text_sample: str,
    button_label: str,
    button_selector: str,
    links: list[tuple[str, str]],
    expected_actions: set[str],
) -> None:
    origin = f"https://{site_id}.example.com"
    discovery = build_discovery(
        {
            "site_id": site_id,
            "origin": origin,
            "url": f"{origin}/",
            "title": site_id.replace("_", " ").title(),
            "text_sample": text_sample,
            "buttons": [{"label": button_label, "selector": button_selector}],
            "links": [{"label": label, "href": f"{origin}{path}"} for label, path in links],
            "forms": [
                {
                    "label": button_label,
                    "selector": "form.primary",
                    "input_selector": "input[name='email']",
                    "submit_selector": button_selector,
                    "fields": [{"selector": "input[name='email']", "name": "Email", "type": "email"}],
                }
            ],
            "platform_hints": {},
        }
    )
    actions = set(discovery.vertical_config["actions"])

    assert discovery.vertical_key == expected_vertical
    assert expected_actions <= actions
    assert discovery.vertical_config["action_candidates"]
    assert discovery.vertical_config["prompt_suggestions"]
    assert discovery.vertical_config["intake_questions"]
