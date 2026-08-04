import { queryElementsDeep } from "../dom/deepDom";

/**
 * What the customer can actually see right now.
 *
 * Two different failures came from the assistant not having this. A question
 * about "these results" was answered with a fresh catalog search rather than the
 * rows on screen, and a spoken success claim ("showing 2 products", "sorted by
 * price") could not be checked against anything, so a failed action still read
 * as a success.
 *
 * The contract is deliberately generic. Entities are discovered from stable
 * identifier attributes rather than from any one site's markup, the entity type
 * comes from the page's own declaration, and only safe display facts already
 * rendered on screen are included - never user-entered values, never free-text
 * dumps of the page.
 */

export const MAX_VISIBLE_ENTITIES = 12;
export const MAX_FILTERS = 8;
export const MAX_TEXT_CHARS = 80;

// Identifier attributes, in priority order, mapped to the entity type they imply
// when the page does not declare one explicitly.
const ENTITY_ID_ATTRIBUTES = Object.freeze([
  ["data-entity-id", ""],
  ["data-product-id", "product"],
  ["data-listing-id", "listing"],
  ["data-offer-id", "offer"],
  ["data-plan-id", "plan"],
  ["data-item-id", ""],
]);
const ENTITY_TYPE_ATTRIBUTE = "data-entity-type";
const DEFAULT_ENTITY_TYPE = "entity";

const SORT_KEYS = Object.freeze(["sort", "sort_by", "sortby", "orderby", "order_by", "order"]);
// Query keys that carry navigation or identity rather than a filter, plus
// anything that could carry personal data.
const NON_FILTER_KEYS = Object.freeze([
  "page", "p", "offset", "cursor", "q", "query", "search", "token", "session",
  "email", "phone", "name", "address", "utm_source", "utm_medium", "utm_campaign",
]);

const FACT_SELECTORS = Object.freeze([
  ["price", "[data-price], [itemprop='price'], .price"],
  ["rating", "[data-rating], [itemprop='ratingValue'], .rating"],
  ["availability", "[data-availability], [itemprop='availability'], .availability, .stock"],
]);

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, MAX_TEXT_CHARS);
}

function isRendered(element) {
  if (!element || typeof element.getBoundingClientRect !== "function") return false;
  const rect = element.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return false;
  const view = element.ownerDocument?.defaultView;
  const style = view?.getComputedStyle?.(element);
  if (style && (style.visibility === "hidden" || style.display === "none")) return false;
  const documentElement = element.ownerDocument?.documentElement;
  const viewportWidth = Number(view?.innerWidth || documentElement?.clientWidth || 0);
  const viewportHeight = Number(view?.innerHeight || documentElement?.clientHeight || 0);
  return (
    viewportWidth > 0 &&
    viewportHeight > 0 &&
    rect.bottom > 0 &&
    rect.right > 0 &&
    rect.top < viewportHeight &&
    rect.left < viewportWidth
  );
}

function identityOf(element) {
  for (const [attribute, impliedType] of ENTITY_ID_ATTRIBUTES) {
    const raw = clean(element.getAttribute(attribute));
    if (raw) return { id: raw, impliedType };
  }
  return null;
}

function entityTypeOf(element, impliedType) {
  const declared = clean(element.getAttribute(ENTITY_TYPE_ATTRIBUTE)).toLowerCase();
  return declared || impliedType || DEFAULT_ENTITY_TYPE;
}

function labelOf(element) {
  const heading = element.querySelector?.("h1, h2, h3, h4, [data-entity-name], [itemprop='name']");
  return clean(heading?.textContent || element.getAttribute("aria-label") || element.getAttribute("title"));
}

function routeOf(element) {
  const link = element.matches?.("a[href]") ? element : element.querySelector?.("a[href]");
  return sameOriginPath(link?.href || "");
}

function factsOf(element) {
  const facts = {};
  for (const [key, selector] of FACT_SELECTORS) {
    const node = element.querySelector?.(selector);
    if (!node) continue;
    const text = clean(node.getAttribute?.("content") || node.getAttribute?.(`data-${key}`) || node.textContent);
    if (text) facts[key] = text;
  }
  return facts;
}

function entitySelector() {
  return ENTITY_ID_ATTRIBUTES.map(([attribute]) => `[${attribute}]`).join(",");
}

export function readVisibleEntities() {
  const seen = new Set();
  const entities = [];
  for (const element of queryElementsDeep(entitySelector())) {
    if (entities.length >= MAX_VISIBLE_ENTITIES) break;
    const identity = identityOf(element);
    if (!identity || seen.has(identity.id) || !isRendered(element)) continue;
    seen.add(identity.id);
    entities.push({
      id: identity.id,
      entity_type: entityTypeOf(element, identity.impliedType),
      label: labelOf(element),
      route: routeOf(element),
      facts: factsOf(element),
    });
  }
  return entities;
}

export function readActiveFilters() {
  const params = searchParams();
  if (!params) return {};
  const filters = {};
  for (const [key, value] of params.entries()) {
    const normalized = key.toLowerCase();
    if (NON_FILTER_KEYS.includes(normalized) || SORT_KEYS.includes(normalized)) continue;
    if (Object.keys(filters).length >= MAX_FILTERS) break;
    filters[clean(key)] = clean(value);
  }
  return filters;
}

export function readActiveSort() {
  const params = searchParams();
  for (const key of SORT_KEYS) {
    const value = clean(params?.get?.(key));
    if (value) return value;
  }
  const control = queryElementsDeep("select[name*='sort' i], select[id*='sort' i]")[0];
  return clean(control?.value);
}

export function readRoute() {
  try {
    return {
      path: clean(window.location.pathname) || "/",
      search: clean(window.location.search),
    };
  } catch (_err) {
    return { path: "", search: "" };
  }
}

/** The bounded, generic snapshot of the screen that travels with a turn. */
export function readPageState() {
  return {
    route: readRoute(),
    filters: readActiveFilters(),
    sort: readActiveSort(),
    visible_entities: readVisibleEntities(),
  };
}

function searchParams() {
  try {
    return new URLSearchParams(window.location.search);
  } catch (_err) {
    return null;
  }
}

function sameOriginPath(value) {
  if (!value) return "";
  try {
    const url = new URL(value, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}` || "/";
  } catch (_err) {
    return "";
  }
}
