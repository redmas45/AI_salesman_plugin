/**
 * Drive a host website through the vertical-neutral `data-aihub-role` contract it
 * publishes, and prove the page actually changed.
 *
 * Nothing here knows any site's routes, CSS, categories, or product names. A host
 * that publishes the contract can be searched, navigated and added-to-cart by the
 * same code, whatever its vertical; a host that does not publish it gets a precise
 * unsupported-host result, never a fabricated success. Every claim these modules
 * return is backed by a re-read of the DOM after the action settled - a click that
 * returned without throwing is not treated as proof.
 *
 * This module is the stable public name. The capabilities live in focused modules
 * beside it: shared role/identity vocabulary, search, product records, navigation.
 */

export {
  AIHUB_ENTITY_NAME_ATTR,
  AIHUB_NAV_ATTR,
  AIHUB_ROLE,
  hostPublishesCart,
  hostPublishesNav,
  hostPublishesProducts,
  hostPublishesSearch,
  normalizeProductName,
  productCardName,
  productCards,
  resolveProductCard,
} from "./hostContractDom";
export { runHostSearch } from "./hostContractSearch";
export { runHostAddToCart, runHostProductDetail } from "./hostContractProducts";
export { runHostNavigate } from "./hostContractNav";
