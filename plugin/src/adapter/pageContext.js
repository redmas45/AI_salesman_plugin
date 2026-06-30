import { CLICKABLE_SELECTOR, FIELD_SELECTOR } from "./controlSelectors";
import { queryElementsDeep } from "./deepDom";
import { submitElementFor } from "./submitResolver";

const MAX_CONTEXT_ITEMS = 12;
const MAX_CONTEXT_FIELDS = 8;
const ATTRIBUTES_FOR_SELECTOR = ["data-testid", "data-test", "data-action", "aria-label", "name"];

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return clean(value).replace(/["\\]/g, "\\$&");
}

function selectorFor(element) {
  if (!element || element.nodeType !== 1) return "";
  if (element.id) return `#${cssEscape(element.id)}`;

  for (const attr of ATTRIBUTES_FOR_SELECTOR) {
    const value = element.getAttribute(attr);
    if (value) return `${element.tagName.toLowerCase()}[${attr}="${cssEscape(value)}"]`;
  }

  const classes = Array.from(element.classList || []).slice(0, 2);
  if (classes.length) return `${element.tagName.toLowerCase()}.${classes.map(cssEscape).join(".")}`;
  return element.tagName.toLowerCase();
}

export function readPageContext(runtimeConfig = {}) {
  return {
    title: document.title || "",
    url: window.location.href,
    path: window.location.pathname,
    productId: readProductId(),
    controls: {
      buttons: contextButtons(),
      links: contextLinks(),
      forms: contextForms(),
    },
    adapter: adapterContext(runtimeConfig),
  };
}

function contextButtons() {
  return queryElementsDeep(CLICKABLE_SELECTOR)
    .slice(0, MAX_CONTEXT_ITEMS)
    .map((element) => ({
      label: elementLabel(element),
      selector: selectorFor(element),
    }))
    .filter((item) => item.label || item.selector);
}

function contextLinks() {
  return queryElementsDeep("a[href]")
    .slice(0, MAX_CONTEXT_ITEMS)
    .map((element) => ({
      label: elementLabel(element),
      selector: selectorFor(element),
      href: sameOriginPath(element.href),
    }))
    .filter((item) => item.href);
}

function contextForms() {
  return queryElementsDeep("form")
    .slice(0, MAX_CONTEXT_ITEMS)
    .map((form) => ({
      label: elementLabel(form),
      selector: selectorFor(form),
      submit_selector: selectorFor(submitElementFor(form)),
      fields: contextFields(form),
    }))
    .filter((form) => form.selector && form.fields.length);
}

function contextFields(form) {
  return Array.from(form.querySelectorAll(FIELD_SELECTOR))
    .slice(0, MAX_CONTEXT_FIELDS)
    .map((field) => ({
      selector: selectorFor(field),
      name: fieldName(field),
      type: fieldType(field),
      placeholder: clean(field.getAttribute("placeholder")),
      autocomplete: clean(field.getAttribute("autocomplete")),
      options: fieldOptions(field),
    }))
    .filter((field) => field.selector);
}

function adapterContext(runtimeConfig) {
  const adapter = runtimeConfig?.adapter || {};
  const policy = adapter.action_policy || {};
  return {
    routes: adapter.routes || {},
    actions: Object.keys(adapter.actions || {}).slice(0, MAX_CONTEXT_ITEMS),
    blocked_actions: list(policy.blocked_actions),
    runtime_blocked_actions: list(policy.runtime_blocked_actions),
    handoff_actions: list(policy.handoff_actions),
    handoff_flows: recordList(policy.handoff_flows).map(handoffFlowContext),
    action_health_summary: adapter.action_health?.summary || {},
  };
}

function handoffFlowContext(flow) {
  return {
    key: clean(flow.key),
    title: clean(flow.title),
    provider: clean(flow.provider),
    provider_label: clean(flow.provider_label),
    action: clean(flow.action),
    severity: clean(flow.severity),
    handling: clean(flow.handling),
    automation_boundary: clean(flow.automation_boundary),
    admin_action: clean(flow.admin_action),
    recovery: clean(flow.recovery),
  };
}

function fieldOptions(field) {
  if (clean(field.tagName).toLowerCase() !== "select") return [];
  return Array.from(field.options || [])
    .slice(0, MAX_CONTEXT_FIELDS)
    .map((option) => clean(option.textContent || option.value))
    .filter(Boolean);
}

function fieldName(field) {
  return clean(
    field.getAttribute("name") ||
      field.id ||
      field.getAttribute("aria-label") ||
      field.getAttribute("title") ||
      field.getAttribute("placeholder") ||
      labelledByText(field),
  );
}

function labelledByText(field) {
  return clean(field.getAttribute("aria-labelledby"))
    .split(/\s+/)
    .map((id) => elementLabel(field.ownerDocument?.getElementById?.(id)))
    .join(" ");
}

function elementLabel(element) {
  if (!element) return "";
  return clean(
    element.innerText ||
      element.textContent ||
      element.getAttribute?.("aria-label") ||
      element.getAttribute?.("title") ||
      element.getAttribute?.("name") ||
      element.getAttribute?.("placeholder") ||
      element.getAttribute?.("data-testid"),
  );
}

function fieldType(field) {
  return clean(field.getAttribute("type") || field.tagName).toLowerCase();
}

function readProductId() {
  const element = document.querySelector("[data-product-id], [data-product], [itemprop='sku']");
  return clean(element?.getAttribute("data-product-id") || element?.getAttribute("data-product") || element?.textContent);
}

function sameOriginPath(value) {
  try {
    const url = new URL(value, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}${url.hash}` || "/";
  } catch (_err) {
    return "";
  }
}

function list(value) {
  return Array.isArray(value) ? value.map(clean).filter(Boolean).slice(0, MAX_CONTEXT_ITEMS) : [];
}

function recordList(value) {
  return Array.isArray(value)
    ? value.filter((item) => item && typeof item === "object").slice(0, MAX_CONTEXT_ITEMS)
    : [];
}
