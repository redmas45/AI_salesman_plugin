import { activateElement, enterText, submitFormElement } from "../adapter/dom/eventDriver";
import {
  AIHUB_ROLE,
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
export async function runHostSearch(query, { broadenIfSparse = false } = {}) {
  const wanted = clean(query);
  if (!hostPublishesSearch()) return null; // unsupported host -> let another executor try
  if (!wanted) return unsupported("host_search", "empty_query");

  const result = await submitHostSearch(wanted);
  if (!broadenIfSparse || !result || result.status !== "succeeded") return result;
  const count = result.evidence?.result_count;
  if (typeof count !== "number" || count > SPARSE_RESULT_COUNT) return result;

  const broader = broadestTerm(wanted);
  if (!broader || broader === wanted) return result;
  const retried = await submitHostSearch(broader);
  if (retried?.status === "succeeded" && (retried.evidence?.result_count || 0) > count) {
    return { ...retried, evidence: { ...retried.evidence, broadened_from: wanted } };
  }
  return result;
}

async function submitHostSearch(wanted) {

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
    // The search ran, but the shopper is looking at an empty page. Reporting that
    // as success let an answer like "I found this matching product" stand on top
    // of "0 results" - the screen and the assistant contradicting each other is
    // worse than admitting the store had nothing for this query.
    return failed("host_search", "no_results", evidence);
  }
  return succeeded("host_search", evidence);
}
