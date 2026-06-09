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

    // Default behaviors
    if (action.action === "NAVIGATE_TO") {
      if (action.parameters?.page) window.location.href = action.parameters.page;
    }
    
    // Dispatch custom events so the host app (like React) can react
    window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
  });
}
