import { ACTIONS, ACTION_PARAMS, DEFAULT_RECOMMENDATION_TITLE } from "../core/constants";
import { executeWithAIHubAdapterResult } from "../core/adapterBridge";
import { showProductOverlay, sortProductOverlay } from "../overlays/productOverlay";
import { resolveProductDetailUrl } from "../catalog/productResolver";

export function canExecuteProductAction(action) {
  return (
    action.action === ACTIONS.SHOW_PRODUCTS ||
    action.action === ACTIONS.SHOW_COMPARISON ||
    action.action === ACTIONS.SHOW_PRODUCT_DETAIL ||
    action.action === ACTIONS.SORT_PRODUCTS
  );
}

export async function executeProductAction(action) {
  if (action.action === ACTIONS.SHOW_COMPARISON) {
    return showProducts(action.parameters || {}, "Product comparison", { syncListing: false });
  }
  if (action.action === ACTIONS.SHOW_PRODUCTS) {
    return showProducts(
      action.parameters || {},
      DEFAULT_RECOMMENDATION_TITLE,
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

async function showProducts(params, fallbackTitle = DEFAULT_RECOMMENDATION_TITLE, options = {}) {
  const productIds = Array.isArray(params[ACTION_PARAMS.PRODUCT_IDS])
    ? params[ACTION_PARAMS.PRODUCT_IDS]
    : [];
  const searchQuery = searchQueryFromParams(params);
  const shouldSyncListing = options.syncListing !== false;
  const listingSync = shouldSyncListing
    ? await syncProductListing(searchQuery)
    : {
        succeeded: false,
        handled: false,
        status: "skipped",
        stage: "product_display_sync",
        reason: "comparison_overlay",
      };
  const overlay = await showProductOverlay(
    productIds,
    params.title || searchQuery || fallbackTitle,
    { searchQuery },
  );
  const evidence = {
    ...(overlay.evidence || {}),
    listing_sync_status: listingSync.status || "",
    listing_sync_stage: listingSync.stage || "",
    listing_sync_reason: listingSync.reason || "",
  };

  if (overlay.status !== "succeeded") {
    return { ...overlay, evidence };
  }
  if (searchQuery && listingSync.handled && !listingSync.succeeded) {
    return {
      status: "failed",
      stage: "product_display_sync",
      reason: listingSync.reason || listingSync.status || "listing_sync_failed",
      evidence,
    };
  }
  return {
    ...overlay,
    stage: listingSync.succeeded ? "product_display_sync" : overlay.stage,
    evidence,
  };
}

async function syncProductListing(searchQuery) {
  const query = clean(searchQuery);
  if (!query) {
    return {
      succeeded: false,
      handled: false,
      status: "skipped",
      stage: "product_display_sync",
      reason: "missing_search_query",
    };
  }

  return executeWithAIHubAdapterResult({
    action: ACTIONS.FILTER_PRODUCTS,
    params: {
      [ACTION_PARAMS.SEARCH_QUERY]: query,
      query,
      q: query,
    },
  });
}

function searchQueryFromParams(params) {
  return clean(
    params[ACTION_PARAMS.SEARCH_QUERY] ||
      params.search ||
      params.query ||
      params.q ||
      "",
  );
}

function clean(value) {
  return String(value || "").trim();
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
