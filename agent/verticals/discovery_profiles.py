"""Registry-driven website discovery hints for vertical automation.

These profiles are deliberately data-only. The crawler and adapter generator use
the same profile fields for every industry so adding a vertical does not require
new crawler branches.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.verticals.registry import FALLBACK_VERTICAL_KEY, get_vertical, list_verticals


@dataclass(frozen=True)
class VerticalDiscoveryProfile:
    """Signals AI Hub uses to classify, crawl, extract, and control a website."""

    key: str
    classification_keywords: tuple[str, ...] = ()
    route_keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)
    route_actions: dict[str, str] = field(default_factory=dict)
    action_labels: dict[str, tuple[str, ...]] = field(default_factory=dict)
    primary_actions: tuple[str, ...] = ()
    form_action: str = "CAPTURE_LEAD"
    discovery_paths: tuple[str, ...] = ()
    high_value_url_keywords: tuple[str, ...] = ()
    jsonld_types: tuple[str, ...] = ()
    text_signals: tuple[str, ...] = ()
    entity_type: str = ""
    category_label: str = ""
    provider_label: str = "Provider"


COMMON_ROUTE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "home": ("home",),
    "about": ("about", "company", "who we are"),
    "contact": ("contact", "support", "help", "callback", "enquiry", "inquiry"),
    "faq": ("faq", "faqs", "questions"),
    "login": ("login", "sign in", "account"),
    "privacy": ("privacy", "terms", "disclaimer"),
}

COMMON_ROUTE_ACTIONS: dict[str, str] = {
    "contact": "OPEN_CONTACT",
    "faq": "OPEN_POLICY",
    "privacy": "OPEN_POLICY",
}

COMMON_ACTION_LABELS: dict[str, tuple[str, ...]] = {
    "OPEN_CONTACT": ("contact", "support", "help"),
    "CAPTURE_LEAD": ("contact", "submit", "send message", "enquire", "inquire"),
    "REQUEST_CALLBACK": ("request callback", "call me", "schedule call"),
    "HANDOFF_TO_HUMAN": ("talk to human", "speak to team", "contact team"),
}

COMMON_DISCOVERY_PATHS: tuple[str, ...] = (
    "/",
    "/about",
    "/services",
    "/contact",
    "/faq",
)

COMMON_HIGH_VALUE_URL_KEYWORDS: tuple[str, ...] = (
    "service",
    "services",
    "solutions",
    "catalog",
    "category",
    "categories",
    "contact",
    "quote",
    "booking",
    "appointment",
)

ECOMMERCE_PROFILE = VerticalDiscoveryProfile(
    key="ecommerce",
    classification_keywords=(
        "shop",
        "store",
        "cart",
        "checkout",
        "product",
        "sale",
        "wishlist",
        "brand",
        "fashion",
        "clothing",
        "apparel",
        "size",
    ),
    route_keywords={
        "shop": ("shop", "store", "products", "catalog", "inventory", "collections", "fashion"),
        "cart": ("cart", "basket", "bag"),
        "checkout": ("checkout", "payment"),
        "sale": ("sale", "deals", "offers"),
    },
    route_actions={
        "shop": "FILTER_PRODUCTS",
        "cart": "NAVIGATE_TO",
        "checkout": "CHECKOUT",
        "sale": "FILTER_PRODUCTS",
    },
    action_labels={
        "ADD_TO_CART": ("add to cart", "add cart", "add to bag", "buy now"),
        "CHECKOUT": ("checkout", "continue to payment", "place order"),
        "FILTER_PRODUCTS": ("search", "filter", "find products"),
    },
    primary_actions=("FILTER_PRODUCTS", "ADD_TO_CART", "CHECKOUT"),
    form_action="FILTER_PRODUCTS",
    discovery_paths=(
        "/shop",
        "/store",
        "/products",
        "/product",
        "/catalog",
        "/catalogue",
        "/collections",
        "/collections/all",
        "/category",
        "/categories",
        "/inventory",
        "/items",
        "/all-products",
        "/shop-all",
        "/store/products",
        "/search",
        "/sale",
    ),
    high_value_url_keywords=(
        "product",
        "products",
        "shop",
        "store",
        "catalog",
        "catalogue",
        "collection",
        "collections",
        "category",
        "categories",
        "inventory",
        "item",
        "sku",
        "fashion",
        "clothing",
        "sale",
    ),
    jsonld_types=("Product", "Offer"),
    text_signals=("add to cart", "buy now", "price", "sale", "in stock", "size", "brand"),
    entity_type="product",
    category_label="Products",
    provider_label="Brand",
)

TRAVEL_PROFILE = VerticalDiscoveryProfile(
    key="travel",
    classification_keywords=(
        "travel",
        "tour",
        "ticket",
        "activity",
        "destination",
        "hotel",
        "flight",
        "booking",
        "attraction",
        "things to do",
    ),
    route_keywords={
        "shop": ("things to do", "activities", "tours", "destinations", "experiences"),
        "booking": ("book", "booking", "reserve", "availability"),
        "destination": ("destination", "city", "places"),
    },
    route_actions={"booking": "START_BOOKING", "destination": "SEARCH_AVAILABILITY", "shop": "SEARCH_AVAILABILITY"},
    action_labels={
        "START_BOOKING": ("book now", "book tickets", "reserve", "select tickets", "check availability"),
        "SEARCH_AVAILABILITY": ("search", "find", "check availability", "search destination"),
        "BUILD_ITINERARY": ("build itinerary", "plan trip"),
    },
    primary_actions=("SEARCH_AVAILABILITY", "START_BOOKING", "OPEN_CONTACT"),
    form_action="SEARCH_AVAILABILITY",
    discovery_paths=("/things-to-do", "/activities", "/tours", "/destinations", "/tickets", "/booking"),
    high_value_url_keywords=("activity", "activities", "tour", "tours", "ticket", "destination", "booking"),
    jsonld_types=("TouristAttraction", "Trip", "Hotel", "LodgingBusiness", "Event", "Service", "Product"),
    text_signals=("tour", "ticket", "destination", "duration", "booking", "availability", "attraction"),
    entity_type="travel_item",
    category_label="Travel Items",
)

INSURANCE_PROFILE = VerticalDiscoveryProfile(
    key="insurance",
    classification_keywords=("insurance", "policy", "premium", "claim", "coverage", "quote", "renewal"),
    route_keywords={
        "quote": ("quote", "premium", "estimate"),
        "claim": ("claim", "claims"),
        "renewal": ("renew", "renewal"),
        "policy": ("policy", "coverage", "disclosure", "terms"),
        "plans": ("plans", "insurance", "products"),
    },
    route_actions={
        "quote": "START_QUOTE",
        "claim": "OPEN_CLAIM_FLOW",
        "renewal": "OPEN_RENEWAL_FLOW",
        "policy": "OPEN_POLICY",
        "plans": "SHOW_ENTITIES",
    },
    action_labels={
        "START_QUOTE": ("get quote", "request quote", "start quote"),
        "OPEN_CLAIM_FLOW": ("file claim", "start claim", "make a claim", "claim"),
        "OPEN_RENEWAL_FLOW": ("renew policy", "renewal", "renew"),
        "OPEN_POLICY": ("policy details", "coverage", "disclosure", "terms"),
        "REQUEST_CALLBACK": ("request callback", "call me"),
    },
    primary_actions=("START_QUOTE", "OPEN_CLAIM_FLOW", "OPEN_RENEWAL_FLOW", "OPEN_POLICY", "REQUEST_CALLBACK", "CAPTURE_LEAD"),
    form_action="START_QUOTE",
    discovery_paths=("/insurance", "/plans", "/policies", "/quote", "/claims", "/renewal"),
    high_value_url_keywords=("insurance", "plan", "plans", "policy", "policies", "coverage", "quote", "premium", "claim", "claims", "renewal"),
    jsonld_types=("Service", "FinancialProduct", "Product"),
    text_signals=("insurance", "policy", "premium", "coverage", "claim", "renewal", "quote", "sum insured", "waiting period", "rider"),
    entity_type="insurance_plan",
    category_label="Insurance Plans",
    provider_label="Insurance Provider",
)

FINANCE_PROFILE = VerticalDiscoveryProfile(
    key="finance_broker",
    classification_keywords=("loan", "mortgage", "broker", "investment", "finance", "rate", "eligibility", "credit"),
    route_keywords={
        "products": ("loans", "mortgage", "products", "finance"),
        "calculator": ("calculator", "emi", "affordability", "rate"),
        "application": ("apply", "application", "eligibility"),
    },
    route_actions={"calculator": "RUN_CALCULATOR", "application": "START_APPLICATION", "products": "SHOW_ENTITIES"},
    action_labels={
        "RUN_CALCULATOR": ("calculate", "calculator", "check emi"),
        "START_APPLICATION": ("apply now", "start application", "check eligibility"),
        "HANDOFF_TO_ADVISOR": ("talk to advisor", "speak to advisor"),
    },
    primary_actions=("RUN_CALCULATOR", "START_APPLICATION", "HANDOFF_TO_ADVISOR", "CAPTURE_LEAD"),
    form_action="START_APPLICATION",
    discovery_paths=("/loans", "/mortgage", "/finance", "/rates", "/calculator", "/apply"),
    high_value_url_keywords=("loan", "mortgage", "finance", "rate", "calculator", "apply", "eligibility"),
    jsonld_types=("FinancialProduct", "Service", "Product"),
    text_signals=("rate", "loan", "emi", "mortgage", "apr", "eligibility", "application"),
    entity_type="financial_product",
    category_label="Financial Products",
)

HEALTHCARE_PROFILE = VerticalDiscoveryProfile(
    key="healthcare",
    classification_keywords=("doctor", "clinic", "appointment", "patient", "treatment", "hospital", "specialist"),
    route_keywords={
        "appointment": ("appointment", "book", "schedule"),
        "providers": ("doctors", "providers", "specialists", "departments"),
        "services": ("treatments", "services", "specialties"),
    },
    route_actions={"appointment": "REQUEST_APPOINTMENT", "providers": "SHOW_ENTITIES", "services": "SHOW_ENTITIES"},
    action_labels={
        "REQUEST_APPOINTMENT": ("book appointment", "schedule appointment", "request appointment"),
        "CHECK_APPOINTMENT_AVAILABILITY": ("check availability", "available slots"),
        "HANDOFF_TO_CLINIC": ("call clinic", "contact clinic"),
    },
    primary_actions=("REQUEST_APPOINTMENT", "CHECK_APPOINTMENT_AVAILABILITY", "HANDOFF_TO_CLINIC", "CAPTURE_LEAD"),
    form_action="REQUEST_APPOINTMENT",
    discovery_paths=("/doctors", "/clinics", "/appointments", "/specialties", "/treatments", "/services"),
    high_value_url_keywords=("doctor", "clinic", "appointment", "specialty", "treatment", "hospital", "department"),
    jsonld_types=("MedicalBusiness", "Physician", "Hospital", "MedicalClinic", "Service", "Product"),
    text_signals=("doctor", "clinic", "appointment", "specialty", "treatment", "patient", "consultation"),
    entity_type="provider",
    category_label="Providers",
    provider_label="Clinic",
)

FOOD_PROFILE = VerticalDiscoveryProfile(
    key="food",
    classification_keywords=("menu", "restaurant", "delivery", "order food", "reservation", "dish", "cuisine"),
    route_keywords={
        "menu": ("menu", "food", "dishes", "grocery"),
        "order": ("order", "delivery", "takeaway"),
        "reservation": ("reservation", "book table"),
    },
    route_actions={"menu": "SHOW_ENTITIES", "order": "CHECKOUT_HANDOFF", "reservation": "CAPTURE_LEAD"},
    action_labels={
        "SET_LOCATION": ("set location", "change location"),
        "CHECKOUT_HANDOFF": ("order now", "checkout", "place order"),
        "SCHEDULE_ORDER": ("schedule order", "preorder"),
    },
    primary_actions=("SET_LOCATION", "SCHEDULE_ORDER", "CHECKOUT_HANDOFF", "CAPTURE_LEAD"),
    form_action="FILTER_ENTITIES",
    discovery_paths=("/menu", "/order", "/delivery", "/restaurants", "/groceries"),
    high_value_url_keywords=("menu", "dish", "food", "restaurant", "delivery", "grocery"),
    jsonld_types=("MenuItem", "Restaurant", "FoodEstablishment", "Product", "Offer"),
    text_signals=("menu", "dish", "restaurant", "delivery", "order", "cuisine", "price"),
    entity_type="menu_item",
    category_label="Menu Items",
)

REAL_ESTATE_PROFILE = VerticalDiscoveryProfile(
    key="real_estate",
    classification_keywords=("property", "real estate", "apartment", "listing", "rent", "buy home", "viewing"),
    route_keywords={
        "listings": ("properties", "listings", "homes", "apartments", "projects"),
        "viewing": ("viewing", "schedule visit", "site visit"),
    },
    route_actions={"listings": "SHOW_ENTITIES", "viewing": "REQUEST_VIEWING"},
    action_labels={
        "REQUEST_VIEWING": ("book viewing", "schedule viewing", "site visit"),
        "CONTACT_AGENT": ("contact agent", "talk to agent"),
        "RUN_AFFORDABILITY_CALCULATOR": ("affordability", "calculate emi"),
    },
    primary_actions=("REQUEST_VIEWING", "CONTACT_AGENT", "RUN_AFFORDABILITY_CALCULATOR", "CAPTURE_LEAD"),
    form_action="FILTER_ENTITIES",
    discovery_paths=("/properties", "/listings", "/projects", "/rent", "/buy", "/schedule-viewing"),
    high_value_url_keywords=("property", "listing", "apartment", "villa", "rent", "buy", "project", "viewing"),
    jsonld_types=("RealEstateListing", "Place", "Residence", "Apartment", "SingleFamilyResidence", "Product"),
    text_signals=("property", "bedroom", "bathroom", "sq ft", "listing", "viewing", "location"),
    entity_type="property_listing",
    category_label="Listings",
)

EDUCATION_PROFILE = VerticalDiscoveryProfile(
    key="education",
    classification_keywords=("course", "class", "learning", "enroll", "syllabus", "program", "certificate"),
    route_keywords={
        "courses": ("courses", "programs", "classes", "training"),
        "syllabus": ("syllabus", "curriculum"),
        "enrollment": ("enroll", "admission", "apply"),
    },
    route_actions={"courses": "SHOW_ENTITIES", "syllabus": "OPEN_SYLLABUS", "enrollment": "START_ENROLLMENT"},
    action_labels={
        "START_ENROLLMENT": ("enroll", "apply now", "start enrollment"),
        "OPEN_SYLLABUS": ("view syllabus", "curriculum"),
        "REQUEST_COUNSELOR_CALLBACK": ("talk to counselor", "request callback"),
    },
    primary_actions=("BUILD_LEARNING_PATH", "START_ENROLLMENT", "REQUEST_COUNSELOR_CALLBACK", "CAPTURE_LEAD"),
    form_action="START_ENROLLMENT",
    discovery_paths=("/courses", "/programs", "/classes", "/syllabus", "/admissions", "/enroll"),
    high_value_url_keywords=("course", "program", "class", "certificate", "syllabus", "enroll", "admission"),
    jsonld_types=("Course", "EducationalOccupationalProgram", "Event", "Product"),
    text_signals=("course", "program", "syllabus", "duration", "certificate", "enroll", "instructor"),
    entity_type="course",
    category_label="Courses",
)

AUTOMOTIVE_PROFILE = VerticalDiscoveryProfile(
    key="automotive",
    classification_keywords=("car", "vehicle", "test drive", "dealer", "auto", "service", "model", "trim"),
    route_keywords={
        "vehicles": ("cars", "vehicles", "inventory", "models"),
        "test_drive": ("test drive", "drive"),
        "service": ("service", "maintenance"),
    },
    route_actions={"vehicles": "SHOW_ENTITIES", "test_drive": "REQUEST_TEST_DRIVE", "service": "CAPTURE_LEAD"},
    action_labels={
        "REQUEST_TEST_DRIVE": ("book test drive", "request test drive"),
        "RUN_CALCULATOR": ("calculate emi", "finance calculator"),
        "CONTACT_AGENT": ("contact dealer", "talk to dealer"),
    },
    primary_actions=("REQUEST_TEST_DRIVE", "RUN_CALCULATOR", "CONTACT_AGENT", "CAPTURE_LEAD"),
    form_action="FILTER_ENTITIES",
    discovery_paths=("/cars", "/vehicles", "/inventory", "/models", "/test-drive", "/service"),
    high_value_url_keywords=("car", "vehicle", "inventory", "model", "trim", "test-drive", "dealer"),
    jsonld_types=("Vehicle", "Car", "Product", "AutoDealer", "Service"),
    text_signals=("vehicle", "model", "mileage", "engine", "test drive", "dealer", "price"),
    entity_type="vehicle_listing",
    category_label="Vehicles",
)

LEGAL_PROFILE = VerticalDiscoveryProfile(
    key="legal_services",
    classification_keywords=("lawyer", "legal", "attorney", "case", "consultation", "practice area"),
    route_keywords={
        "services": ("practice areas", "services", "legal services"),
        "consultation": ("consultation", "case review", "intake"),
    },
    route_actions={"services": "SHOW_ENTITIES", "consultation": "REQUEST_CONSULTATION"},
    action_labels={
        "REQUEST_CONSULTATION": ("request consultation", "book consultation"),
        "START_INTAKE": ("start intake", "case review"),
        "HANDOFF_TO_LAWYER": ("talk to lawyer", "speak to attorney"),
    },
    primary_actions=("START_INTAKE", "REQUEST_CONSULTATION", "HANDOFF_TO_LAWYER", "CAPTURE_LEAD"),
    form_action="REQUEST_CONSULTATION",
    discovery_paths=("/practice-areas", "/services", "/attorneys", "/lawyers", "/consultation", "/intake"),
    high_value_url_keywords=("legal", "lawyer", "attorney", "practice", "consultation", "case"),
    jsonld_types=("LegalService", "Attorney", "Service", "Organization"),
    text_signals=("legal", "lawyer", "attorney", "case", "consultation", "practice area"),
    entity_type="legal_service",
    category_label="Legal Services",
)

JOBS_PROFILE = VerticalDiscoveryProfile(
    key="jobs_recruiting",
    classification_keywords=("job", "career", "recruit", "resume", "apply now", "vacancy", "hiring"),
    route_keywords={
        "jobs": ("jobs", "careers", "openings", "vacancies"),
        "application": ("apply", "application", "resume"),
    },
    route_actions={"jobs": "MATCH_JOBS", "application": "START_APPLICATION"},
    action_labels={
        "MATCH_JOBS": ("find jobs", "match jobs", "search jobs"),
        "START_APPLICATION": ("apply now", "start application"),
        "HANDOFF_TO_RECRUITER": ("talk to recruiter", "contact recruiter"),
    },
    primary_actions=("MATCH_JOBS", "START_APPLICATION", "HANDOFF_TO_RECRUITER", "CAPTURE_LEAD"),
    form_action="MATCH_JOBS",
    discovery_paths=("/jobs", "/careers", "/openings", "/vacancies", "/apply"),
    high_value_url_keywords=("job", "career", "opening", "vacancy", "apply", "recruit"),
    jsonld_types=("JobPosting", "Organization", "Service"),
    text_signals=("job", "role", "salary", "apply", "resume", "experience", "skills"),
    entity_type="job_posting",
    category_label="Jobs",
)

EVENTS_PROFILE = VerticalDiscoveryProfile(
    key="events_ticketing",
    classification_keywords=("event", "ticket", "concert", "show", "venue", "seat", "festival"),
    route_keywords={
        "events": ("events", "shows", "concerts", "festival"),
        "tickets": ("tickets", "booking", "seats"),
    },
    route_actions={"events": "SHOW_ENTITIES", "tickets": "START_TICKET_PURCHASE"},
    action_labels={
        "CHECK_AVAILABILITY": ("check availability", "available tickets"),
        "START_TICKET_PURCHASE": ("buy tickets", "book tickets", "select seats"),
        "JOIN_WAITLIST": ("join waitlist", "notify me"),
    },
    primary_actions=("CHECK_AVAILABILITY", "START_TICKET_PURCHASE", "JOIN_WAITLIST", "CAPTURE_LEAD"),
    form_action="CHECK_AVAILABILITY",
    discovery_paths=("/events", "/tickets", "/shows", "/concerts", "/venues", "/schedule"),
    high_value_url_keywords=("event", "ticket", "concert", "show", "venue", "seat"),
    jsonld_types=("Event", "MusicEvent", "TheaterEvent", "SportsEvent", "Product", "Offer"),
    text_signals=("event", "ticket", "venue", "date", "showtime", "seat", "availability"),
    entity_type="event",
    category_label="Events",
)

CONSTRUCTION_PROFILE = VerticalDiscoveryProfile(
    key="construction",
    classification_keywords=(
        "construction",
        "contractor",
        "renovation",
        "remodeling",
        "builder",
        "civil",
        "architecture",
        "interior",
        "roofing",
        "concrete",
        "project",
        "site visit",
        "estimate",
    ),
    route_keywords={
        "services": ("services", "construction services", "renovation", "remodeling", "contracting"),
        "projects": ("projects", "portfolio", "work", "gallery", "case studies"),
        "estimate": ("estimate", "quote", "pricing", "consultation"),
        "site_visit": ("site visit", "inspection", "survey"),
    },
    route_actions={
        "services": "OPEN_SERVICES",
        "projects": "OPEN_PROJECTS",
        "estimate": "REQUEST_ESTIMATE",
        "site_visit": "REQUEST_SITE_VISIT",
    },
    action_labels={
        "REQUEST_ESTIMATE": ("get estimate", "request estimate", "get quote", "request quote"),
        "REQUEST_SITE_VISIT": ("book site visit", "schedule site visit", "schedule inspection"),
        "OPEN_PROJECTS": ("view projects", "portfolio", "our work"),
        "OPEN_SERVICES": ("view services", "services"),
    },
    primary_actions=("REQUEST_ESTIMATE", "REQUEST_SITE_VISIT", "OPEN_PROJECTS", "OPEN_SERVICES", "CAPTURE_LEAD"),
    form_action="REQUEST_ESTIMATE",
    discovery_paths=("/services", "/projects", "/portfolio", "/gallery", "/renovation", "/construction", "/estimate", "/quote"),
    high_value_url_keywords=("construction", "contractor", "renovation", "remodel", "project", "portfolio", "estimate", "quote", "builder", "roofing", "concrete"),
    jsonld_types=("LocalBusiness", "HomeAndConstructionBusiness", "GeneralContractor", "ProfessionalService", "Service", "Product"),
    text_signals=("construction", "contractor", "renovation", "remodel", "project", "estimate", "site visit", "roofing", "concrete"),
    entity_type="construction_service",
    category_label="Construction Services",
    provider_label="Contractor",
)

GENERIC_PROFILE = VerticalDiscoveryProfile(
    key=FALLBACK_VERTICAL_KEY,
    classification_keywords=(),
    route_keywords={"services": ("services", "solutions"), "resources": ("resources", "blog", "articles")},
    route_actions={"services": "SHOW_ENTITIES", "resources": "SHOW_ENTITIES"},
    action_labels=COMMON_ACTION_LABELS,
    primary_actions=("SHOW_ENTITIES", "OPEN_CONTACT", "CAPTURE_LEAD"),
    form_action="CAPTURE_LEAD",
    discovery_paths=("/services", "/solutions", "/resources", "/blog"),
    high_value_url_keywords=("service", "solution", "resource", "article", "faq"),
    jsonld_types=("Service", "LocalBusiness", "Organization", "Article", "FAQPage", "Product"),
    text_signals=("service", "solution", "contact", "quote", "support"),
    entity_type="knowledge_item",
    category_label="Knowledge",
)

_PROFILES: tuple[VerticalDiscoveryProfile, ...] = (
    ECOMMERCE_PROFILE,
    INSURANCE_PROFILE,
    TRAVEL_PROFILE,
    FINANCE_PROFILE,
    HEALTHCARE_PROFILE,
    FOOD_PROFILE,
    REAL_ESTATE_PROFILE,
    EDUCATION_PROFILE,
    AUTOMOTIVE_PROFILE,
    LEGAL_PROFILE,
    JOBS_PROFILE,
    EVENTS_PROFILE,
    CONSTRUCTION_PROFILE,
    GENERIC_PROFILE,
)

_PROFILE_BY_KEY = {profile.key: profile for profile in _PROFILES}


def get_discovery_profile(vertical_key: str | None) -> VerticalDiscoveryProfile:
    """Return discovery hints for a vertical, falling back to generic."""
    try:
        normalized = get_vertical(vertical_key).key
    except ValueError:
        normalized = FALLBACK_VERTICAL_KEY
    return _PROFILE_BY_KEY.get(normalized) or GENERIC_PROFILE


def list_discovery_profiles() -> list[VerticalDiscoveryProfile]:
    """Return profiles in backend vertical display order."""
    ordered_keys = [vertical.key for vertical in list_verticals()]
    return [_PROFILE_BY_KEY[key] for key in ordered_keys if key in _PROFILE_BY_KEY]


def merged_route_keywords(profile: VerticalDiscoveryProfile) -> dict[str, tuple[str, ...]]:
    """Return common and vertical route keyword maps."""
    return {**COMMON_ROUTE_KEYWORDS, **profile.route_keywords}


def merged_route_actions(profile: VerticalDiscoveryProfile) -> dict[str, str]:
    """Return route-to-action mapping for adapter generation."""
    return {**COMMON_ROUTE_ACTIONS, **profile.route_actions}


def merged_action_labels(profile: VerticalDiscoveryProfile) -> dict[str, tuple[str, ...]]:
    """Return common and vertical action label hints."""
    merged = dict(COMMON_ACTION_LABELS)
    for action, labels in profile.action_labels.items():
        merged[action] = tuple(dict.fromkeys((*merged.get(action, ()), *labels)))
    return merged


def discovery_paths_for(vertical_key: str | None) -> tuple[str, ...]:
    profile = get_discovery_profile(vertical_key)
    return tuple(dict.fromkeys((*COMMON_DISCOVERY_PATHS, *profile.discovery_paths)))


def high_value_url_keywords_for(vertical_key: str | None) -> tuple[str, ...]:
    profile = get_discovery_profile(vertical_key)
    return tuple(dict.fromkeys((*COMMON_HIGH_VALUE_URL_KEYWORDS, *profile.high_value_url_keywords)))


def knowledge_entity_type_for(vertical_key: str | None) -> str:
    profile = get_discovery_profile(vertical_key)
    if profile.entity_type:
        return profile.entity_type
    try:
        vertical = get_vertical(vertical_key)
        return vertical.entity_types[0] if vertical.entity_types else "knowledge_item"
    except ValueError:
        return "knowledge_item"
