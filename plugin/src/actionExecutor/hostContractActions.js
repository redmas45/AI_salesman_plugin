import { ACTIONS, ACTION_PARAMS } from "../core/constants";
import {
  hostPublishesCart,
  hostPublishesNav,
  hostPublishesProducts,
  hostPublishesSearch,
  runHostAddToCart,
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
 * Samsung phones?" wants the store's own results page, not a placard summarising
 * it. Comparison is deliberately excluded - a side-by-side placard is the useful
 * form for that one case, and it stays the only product action that opens one.
 */

const SEARCH_ACTIONS = new Set([ACTIONS.FILTER_PRODUCTS, ACTIONS.SHOW_PRODUCTS]);
const DETAIL_ACTIONS = new Set([ACTIONS.SHOW_PRODUCT_DETAIL]);

function actionParams(action) {
  return action.parameters || action.params || {};
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
  if (DETAIL_ACTIONS.has(name)) return runHostProductDetail(params);
  if (SEARCH_ACTIONS.has(name)) {
    const query = searchQuery(action);
    // Discovery: the shopper wants to see the range being described, so a query
    // the storefront matched too literally is broadened once.
    return query ? runHostSearch(query, { broadenIfSparse: true }) : null;
  }
  if (name === ACTIONS.NAVIGATE_TO) {
    const target = navTarget(action);
    return target ? runHostNavigate(target) : null;
  }
  return null;
}
