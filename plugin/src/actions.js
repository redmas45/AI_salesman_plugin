export function executeActions(actions) {
  actions.forEach(action => {
    console.log("ShopBot executing action:", action);
    
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
    }

    // Default behaviors
    if (action.action === "NAVIGATE_TO") {
      if (action.parameters?.page) window.location.href = action.parameters.page;
    }
    
    // Dispatch custom events so the host app (like React) can react
    window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
  });
}
