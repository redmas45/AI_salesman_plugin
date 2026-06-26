import { ACTIONS, ACTION_PARAMS } from "../constants";

const DEFAULT_NAVIGATION_ROUTES = Object.freeze({
  cart: "/cart",
  checkout: "/checkout",
  contact: "/contact",
  home: "/",
  shop: "/shop",
});

const ACTION_BUTTON_LABELS = Object.freeze({
  [ACTIONS.ADD_TO_CART]: ["add to cart", "add cart", "buy now"],
  [ACTIONS.CHECKOUT]: ["checkout", "place order", "buy now"],
  START_BOOKING: ["book now", "reserve", "check availability"],
  START_QUOTE: ["get quote", "request quote", "start quote"],
  REQUEST_APPOINTMENT: ["book appointment", "request appointment", "schedule"],
  CAPTURE_LEAD: ["contact", "submit", "send"],
});

const SEARCH_INPUT_SELECTORS = Object.freeze([
  "input[type='search']",
  "input[name='q']",
  "input[name='query']",
  "input[placeholder*='Search' i]",
]);

const BUTTON_SELECTOR = "button, a, input[type='button'], input[type='submit']";

function clean(value) {
  return String(value || "").trim();
}

function normalizeAction(action) {
  const params = action?.params || action?.parameters || {};
  return {
    ...(action || {}),
    action: clean(action?.action).toUpperCase(),
    params,
    parameters: params,
  };
}

export async function executeConfiguredAction(action, runtimeConfig) {
  const normalizedAction = normalizeAction(action);
  const actionConfig = runtimeConfig?.adapter?.actions?.[normalizedAction.action];
  if (!actionConfig || typeof actionConfig !== "object") return false;

  if (actionConfig.type === "navigate") {
    return navigateToPath(actionConfig.path);
  }
  if (actionConfig.type === "click") {
    return clickSelector(actionConfig.selector);
  }
  if (actionConfig.type === "form") {
    return submitConfiguredForm(actionConfig, normalizedAction.parameters);
  }
  return false;
}

export async function executeDomFallback(action, runtimeConfig) {
  const normalizedAction = normalizeAction(action);
  if (normalizedAction.action === ACTIONS.NAVIGATE_TO) {
    return navigateToNamedPage(normalizedAction.parameters?.[ACTION_PARAMS.PAGE], runtimeConfig);
  }
  if (normalizedAction.action === ACTIONS.FILTER_PRODUCTS) {
    return submitSearch(normalizedAction.parameters?.[ACTION_PARAMS.SEARCH_QUERY]);
  }
  if (normalizedAction.action === ACTIONS.CHECKOUT) {
    return navigateToNamedPage("checkout", runtimeConfig) || clickByActionLabel(normalizedAction.action);
  }
  if (normalizedAction.action === ACTIONS.ADD_TO_CART && !isCurrentProductAction(normalizedAction)) {
    return false;
  }
  return clickByActionLabel(normalizedAction.action);
}

export function readPageContext() {
  return {
    title: document.title || "",
    url: window.location.href,
    path: window.location.pathname,
    platformHints: platformHints(),
    productId: readProductId(),
  };
}

function submitConfiguredForm(actionConfig, params) {
  const form = queryElement(actionConfig.form);
  const input = queryElement(actionConfig.input);
  if (!input) return false;

  setNativeValue(input, clean(params?.query || params?.search_query || params?.q));
  dispatchInputEvents(input);
  if (form && typeof form.requestSubmit === "function") {
    form.requestSubmit();
    return true;
  }
  return clickSelector(actionConfig.submit);
}

function navigateToNamedPage(page, runtimeConfig) {
  const pageKey = clean(page).replace(/^\/+|\/+$/g, "") || "home";
  const routeMap = {
    ...DEFAULT_NAVIGATION_ROUTES,
    ...(runtimeConfig?.adapter?.routes || {}),
  };
  return navigateToPath(routeMap[pageKey] || `/${pageKey}`);
}

function submitSearch(query) {
  const searchQuery = clean(query);
  if (!searchQuery) return false;

  for (const selector of SEARCH_INPUT_SELECTORS) {
    const input = queryElement(selector);
    if (!input) continue;
    setNativeValue(input, searchQuery);
    dispatchInputEvents(input);
    return submitNearestForm(input);
  }
  return false;
}

function submitNearestForm(input) {
  const form = input.closest("form");
  if (form && typeof form.requestSubmit === "function") {
    form.requestSubmit();
    return true;
  }
  const submitButton = form?.querySelector("button[type='submit'], input[type='submit']");
  if (submitButton) {
    submitButton.click();
    return true;
  }
  input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  return true;
}

function clickByActionLabel(actionName) {
  const labels = ACTION_BUTTON_LABELS[actionName] || [];
  for (const label of labels) {
    const element = findClickableByText(label);
    if (!element) continue;
    element.click();
    return true;
  }
  return false;
}

function clickSelector(selector) {
  const element = queryElement(selector);
  if (!element) return false;
  element.click();
  return true;
}

function navigateToPath(path) {
  const targetPath = clean(path);
  if (!targetPath || /^https?:\/\//i.test(targetPath)) return false;
  window.location.href = targetPath.startsWith("/") ? targetPath : `/${targetPath}`;
  return true;
}

function queryElement(selector) {
  if (!selector || typeof selector !== "string") return null;
  try {
    return document.querySelector(selector);
  } catch (_err) {
    return null;
  }
}

function findClickableByText(label) {
  const expected = clean(label).toLowerCase();
  if (!expected) return null;

  for (const element of document.querySelectorAll(BUTTON_SELECTOR)) {
    const text = clean(element.innerText || element.value || element.getAttribute("aria-label")).toLowerCase();
    if (text.includes(expected)) return element;
  }
  return null;
}

function setNativeValue(input, value) {
  const prototype = Object.getPrototypeOf(input);
  const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
  if (descriptor?.set) {
    descriptor.set.call(input, value);
    return;
  }
  input.value = value;
}

function dispatchInputEvents(input) {
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function readProductId() {
  const element = document.querySelector("[data-product-id], [data-product], [itemprop='sku']");
  return clean(element?.getAttribute("data-product-id") || element?.getAttribute("data-product") || element?.textContent);
}

function isCurrentProductAction(action) {
  const targetProductId = clean(action.parameters?.[ACTION_PARAMS.PRODUCT_ID]);
  const currentProductId = readProductId();
  if (!targetProductId) return true;
  return Boolean(currentProductId && currentProductId === targetProductId);
}

function platformHints() {
  return {
    shopify: Boolean(window.Shopify || document.querySelector('script[src*="cdn.shopify.com"]')),
    woocommerce: Boolean(document.body?.classList?.contains("woocommerce") || window.wc_add_to_cart_params),
  };
}
