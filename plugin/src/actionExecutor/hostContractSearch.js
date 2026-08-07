import { activateElement, enterText, submitFormElement } from "../adapter/dom/eventDriver";
import {
  AIHUB_ROLE,
  normalizeProductName,
  productCardName,
  productCards,
  REVEAL_TIMEOUT_MS,
  SETTLE_TIMEOUT_MS,
  clean,
  failed,
  findRole,
  hostPublishesSearch,
  succeeded,
  unconfirmed,
  unsupported,
  waitFor,
} from "./hostContractDom";

/**
 * Drive the host's own search box so the customer's real page moves.
 *
 * Ordinary discovery ("do you have flagship phones?") is a website action, not an
 * overlay: the shopper should end up on the store's real results, able to keep
 * browsing after the assistant stops talking. This fills the published input,
 * submits the published form, and then proves from the DOM that the results the
 * page now shows are the ones that were asked for.
 */

function locationReflectsQuery(query) {
  try {
    const haystack = `${window.location.pathname}${window.location.search}`.toLowerCase();
    return haystack.includes(encodeURIComponent(query).toLowerCase()) || haystack.includes(query.toLowerCase());
  } catch (_err) {
    return false;
  }
}

// A phrase built from several words ("flagship phone") is matched literally by many
// storefronts, so a discovery query can land on one lonely result while the
// assistant is describing a dozen. When that happens the broadest meaningful word
// is retried once, so the page ends up showing the range being talked about.
const SPARSE_RESULT_COUNT = 1;

/** True when the broader query still carries the request's first constraint. */
function keepsLeadingConstraint(original, broader) {
  const words = clean(original).split(/\s+/).filter(Boolean);
  if (words.length < 2) return true;
  return clean(broader).split(/\s+/).includes(words[0]);
}

function broadestTerm(query) {
  const words = clean(query).split(/\s+/).filter((word) => word.length > 2);
  if (words.length < 2) return "";
  return words.reduce((longest, word) => (word.length > longest.length ? word : longest), "");
}

/**
 * Set a value React (or any framework) observes, then submit the real form.
 *
 * `broadenIfSparse` is for discovery, where the customer wants to see a range.
 * Identity lookups (resolving one named record) must never broaden - landing on
 * more results is exactly what makes a specific product ambiguous.
 */
export async function runHostSearch(query, { broadenIfSparse = false, requested = [], filters = {} } = {}) {
  const wanted = clean(query);
  if (!hostPublishesSearch()) return null; // unsupported host -> let another executor try
  if (!wanted) return unsupported("host_search", "empty_query");

  const result = await submitHostSearch(wanted, requested, filters);
  if (!broadenIfSparse || !result || result.status !== "succeeded") return result;
  const count = result.evidence?.result_count;
  if (typeof count !== "number" || count > SPARSE_RESULT_COUNT) return result;

  const broader = broadestTerm(wanted);
  // Broadening must never drop the constraint that made the request specific.
  // Widening "samsung smartphones" to "smartphones" would show every brand's
  // phones while the answer talks about one brand's.
  if (!broader || broader === wanted || !keepsLeadingConstraint(wanted, broader)) return result;
  const retried = await submitHostSearch(broader, requested, filters);
  if (retried?.status === "succeeded" && (retried.evidence?.result_count || 0) > count) {
    return { ...retried, evidence: { ...retried.evidence, broadened_from: wanted } };
  }
  return result;
}

/**
 * What the page is actually showing, by identity rather than by count.
 *
 * A non-empty results page is not proof that the customer is looking at what
 * the answer named: a query can return plenty of unrelated records. Reading the
 * rendered identities lets the turn compare what was asked for with what is
 * visible, and report the difference instead of claiming success.
 */
function renderedIdentities() {
  return productCards()
    .map((card) => ({
      id: clean(card.getAttribute?.("data-product-id") || ""),
      name: clean(productCardName(card)),
    }))
    .filter((entity) => entity.id || entity.name);
}

function requestedIdentities(requested) {
  return (Array.isArray(requested) ? requested : [])
    .map((entity) => (typeof entity === "string" ? { name: entity } : entity || {}))
    .map((entity) => ({ id: clean(entity.id || ""), name: clean(entity.name || "") }))
    .filter((entity) => entity.id || entity.name);
}

/** How many of the given records the page is actually showing, by identity. */
function visibleRequestedCount(requested, rendered) {
  const renderedIds = new Set(rendered.map((entity) => entity.id).filter(Boolean));
  const renderedNames = new Set(
    rendered.map((entity) => normalizeProductName(entity.name)).filter(Boolean),
  );
  return requested.filter(
    (entity) =>
      (entity.id && renderedIds.has(entity.id)) ||
      (entity.name && renderedNames.has(normalizeProductName(entity.name))),
  ).length;
}

