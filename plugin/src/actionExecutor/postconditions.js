import { readPageState } from "../adapter/runtime/visibleEntities";
import { takePendingPostcondition } from "./pendingPostcondition";

/**
 * Typed postconditions: what the page must actually look like for an action to
 * count as done.
 *
 * An executor returning `true` only proves that a code path ran without
 * throwing. It does not prove the customer's screen changed. Maya used that
 * return value as evidence, so a sort that silently did nothing, an overlay that
 * rendered no rows, or a filter the site ignored were all reported as success.
 *
 * Each action family therefore declares an observable postcondition, checked
 * against a fresh reading of the page after execution. Families with nothing
 * observable declare none and are left exactly as the executor reported them -
 * this adds evidence where evidence exists and never invents it where it does not.
 */

export const POSTCONDITION_FAMILY = Object.freeze({
  DISPLAY: "display",
  NAVIGATION: "navigation",
  DETAIL: "detail",
  FILTER: "filter",
  SORT: "sort",
  CART: "cart",
  NONE: "none",
});

export const POSTCONDITION_TIMEOUT_MS = 1200;
export const POSTCONDITION_POLL_MS = 60;

const FAMILY_BY_ACTION = Object.freeze({
  SHOW_PRODUCTS: POSTCONDITION_FAMILY.DISPLAY,
  SHOW_ENTITIES: POSTCONDITION_FAMILY.DISPLAY,
  SHOW_COMPARISON: POSTCONDITION_FAMILY.DISPLAY,
  COMPARE_ENTITIES: POSTCONDITION_FAMILY.DISPLAY,
  NAVIGATE_TO: POSTCONDITION_FAMILY.NAVIGATION,
  SHOW_PRODUCT_DETAIL: POSTCONDITION_FAMILY.DETAIL,
  OPEN_ENTITY_DETAIL: POSTCONDITION_FAMILY.DETAIL,
  FILTER_PRODUCTS: POSTCONDITION_FAMILY.FILTER,
  CLEAR_FILTERS: POSTCONDITION_FAMILY.FILTER,
  SORT_PRODUCTS: POSTCONDITION_FAMILY.SORT,
  SORT_ENTITIES: POSTCONDITION_FAMILY.SORT,
  ADD_TO_CART: POSTCONDITION_FAMILY.CART,
  REMOVE_FROM_CART: POSTCONDITION_FAMILY.CART,
  UPDATE_CART_QUANTITY: POSTCONDITION_FAMILY.CART,
  CLEAR_CART: POSTCONDITION_FAMILY.CART,
});

const CART_COUNT_SELECTOR =
  "[data-cart-count], [data-testid='cart-count'], .cart-count, #cart-count";

export function familyForAction(actionName) {
  return FAMILY_BY_ACTION[String(actionName || "").toUpperCase()] || POSTCONDITION_FAMILY.NONE;
}

export function observePage() {
  const state = readPageState();
  return {
    path: state.route.path,
    search: state.route.search,
    filters: state.filters,
    sort: String(state.sort || "").toLowerCase(),
    visibleIds: state.visible_entities.map((entity) => String(entity.id)),
    cartCount: readCartCount(),
  };
}

function readCartCount() {
  const element = document.querySelector(CART_COUNT_SELECTOR);
  if (!element) return null;
  const raw = element.getAttribute("data-cart-count") ?? element.textContent;
  const parsed = Number.parseInt(String(raw || "").replace(/[^\d-]/g, ""), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function requestedIds(params) {
  const ids = [];
  for (const key of ["product_ids", "entity_ids"]) {
    if (Array.isArray(params[key])) ids.push(...params[key].map(String));
  }
  for (const key of ["product_id", "entity_id"]) {
    if (params[key]) ids.push(String(params[key]));
  }
  return ids;
}

function normalizePath(value) {
  const path = String(value || "").split("?")[0].split("#")[0];
  return path.length > 1 ? path.replace(/\/+$/, "") : path;
}

function normalizeRouteKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9/_\s-]+/g, " ")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\s+/g, "-");
}

