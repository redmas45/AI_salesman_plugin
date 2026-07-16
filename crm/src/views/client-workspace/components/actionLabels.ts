import { labelize } from '../../../utils/format';

const ACTION_LABELS: Record<string, string> = {
  ADD_TO_CART: 'Add to cart',
  CHECKOUT: 'Checkout',
  CLEAR_CART: 'Clear cart',
  CLEAR_FILTERS: 'Clear filters',
  CLEAR_HISTORY: 'Clear history',
  CAPTURE_LEAD: 'Capture lead',
  COMPARE_ENTITIES: 'Compare records',
  FILTER_PRODUCTS: 'Filter records',
  FILTER_ENTITIES: 'Filter records',
  HANDOFF_TO_AGENT: 'Agent handoff',
  HANDOFF_TO_HUMAN: 'Human handoff',
  HANDOFF_TO_LICENSED_AGENT: 'Licensed agent handoff',
  NAVIGATE_TO: 'Navigate',
  OPEN_CLAIM_FLOW: 'Open claims',
  OPEN_CONTACT: 'Open contact',
  OPEN_POLICY: 'Open policy',
  OPEN_RENEWAL_FLOW: 'Open renewal',
  REMOVE_FROM_CART: 'Remove from cart',
  SHOW_COMPARISON: 'Compare records',
  SHOW_ENTITIES: 'Show records',
  SHOW_PRODUCTS: 'Show records',
  SHOW_PRODUCT_DETAIL: 'Record detail',
  SORT_ENTITIES: 'Sort records',
  SORT_PRODUCTS: 'Sort records',
  START_QUOTE: 'Start quote',
  UPDATE_CART_QUANTITY: 'Update quantity',
  UPDATE_PREFERENCES: 'Update preferences',
};

export function actionLabel(action: string): string {
  return ACTION_LABELS[action] || labelize(action);
}
