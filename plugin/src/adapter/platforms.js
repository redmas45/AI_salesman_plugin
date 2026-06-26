import { ACTIONS, ACTION_PARAMS, CART_PAGE_TARGETS } from "../constants";

const PLATFORM_SHOPIFY = "shopify";
const PLATFORM_WOOCOMMERCE = "woocommerce";
const PLATFORM_CUSTOM = "custom";

function positiveIdentifier(value) {
  const text = String(value || "").trim();
  return /^\d+$/.test(text) ? text : "";
}

function actionQuantity(params, fallback = 1) {
  const quantity = Number(params?.[ACTION_PARAMS.QUANTITY]);
  return Number.isFinite(quantity) && quantity > 0 ? Math.floor(quantity) : fallback;
}

async function postJson(path, payload) {
  const response = await fetch(new URL(path, window.location.origin), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    credentials: "same-origin",
  });
  return response.ok;
}

export function detectPlatform() {
  if (isShopify()) return PLATFORM_SHOPIFY;
  if (isWooCommerce()) return PLATFORM_WOOCOMMERCE;
  return PLATFORM_CUSTOM;
}

export async function executePlatformAction(action) {
  const platform = detectPlatform();
  if (platform === PLATFORM_SHOPIFY) {
    return executeShopifyAction(action);
  }
  if (platform === PLATFORM_WOOCOMMERCE) {
    return executeWooCommerceAction(action);
  }
  return false;
}

function isShopify() {
  return Boolean(
    window.Shopify ||
      document.querySelector('meta[name="shopify-checkout-api-token"]') ||
      document.querySelector('script[src*="cdn.shopify.com"]'),
  );
}

function isWooCommerce() {
  return Boolean(
    document.body?.classList?.contains("woocommerce") ||
      window.wc_add_to_cart_params ||
      document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'),
  );
}

async function executeShopifyAction(action) {
  const params = action.parameters || {};
  if (action.action === ACTIONS.ADD_TO_CART) {
    const variantId = positiveIdentifier(params.variant_id || params.cart_id || params[ACTION_PARAMS.PRODUCT_ID]);
    return variantId ? postJson("/cart/add.js", { items: [{ id: variantId, quantity: actionQuantity(params) }] }) : false;
  }
  if (action.action === ACTIONS.REMOVE_FROM_CART) {
    const lineId = positiveIdentifier(params.cart_id || params.variant_id || params[ACTION_PARAMS.PRODUCT_ID]);
    return lineId ? postJson("/cart/change.js", { id: lineId, quantity: 0 }) : false;
  }
  if (action.action === ACTIONS.UPDATE_CART_QUANTITY) {
    const lineId = positiveIdentifier(params.cart_id || params.variant_id || params[ACTION_PARAMS.PRODUCT_ID]);
    return lineId ? postJson("/cart/change.js", { id: lineId, quantity: actionQuantity(params, 0) }) : false;
  }
  if (action.action === ACTIONS.CLEAR_CART) return postJson("/cart/clear.js", {});
  if (action.action === ACTIONS.CHECKOUT) return navigateToPath("/checkout");
  if (isCartNavigation(action)) return navigateToPath("/cart");
  return false;
}

async function executeWooCommerceAction(action) {
  const params = action.parameters || {};
  if (action.action === ACTIONS.ADD_TO_CART) {
    const productId = positiveIdentifier(params.variant_id || params.cart_id || params[ACTION_PARAMS.PRODUCT_ID]);
    return productId ? postJson("/wp-json/wc/store/cart/add-item", { id: Number(productId), quantity: actionQuantity(params) }) : false;
  }
  if (action.action === ACTIONS.REMOVE_FROM_CART) {
    const key = String(params.cart_key || params.key || "").trim();
    return key ? postJson("/wp-json/wc/store/cart/remove-item", { key }) : false;
  }
  if (action.action === ACTIONS.UPDATE_CART_QUANTITY) {
    const key = String(params.cart_key || params.key || "").trim();
    return key ? postJson("/wp-json/wc/store/cart/update-item", { key, quantity: actionQuantity(params, 0) }) : false;
  }
  if (action.action === ACTIONS.CHECKOUT) return navigateToPath("/checkout");
  if (isCartNavigation(action)) return navigateToPath("/cart");
  return false;
}

function isCartNavigation(action) {
  return action.action === ACTIONS.NAVIGATE_TO && CART_PAGE_TARGETS.has(action.parameters?.[ACTION_PARAMS.PAGE]);
}

function navigateToPath(path) {
  window.location.href = path;
  return true;
}
