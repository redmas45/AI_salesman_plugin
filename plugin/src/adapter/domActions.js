import { ACTIONS, ACTION_PARAMS } from "../constants";
import { showHandoffOverlay } from "../handoffOverlay";
import { labelsForAction } from "./actionLabels";
import { missingRequiredParams, stopForMissingParams } from "./actionParams";
import { runDomSequence } from "./domSequence";
import { activateElement, enterText, submitFormElement } from "./eventDriver";
import { fillFormFields } from "./formFiller";
import { resolveProductActionPath } from "./productNavigation";
import {
  clean,
  findClickableTarget,
  findFieldTarget,
  findFormTarget,
  queryElement,
} from "./targetResolver";

const DEFAULT_NAVIGATION_ROUTES = Object.freeze({
  cart: "/cart",
  checkout: "/checkout",
  contact: "/contact",
  home: "/",
  shop: "/shop",
});

const SEARCH_INPUT_SELECTORS = Object.freeze([
  "input[type='search']",
  "input[name='q']",
  "input[name='query']",
  "input[placeholder*='Search' i]",
]);

const PRODUCT_SPECIFIC_DOM_ACTIONS = new Set([
  ACTIONS.ADD_TO_CART,
  ACTIONS.REMOVE_FROM_CART,
  ACTIONS.UPDATE_CART_QUANTITY,
]);

const AUTO_SUBMIT_ACTIONS = new Set([
  "FILTER_PRODUCTS",
  "FILTER_ENTITIES",
  "SEARCH_AVAILABILITY",
  "CHECK_AVAILABILITY",
  "CHECK_DELIVERY_AVAILABILITY",
  "MATCH_JOBS",
  "SET_LOCATION",
]);

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
  if (normalizedAction.action === ACTIONS.NAVIGATE_TO) return false;
  const actionConfig = runtimeConfig?.adapter?.actions?.[normalizedAction.action];
  if (!actionConfig || typeof actionConfig !== "object") return false;
  if (await isProductSpecificActionOnDifferentPage(normalizedAction)) return false;

  if (actionConfig.type === "navigate") {
    return navigateToPath(actionConfig.path);
  }
  if (actionConfig.type === "click") {
    if (await shouldNavigateToActionPage(normalizedAction, actionConfig)) return true;
    return clickConfiguredAction(normalizedAction.action, actionConfig);
  }
  if (actionConfig.type === "form") {
    if (await shouldNavigateToActionPage(normalizedAction, actionConfig)) return true;
    return submitConfiguredForm(normalizedAction.action, actionConfig, normalizedAction.parameters);
  }
  if (actionConfig.type === "sequence") {
    if (await shouldNavigateToActionPage(normalizedAction, actionConfig)) return true;
    const missingParams = missingRequiredParams(actionConfig, normalizedAction.parameters);
    if (missingParams.length) return stopForMissingParams(missingParams);
    return runDomSequence(actionConfig.steps, normalizedAction.parameters, runtimeConfig, actionConfig);
  }
  if (actionConfig.type === "handoff") {
    return showHandoffOverlay(normalizedAction.action, {
      ...normalizedAction.parameters,
      path: actionConfig.path,
      message: actionConfig.message,
      reason: actionConfig.reason,
    });
  }
  return false;
}

export async function executeDomFallback(action, runtimeConfig) {
  const normalizedAction = normalizeAction(action);
  if (normalizedAction.action === ACTIONS.NAVIGATE_TO) {
    return navigateToNamedPage(normalizedAction.parameters?.[ACTION_PARAMS.PAGE], runtimeConfig);
  }
  if (normalizedAction.action === ACTIONS.FILTER_PRODUCTS) {
    const searchQuery = normalizedAction.parameters?.[ACTION_PARAMS.SEARCH_QUERY];
    return submitSearch(searchQuery) || navigateToSearchPage(searchQuery, runtimeConfig);
  }
  if (normalizedAction.action === ACTIONS.RUN_DOM_SEQUENCE) {
    return runDomSequence(normalizedAction.parameters?.steps, normalizedAction.parameters, runtimeConfig);
  }
  if (normalizedAction.action === ACTIONS.CHECKOUT) {
    return navigateToNamedPage("checkout", runtimeConfig) || clickByActionLabel(normalizedAction.action);
  }
  if (normalizedAction.action === ACTIONS.ADD_TO_CART && !(await isCurrentProductAction(normalizedAction))) {
    return false;
  }
  return clickByActionLabel(normalizedAction.action);
}

function submitConfiguredForm(actionName, actionConfig, params) {
  const missingParams = missingRequiredParams(actionConfig, params);
  if (missingParams.length) return stopForMissingParams(missingParams);

  const target = findFormTarget({
    ...actionConfig,
    labels: labelsForAction(actionName, actionConfig),
  });
  const form = target.form;
  const input = target.input;
  const fillResult = fillFormFields(form, params, {
    fallbackInput: input,
    fieldSchema: actionConfig.field_schema,
  });

  const fallbackQuery = clean(params?.query || params?.search_query || params?.q);
  if (fillResult.filled === 0 && input && fallbackQuery) {
    enterText(input, fallbackQuery);
  }
  if (fillResult.total > 0 && fillResult.filled === 0 && !input) return false;
  if (!shouldSubmitForm(actionName, actionConfig)) return true;
  if (submitFormElement(form)) return true;
  return clickElement(target.submit) || clickConfiguredAction(actionName, { selector: actionConfig.submit });
}

function navigateToNamedPage(page, runtimeConfig) {
  const pageKey = clean(page).replace(/^\/+|\/+$/g, "") || "home";
  const routeMap = {
    ...DEFAULT_NAVIGATION_ROUTES,
    ...(runtimeConfig?.adapter?.routes || {}),
  };
  return navigateToPath(routeMap[pageKey] || `/${pageKey}`);
}

