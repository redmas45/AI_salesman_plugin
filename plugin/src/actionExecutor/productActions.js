import { ACTIONS, ACTION_PARAMS, DEFAULT_RECOMMENDATION_TITLE } from "../constants";
import { showProductOverlay, sortProductOverlay } from "../productOverlay";
import { resolveProductDetailUrl } from "../productResolver";

export function canExecuteProductAction(action) {
  return (
    action.action === ACTIONS.SHOW_PRODUCTS ||
    action.action === ACTIONS.SHOW_COMPARISON ||
    action.action === ACTIONS.SHOW_PRODUCT_DETAIL ||
    action.action === ACTIONS.SORT_PRODUCTS
  );
}

export async function executeProductAction(action) {
  if (action.action === ACTIONS.SHOW_PRODUCTS || action.action === ACTIONS.SHOW_COMPARISON) {
    return showProducts(
      action.parameters || {},
      action.action === ACTIONS.SHOW_COMPARISON ? "Product comparison" : DEFAULT_RECOMMENDATION_TITLE,
    );
  }
  if (action.action === ACTIONS.SHOW_PRODUCT_DETAIL) {
    return showProductDetail(action.parameters || {});
  }
  if (action.action === ACTIONS.SORT_PRODUCTS) {
    return sortProductOverlay(action.parameters || {});
  }
  return false;
}

async function showProducts(params, fallbackTitle = DEFAULT_RECOMMENDATION_TITLE) {
  await showProductOverlay(
    params[ACTION_PARAMS.PRODUCT_IDS] || [],
    params[ACTION_PARAMS.SEARCH_QUERY] || params.title || fallbackTitle,
  );
  return true;
}

async function showProductDetail(params) {
  let productUrl = "";
  try {
    productUrl = await resolveProductDetailUrl(params[ACTION_PARAMS.PRODUCT_ID]);
  } catch (error) {
    console.warn("[AI Hub Widget] Product detail URL lookup failed:", error);
    return false;
  }

  if (!productUrl) return false;
  window.location.href = productUrl;
  return true;
}