function sameOriginPath(value) {
  const raw = String(value || "").trim();
  if (!raw || /^(?:javascript:|data:|\/\/)/i.test(raw)) return "";
  try {
    const url = new URL(raw, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return normalizePath(url.pathname || "/");
  } catch (_err) {
    return "";
  }
}

function requestedNavigationPath(page) {
  const raw = String(page || "").trim();
  if (!raw) return "";
  if (raw === "/" || normalizeRouteKey(raw) === "home") return "/";

  const routes =
    window.AIHubAdapterRuntime?.config?.adapter?.routes ||
    window.AIHubAdapter?.config?.adapter?.routes ||
    {};
  const requestedKey = normalizeRouteKey(raw);
  for (const [key, value] of Object.entries(routes)) {
    if (normalizeRouteKey(key) !== requestedKey) continue;
    const mapped = sameOriginPath(value);
    if (mapped) return mapped;
  }

  if (raw.startsWith("/") || /^https?:\/\//i.test(raw)) return sameOriginPath(raw);
  return normalizePath(`/${requestedKey}`);
}

function checkDisplay(params, observation) {
  const wanted = requestedIds(params);
  if (!wanted.length) {
    return observation.visibleIds.length > 0
      ? { satisfied: true, reason: "" }
      : { satisfied: false, reason: "nothing_visible" };
  }
  const missing = wanted.filter((id) => !observation.visibleIds.includes(id));
  return missing.length
    ? { satisfied: false, reason: "requested_records_not_visible" }
    : { satisfied: true, reason: "" };
}

function checkNavigation(params, observation, before) {
  const target = requestedNavigationPath(params.page);
  const current = normalizePath(observation.path);
  if (target && current === target) return { satisfied: true, reason: "" };
  if (!target && current !== normalizePath(before.path)) return { satisfied: true, reason: "" };
  if (target && current !== normalizePath(before.path)) {
    return { satisfied: false, reason: "wrong_route" };
  }
  return { satisfied: false, reason: "route_unchanged" };
}

function checkDetail(params, observation, before) {
  const wanted = requestedIds(params)[0];
  if (!wanted) return { satisfied: false, reason: "no_record_requested" };
  const route = `${observation.path}${observation.search}`;
  if (route.includes(wanted)) return { satisfied: true, reason: "" };
  if (observation.visibleIds.includes(wanted) && observation.path !== before.path) {
    return { satisfied: true, reason: "" };
  }
  return { satisfied: false, reason: "record_not_opened" };
}

function checkFilter(actionName, params, observation) {
  if (actionName === "CLEAR_FILTERS") {
    return Object.keys(observation.filters).length === 0
      ? { satisfied: true, reason: "" }
      : { satisfied: false, reason: "filters_still_active" };
  }
  const normalizedApplied = new Map(
    Object.entries(observation.filters).map(([key, value]) => [
      key.toLowerCase(),
      normalizeFilterValue(value),
    ]),
  );
  const requested = params.filters && typeof params.filters === "object" ? params.filters : params;
  const ignored = new Set([
    "product_ids", "entity_ids", "page", "search_query", "query", "q", "request_id",
  ]);
  const meaningful = Object.entries(requested || {}).filter(
    ([key, value]) => !ignored.has(key.toLowerCase()) && normalizeFilterValue(value),
  );
  if (!meaningful.length) {
    return normalizedApplied.size > 0
      ? { satisfied: true, reason: "" }
      : { satisfied: false, reason: "no_filter_observed" };
  }
  const matches = meaningful.every(([key, value]) => {
    const observed = normalizedApplied.get(key.toLowerCase());
    return observed !== undefined && observed === normalizeFilterValue(value);
  });
  return matches
    ? { satisfied: true, reason: "" }
    : { satisfied: false, reason: "filter_value_mismatch" };
}

function normalizeFilterValue(value) {
  const parts = Array.isArray(value) ? value : [value];
  return parts
    .map((part) => String(part ?? "").trim().toLowerCase())
    .filter(Boolean)
    .sort()
    .join(",");
}

function checkSort(params, observation, before) {
  const wanted = String(params.sort_by || "").toLowerCase();
  if (wanted && observation.sort && observation.sort.includes(wanted.split("_")[0])) {
    return { satisfied: true, reason: "" };
  }
  const orderChanged = observation.visibleIds.join(",") !== before.visibleIds.join(",");
  return orderChanged
    ? { satisfied: true, reason: "" }
    : { satisfied: false, reason: "order_unchanged" };
}

function checkCart(actionName, observation, before) {
  if (before.cartCount === null || observation.cartCount === null) {
    return { satisfied: false, reason: "cart_state_unobservable" };
  }
  const increased = observation.cartCount > before.cartCount;
  const decreased = observation.cartCount < before.cartCount;
  if (actionName === "ADD_TO_CART") {
    return increased ? { satisfied: true, reason: "" } : { satisfied: false, reason: "cart_unchanged" };
  }
  if (actionName === "REMOVE_FROM_CART") {
    return decreased ? { satisfied: true, reason: "" } : { satisfied: false, reason: "cart_unchanged" };
  }
  if (actionName === "CLEAR_CART") {
    return observation.cartCount === 0
      ? { satisfied: true, reason: "" }
      : { satisfied: false, reason: "cart_not_empty" };
  }
  return observation.cartCount !== before.cartCount
    ? { satisfied: true, reason: "" }
    : { satisfied: false, reason: "cart_unchanged" };
}

export function checkPostcondition(action, observation, before) {
  const name = String(action?.action || "").toUpperCase();
  const params = action?.parameters || action?.params || {};
  const family = familyForAction(name);
  if (family === POSTCONDITION_FAMILY.DISPLAY) return checkDisplay(params, observation);
  if (family === POSTCONDITION_FAMILY.NAVIGATION) return checkNavigation(params, observation, before);
  if (family === POSTCONDITION_FAMILY.DETAIL) return checkDetail(params, observation, before);
  if (family === POSTCONDITION_FAMILY.FILTER) return checkFilter(name, params, observation);
  if (family === POSTCONDITION_FAMILY.SORT) return checkSort(params, observation, before);
  if (family === POSTCONDITION_FAMILY.CART) return checkCart(name, observation, before);
  return { satisfied: true, reason: "no_postcondition" };
}

/**
 * Observe the page until the action's postcondition holds, or until the budget
 * expires. Returns the verdict plus the reason, which the caller records as
 * evidence so a failure is diagnosable rather than merely "unverified".
 */
export async function verifyPostcondition(action, before) {
  const family = familyForAction(action?.action);
  if (family === POSTCONDITION_FAMILY.NONE) {
    return { family, verified: true, reason: "no_postcondition" };
  }
  const deadline = Date.now() + POSTCONDITION_TIMEOUT_MS;
  let verdict = { satisfied: false, reason: "not_observed" };
  while (Date.now() < deadline) {
    verdict = checkPostcondition(action, observePage(), before);
    if (verdict.satisfied) break;
    await sleep(POSTCONDITION_POLL_MS);
  }
  return { family, verified: verdict.satisfied, reason: verdict.reason };
}

/**
 * Re-check a postcondition that was recorded before the page navigated away.
 *
 * Runs once when the widget boots on the destination page. The record is
 * consumed whether or not it is satisfied, so a stale entry can never make a
 * later, unrelated turn look successful.
 */
export function resumePendingPostcondition(siteId) {
  const record = takePendingPostcondition(siteId);
  if (!record) return null;
  const observed = observePage();
  const target = String(record.target_path || "").split("?")[0];
  const routeReached = !target || normalizePath(observed.path) === normalizePath(target);
  const idsPresent =
    record.ids.length === 0 || record.ids.some((id) => observed.visibleIds.includes(String(id)));
  return {
    action: record.action,
    ids: record.ids,
    verified: routeReached && idsPresent,
    reason: routeReached ? (idsPresent ? "" : "record_not_present") : "route_not_reached",
  };
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
