import { showProductOverlay } from "./productOverlay";
import { resolveProductDetailUrl } from "./productResolver";
import { executeWithAIHubAdapter, hasAIHubAdapter } from "./adapterBridge";
import {
  ACTION_PARAMS,
  ACTIONS,
  CART_PAGE_TARGETS,
  DEFAULT_RECOMMENDATION_TITLE,
  EVENTS,
} from "./constants";

function normalizeAction(action) {
  const params = action?.params || action?.parameters || {};
  return {
    ...(action || {}),
    params,
    parameters: params,
  };
}

function navigationTarget(page) {
  const raw = String(page || "").trim();
  if (!raw) return "";
  if (/^https?:\/\//i.test(raw)) return "";
  if (raw === "home" || raw === "/") return "/";

  const path = raw.replace(/^\/+|\/+$/g, "");
  return path ? `/${path}/` : "/";
}

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

class AIHubAdapterActionAdapter {
  canHandle() {
    return hasAIHubAdapter();
  }

  async handle(action) {
    return executeWithAIHubAdapter(action);
  }
}

class ProductOverlayAdapter {
  canHandle(action) {
    return action.action === ACTIONS.SHOW_PRODUCTS;
  }

  async handle(action) {
    const params = action.parameters || {};
    await showProductOverlay(
      params[ACTION_PARAMS.PRODUCT_IDS] || [],
      params[ACTION_PARAMS.SEARCH_QUERY] || DEFAULT_RECOMMENDATION_TITLE,
    );
    return true;
  }
}

class ProductDetailNavigationAdapter {
  canHandle(action) {
    return action.action === ACTIONS.SHOW_PRODUCT_DETAIL;
  }

  async handle(action) {
    let productUrl = "";
    try {
      const productId = action.parameters?.[ACTION_PARAMS.PRODUCT_ID];
      productUrl = await resolveProductDetailUrl(productId);
    } catch (error) {
      console.warn("[ShopBot] Product detail URL lookup failed:", error);
      return false;
    }

    if (!productUrl) return false;
    window.location.href = productUrl;
    return true;
  }
}

class ShopBotConfigAdapter {
  canHandle(action) {
    const hooks = window.ShopBotConfig;
    if (!hooks) return false;

    if (action.action === ACTIONS.ADD_TO_CART) return typeof hooks.onAddToCart === "function";
    if (action.action === ACTIONS.FILTER_PRODUCTS) return typeof hooks.onFilter === "function";
    if (action.action === ACTIONS.CHECKOUT) return typeof hooks.onCheckout === "function";
    if (action.action === ACTIONS.NAVIGATE_TO) {
      const page = action.parameters?.[ACTION_PARAMS.PAGE];
      if (CART_PAGE_TARGETS.has(page) && typeof hooks.onOpenCart === "function") {
        return true;
      }
      return typeof hooks.onNavigate === "function";
    }
    return false;
  }

  async handle(action) {
    const hooks = window.ShopBotConfig;
    if (action.action === ACTIONS.ADD_TO_CART) {
      await hooks.onAddToCart(
        action.parameters?.[ACTION_PARAMS.PRODUCT_ID],
        action.parameters?.[ACTION_PARAMS.QUANTITY],
      );
      return true;
    }
    if (action.action === ACTIONS.FILTER_PRODUCTS) {
      await hooks.onFilter(action.parameters);
      return true;
    }
    if (action.action === ACTIONS.CHECKOUT) {
      await hooks.onCheckout(action.parameters);
      return true;
    }
    if (action.action === ACTIONS.NAVIGATE_TO) {
      const page = action.parameters?.[ACTION_PARAMS.PAGE];
      if (CART_PAGE_TARGETS.has(page) && typeof hooks.onOpenCart === "function") {
        await hooks.onOpenCart(action.parameters);
        return true;
      }
      await hooks.onNavigate(page, action.parameters);
      return true;
    }
    return false;
  }
}

class ShopCartAdapter {
  canHandle(action) {
    const cart = window.ShopCart;
    if (!cart) return false;

    const page = action.parameters?.[ACTION_PARAMS.PAGE];
    return (
      (action.action === ACTIONS.ADD_TO_CART && typeof cart.addItem === "function") ||
      (action.action === ACTIONS.CLEAR_CART && typeof cart.clear === "function") ||
      (action.action === ACTIONS.NAVIGATE_TO && CART_PAGE_TARGETS.has(page) && typeof cart.open === "function") ||
      (action.action === ACTIONS.CHECKOUT && typeof cart.checkout === "function") ||
      (action.action === ACTIONS.SHOW_PRODUCTS && typeof cart.showProducts === "function") ||
      (action.action === ACTIONS.SHOW_COMPARISON && typeof cart.showComparison === "function") ||
      (action.action === ACTIONS.FILTER_PRODUCTS && typeof cart.filterProducts === "function") ||
      (action.action === ACTIONS.SHOW_PRODUCT_DETAIL && typeof cart.showProductDetail === "function") ||
      (action.action === ACTIONS.REMOVE_FROM_CART && typeof cart.removeItem === "function") ||
      (action.action === ACTIONS.UPDATE_CART_QUANTITY && typeof cart.updateQuantity === "function")
    );
  }

  async handle(action) {
    const cart = window.ShopCart;
    const params = action.parameters || {};

    if (action.action === ACTIONS.ADD_TO_CART) {
      await cart.addItem(params[ACTION_PARAMS.PRODUCT_ID], params[ACTION_PARAMS.QUANTITY] || 1);
      return true;
    }
    if (action.action === ACTIONS.CLEAR_CART) {
      cart.clear();
      return true;
    }
    if (action.action === ACTIONS.NAVIGATE_TO) {
      cart.open();
      return true;
    }
    if (action.action === ACTIONS.CHECKOUT) {
      await cart.checkout(params);
      return true;
    }
    if (action.action === ACTIONS.SHOW_PRODUCTS) {
      await cart.showProducts(
        params[ACTION_PARAMS.PRODUCT_IDS] || [],
        params[ACTION_PARAMS.SEARCH_QUERY] || DEFAULT_RECOMMENDATION_TITLE,
      );
      return true;
    }
    if (action.action === ACTIONS.SHOW_COMPARISON) {
      await cart.showComparison(params[ACTION_PARAMS.PRODUCT_IDS] || []);
      return true;
    }
    if (action.action === ACTIONS.FILTER_PRODUCTS) {
      await cart.filterProducts(params);
      return true;
    }
    if (action.action === ACTIONS.SHOW_PRODUCT_DETAIL) {
      await cart.showProductDetail(params[ACTION_PARAMS.PRODUCT_ID]);
      return true;
    }
    if (action.action === ACTIONS.REMOVE_FROM_CART) {
      await cart.removeItem(params[ACTION_PARAMS.PRODUCT_ID]);
      return true;
    }
    if (action.action === ACTIONS.UPDATE_CART_QUANTITY) {
      await cart.updateQuantity(
        params[ACTION_PARAMS.PRODUCT_ID],
        Number(params[ACTION_PARAMS.QUANTITY]) || 0,
      );
      return true;
    }
    return false;
  }
}

class ShopifyNativeAdapter {
  canHandle(action) {
    if (!this.isShopify()) return false;
    return (
      action.action === ACTIONS.ADD_TO_CART ||
      action.action === ACTIONS.CLEAR_CART ||
      action.action === ACTIONS.CHECKOUT ||
      action.action === ACTIONS.REMOVE_FROM_CART ||
      action.action === ACTIONS.UPDATE_CART_QUANTITY ||
      (action.action === ACTIONS.NAVIGATE_TO && CART_PAGE_TARGETS.has(action.parameters?.[ACTION_PARAMS.PAGE]))
    );
  }

  isShopify() {
    return Boolean(
      window.Shopify ||
        document.querySelector('meta[name="shopify-checkout-api-token"]') ||
        document.querySelector('script[src*="cdn.shopify.com"]'),
    );
  }

  async handle(action) {
    const params = action.parameters || {};
    if (action.action === ACTIONS.ADD_TO_CART) {
      const variantId = positiveIdentifier(params.variant_id || params.cart_id || params[ACTION_PARAMS.PRODUCT_ID]);
      if (!variantId) return false;
      return postJson("/cart/add.js", {
        items: [{ id: variantId, quantity: actionQuantity(params) }],
      });
    }
    if (action.action === ACTIONS.REMOVE_FROM_CART) {
      const lineId = positiveIdentifier(params.cart_id || params.variant_id || params[ACTION_PARAMS.PRODUCT_ID]);
      if (!lineId) return false;
      return postJson("/cart/change.js", { id: lineId, quantity: 0 });
    }
    if (action.action === ACTIONS.UPDATE_CART_QUANTITY) {
      const lineId = positiveIdentifier(params.cart_id || params.variant_id || params[ACTION_PARAMS.PRODUCT_ID]);
      if (!lineId) return false;
      return postJson("/cart/change.js", { id: lineId, quantity: actionQuantity(params, 0) });
    }
    if (action.action === ACTIONS.CLEAR_CART) {
      return postJson("/cart/clear.js", {});
    }
    if (action.action === ACTIONS.CHECKOUT) {
      window.location.href = "/checkout";
      return true;
    }
    if (action.action === ACTIONS.NAVIGATE_TO) {
      window.location.href = "/cart";
      return true;
    }
    return false;
  }
}

class WooCommerceNativeAdapter {
  canHandle(action) {
    if (!this.isWooCommerce()) return false;
    return (
      action.action === ACTIONS.ADD_TO_CART ||
      action.action === ACTIONS.CHECKOUT ||
      action.action === ACTIONS.REMOVE_FROM_CART ||
      action.action === ACTIONS.UPDATE_CART_QUANTITY ||
      (action.action === ACTIONS.NAVIGATE_TO && CART_PAGE_TARGETS.has(action.parameters?.[ACTION_PARAMS.PAGE]))
    );
  }

  isWooCommerce() {
    return Boolean(
      document.body?.classList?.contains("woocommerce") ||
        window.wc_add_to_cart_params ||
        document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'),
    );
  }

  async handle(action) {
    const params = action.parameters || {};
    if (action.action === ACTIONS.ADD_TO_CART) {
      const productId = positiveIdentifier(params.variant_id || params.cart_id || params[ACTION_PARAMS.PRODUCT_ID]);
      if (!productId) return false;
      return postJson("/wp-json/wc/store/cart/add-item", {
        id: Number(productId),
        quantity: actionQuantity(params),
      });
    }
    if (action.action === ACTIONS.REMOVE_FROM_CART) {
      const key = String(params.cart_key || params.key || "").trim();
      if (!key) return false;
      return postJson("/wp-json/wc/store/cart/remove-item", { key });
    }
    if (action.action === ACTIONS.UPDATE_CART_QUANTITY) {
      const key = String(params.cart_key || params.key || "").trim();
      if (!key) return false;
      return postJson("/wp-json/wc/store/cart/update-item", {
        key,
        quantity: actionQuantity(params, 0),
      });
    }
    if (action.action === ACTIONS.CHECKOUT) {
      window.location.href = "/checkout";
      return true;
    }
    if (action.action === ACTIONS.NAVIGATE_TO) {
      window.location.href = "/cart";
      return true;
    }
    return false;
  }
}

class BrowserNavigationAdapter {
  canHandle(action) {
    return action.action === ACTIONS.NAVIGATE_TO && Boolean(navigationTarget(action.parameters?.[ACTION_PARAMS.PAGE]));
  }

  handle(action) {
    window.location.href = navigationTarget(action.parameters?.[ACTION_PARAMS.PAGE]);
    return true;
  }
}

class EventAdapter {
  canHandle() {
    return true;
  }

  handle(action) {
    window.dispatchEvent(new CustomEvent(EVENTS.SHOPBOT_ACTION, { detail: action }));
    return true;
  }
}

class ActionExecutor {
  constructor(adapters) {
    this.adapters = adapters;
  }

  async execute(actions) {
    for (const rawAction of actions || []) {
      const action = normalizeAction(rawAction);
      if (!action.action) continue;

      for (const adapter of this.adapters) {
        if (!adapter.canHandle(action)) continue;
        const handled = await adapter.handle(action);
        if (handled) break;
      }
    }
  }
}

const executor = new ActionExecutor([
  new AIHubAdapterActionAdapter(),
  new ProductOverlayAdapter(),
  new ProductDetailNavigationAdapter(),
  new ShopBotConfigAdapter(),
  new ShopCartAdapter(),
  new ShopifyNativeAdapter(),
  new WooCommerceNativeAdapter(),
  new BrowserNavigationAdapter(),
  new EventAdapter(),
]);

export function executeActions(actions) {
  return executor.execute(actions);
}
