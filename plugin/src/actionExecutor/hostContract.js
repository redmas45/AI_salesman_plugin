import { queryElementDeep, queryElementsDeep } from "../adapter/dom/deepDom";
import { activateElement, enterText, submitFormElement } from "../adapter/dom/eventDriver";

/**
 * Drive a host website through the vertical-neutral `data-aihub-role` contract it
 * publishes, and prove the page actually changed.
 *
 * Nothing here knows any site's routes, CSS, categories, or product names. A host
 * that publishes the contract can be searched and added-to-cart by the same code,
 * whatever its vertical; a host that does not publish it gets a precise
 * unsupported-host result, never a fabricated success. Every claim this module
 * returns is backed by a re-read of the DOM after the action settled - a button
 * click that returned without throwing is not treated as proof.
 */

export const AIHUB_ROLE = Object.freeze({
  searchForm: "search-form",
  searchInput: "search-input",
  searchSubmit: "search-submit",
  searchResults: "search-results",
  addToCart: "add-to-cart",
  cartButton: "cart-button",
  cartLineItem: "cart-line-item",
  navLink: "nav-link",
});
const AIHUB_NAV_ATTR = "data-aihub-nav";

const SETTLE_TIMEOUT_MS = 4000;
const REVEAL_TIMEOUT_MS = 1500;
const POLL_MS = 80;

const roleSelector = (role) => `[data-aihub-role="${role}"]`;
const findRole = (role) => queryElementDeep(roleSelector(role));
const findRoleAll = (role) => queryElementsDeep(roleSelector(role));

export function hostPublishesSearch() {
  return Boolean(findRole(AIHUB_ROLE.searchForm) || findRole(AIHUB_ROLE.searchInput) || findRole(AIHUB_ROLE.searchSubmit));
}

export function hostPublishesCart() {
  return Boolean(findRole(AIHUB_ROLE.addToCart));
}

export function hostPublishesNav() {
  return findRoleAll(AIHUB_ROLE.navLink).length > 0;
}

