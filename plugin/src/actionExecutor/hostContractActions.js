import { ACTIONS, ACTION_PARAMS } from "../core/constants";
import {
  hostPublishesCart,
  hostPublishesNav,
  hostPublishesSearch,
  runHostAddToCart,
  runHostNavigate,
  runHostSearch,
} from "./hostContract";

/**
 * Prefer the published host contract for the two actions that must change the real
 * website - searching the storefront and adding to its cart. This executor runs
 * before the overlay/discovery executors, but only claims an action when the host
 * actually publishes the matching contract; otherwise it returns null and the
 * existing executors handle it, so a host without the contract is never regressed.
 */

const SEARCH_ACTIONS = new Set([ACTIONS.FILTER_PRODUCTS]);

function searchQuery(action) {
  const params = action.parameters || action.params || {};
  return String(
    params[ACTION_PARAMS.SEARCH_QUERY] || params.search || params.query || params.q || "",
  ).trim();
}

function navTarget(action) {
  const params = action.parameters || action.params || {};
  return String(params[ACTION_PARAMS.PAGE] || params.page || params.target || "").trim();
}

export function canExecuteHostContractAction(action) {
  const name = action.action;
  if (name === ACTIONS.ADD_TO_CART) return hostPublishesCart();
  if (SEARCH_ACTIONS.has(name)) return hostPublishesSearch() && Boolean(searchQuery(action));
  if (name === ACTIONS.NAVIGATE_TO) return hostPublishesNav() && Boolean(navTarget(action));
  return false;
}

export async function executeHostContractAction(action) {
  const name = action.action;
  const params = action.parameters || action.params || {};
  if (name === ACTIONS.ADD_TO_CART) return runHostAddToCart(params);
  if (SEARCH_ACTIONS.has(name)) {
    const query = searchQuery(action);
    return query ? runHostSearch(query) : null;
  }
  if (name === ACTIONS.NAVIGATE_TO) {
    const target = navTarget(action);
    return target ? runHostNavigate(target) : null;
  }
  return null;
}
