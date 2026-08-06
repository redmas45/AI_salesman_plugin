import { queryElementsDeep } from "../adapter/dom/deepDom";

/**
 * Shared vocabulary for driving a host website through the vertical-neutral
 * `data-aihub-role` contract it publishes.
 *
 * Nothing here knows any site's routes, CSS, categories, or product names. Role
 * lookup, product identity, settle helpers, and the typed result shapes live
 * together because every capability module (search, products, navigation) needs
 * exactly this much and nothing more.
 */

export const AIHUB_ROLE = Object.freeze({
  searchForm: "search-form",
  searchInput: "search-input",
  searchSubmit: "search-submit",
  searchResults: "search-results",
  addToCart: "add-to-cart",
  checkout: "checkout",
  clearCart: "clear-cart",
  cartButton: "cart-button",
  cartLineItem: "cart-line-item",
  navLink: "nav-link",
  productCard: "product-card",
  productLink: "product-link",
  productName: "product-name",
  productDetail: "product-detail",
  productTitle: "product-title",
});

export const AIHUB_NAV_ATTR = "data-aihub-nav";
// A host publishes each record's exact name here. It is the identity a Hub whose
// catalog uses different ids can still match on.
export const AIHUB_ENTITY_NAME_ATTR = "data-entity-name";

export const SETTLE_TIMEOUT_MS = 4000;
export const REVEAL_TIMEOUT_MS = 1500;
export const POLL_MS = 80;

// The assistant renders its own record cards, and they are keyed by the Hub's
// product ids. Resolving one of those instead of the website's own card means
// clicking inside our overlay while the customer's real cart never changes, so
// the assistant's UI is excluded from every host lookup.
const ASSISTANT_UI_SELECTOR = '[id^="mayabot"], [data-aihub-widget]';

/** True when the element belongs to the host page rather than to our own UI. */
export function isHostElement(element) {
  return Boolean(element) && !element.closest?.(ASSISTANT_UI_SELECTOR);
}

export const roleSelector = (role) => `[data-aihub-role="${role}"]`;
export const findRoleAll = (role) => queryElementsDeep(roleSelector(role)).filter(isHostElement);
export const findRole = (role) => findRoleAll(role)[0] || null;

/** The host's own element carrying this record id, ignoring our overlays. */
export function hostElementForProductId(productId) {
  const id = clean(productId);
  if (!id) return null;
  return queryElementsDeep(`[data-product-id="${cssEscape(id)}"]`).find(isHostElement) || null;
}

export function clean(value) {
  return String(value == null ? "" : value).trim();
}

export function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return clean(value).replace(/["\\]/g, "\\$&");
}

export async function waitFor(predicate, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const value = predicate();
    if (value) return value;
    if (Date.now() >= deadline) return null;
    await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
  }
}

export function hostPublishesSearch() {
  return Boolean(
    findRole(AIHUB_ROLE.searchForm) || findRole(AIHUB_ROLE.searchInput) || findRole(AIHUB_ROLE.searchSubmit),
  );
}

export function hostPublishesCart() {
  return Boolean(findRole(AIHUB_ROLE.addToCart));
}

export function hostPublishesCheckout() {
  return Boolean(findRole(AIHUB_ROLE.checkout));
}

export function hostPublishesClearCart() {
  return Boolean(findRole(AIHUB_ROLE.clearCart));
}

export function hostPublishesNav() {
  return findRoleAll(AIHUB_ROLE.navLink).length > 0;
}

/** True when the page exposes records the assistant can identify and open. */
export function hostPublishesProducts() {
  return productCards().length > 0;
}

export function normalizePath(value) {
  const path = String(value || "").split("?")[0].split("#")[0];
  return path.length > 1 ? path.replace(/\/+$/, "") : path || "/";
}

export function sameOriginPath(value) {
  try {
    const url = new URL(String(value || ""), window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}` || "/";
  } catch (_err) {
    return "";
  }
}

export function normalizeKey(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

/**
 * Fold a record name to a comparable form: case and separator/spacing noise vary
 * between a catalog row and its rendered label, but nothing else may. This is an
 * equality key, never a similarity score - a partial overlap is not a match.
 *
 * Only separators are folded. Symbols that distinguish one model from another
 * are kept, because stripping every non-alphanumeric character makes "S26+" and
 * "S26" the same string - and two different products sharing a key is how an
 * assistant ends up adding the wrong one.
 */
export function normalizeProductName(value) {
  return clean(value)
    .toLowerCase()
    .replace(/[\s\-_/\\,.:;|]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Every record the HOST currently shows, preferring its published card role. */
export function productCards() {
  const roled = findRoleAll(AIHUB_ROLE.productCard);
  if (roled.length) return roled;
  return queryElementsDeep("[data-product-id]").filter(isHostElement);
}

/** The exact name a card publishes, from its identity attribute or name role. */
export function productCardName(card) {
  const published = clean(card?.getAttribute?.(AIHUB_ENTITY_NAME_ATTR));
  if (published) return published;
  return clean(card?.querySelector?.(roleSelector(AIHUB_ROLE.productName))?.textContent);
}

export const MATCHED_BY_ID = "product_id";
export const MATCHED_BY_NAME = "product_name";

/**
 * Find the one card the action means.
 *
 * The host's own id wins whenever it is present in the page. When the Hub's
 * catalog keys the product differently, the exact record name is the fallback -
 * and it must identify exactly one card. Several cards sharing a name is
 * reported as ambiguous so the caller can ask, never silently resolved to the
 * first one; that guess is how an assistant ends up adding the wrong product.
 */
export function resolveProductCard(productId, productName) {
  const byId = hostElementForProductId(productId);
  if (byId) return { card: byId, matchedBy: MATCHED_BY_ID };
  const wanted = normalizeProductName(productName);
  if (!wanted) return null;
  const matches = productCards().filter((card) => normalizeProductName(productCardName(card)) === wanted);
  if (matches.length === 1) return { card: matches[0], matchedBy: MATCHED_BY_NAME };
  if (matches.length > 1) return { ambiguous: true, matchCount: matches.length };
  return null;
}

export function succeeded(stage, evidence, reason = "") {
  return { handled: true, status: "succeeded", self_verified: true, stage, reason, evidence: evidence || {} };
}

export function failed(stage, reason, evidence) {
  return { handled: true, status: "failed", stage, reason, evidence: evidence || {} };
}

export function unconfirmed(stage, reason, evidence) {
  return { handled: true, status: "unconfirmed", stage, reason, evidence: evidence || {} };
}

export function unsupported(stage, reason) {
  return { handled: true, status: "unsupported_host", stage, reason, evidence: {} };
}
