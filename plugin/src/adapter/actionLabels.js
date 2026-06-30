import { ACTIONS } from "../constants";

export const ACTION_BUTTON_LABELS = Object.freeze({
  [ACTIONS.ADD_TO_CART]: ["add to cart", "add cart", "add to bag", "buy now"],
  [ACTIONS.CHECKOUT]: ["checkout", "place order", "buy now"],
  FILTER_PRODUCTS: ["search", "filter", "find products"],
  FILTER_ENTITIES: ["search", "filter", "find"],
  START_BOOKING: ["book now", "reserve", "check availability"],
  START_QUOTE: ["get quote", "request quote", "start quote"],
  START_APPLICATION: ["apply now", "start application", "check eligibility"],
  REQUEST_APPOINTMENT: ["book appointment", "request appointment", "schedule"],
  REQUEST_TEST_DRIVE: ["book test drive", "request test drive"],
  REQUEST_VIEWING: ["book viewing", "schedule viewing", "site visit"],
  REQUEST_CONSULTATION: ["request consultation", "book consultation"],
  REQUEST_ESTIMATE: ["get estimate", "request estimate", "get quote", "request quote"],
  REQUEST_SITE_VISIT: ["site visit", "schedule site visit", "book site visit"],
  START_TICKET_PURCHASE: ["buy tickets", "book tickets", "select seats"],
  START_ENROLLMENT: ["enroll", "apply now", "start enrollment"],
  OPEN_CONTACT: ["contact", "support", "help"],
  OPEN_PROJECTS: ["projects", "portfolio", "our work"],
  OPEN_SERVICES: ["services", "view services"],
  OPEN_POLICY: ["policy", "terms", "coverage", "privacy"],
  OPEN_CLAIM_FLOW: ["claim", "file claim", "start claim"],
  OPEN_RENEWAL_FLOW: ["renew", "renew policy", "renewal"],
  OPEN_SYLLABUS: ["syllabus", "curriculum"],
  RUN_CALCULATOR: ["calculate", "calculator", "check emi"],
  RUN_AFFORDABILITY_CALCULATOR: ["affordability", "calculate emi"],
  CHECK_AVAILABILITY: ["check availability", "available"],
  SEARCH_AVAILABILITY: ["search", "find", "check availability"],
  MATCH_JOBS: ["find jobs", "match jobs", "search jobs"],
  CAPTURE_LEAD: ["contact", "submit", "send", "enquire", "inquire"],
});

export function labelsForAction(actionName, actionConfig = {}) {
  const labels = [
    actionConfig.label,
    actionConfig.text,
    ...(ACTION_BUTTON_LABELS[String(actionName || "").toUpperCase()] || []),
  ];
  return labels.map((label) => String(label || "").trim().toLowerCase()).filter(Boolean);
}
