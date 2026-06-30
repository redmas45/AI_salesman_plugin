import { CLICKABLE_SELECTOR, FIELD_SELECTOR } from "./controlSelectors";

const INTERACTION_PATH = "/v1/widget/interaction-event";
const TRACKER_FLAG = "__aihubAdapterInteractionTracker";
const SELECTOR_ATTRIBUTES = ["data-testid", "data-test", "data-action", "aria-label", "name"];
const MAX_FIELDS = 12;
const DUPLICATE_WINDOW_MS = 1200;

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function apiUrl(path, apiBaseUrl) {
  return new URL(path, apiBaseUrl).toString();
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function selectorFor(element) {
  if (!element || element.nodeType !== 1) return "";
  if (element.id) return `#${cssEscape(element.id)}`;

  for (const attr of SELECTOR_ATTRIBUTES) {
    const value = element.getAttribute(attr);
    if (value) return `${element.tagName.toLowerCase()}[${attr}="${cssEscape(value)}"]`;
  }

  const classes = Array.from(element.classList || []).slice(0, 2);
  if (classes.length) {
    return `${element.tagName.toLowerCase()}.${classes.map(cssEscape).join(".")}`;
  }
  return element.tagName.toLowerCase();
}

function elementLabel(element) {
  return clean(element?.innerText || element?.value || element?.getAttribute?.("aria-label") || element?.getAttribute?.("title"));
}

function formFields(form) {
  return Array.from(form?.querySelectorAll?.(FIELD_SELECTOR) || [])
    .slice(0, MAX_FIELDS)
    .map((field) => ({
      selector: selectorFor(field),
      name: clean(field.getAttribute("name") || field.id || field.getAttribute("placeholder") || field.getAttribute("aria-label")),
      type: clean(field.getAttribute("type") || field.tagName).toLowerCase(),
      placeholder: clean(field.getAttribute("placeholder")),
    }))
    .filter((field) => field.selector);
}

function basePayload(siteId) {
  return {
    site_id: siteId,
    origin: window.location.origin,
    url: window.location.href,
    occurred_at: new Date().toISOString(),
  };
}

function clickPayload(siteId, event) {
  const target = closestClickableTarget(event);
  if (!target || target.closest?.("#shopbot-widget")) return null;

  return {
    ...basePayload(siteId),
    event_type: "click",
    label: elementLabel(target),
    selector: selectorFor(target),
    tag: clean(target.tagName).toLowerCase(),
    href: target.href || target.getAttribute?.("href") || "",
  };
}

function closestClickableTarget(event) {
  for (const node of event.composedPath?.() || []) {
    if (node?.nodeType === 1 && node.matches?.(CLICKABLE_SELECTOR)) return node;
  }
  return event.target?.closest?.(CLICKABLE_SELECTOR) || null;
}

function submitPayload(siteId, event) {
  const form = event.target;
  if (!form || form.tagName?.toLowerCase() !== "form" || form.closest?.("#shopbot-widget")) return null;

  const submitter = event.submitter;
  return {
    ...basePayload(siteId),
    event_type: "submit",
    label: elementLabel(form) || elementLabel(submitter),
    selector: selectorFor(form),
    tag: "form",
    form: {
      selector: selectorFor(form),
      submit_selector: selectorFor(submitter),
      fields: formFields(form),
    },
  };
}

async function postInteraction(apiBaseUrl, payload) {
  await fetch(apiUrl(INTERACTION_PATH, apiBaseUrl), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    keepalive: true,
  });
}

function eventKey(payload) {
  return [payload.event_type, payload.url, payload.selector, payload.label].join(":");
}

export function installInteractionTracker(apiBaseUrl, siteId) {
  if (window[TRACKER_FLAG]) return;
  window[TRACKER_FLAG] = true;

  let lastKey = "";
  let lastAt = 0;
  const send = (payload) => {
    if (!payload) return;
    const key = eventKey(payload);
    const now = Date.now();
    if (key === lastKey && now - lastAt < DUPLICATE_WINDOW_MS) return;
    lastKey = key;
    lastAt = now;
    postInteraction(apiBaseUrl, payload).catch((err) => {
      console.warn("[AIHubAdapter] Interaction report failed.", err);
    });
  };

  document.addEventListener("click", (event) => send(clickPayload(siteId, event)), true);
  document.addEventListener("submit", (event) => send(submitPayload(siteId, event)), true);
}
