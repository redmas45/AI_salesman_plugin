const FINAL_ACTION_KEYWORDS = Object.freeze({
  APPLICATION: ["apply", "application", "enroll", "upload", "resume", "job"],
  BOOKING: ["book", "booking", "reserve", "schedule", "appointment", "ticket"],
  CHECKOUT: ["checkout", "pay", "payment", "order", "purchase", "cart"],
  QUOTE: ["quote", "estimate", "consultation", "contact", "lead", "submit"],
});

const BLOCKED_ACTION_GROUPS = Object.freeze({
  APPLICATION: new Set(["START_APPLICATION", "START_ENROLLMENT", "START_INTAKE", "MATCH_JOBS"]),
  BOOKING: new Set([
    "START_BOOKING",
    "START_TICKET_PURCHASE",
    "REQUEST_APPOINTMENT",
    "BOOK_APPOINTMENT_REQUEST",
    "REQUEST_VIEWING",
    "REQUEST_SITE_VISIT",
  ]),
  CHECKOUT: new Set(["CHECKOUT", "CHECKOUT_HANDOFF", "SCHEDULE_ORDER"]),
  QUOTE: new Set(["START_QUOTE", "REQUEST_ESTIMATE", "REQUEST_CONSULTATION", "CAPTURE_LEAD", "CAPTURE_PATIENT_LEAD"]),
});

const FINALIZING_OPERATIONS = new Set(["click", "navigate", "submit"]);

function clean(value) {
  return String(value || "").trim();
}

function lowerText(value) {
  return clean(value).toLowerCase();
}

function blockedActions(runtimeConfig) {
  const policy = runtimeConfig?.adapter?.action_policy || {};
  if (!Array.isArray(policy.blocked_actions)) return new Set();
  return new Set(policy.blocked_actions.map((item) => clean(item).toUpperCase()).filter(Boolean));
}

function hasBlockedGroup(blocked, groupName) {
  for (const action of BLOCKED_ACTION_GROUPS[groupName] || []) {
    if (blocked.has(action)) return true;
  }
  return false;
}

function stepText(step) {
  return lowerText(
    [
      step?.selector,
      step?.label,
      step?.path,
      step?.url,
      step?.href,
      step?.name,
      step?.text,
      step?.value,
    ].join(" ")
  );
}

function matchesAnyKeyword(text, keywords) {
  return keywords.some((keyword) => text.includes(keyword));
}

function blockedGroupForStep(step, runtimeConfig) {
  const op = lowerText(step?.op || step?.type || step?.action);
  if (!FINALIZING_OPERATIONS.has(op)) return "";

  const text = stepText(step);
  const blocked = blockedActions(runtimeConfig);
  for (const [groupName, keywords] of Object.entries(FINAL_ACTION_KEYWORDS)) {
    if (hasBlockedGroup(blocked, groupName) && matchesAnyKeyword(text, keywords)) {
      return groupName.toLowerCase();
    }
  }
  return "";
}

export function sequencePolicyBlock(steps, runtimeConfig) {
  if (!Array.isArray(steps)) return null;

  for (const step of steps) {
    const groupName = blockedGroupForStep(step, runtimeConfig);
    if (!groupName) continue;
    return {
      reason: "blocked_sequence_step",
      group: groupName,
      step: {
        op: clean(step?.op || step?.type || step?.action),
        selector: clean(step?.selector),
        label: clean(step?.label),
        path: clean(step?.path || step?.url || step?.href),
      },
    };
  }
  return null;
}