function clean(value) {
  return String(value == null ? "" : value).trim();
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return clean(value).replace(/["\\]/g, "\\$&");
}

async function waitFor(predicate, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const value = predicate();
    if (value) return value;
    if (Date.now() >= deadline) return null;
    await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
  }
}

function locationReflectsQuery(query) {
  try {
    const haystack = `${window.location.pathname}${window.location.search}`.toLowerCase();
    return haystack.includes(encodeURIComponent(query).toLowerCase()) || haystack.includes(query.toLowerCase());
  } catch (_err) {
    return false;
  }
}

/** Set a value React (or any framework) observes, then submit the real form. */
export async function runHostSearch(query) {
  const wanted = clean(query);
  if (!hostPublishesSearch()) return null; // unsupported host -> let another executor try
  if (!wanted) return unsupported("host_search", "empty_query");

  let input = findRole(AIHUB_ROLE.searchInput);
  if (!input) {
    const reveal = findRole(AIHUB_ROLE.searchSubmit) || findRole(AIHUB_ROLE.searchForm);
    if (reveal) activateElement(reveal);
    input = await waitFor(() => findRole(AIHUB_ROLE.searchInput), REVEAL_TIMEOUT_MS);
  }
  if (!input) return failed("host_search", "search_input_unavailable");

  enterText(input, wanted);
  const form = input.closest?.("form") || findRole(AIHUB_ROLE.searchForm);
  submitFormElement(form || findRole(AIHUB_ROLE.searchSubmit) || input);

  const settled = await waitFor(() => {
    const results = findRole(AIHUB_ROLE.searchResults);
    if (!results || results.getAttribute("data-results-loading") === "true") return null;
    return results;
  }, SETTLE_TIMEOUT_MS);
  if (!settled) return unconfirmed("host_search", "results_not_settled");

  const rawCount = Number(settled.getAttribute("data-result-count"));
  const evidence = {
    result_count: Number.isFinite(rawCount) ? rawCount : null,
    query: settled.getAttribute("data-query") || "",
    route: `${window.location.pathname}${window.location.search}`,
    route_reflects_query: locationReflectsQuery(wanted),
  };
  const reflected = evidence.route_reflects_query || evidence.query.toLowerCase().includes(wanted.toLowerCase());
  if (!reflected) return failed("host_search", "query_not_reflected", evidence);
  if (settled.getAttribute("data-results-empty") === "true" || evidence.result_count === 0) {
    return { handled: true, status: "succeeded", self_verified: true, stage: "host_search", reason: "no_results", evidence };
  }
  return { handled: true, status: "succeeded", self_verified: true, stage: "host_search", evidence };
}

function readCartCount() {
  const node = findRole(AIHUB_ROLE.cartButton) || queryElementDeep("[data-cart-count]");
  if (!node) return null;
  const value = Number(node.getAttribute("data-cart-count"));
  return Number.isFinite(value) ? value : null;
}

function cartLineIds() {
  return findRoleAll(AIHUB_ROLE.cartLineItem)
    .map((item) => clean(item.getAttribute("data-product-id")))
    .filter(Boolean);
}

function findAddControl(productId) {
  const id = clean(productId);
  if (id) {
    const direct = queryElementDeep(`${roleSelector(AIHUB_ROLE.addToCart)}[data-product-id="${cssEscape(id)}"]`);
    if (direct) return direct;
    const card = queryElementDeep(`[data-product-id="${cssEscape(id)}"]`);
    const within = card?.querySelector?.(roleSelector(AIHUB_ROLE.addToCart));
    if (within) return within;
    return null; // a specific product was named but its control is not on this page
  }
  return findRole(AIHUB_ROLE.addToCart);
}

function isDisabled(element) {
  return Boolean(element.disabled) || element.getAttribute("aria-disabled") === "true";
}

/** Activate the real add control and confirm the host cart actually changed. */
export async function runHostAddToCart(params) {
  if (!hostPublishesCart()) return null; // unsupported host -> let another executor try
  const productId = clean(params?.product_id || params?.entity_id);
  const control = findAddControl(productId);
  if (!control) return failed("host_add_to_cart", productId ? "product_not_on_page" : "add_control_missing", { product_id: productId });
  if (isDisabled(control)) return failed("host_add_to_cart", "add_control_disabled", { product_id: productId });

  const beforeCount = readCartCount();
  const beforeLines = cartLineIds();
  activateElement(control);

  const changed = await waitFor(() => {
    const afterCount = readCartCount();
    const lines = cartLineIds();
    const countIncreased = beforeCount != null && afterCount != null && afterCount > beforeCount;
    const namedLineAppeared = productId && lines.includes(productId) && !beforeLines.includes(productId);
    const anyLineAppeared = lines.length > beforeLines.length;
    return countIncreased || namedLineAppeared || anyLineAppeared ? { afterCount, lines } : null;
  }, SETTLE_TIMEOUT_MS);

  const afterCount = readCartCount();
  const evidence = { cart_before: beforeCount, cart_after: afterCount, product_id: productId };
  if (!changed) return failed("host_add_to_cart", "cart_unchanged", evidence);
  return {
    handled: true,
    status: "succeeded",
    self_verified: true,
    stage: "host_add_to_cart",
    evidence: { ...evidence, line_item_present: productId ? cartLineIds().includes(productId) : true },
  };
}

function normalizeKey(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function normalizePath(value) {
  const path = String(value || "").split("?")[0].split("#")[0];
  return path.length > 1 ? path.replace(/\/+$/, "") : path || "/";
}

function sameOriginPath(value) {
  try {
    const url = new URL(String(value || ""), window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}` || "/";
  } catch (_err) {
    return "";
  }
}

/** Find the published nav link whose key/label best matches the requested target. */
function findNavTarget(target) {
  const wanted = normalizeKey(target);
  if (!wanted) return null;
  const links = findRoleAll(AIHUB_ROLE.navLink);
  return (
    links.find((link) => normalizeKey(link.getAttribute(AIHUB_NAV_ATTR)) === wanted) ||
    links.find((link) => normalizeKey(link.textContent) === wanted) ||
    links.find((link) => {
      const label = normalizeKey(link.textContent);
      return label && (label.includes(wanted) || wanted.includes(label));
    }) ||
    null
  );
}

/**
 * Navigate via the host's own published nav link, and verify the real page moved.
 *
 * The target is matched to a link the site published; nothing here invents a route
 * from category text. Success requires the URL to actually become that link's
 * destination AND the destination page to render - a URL change to the wrong route,
 * or no change, or an unrendered page, is a failure with a precise reason.
 */
export async function runHostNavigate(target) {
  if (!hostPublishesNav()) return null; // unsupported host -> let another executor try
  const link = findNavTarget(target);
  if (!link) return failed("host_navigate", "no_matching_nav_target", { target: clean(target) });

  const expected = normalizePath(sameOriginPath(link.getAttribute("href") || link.href));
  const before = normalizePath(window.location.pathname);
  activateElement(link);

  const reached = await waitFor(
    () => (expected && normalizePath(window.location.pathname) === expected ? true : null),
    SETTLE_TIMEOUT_MS,
  );
  const now = normalizePath(window.location.pathname);
  const evidence = { target: clean(target), expected, route: `${window.location.pathname}${window.location.search}` };
  if (!reached) {
    if (now !== before) return failed("host_navigate", "wrong_route", { ...evidence, actual: now });
    return failed("host_navigate", "route_unchanged", { ...evidence, actual: now });
  }
  // The destination must actually render, not just change the URL.
  const ready = await waitFor(
    () => (document.querySelector("main, [data-aihub-role='search-results'], [data-product-id]") ? true : null),
    SETTLE_TIMEOUT_MS,
  );
  if (!ready) return failed("host_navigate", "page_not_ready", evidence);
  return { handled: true, status: "succeeded", self_verified: true, stage: "host_navigate", evidence };
}

function failed(stage, reason, evidence) {
  return { handled: true, status: "failed", stage, reason, evidence: evidence || {} };
}

function unconfirmed(stage, reason, evidence) {
  return { handled: true, status: "unconfirmed", stage, reason, evidence: evidence || {} };
}

function unsupported(stage, reason) {
  return { handled: true, status: "unsupported_host", stage, reason, evidence: {} };
}
