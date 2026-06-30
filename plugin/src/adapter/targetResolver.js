import { CLICKABLE_SELECTOR, FIELD_SELECTOR } from "./controlSelectors";
import { queryElementDeep, queryElementsDeep } from "./deepDom";
import { submitElementFor } from "./submitResolver";

export function queryElement(selector) {
  return queryElementDeep(selector);
}

export function findClickableTarget(hints = {}) {
  const labels = normalizedHints(hints);
  const configured = queryElement(hints.selector);
  if (isClickable(configured)) {
    const childTarget = bestTextMatch(clickableChildren(configured), labels);
    return childTarget || configured;
  }

  if (!labels.length) return null;

  const candidates = queryElementsDeep(CLICKABLE_SELECTOR).filter(isVisibleElement);
  return bestTextMatch(candidates, labels);
}

export function findFieldTarget(hints = {}) {
  const configured = queryElement(hints.selector);
  if (isField(configured)) return configured;

  const labels = normalizedHints(hints);
  if (!labels.length) return null;

  const fields = queryElementsDeep(FIELD_SELECTOR).filter(isVisibleElement);
  return bestFieldMatch(fields, labels);
}

export function findFormTarget(hints = {}) {
  const configuredElement = queryElement(hints.form || hints.selector);
  const configuredInput = queryElement(hints.input);
  const configuredSubmit = queryElement(hints.submit);
  if (configuredElement || configuredInput || configuredSubmit) {
    const form = formFromElement(configuredElement) || configuredInput?.closest?.("form") || configuredSubmit?.closest?.("form");
    return {
      form: form || null,
      input: configuredInput || firstField(form),
      submit: configuredSubmit || firstSubmit(form),
    };
  }

  const labels = normalizedHints(hints);
  const forms = queryElementsDeep("form").filter(isVisibleElement);
  return bestFormMatch(forms, labels);
}

export function clean(value) {
  return String(value || "").trim();
}

export function elementText(element) {
  if (!element) return "";
  return clean(
    element.innerText ||
      element.textContent ||
      element.value ||
      element.getAttribute("aria-label") ||
      element.getAttribute("title") ||
      element.getAttribute("name") ||
      element.getAttribute("placeholder") ||
      element.getAttribute("data-testid"),
  );
}

function bestFormMatch(forms, labels) {
  for (const form of forms) {
    const text = normalizeText([elementText(form), fieldSummary(form), submitSummary(form)].join(" "));
    if (labels.some((label) => phraseMatches(text, label))) {
      return { form, input: firstField(form), submit: firstSubmit(form) };
    }
  }
  return { form: null, input: null, submit: null };
}

function bestFieldMatch(fields, labels) {
  for (const field of fields) {
    const text = normalizeText([elementText(field), field.name, field.id].join(" "));
    if (labels.some((label) => phraseMatches(text, label))) return field;
  }
  return null;
}

function bestTextMatch(elements, labels) {
  if (!labels.length) return null;
  for (const element of elements) {
    const text = normalizeText(elementText(element));
    if (labels.some((label) => text === label)) return element;
  }
  for (const element of elements) {
    const text = normalizeText(elementText(element));
    if (labels.some((label) => phraseMatches(text, label))) return element;
  }
  return null;
}

function clickableChildren(element) {
  return Array.from(element?.querySelectorAll?.(CLICKABLE_SELECTOR) || []).filter(isVisibleElement);
}

function normalizedHints(hints) {
  const values = [
    hints.label,
    hints.text,
    hints.name,
    hints.param,
    hints.parameter,
    hints.placeholder,
    ...(Array.isArray(hints.labels) ? hints.labels : []),
    ...(Array.isArray(hints.fields) ? hints.fields : []),
  ];
  return values.map(normalizeText).filter(Boolean);
}

function firstField(form) {
  return form?.querySelector?.(FIELD_SELECTOR) || null;
}

function formFromElement(element) {
  if (!element) return null;
  return clean(element.tagName).toLowerCase() === "form" ? element : element.closest?.("form") || null;
}

function firstSubmit(form) {
  return submitElementFor(form);
}

function fieldSummary(form) {
  return Array.from(form?.querySelectorAll?.(FIELD_SELECTOR) || [])
    .map((field) => [elementText(field), field.name, field.id].join(" "))
    .join(" ");
}

function submitSummary(form) {
  return elementText(submitElementFor(form));
}

function isClickable(element) {
  return Boolean(element && typeof element.click === "function" && isVisibleElement(element));
}

function isField(element) {
  if (!element || !isVisibleElement(element)) return false;
  const tag = clean(element.tagName).toLowerCase();
  const role = clean(element.getAttribute("role")).toLowerCase();
  return (
    tag === "input" ||
    tag === "select" ||
    tag === "textarea" ||
    element.isContentEditable ||
    ["checkbox", "combobox", "listbox", "radio", "searchbox", "textbox"].includes(role)
  );
}

function isVisibleElement(element) {
  if (!element) return false;
  if (element.hidden || element.getAttribute("aria-hidden") === "true") return false;
  const style = window.getComputedStyle?.(element);
  if (style && (style.display === "none" || style.visibility === "hidden")) return false;
  return true;
}

function phraseMatches(text, label) {
  if (!text || !label) return false;
  if (text.includes(label) || label.includes(text)) return true;
  const labelTokens = label.split(" ").filter(Boolean);
  return labelTokens.length > 1 && labelTokens.every((token) => text.includes(token));
}

function normalizeText(value) {
  return clean(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
