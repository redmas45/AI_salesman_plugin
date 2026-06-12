function navigationTarget(page) {
  const raw = String(page || "").trim();
  if (!raw) return "";
  if (/^https?:\/\//i.test(raw)) return "";
  if (raw === "home" || raw === "/") return "/";

  const path = raw.replace(/^\/+|\/+$/g, "");
  return path ? `/${path}/` : "/";
}

export function executeActions(actions) {
  actions.forEach(action => {
    console.log("ShopBot executing action:", action);

    // Normalize both params and parameters keys to ensure compatibility
    const params = action.params || action.parameters || {};
    action.params = params;
    action.parameters = params;
    
    // Look for site owner overrides
    if (window.ShopBotConfig) {
      if (action.action === "ADD_TO_CART" && window.ShopBotConfig.onAddToCart) {
        window.ShopBotConfig.onAddToCart(action.parameters?.product_id, action.parameters?.quantity);
        return;
      }
      if (action.action === "FILTER_PRODUCTS" && window.ShopBotConfig.onFilter) {
        window.ShopBotConfig.onFilter(action.parameters);
        return;
      }
    }

    // Native Cart Integrations
    if (window.ShopCart) {
      if (action.action === "ADD_TO_CART") {
        window.ShopCart.addItem(action.parameters?.product_id, action.parameters?.quantity || 1);
        return;
      }
      if (action.action === "CLEAR_CART") {
        window.ShopCart.clear();
        return;
      }
      if (action.action === "NAVIGATE_TO" && (action.parameters?.page === "cart" || action.parameters?.page === "/cart")) {
        window.ShopCart.open();
        return;
      }
      if (action.action === "CHECKOUT" && window.ShopCart.checkout) {
        window.ShopCart.checkout(action.parameters);
        return;
      }
    }

    // Default behaviors
    if (action.action === "NAVIGATE_TO") {
      const target = navigationTarget(action.parameters?.page);
      if (target) window.location.href = target;
    }
    
    // Dispatch custom events so the host app (like React) can react
    window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
  });
}
