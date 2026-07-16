import { sequencePolicyBlock } from "./domSequencePolicy";
import {
  activateElement,
  enterText,
  selectNativeOption,
  setControlChecked,
  submitFormElement,
} from "./eventDriver";
import { normalizeSchemaValue, schemaItemForParam, schemaParamKey } from "./fieldSchema";
import {
  clean,
  elementText,
  findClickableTarget,
  findFieldTarget,
  findFormTarget,
  queryElement,
} from "./targetResolver";

const MAX_SEQUENCE_STEPS = 30;
const MAX_WAIT_MS = 5000;
const POLL_INTERVAL_MS = 100;
const ALLOWED_OPERATIONS = new Set([
  "check",
  "click",
  "fill",
  "focus",
  "navigate",
  "scroll",
  "select",
  "set_value",
  "submit",
  "uncheck",
  "wait",
  "wait_for",
]);

function normalizeOperation(step) {
  return clean(step?.op || step?.type || step?.action).toLowerCase();
}

function stepsFrom(value) {
  if (!Array.isArray(value)) return [];
  return value.slice(0, MAX_SEQUENCE_STEPS).filter((step) => step && typeof step === "object");
}

export async function runDomSequence(steps, params = {}, runtimeConfig = {}, actionConfig = {}) {
  const sequence = stepsFrom(steps);
  if (!sequence.length) return false;

  const policyBlock = sequencePolicyBlock(sequence, runtimeConfig);
  if (policyBlock) {
    console.warn("[AIHubAdapter] DOM sequence blocked by runtime policy.", policyBlock);
    return false;
  }

  for (const step of sequence) {
    const success = await runStep(step, params, actionConfig);
    if (!success && step.optional !== true) return false;
  }
  return true;
}

async function runStep(step, params, actionConfig) {
  const operation = normalizeOperation(step);
  if (!ALLOWED_OPERATIONS.has(operation)) return false;

  if (operation === "click") return clickStep(step);
  if (operation === "fill" || operation === "set_value") return fillStep(step, params, actionConfig);
  if (operation === "select") return selectStep(step, params, actionConfig);
  if (operation === "check") return checkStep(step, true, params, actionConfig);
  if (operation === "uncheck") return checkStep(step, false, params, actionConfig);
  if (operation === "submit") return submitStep(step);
  if (operation === "navigate") return navigateStep(step);
  if (operation === "scroll") return scrollStep(step);
  if (operation === "focus") return focusStep(step);
  if (operation === "wait") return waitStep(step);
  if (operation === "wait_for") return waitForStep(step);
  return false;
}

function clickStep(step) {
  const element = findClickableTarget(step);
  return activateElement(element);
}

function fillStep(step, params, actionConfig) {
  const input = findFieldTarget(step);
  if (!input) return false;

  return enterText(input, resolveValue(step, params, actionConfig));
}

function selectStep(step, params, actionConfig) {
  const input = findFieldTarget(step);
  if (!input) return false;

  const value = resolveValue(step, params, actionConfig);
  if (selectNativeOption(input, value)) return true;
  if (!enterText(input, value)) return false;
  activateElement(input);
  activateElement(findClickableTarget({ label: value, text: value }));
  return true;
}

function checkStep(step, checked, params, actionConfig) {
  const input = findFieldTarget(step);
  if (!input) return false;
  const value = resolveValue(step, params, actionConfig);
  if (fieldType(input) === "radio") {
    return setControlChecked(matchingRadio(input, value) || input, true);
  }
  const explicitState = checkboxState(value);
  return setControlChecked(input, explicitState ?? checked);
}

function submitStep(step) {
  const target = findFormTarget(step);
  const element = target.form || target.submit || queryElement(step.selector);
  const form = element?.tagName?.toLowerCase() === "form" ? element : element?.closest?.("form");
  return submitFormElement(form || element);
}

