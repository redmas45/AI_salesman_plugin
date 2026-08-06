import { activateElement } from "../adapter/dom/eventDriver";
import {
  AIHUB_NAV_ATTR,
  AIHUB_ROLE,
  SETTLE_TIMEOUT_MS,
  clean,
  failed,
  findRoleAll,
  hostPublishesCheckout,
  hostPublishesNav,
  normalizeKey,
  normalizePath,
  sameOriginPath,
  succeeded,
  waitFor,
} from "./hostContractDom";

/**
 * Navigate via the host's own published nav link, and verify the real page moved.
 *
 * The target is matched to a link the site published; nothing here invents a
 * route from category text. Success requires the URL to actually become that
 * link's destination AND the destination page to render - a URL change to the
 * wrong route, or no change, or an unrendered page, is a failure with a precise
 * reason.
 */

const NAV_STAGE = "host_navigate";
const CHECKOUT_STAGE = "host_checkout";
const READY_SELECTOR = "main, [data-aihub-role='search-results'], [data-product-id]";

/**
 * Find the published nav link whose key or label best matches the requested target.
 *
 * Both handles are matched, exact first and then by containment. Matching the
 * visible label alone was not enough: a site may publish the key `fashion-women`
 * under the label "Women's fashion", so a request for that section found nothing
 * even though the site had published exactly the right link. The key is the
 * stable contract handle, so it is always considered.
 */
function findNavTarget(target) {
  const wanted = normalizeKey(target);
  if (!wanted) return null;
  const links = findRoleAll(AIHUB_ROLE.navLink);
  // A link is addressable by its published key, its visible label, or its own
  // destination: the Hub may name a section any of those ways.
  const handlesOf = (link) =>
    [
      normalizeKey(link.getAttribute(AIHUB_NAV_ATTR)),
      normalizeKey(link.textContent),
      normalizeKey(sameOriginPath(link.getAttribute("href") || link.href)),
    ].filter(Boolean);

  const exact = links.find((link) => handlesOf(link).includes(wanted));
  if (exact) return exact;

  // Otherwise take the MOST SPECIFIC overlap, never merely the first one found.
  // A request for "shop?category=electronics" overlaps the broad "shop" link as
  // well as the "electronics" one; picking whichever appeared first in the page
  // sent shoppers to the entire catalogue instead of the section they asked for.
  let best = null;
  let bestScore = 0;
  for (const link of links) {
    for (const handle of handlesOf(link)) {
      if (!wanted.includes(handle) && !handle.includes(wanted)) continue;
      if (handle.length > bestScore) {
        bestScore = handle.length;
        best = link;
      }
    }
  }
  return best;
}

function searchParamsOf(value) {
  try {
    return new URL(String(value || ""), window.location.origin).searchParams;
  } catch (_err) {
    return new URLSearchParams();
  }
}

/**
 * True when the current URL satisfies the destination the link points at.
 *
 * Sections are often distinguished only by a query parameter (`/shop?category=x`),
 * so comparing paths alone would report arrival at the wrong section as success.
 * Every parameter the published link carries must be present with the same value.
 */
function routeSatisfies(expectedHref) {
  if (normalizePath(window.location.pathname) !== normalizePath(expectedHref)) return false;
  const current = new URLSearchParams(window.location.search);
  for (const [key, value] of searchParamsOf(expectedHref).entries()) {
    if (current.get(key) !== value) return false;
  }
  return true;
}

export async function runHostNavigate(target) {
  if (!hostPublishesNav()) return null; // unsupported host -> let another executor try
  const link = findNavTarget(target);
  if (!link) return failed(NAV_STAGE, "no_matching_nav_target", { target: clean(target) });

  const expected = sameOriginPath(link.getAttribute("href") || link.href);
  const before = normalizePath(window.location.pathname);
  activateElement(link);

  const reached = await waitFor(() => (expected && routeSatisfies(expected) ? true : null), SETTLE_TIMEOUT_MS);
  const now = normalizePath(window.location.pathname);
  const evidence = {
    target: clean(target),
    expected: normalizePath(expected),
    route: `${window.location.pathname}${window.location.search}`,
  };
  if (!reached) {
    if (now !== before) return failed(NAV_STAGE, "wrong_route", { ...evidence, actual: now });
    return failed(NAV_STAGE, "route_unchanged", { ...evidence, actual: now });
  }
  // The destination must actually render, not just change the URL.
  const ready = await waitFor(() => (document.querySelector(READY_SELECTOR) ? true : null), SETTLE_TIMEOUT_MS);
  if (!ready) return failed(NAV_STAGE, "page_not_ready", evidence);
  return succeeded(NAV_STAGE, evidence);
}

/** Open the host's real checkout control and verify the checkout route changed. */
export async function runHostCheckout() {
  if (!hostPublishesCheckout()) return null;
  const control = findRoleAll(AIHUB_ROLE.checkout)[0];
  if (!control) return null;

  const before = `${window.location.pathname}${window.location.search}`;
  const expected = sameOriginPath(control.getAttribute("href") || "/checkout");
  activateElement(control);
  const reached = await waitFor(
    () => (expected && routeSatisfies(expected) ? true : null),
    SETTLE_TIMEOUT_MS,
  );
  const current = `${window.location.pathname}${window.location.search}`;
  const evidence = { expected: normalizePath(expected || "/checkout"), route: current };
  if (reached) return succeeded(CHECKOUT_STAGE, evidence);
  return failed(
    CHECKOUT_STAGE,
    current === before ? "route_unchanged" : "wrong_route",
    evidence,
  );
}