/**
 * Publish this turn's hard filters onto the host's search form.
 *
 * The host owns which canonical filters it accepts and which URL key each maps
 * to: it publishes a slot per filter marked with the vertical-neutral
 * `data-aihub-filter` name. Every published slot is reset first so a previous
 * turn's budget can never leak into an unfiltered search, then the ones this turn
 * resolved are set. Returns the canonical keys that were actually applied.
 */
function applyHostFilters(form, filters) {
  if (!form || typeof form.querySelectorAll !== "function") return [];
  const applied = [];
  for (const slot of form.querySelectorAll("[data-aihub-filter]")) {
    const key = clean(slot.getAttribute("data-aihub-filter"));
    const value = key && filters ? filters[key] : "";
    // Uncontrolled published slots: a direct value set is what the host reads on
    // submit, and it survives because nothing else owns the field.
    slot.value = value != null ? String(value) : "";
    if (slot.value) applied.push(key);
  }
  return applied;
}

async function submitHostSearch(wanted, requested = [], filters = {}) {

  let input = findRole(AIHUB_ROLE.searchInput);
  if (!input) {
    const reveal = findRole(AIHUB_ROLE.searchSubmit) || findRole(AIHUB_ROLE.searchForm);
    if (reveal) activateElement(reveal);
    input = await waitFor(() => findRole(AIHUB_ROLE.searchInput), REVEAL_TIMEOUT_MS);
  }
  if (!input) return failed("host_search", "search_input_unavailable");

  enterText(input, wanted);
  const form = input.closest?.("form") || findRole(AIHUB_ROLE.searchForm);
  const appliedFilters = applyHostFilters(form, filters);
  submitFormElement(form || findRole(AIHUB_ROLE.searchSubmit) || input);

  const settled = await waitFor(() => {
    const results = findRole(AIHUB_ROLE.searchResults);
    if (!results || results.getAttribute("data-results-loading") === "true") return null;
    return results;
  }, SETTLE_TIMEOUT_MS);
  if (!settled) return unconfirmed("host_search", "results_not_settled");

  const rawCount = Number(settled.getAttribute("data-result-count"));
  const rendered = renderedIdentities();
  const wantedEntities = requestedIdentities(requested);
  // A name is a claim the customer will read on the page, so a named record is
  // verified by identity. An id alone is not: the Hub keys its ingested catalog
  // differently from the storefront, so a Hub id absent from the host's own
  // id-space proves nothing about which products are shown. Only named records
  // gate the search; an id-only request rests on query reflection and a
  // non-empty page instead of an impossible cross-id-space match.
  const namedEntities = wantedEntities.filter((entity) => entity.name);
  const visibleRequested = visibleRequestedCount(wantedEntities, rendered);
  const visibleNamed = visibleRequestedCount(namedEntities, rendered);
  const evidence = {
    result_count: Number.isFinite(rawCount) ? rawCount : null,
    query: settled.getAttribute("data-query") || "",
    route: `${window.location.pathname}${window.location.search}`,
    route_reflects_query: locationReflectsQuery(wanted),
    requested_ids: wantedEntities.map((entity) => entity.id).filter(Boolean),
    requested_count: wantedEntities.length,
    named_requested_count: namedEntities.length,
    rendered_ids: rendered.map((entity) => entity.id).filter(Boolean),
    rendered_product_count: rendered.length,
    visible_requested_count: visibleRequested,
    applied_filters: appliedFilters,
  };
  const reflected = evidence.route_reflects_query || evidence.query.toLowerCase().includes(wanted.toLowerCase());
  if (!reflected) return failed("host_search", "query_not_reflected", evidence);
  if (settled.getAttribute("data-results-empty") === "true" || evidence.result_count === 0) {
    // The search ran, but the shopper is looking at an empty page. Reporting that
    // as success let an answer like "I found this matching product" stand on top
    // of "0 results" - the screen and the assistant contradicting each other is
    // worse than admitting the store had nothing for this query.
    return failed("host_search", "no_results", evidence);
  }
  if (namedEntities.length && visibleNamed === 0) {
    // The page has results, but none of them are the records the answer named by
    // name. A non-empty page of unrelated products is not the search that was
    // asked for, and reporting it as success is how speech and screen diverge.
    return failed("host_search", "requested_records_not_visible", evidence);
  }
  return succeeded("host_search", evidence);
}
