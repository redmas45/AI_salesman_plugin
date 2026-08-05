import { activateElement } from "../adapter/dom/eventDriver";
import { queryElementsDeep } from "../adapter/dom/deepDom";
import {
  AIHUB_ROLE,
  MATCHED_BY_ID,
  SETTLE_TIMEOUT_MS,
  clean,
  cssEscape,
  failed,
  findRole,
  findRoleAll,
  hostPublishesCart,
  hostPublishesProducts,
  hostPublishesSearch,
  isHostElement,
  normalizePath,
  normalizeProductName,
  productCardName,
  resolveProductCard,
  roleSelector,
  succeeded,
  waitFor,
} from "./hostContractDom";
import { runHostSearch } from "./hostContractSearch";

/**
 * Operate the host's real product controls: add a specific record to the cart,
 * and open a specific record's own page.
 *
 * Both start from the same problem - the requested record has to be found on a
 * page that may not be showing it yet. The host's search contract is used to
 * bring it into view, and identity is then resolved from what the host itself
 * published. Nothing is claimed until the cart or the destination page proves it.
 */

const CART_STAGE = "host_add_to_cart";
const DETAIL_STAGE = "host_product_detail";

function readCartCount() {
  const node =
    findRole(AIHUB_ROLE.cartButton) ||
    queryElementsDeep("[data-cart-count]").find(isHostElement) ||
    null;
  if (!node) return null;
  const value = Number(node.getAttribute("data-cart-count"));
  return Number.isFinite(value) ? value : null;
}

function cartLineIds() {
  return findRoleAll(AIHUB_ROLE.cartLineItem)
    .map((item) => clean(item.getAttribute("data-product-id")))
    .filter(Boolean);
}

function isDisabled(element) {
  return Boolean(element.disabled) || element.getAttribute("aria-disabled") === "true";
}

/**
 * Locate the requested record, searching the host for it when it is not on the
 * page yet. Returns the resolution, or a typed failure the caller can return.
 */
async function locateRecord(stage, productId, productName) {
  let resolved = resolveProductCard(productId, productName);
  if (!resolved && productName && hostPublishesSearch()) {
    // Not on this page: use the host's own search to bring it into view rather
    // than guessing a URL for it.
    const search = await runHostSearch(productName);
    if (search && search.status === "succeeded") {
      resolved = resolveProductCard(productId, productName);
    }
  }
  if (!resolved) {
    return { error: failed(stage, "product_not_on_page", { product_id: clean(productId), product_name: clean(productName) }) };
  }
  if (resolved.ambiguous) {
    return {
      error: failed(stage, "ambiguous_product", {
        product_name: clean(productName),
        match_count: resolved.matchCount,
      }),
    };
  }
  return resolved;
}

/** The add control that belongs to this record, never a neighbouring card's. */
function addControlFor(card, productId) {
  const id = clean(productId);
  if (id) {
    const direct = queryElementsDeep(
      `${roleSelector(AIHUB_ROLE.addToCart)}[data-product-id="${cssEscape(id)}"]`,
    ).find(isHostElement);
    if (direct) return direct;
  }
  return card?.querySelector?.(roleSelector(AIHUB_ROLE.addToCart)) || null;
}

/** Activate the real add control and confirm the host cart actually changed. */
export async function runHostAddToCart(params) {
  if (!hostPublishesCart() && !hostPublishesProducts()) return null; // unsupported host
  const productId = clean(params?.product_id || params?.entity_id);
  const productName = clean(params?.product_name);

  const located = await locateRecord(CART_STAGE, productId, productName);
  if (located.error) return located.error;

  const hostProductId = clean(located.card.getAttribute("data-product-id")) || productId;
  const control = addControlFor(located.card, located.matchedBy === MATCHED_BY_ID ? productId : hostProductId);
  if (!control) return failed(CART_STAGE, "add_control_missing", { product_id: hostProductId, product_name: productName });
  if (isDisabled(control)) return failed(CART_STAGE, "add_control_disabled", { product_id: hostProductId, product_name: productName });

  const beforeCount = readCartCount();
  const beforeLines = cartLineIds();
  activateElement(control);

  const changed = await waitFor(() => {
    const afterCount = readCartCount();
    const lines = cartLineIds();
    const countIncreased = beforeCount != null && afterCount != null && afterCount > beforeCount;
    const namedLineAppeared = hostProductId && lines.includes(hostProductId) && !beforeLines.includes(hostProductId);
    const anyLineAppeared = lines.length > beforeLines.length;
    return countIncreased || namedLineAppeared || anyLineAppeared ? { afterCount, lines } : null;
  }, SETTLE_TIMEOUT_MS);

  const evidence = {
    cart_before: beforeCount,
    cart_after: readCartCount(),
    product_id: hostProductId,
    product_name: productName,
    matched_by: located.matchedBy,
  };
  if (!changed) return failed(CART_STAGE, "cart_unchanged", evidence);
  return succeeded(CART_STAGE, {
    ...evidence,
    line_item_present: hostProductId ? cartLineIds().includes(hostProductId) : true,
  });
}

/** The record's own link, as published by the host - never a guessed route. */
function productLinkIn(card) {
  return card?.querySelector?.(roleSelector(AIHUB_ROLE.productLink)) || card?.querySelector?.("a[href]") || null;
}

/**
 * Confirm the page now showing is the requested record's page.
 *
 * A URL change alone is not arrival: the destination must publish the record's
 * identity, or render its exact title. Anything less is reported unverified.
 */
function detailIdentityMatches(hostProductId, productName) {
  const detail = findRole(AIHUB_ROLE.productDetail);
  const wantedName = normalizeProductName(productName);
  if (detail) {
    const detailId = clean(detail.getAttribute("data-product-id"));
    if (hostProductId && detailId && detailId === hostProductId) return "product_id";
    const detailName = normalizeProductName(productCardName(detail));
    if (wantedName && detailName && detailName === wantedName) return "product_name";
  }
  const title = findRole(AIHUB_ROLE.productTitle);
  if (title && wantedName && normalizeProductName(title.textContent) === wantedName) return "product_title";
  return "";
}

/** Open the requested record's real product page and verify arrival. */
export async function runHostProductDetail(params) {
  if (!hostPublishesProducts() && !hostPublishesSearch()) return null; // unsupported host
  const productId = clean(params?.product_id || params?.entity_id);
  const productName = clean(params?.product_name);

  const located = await locateRecord(DETAIL_STAGE, productId, productName);
  if (located.error) return located.error;

  const hostProductId = clean(located.card.getAttribute("data-product-id")) || productId;
  const link = productLinkIn(located.card);
  if (!link) return failed(DETAIL_STAGE, "product_link_missing", { product_id: hostProductId, product_name: productName });

  const before = normalizePath(window.location.pathname);
  activateElement(link);

  const verifiedBy = await waitFor(() => detailIdentityMatches(hostProductId, productName) || null, SETTLE_TIMEOUT_MS);
  const evidence = {
    product_id: hostProductId,
    product_name: productName,
    matched_by: located.matchedBy,
    route: `${window.location.pathname}${window.location.search}`,
    verified_by: verifiedBy || "",
  };
  if (verifiedBy) return succeeded(DETAIL_STAGE, evidence);
  if (normalizePath(window.location.pathname) === before) {
    return failed(DETAIL_STAGE, "route_unchanged", evidence);
  }
  return failed(DETAIL_STAGE, "product_page_not_confirmed", evidence);
}
