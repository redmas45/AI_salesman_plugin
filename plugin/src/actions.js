import { showProductOverlay } from "./productOverlay";

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

class ProductOverlayAdapter {
  canHandle(action) {
    return action.action === "SHOW_PRODUCTS";
  }

  async handle(action) {
    const params = action.parameters || {};
    await showProductOverlay(params.product_ids || [], params.search_query || "Recommended products");
    return true;
  }
}

class ShopBotConfigAdapter {
  canHandle(action) {
    const hooks = window.ShopBotConfig;
    if (!hooks) return false;

    if (action.action === "ADD_TO_CART") return typeof hooks.onAddToCart === "function";
    if (action.action === "FILTER_PRODUCTS") return typeof hooks.onFilter === "function";
    if (action.action === "CHECKOUT") return typeof hooks.onCheckout === "function";
    if (action.action === "NAVIGATE_TO") {
      const page = action.parameters?.page;
      if ((page === "cart" || page === "/cart") && typeof hooks.onOpenCart === "function") {
        return true;
      }
      return typeof hooks.onNavigate === "function";
    }
    return false;
  }

  async handle(action) {
    const hooks = window.ShopBotConfig;
    if (action.action === "ADD_TO_CART") {
      await hooks.onAddToCart(action.parameters?.product_id, action.parameters?.quantity);
      return true;
    }
    if (action.action === "FILTER_PRODUCTS") {
      await hooks.onFilter(action.parameters);
      return true;
    }
    if (action.action === "CHECKOUT") {
      await hooks.onCheckout(action.parameters);
      return true;
    }
    if (action.action === "NAVIGATE_TO") {
      const page = action.parameters?.page;
      if ((page === "cart" || page === "/cart") && typeof hooks.onOpenCart === "function") {
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

    const page = action.parameters?.page;
    return (
      (action.action === "ADD_TO_CART" && typeof cart.addItem === "function") ||
      (action.action === "CLEAR_CART" && typeof cart.clear === "function") ||
      (action.action === "NAVIGATE_TO" && (page === "cart" || page === "/cart") && typeof cart.open === "function") ||
      (action.action === "CHECKOUT" && typeof cart.checkout === "function") ||
      (action.action === "SHOW_PRODUCTS" && typeof cart.showProducts === "function") ||
      (action.action === "SHOW_COMPARISON" && typeof cart.showComparison === "function") ||
      (action.action === "FILTER_PRODUCTS" && typeof cart.filterProducts === "function") ||
      (action.action === "SHOW_PRODUCT_DETAIL" && typeof cart.showProductDetail === "function") ||
      (action.action === "REMOVE_FROM_CART" && typeof cart.removeItem === "function") ||
      (action.action === "UPDATE_CART_QUANTITY" && typeof cart.updateQuantity === "function")
    );
  }

  async handle(action) {
    const cart = window.ShopCart;
    const params = action.parameters || {};

    if (action.action === "ADD_TO_CART") {
      await cart.addItem(params.product_id, params.quantity || 1);
      return true;
    }
    if (action.action === "CLEAR_CART") {
      cart.clear();
      return true;
    }
    if (action.action === "NAVIGATE_TO") {
      cart.open();
      return true;
    }
    if (action.action === "CHECKOUT") {
      await cart.checkout(params);
      return true;
    }
    if (action.action === "SHOW_PRODUCTS") {
      await cart.showProducts(params.product_ids || [], params.search_query || "Recommended products");
      return true;
    }
    if (action.action === "SHOW_COMPARISON") {
      await cart.showComparison(params.product_ids || []);
      return true;
    }
    if (action.action === "FILTER_PRODUCTS") {
      await cart.filterProducts(params);
      return true;
    }
    if (action.action === "SHOW_PRODUCT_DETAIL") {
      await cart.showProductDetail(params.product_id);
      return true;
    }
    if (action.action === "REMOVE_FROM_CART") {
      await cart.removeItem(params.product_id);
      return true;
    }
    if (action.action === "UPDATE_CART_QUANTITY") {
      await cart.updateQuantity(params.product_id, Number(params.quantity) || 0);
      return true;
    }
    return false;
  }
}

class BrowserNavigationAdapter {
  canHandle(action) {
    return action.action === "NAVIGATE_TO" && Boolean(navigationTarget(action.parameters?.page));
  }

  handle(action) {
    window.location.href = navigationTarget(action.parameters?.page);
    return true;
  }
}

class EventAdapter {
  canHandle() {
    return true;
  }

  handle(action) {
    window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
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
      console.log("ShopBot executing action:", action);

      for (const adapter of this.adapters) {
        if (!adapter.canHandle(action)) continue;
        const handled = await adapter.handle(action);
        if (handled) break;
      }
    }
  }
}

const executor = new ActionExecutor([
  new ProductOverlayAdapter(),
  new ShopBotConfigAdapter(),
  new ShopCartAdapter(),
  new BrowserNavigationAdapter(),
  new EventAdapter(),
]);

export function executeActions(actions) {
  return executor.execute(actions);
}
