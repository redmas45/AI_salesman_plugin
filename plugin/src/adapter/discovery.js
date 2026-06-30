import { collectBarrierHints } from "./barrierHints";
import { CLICKABLE_SELECTOR, FIELD_SELECTOR, FORM_INPUT_SELECTOR } from "./controlSelectors";
import { queryElementsDeep } from "./deepDom";
import { collectRuntimeCapabilities } from "./runtimeCapabilities";
import { submitElementFor, submitTextFor } from "./submitResolver";

const REGISTER_PATH = "/v1/widget/register";
const MAX_TEXT_CHARS = 2500;
const MAX_HTML_CHARS = 6000;
const MAX_ELEMENTS = 80;
const MAX_LABEL_CHARS = 160;
const MAX_SELECTOR_CHARS = 260;
const MAX_HREF_CHARS = 600;
const MAX_FIELD_TEXT_CHARS = 160;
const MAX_FIELD_TYPE_CHARS = 40;
const ATTRIBUTES_FOR_SELECTOR = ["data-testid", "data-test", "data-action", "aria-label", "name"];
const FORM_SELECTOR = "form";
const MAX_FORM_FIELDS = 12;
const MAX_FIELD_OPTIONS = 20;
const REQUIRED_ARIA_VALUE = "true";
const OPTION_SELECTOR = "[role='option'], [role='radio'], [role='menuitemradio'], [role='menuitemcheckbox']";

function clean(value, maxChars = 0) {
  const cleaned = String(value || "").replace(/\s+/g, " ").trim();
  return maxChars > 0 ? cleaned.slice(0, maxChars) : cleaned;
}

function apiUrl(path, apiBaseUrl) {
  return new URL(path, apiBaseUrl).toString();
}

function textSample() {
  return clean(document.body?.innerText || "").slice(0, MAX_TEXT_CHARS);
}