function navigateToSearchPage(query, runtimeConfig) {
  const searchQuery = clean(query);
  if (!searchQuery) return false;
  const routeMap = {
    ...DEFAULT_NAVIGATION_ROUTES,
    ...(runtimeConfig?.adapter?.routes || {}),
  };
  const shopPath = routeMap.shop || DEFAULT_NAVIGATION_ROUTES.shop;
  const pagePath = sameOriginPath(shopPath);
  if (!pagePath) return false;

  try {
    const url = new URL(pagePath, window.location.origin);
    url.searchParams.set("q", searchQuery);
    return navigateToPath(`${url.pathname}${url.search}${url.hash}`);
  } catch (_err) {
    return false;
  }
}

function navigateToActionPage(actionConfig, params = {}) {
  const pagePath = actionPagePath(actionConfig, params);
  if (!pagePath || pagePath === currentPagePath()) return false;
  return navigateToPath(pagePath);
}

async function shouldNavigateToActionPage(action, actionConfig) {
  if (await isCurrentProductSpecificAction(action)) return false;
  return navigateToActionPage(actionConfig, action.parameters);
}

function actionPagePath(actionConfig, params = {}) {
  const pagePath = sameOriginPath(actionConfig?.page_path || actionConfig?.pagePath || actionConfig?.source_path || actionConfig?.sourcePath);
  const searchQuery = clean(params?.[ACTION_PARAMS.SEARCH_QUERY] || params?.query || params?.q);
  if (!pagePath || !searchQuery) return pagePath;

  try {
    const url = new URL(pagePath, window.location.origin);
    url.searchParams.set("q", searchQuery);
    return `${url.pathname}${url.search}${url.hash}`;
  } catch (_err) {
    return pagePath;
  }
}

function currentPagePath() {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function sameOriginPath(path) {
  const target = clean(path);
  if (!target || /^https?:\/\//i.test(target) || target.startsWith("javascript:")) return "";
  try {
    const url = new URL(target, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}${url.hash}`;
  } catch (_err) {
    return "";
  }
}

function submitSearch(query) {
  const searchQuery = clean(query);
  if (!searchQuery) return false;

  for (const selector of SEARCH_INPUT_SELECTORS) {
    const input = queryElement(selector);
    if (!input) continue;
    enterText(input, searchQuery);
    return submitNearestForm(input);
  }
  const input = findFieldTarget({ labels: ["search", "find", "query", "keyword"] });
  if (!input) return false;
  enterText(input, searchQuery);
  return submitNearestForm(input);
}

function shouldSubmitForm(actionName, actionConfig) {
  const submitMode = clean(actionConfig.submit_mode || actionConfig.submitMode).toLowerCase();
  if (submitMode === "submit" || submitMode === "auto_submit") return true;
  if (submitMode === "fill_only" || submitMode === "prepare_only") return false;
  if (actionConfig.auto_submit === true) return true;
  return AUTO_SUBMIT_ACTIONS.has(clean(actionName).toUpperCase());
}

function submitNearestForm(input) {
  const form = input.closest("form");
  if (submitFormElement(form)) return true;
  const submitButton = form?.querySelector("button[type='submit'], input[type='submit']");
  if (activateElement(submitButton)) return true;
  input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  return true;
}

function clickByActionLabel(actionName) {
  return clickElement(findClickableTarget({ labels: labelsForAction(actionName) }));
}

function clickConfiguredAction(actionName, actionConfig) {
  const element = findClickableTarget({
    selector: actionConfig.selector,
    label: actionConfig.label,
    text: actionConfig.text,
    labels: labelsForAction(actionName, actionConfig),
  });
  return clickElement(element);
}

function clickElement(element) {
  return activateElement(element);
}

function navigateToPath(path) {
  const targetPath = clean(path);
  if (!targetPath || /^https?:\/\//i.test(targetPath)) return false;
  window.location.href = targetPath.startsWith("/") ? targetPath : `/${targetPath}`;
  return true;
}

async function isCurrentProductAction(action) {
  const targetProductId = clean(action.parameters?.[ACTION_PARAMS.PRODUCT_ID]);
  const currentProductId = readProductId();
  if (!targetProductId) return true;
  if (currentProductId && currentProductId === targetProductId) return true;

  const targetPath = await resolveProductActionPath(targetProductId);
  return Boolean(targetPath && samePath(targetPath, currentPagePath()));
}

async function isProductSpecificActionOnDifferentPage(action) {
  const actionName = clean(action.action).toUpperCase();
  if (!PRODUCT_SPECIFIC_DOM_ACTIONS.has(actionName)) return false;
  return !(await isCurrentProductAction(action));
}

async function isCurrentProductSpecificAction(action) {
  const actionName = clean(action.action).toUpperCase();
  return PRODUCT_SPECIFIC_DOM_ACTIONS.has(actionName) && (await isCurrentProductAction(action));
}

function readProductId() {
  const element = document.querySelector("[data-product-id], [data-product], [itemprop='sku']");
  return clean(element?.getAttribute("data-product-id") || element?.getAttribute("data-product") || element?.textContent) || productIdFromPath();
}

function productIdFromPath() {
  const match = window.location.pathname.match(/\/product\/([^/?#]+)/i);
  return match ? decodeURIComponent(match[1]) : "";
}

function samePath(left, right) {
  const normalize = (value) => {
    const path = sameOriginPath(value);
    return path.replace(/\/+$/, "") || "/";
  };
  return normalize(left) === normalize(right);
}
