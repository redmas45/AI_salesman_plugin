import { ACTIONS, ACTION_PARAMS } from "../core/constants";
import {
  hostPublishesCart,
  hostPublishesCheckout,
  hostPublishesClearCart,
  hostPublishesNav,
  hostPublishesProducts,
  hostPublishesSearch,
  runHostAddToCart,
  runHostCheckout,
  runHostClearCart,
  runHostNavigate,
  runHostProductDetail,
  runHostSearch,
} from "./hostContract";

/**
 * Route an action to the published host contract, so the customer's real website
 * moves instead of an overlay standing in for it.
 *
 * This executor runs before the overlay/discovery executors, but only claims an
 * action when the host actually publishes the matching contract AND the action
 * carries what that contract needs; otherwise it returns null and the existing
 * executors handle it, so a host without the contract is never regressed.
 *
 * Ordinary discovery is deliberately included: a shopper asking "do you have
 * flagship phones?" wants the store's own results page, not a placard summarising
 * it. Comparison is deliberately excluded - a side-by-side placard is the useful
 * form for that one case, and it stays the only product action that opens one.
 */

const SEARCH_ACTIONS = new Set([ACTIONS.FILTER_PRODUCTS, ACTIONS.SHOW_PRODUCTS]);

/** The records an action says it is displaying, as identities to verify. */
function requestedRecords(action) {
  const params = action?.params || {};
  const ids = params[ACTION_PARAMS.PRODUCT_IDS] || params[ACTION_PARAMS.ENTITY_IDS] || [];
  const identities = (Array.isArray(ids) ? ids : []).map((id) => ({ id: String(id || ""), name: "" }));
  const single = params[ACTION_PARAMS.PRODUCT_NAME];
  if (!identities.length && single) identities.push({ id: "", name: String(single) });
  return identities;
}
const DETAIL_ACTIONS = new Set([ACTIONS.SHOW_PRODUCT_DETAIL]);

function actionParams(action) {
  return action.parameters || action.params || {};
}

// The turn's resolved hard constraints, as a flat map of canonical filter keys to
// scalar values (e.g. {max_price: 20000, brand: "Acme"}). The Hub speaks only
// these canonical names; the host maps each to its own URL/control syntax. Nested,
// non-scalar, or empty values are dropped so nothing malformed reaches the page.
function requestedFilters(action) {
  const raw = actionParams(action).filters;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const filters = {};
  for (const [key, value] of Object.entries(raw)) {
    if (value === null || value === undefined || value === "") continue;
    if (typeof value === "object") continue;
    filters[String(key)] = String(value);
  }
  return filters;
}

function searchQuery(action) {
  const params = actionParams(action);
  return String(
    params[ACTION_PARAMS.SEARCH_QUERY] || params.search || params.query || params.q || "",
  ).trim();
}

function navTarget(action) {
  const params = actionParams(action);
  return String(params[ACTION_PARAMS.PAGE] || params.page || params.target || "").trim();
}

/** A record is addressable when the host or the Hub named it. */
function hasRecordIdentity(action) {
  const params = actionParams(action);
  return Boolean(
    params[ACTION_PARAMS.PRODUCT_ID] ||
      params.entity_id ||
      String(params[ACTION_PARAMS.PRODUCT_NAME] || "").trim(),
  );
}

export function canExecuteHostContractAction(action) {
  const name = action.action;
  if (name === ACTIONS.ADD_TO_CART) {
    return (hostPublishesCart() || hostPublishesProducts()) && hasRecordIdentity(action);
  }
  if (name === ACTIONS.CHECKOUT) return hostPublishesCheckout();
  if (name === ACTIONS.CLEAR_CART) return hostPublishesClearCart();
  if (DETAIL_ACTIONS.has(name)) {
    return (hostPublishesProducts() || hostPublishesSearch()) && hasRecordIdentity(action);
  }
  if (SEARCH_ACTIONS.has(name)) return hostPublishesSearch() && Boolean(searchQuery(action));
  if (name === ACTIONS.NAVIGATE_TO) return hostPublishesNav() && Boolean(navTarget(action));
  return false;
}

export async function executeHostContractAction(action) {
  const name = action.action;
  const params = actionParams(action);
  if (name === ACTIONS.ADD_TO_CART) return runHostAddToCart(params);
  if (name === ACTIONS.CHECKOUT) return runHostCheckout();
  if (name === ACTIONS.CLEAR_CART) return runHostClearCart();
  if (DETAIL_ACTIONS.has(name)) return runHostProductDetail(params);
  if (SEARCH_ACTIONS.has(name)) {
    const query = searchQuery(action);
    // Discovery: the shopper wants to see the range being described, so a query
    // the storefront matched too literally is broadened once.
    // The ids and names the answer named travel with the query, so the executor
    // can prove those records are the ones on screen rather than merely proving
    // the page is not empty.
    return query
      ? runHostSearch(query, {
          broadenIfSparse: true,
          requested: requestedRecords(action),
          filters: requestedFilters(action),
        })
      : null;
  }
  if (name === ACTIONS.NAVIGATE_TO) {
    const target = navTarget(action);
    return target ? runHostNavigate(target) : null;
  }
  return null;
}
