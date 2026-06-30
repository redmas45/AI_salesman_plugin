import { ACTIONS, ACTION_PARAMS, DEFAULT_CART_QUANTITY } from "../constants";

function clean(value) {
  return String(value || "").trim();
}

function paramsFor(action) {
  return action?.params || action?.parameters || {};
}

function positiveQuantity(value) {
  const quantity = Number(value || DEFAULT_CART_QUANTITY);
  return Number.isFinite(quantity) && quantity > 0 ? quantity : DEFAULT_CART_QUANTITY;
}

function clientApi() {
  if (window.AIHubClient && typeof window.AIHubClient === "object") {
    return window.AIHubClient;
  }
  if (window.__AIHUB_CLIENT__ && typeof window.__AIHUB_CLIENT__ === "object") {
    return window.__AIHUB_CLIENT__;
  }
  return null;
}

export async function executeClientHookAction(action) {
  const actionName = clean(action?.action).toUpperCase();
  const params = paramsFor(action);

  if (actionName === ACTIONS.ADD_TO_CART) {
    return addToCart(params);
  }
  if (actionName === ACTIONS.CHECKOUT) {
    return checkout();
  }
  if (actionName === ACTIONS.SHOW_PRODUCT_DETAIL) {
    return showProductDetail(params);
  }
  if (actionName === ACTIONS.FILTER_PRODUCTS) {
    return filterProducts(params);
  }
  if (actionName === ACTIONS.NAVIGATE_TO) {
    return navigateTo(params);
  }
  return false;
}

async function addToCart(params) {
  const productId = clean(params[ACTION_PARAMS.PRODUCT_ID] || params.productId || params.id);
  if (!productId) return false;
  const quantity = positiveQuantity(params[ACTION_PARAMS.QUANTITY] || params.quantity);

  const client = clientApi();
  if (typeof client?.addToCart === "function") {
    await client.addToCart({ productId, quantity, params });
    return true;
  }
  return false;
}

function checkout() {
  const client = clientApi();
  if (typeof client?.checkout === "function") {
    client.checkout();
    return true;
  }
  return false;
}

function showProductDetail(params) {
  const productId = clean(params[ACTION_PARAMS.PRODUCT_ID] || params.productId || params.id);
  if (!productId) return false;

  const client = clientApi();
  if (typeof client?.showProductDetail === "function") {
    client.showProductDetail({ productId, params });
    return true;
  }
  return false;
}

function filterProducts(params) {
  const client = clientApi();
  if (typeof client?.filterProducts === "function") {
    client.filterProducts(params);
    return true;
  }
  return false;
}

function navigateTo(params) {
  const page = clean(params[ACTION_PARAMS.PAGE] || params.page || params.path);
  if (!page) return false;

  const client = clientApi();
  if (typeof client?.navigateTo === "function") {
    client.navigateTo({ page, params });
    return true;
  }
  return false;
}