function htmlSample() {
  const clone = document.body?.cloneNode(true);
  if (!clone) return "";
  clone.querySelectorAll("script, style, noscript, iframe").forEach((node) => node.remove());
  return String(clone.innerHTML || "").slice(0, MAX_HTML_CHARS);
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function selectorFor(element) {
  if (!element || element.nodeType !== 1) return "";
  if (element.id) return clean(`#${cssEscape(element.id)}`, MAX_SELECTOR_CHARS);

  for (const attr of ATTRIBUTES_FOR_SELECTOR) {
    const value = element.getAttribute(attr);
    if (value) return clean(`${element.tagName.toLowerCase()}[${attr}="${cssEscape(value)}"]`, MAX_SELECTOR_CHARS);
  }

  const classes = Array.from(element.classList || []).slice(0, 2);
  if (classes.length > 0) {
    return clean(`${element.tagName.toLowerCase()}.${classes.map(cssEscape).join(".")}`, MAX_SELECTOR_CHARS);
  }

  return clean(element.tagName.toLowerCase(), MAX_SELECTOR_CHARS);
}

function clickableElements() {
  return queryElementsDeep(CLICKABLE_SELECTOR)
    .slice(0, MAX_ELEMENTS)
    .map((element) => ({
      label: clean(element.innerText || element.value || element.getAttribute("aria-label") || element.getAttribute("title"), MAX_LABEL_CHARS),
      selector: selectorFor(element),
      href: clean(element.href || "", MAX_HREF_CHARS),
    }))
    .filter((element) => element.label || element.href);
}

function linkElements() {
  return queryElementsDeep("a[href]")
    .slice(0, MAX_ELEMENTS)
    .map((element) => ({
      label: clean(element.innerText || element.getAttribute("aria-label") || element.getAttribute("title"), MAX_LABEL_CHARS),
      selector: selectorFor(element),
      href: clean(element.href || "", MAX_HREF_CHARS),
    }))
    .filter((element) => element.href);
}

function formElements() {
  return queryElementsDeep(FORM_SELECTOR)
    .slice(0, MAX_ELEMENTS)
    .map((form) => {
      const input = form.querySelector(FORM_INPUT_SELECTOR);
      const submit = submitElementFor(form);
      return {
        label: formLabel(form, input, submit),
        selector: selectorFor(form),
        input_selector: selectorFor(input),
        submit_selector: selectorFor(submit),
        fields: formFields(form),
      };
    })
    .filter((form) => form.input_selector);
}

function formLabel(form, input, submit) {
  const submitText = submitTextFor(submit);
  const formText = clean(form.innerText || input?.getAttribute("placeholder") || input?.getAttribute("name") || input?.getAttribute("aria-label"));
  return clean([submitText, formText].filter(Boolean).join(" "), MAX_LABEL_CHARS);
}

function formFields(form) {
  return Array.from(form.querySelectorAll(FIELD_SELECTOR))
    .slice(0, MAX_FORM_FIELDS)
    .map((field) => ({
      selector: selectorFor(field),
      name: clean(field.getAttribute("name") || field.id || field.getAttribute("aria-label"), MAX_FIELD_TEXT_CHARS),
      label: fieldLabel(field),
      type: clean(field.getAttribute("type") || field.tagName, MAX_FIELD_TYPE_CHARS).toLowerCase(),
      placeholder: clean(field.getAttribute("placeholder"), MAX_FIELD_TEXT_CHARS),
      autocomplete: clean(field.getAttribute("autocomplete"), MAX_FIELD_TEXT_CHARS),
      required: fieldRequired(field),
      options: fieldOptions(field),
    }))
    .filter((field) => field.selector);
}

function fieldLabel(field) {
  const labels = [
    explicitFieldLabel(field),
    wrappingFieldLabel(field),
    nearbyFieldLabel(field),
    field.getAttribute("aria-label"),
  ];
  return clean(labels.find(Boolean), MAX_FIELD_TEXT_CHARS);
}

function explicitFieldLabel(field) {
  const id = field.id || field.getAttribute("id");
  if (!id) return "";
  const label = document.querySelector(`label[for="${cssEscape(id)}"]`);
  return labelTextWithoutControls(label);
}

function wrappingFieldLabel(field) {
  const parentLabel = field.closest?.("label");
  return labelTextWithoutControls(parentLabel);
}

function nearbyFieldLabel(field) {
  const container = field.parentElement;
  const containerLabel = container?.querySelector?.("label");
  if (containerLabel && !containerLabel.contains(field)) {
    return labelTextWithoutControls(containerLabel);
  }
  const previous = field.previousElementSibling;
  if (clean(previous?.tagName).toLowerCase() === "label") {
    return labelTextWithoutControls(previous);
  }
  return "";
}

function labelTextWithoutControls(label) {
  if (!label) return "";
  const clone = label.cloneNode(true);
  clone.querySelectorAll?.(`${FIELD_SELECTOR}, option`).forEach((node) => node.remove());
  return clean(clone.innerText || clone.textContent, MAX_FIELD_TEXT_CHARS);
}

function fieldRequired(field) {
  return Boolean(field.required || field.hasAttribute("required") || field.getAttribute("aria-required") === REQUIRED_ARIA_VALUE);
}

function fieldOptions(field) {
  if (field.tagName?.toLowerCase() === "select") {
    return optionElements(field.querySelectorAll("option"));
  }

  const controlledOptions = controlledFieldOptions(field);
  if (controlledOptions.length) return controlledOptions;

  const ownedOptions = optionElements(field.querySelectorAll(OPTION_SELECTOR));
  if (ownedOptions.length) return ownedOptions;

  const listId = field.getAttribute("list");
  if (listId) {
    return optionElements(document.getElementById(listId)?.querySelectorAll("option"));
  }

  const type = fieldType(field);
  if (type !== "radio" && type !== "checkbox") return [];
  const option = { label: fieldLabel(field), value: clean(field.value, MAX_FIELD_TEXT_CHARS) };
  return option.label || option.value ? [option] : [];
}

function controlledFieldOptions(field) {
  const ids = clean(`${field.getAttribute("aria-controls") || ""} ${field.getAttribute("aria-owns") || ""}`)
    .split(/\s+/)
    .filter(Boolean);
  return ids.flatMap((id) => optionElements(document.getElementById(id)?.querySelectorAll(OPTION_SELECTOR)));
}

function fieldType(field) {
  const role = clean(field.getAttribute("role")).toLowerCase();
  if (role === "radio" || role === "checkbox") return role;
  return clean(field.getAttribute("type") || field.tagName).toLowerCase();
}

function optionElements(elements) {
  return Array.from(elements || [])
    .slice(0, MAX_FIELD_OPTIONS)
    .map((option) => ({
      label: clean(option.label || option.innerText || option.textContent || option.getAttribute?.("aria-label"), MAX_FIELD_TEXT_CHARS),
      value: clean(option.value || option.getAttribute?.("data-value") || option.getAttribute?.("value"), MAX_FIELD_TEXT_CHARS),
    }))
    .filter((option) => option.label || option.value);
}

function platformHints() {
  return {
    shopify: Boolean(window.Shopify || document.querySelector('script[src*="cdn.shopify.com"]')),
    woocommerce: Boolean(document.body?.classList?.contains("woocommerce") || window.wc_add_to_cart_params),
  };
}

export async function collectDiscoveryPayload(siteId) {
  return {
    site_id: siteId,
    origin: window.location.origin,
    url: window.location.href,
    title: document.title || "",
    text_sample: textSample(),
    html_sample: htmlSample(),
    buttons: clickableElements(),
    links: linkElements(),
    forms: formElements(),
    platform_hints: platformHints(),
    barrier_hints: collectBarrierHints(),
    runtime_capabilities: await collectRuntimeCapabilities(),
  };
}

export async function registerPageDiscovery(apiBaseUrl, siteId) {
  const payload = await collectDiscoveryPayload(siteId);
  try {
    const response = await fetch(apiUrl(REGISTER_PATH, apiBaseUrl), {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) return null;
    return response.json();
  } catch (err) {
    console.warn("[AIHubAdapter] Discovery registration failed.", err);
    return null;
  }
}