function navigateStep(step) {
  const targetPath = sameOriginPath(step.path || step.url || step.href);
  if (!targetPath) return false;

  window.location.href = targetPath;
  return true;
}

function scrollStep(step) {
  const target = queryElement(step.selector);
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: step.block || "center" });
    return true;
  }

  if (clean(step.to).toLowerCase() === "bottom") {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    return true;
  }

  window.scrollTo({ top: numberValue(step.y, 0), left: numberValue(step.x, 0), behavior: "smooth" });
  return true;
}

function focusStep(step) {
  const element = findFieldTarget(step) || queryElement(step.selector);
  if (!element || typeof element.focus !== "function") return false;

  element.focus();
  return true;
}

async function waitStep(step) {
  await sleep(waitMs(step.ms || step.timeout_ms));
  return true;
}

async function waitForStep(step) {
  const selector = clean(step.selector);
  if (!selector) return false;

  const deadline = Date.now() + waitMs(step.ms || step.timeout_ms);
  while (Date.now() <= deadline) {
    if (queryElement(selector)) return true;
    await sleep(POLL_INTERVAL_MS);
  }
  return false;
}

function resolveValue(step, params, actionConfig) {
  const key = clean(step.param || step.parameter || step.name);
  if (key && params && Object.prototype.hasOwnProperty.call(params, key)) {
    return clean(normalizeSchemaValue(actionConfig?.field_schema, key, params[key]));
  }
  const schemaItem = schemaItemForParam(actionConfig?.field_schema, key);
  const schemaKey = schemaItem ? schemaParamKey(schemaItem, params) : "";
  if (schemaKey) {
    return clean(normalizeSchemaValue(actionConfig?.field_schema, key, params[schemaKey]));
  }
  return clean(step.value);
}

function matchingRadio(input, value) {
  const wanted = normalizeText(value);
  if (!wanted) return null;
  return radioGroup(input).find((candidate) => radioMatches(candidate, wanted)) || null;
}

function radioGroup(input) {
  const name = clean(input.getAttribute?.("name"));
  if (!name) return [input];
  const form = input.closest?.("form");
  return Array.from(
    form?.querySelectorAll?.(`input[type="radio"][name="${cssEscape(name)}"], [role="radio"][name="${cssEscape(name)}"]`) || [input],
  );
}

function radioMatches(input, wanted) {
  const text = normalizeText([input.value, labelText(input), elementText(input)].join(" "));
  return text === wanted || text.includes(wanted) || wanted.includes(text);
}

function checkboxState(value) {
  const text = normalizeText(value);
  if (["true", "yes", "y", "1", "on", "checked", "agree", "accepted"].includes(text)) return true;
  if (["false", "no", "n", "0", "off", "unchecked", "decline", "declined"].includes(text)) return false;
  return null;
}

function fieldType(field) {
  const role = clean(field.getAttribute?.("role")).toLowerCase();
  if (role === "radio" || role === "checkbox") return role;
  return clean(field.getAttribute?.("type") || field.tagName).toLowerCase();
}

function labelText(field) {
  const id = clean(field.id);
  const explicit = id ? elementText(field.ownerDocument?.querySelector?.(`label[for="${cssEscape(id)}"]`)) : "";
  return [explicit, elementText(field.closest?.("label"))].filter(Boolean).join(" ");
}

function cssEscape(value) {
  return window.CSS?.escape ? window.CSS.escape(value) : clean(value).replace(/["\\]/g, "\\$&");
}

function normalizeText(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}

function sameOriginPath(value) {
  const target = clean(value);
  if (!target || target.startsWith("javascript:") || target.startsWith("data:")) return "";

  try {
    const url = new URL(target, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}${url.hash}` || "/";
  } catch (_err) {
    return "";
  }
}

function waitMs(value) {
  const ms = Number(value);
  if (!Number.isFinite(ms) || ms < 0) return POLL_INTERVAL_MS;
  return Math.min(Math.floor(ms), MAX_WAIT_MS);
}

function numberValue(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
