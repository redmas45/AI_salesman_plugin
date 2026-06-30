import { executeWithAIHubAdapterResult, hasAIHubAdapter } from "../adapterBridge";
import { ACTIONS } from "../constants";

export const STOP_ACTION_FALLBACK = "stop_action_fallback";
const PRODUCT_OVERLAY_ACTIONS = new Set([
  ACTIONS.SHOW_PRODUCTS,
  ACTIONS.SHOW_COMPARISON,
  ACTIONS.SHOW_PRODUCT_DETAIL,
  ACTIONS.SORT_PRODUCTS,
]);

export function canExecuteRuntimeAction(action) {
  return hasAIHubAdapter() && !PRODUCT_OVERLAY_ACTIONS.has(action.action);
}

export async function executeRuntimeAction(action) {
  const result = await executeWithAIHubAdapterResult(action);
  if (result.succeeded) return true;
  if (result.blocked || result.disabled) return STOP_ACTION_FALLBACK;
  return false;
}
