import { config } from "../core/config";
import { API_PATHS } from "../core/constants";

const HOST_CATALOG_ENDPOINTS = Object.freeze([
  { path: "/api/products?per_page=96", routePrefix: "/product/" },
  { path: "/api/products", routePrefix: "/product/" },
  { path: "/api/products.json", routePrefix: "" },
  { path: "/products.json", routePrefix: "/products/" },
  { path: "/collections/all/products.json", routePrefix: "/products/" },
]);
const CATALOG_ARRAY_FIELDS = Object.freeze(["products", "data", "items", "results"]);
const PRODUCT_ID_FIELDS = Object.freeze(["id", "product_id", "handle", "sku"]);
const PRODUCT_NAME_FIELDS = Object.freeze(["name", "title"]);
const PRODUCT_URL_FIELDS = Object.freeze(["url", "href", "permalink", "product_url"]);
const PRODUCT_IMAGE_FIELDS = Object.freeze([
  "image_url",
  "imageUrl",
  "image_src",
  "imageSrc",
  "image",
  "images",
  "media",
  "thumbnail",
  "thumbnail_url",
  "featured_image",
  "featuredImage",
  "featured_image_url",
]);
const PRODUCT_BRAND_FIELDS = Object.freeze(["brand", "vendor"]);
const PRODUCT_CATEGORY_FIELDS = Object.freeze(["category", "category_name", "product_type"]);
const PRODUCT_DESCRIPTION_FIELDS = Object.freeze(["description", "summary", "body_html"]);
const PRODUCT_ORIGINAL_PRICE_FIELDS = Object.freeze(["original_price", "compare_at_price", "regular_price"]);
const PRODUCT_CURRENCY_FIELDS = Object.freeze(["currency", "currency_code"]);
const PRODUCT_DISPLAY_PRICE_FIELDS = Object.freeze(["display_price", "price_text", "formatted_price"]);
const DEFAULT_PRODUCT_BRAND = "Unknown Brand";
const DEFAULT_PRODUCT_CATEGORY = "Products";
const PRODUCT_ROUTE_SUFFIX = "/";
const HANDLE_PATTERN = /^[a-z0-9][a-z0-9-]*$/i;

let hostCatalogPromise = null;

function clean(value) {
  if (value === null || value === undefined || typeof value === "object") return "";
  return String(value || "").trim();
}

function normalizeLookupText(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function queryTerms(value) {
  const stopWords = new Set([
    "a",
    "am",
    "an",
    "and",
    "ask",
    "asked",
    "did",
    "for",
    "me",
    "not",
    "on",
    "only",
    "please",
    "show",
    "some",
    "the",
    "to",
    "wanna",
    "want",
    "what",
    "with",
    "you",
    "your",
  ]);
  const terms = [];
  const seen = new Set();
  for (const word of removeNegativeCorrections(normalizeLookupText(value)).split(" ")) {
    const term = canonicalQueryTerm(word);
    if (term.length <= 1 || stopWords.has(term) || seen.has(term)) continue;
    terms.push(term);
    seen.add(term);
  }
  return terms;
}

function removeNegativeCorrections(text) {
  return text.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g, " ");
}

function canonicalQueryTerm(word) {
  if (["phone", "phones", "mobile", "mobiles"].includes(word)) return "phone";
  if (["book", "books"].includes(word)) return "books";
  return word;
}

function valuesFrom(raw, fields) {
  return fields.map((field) => clean(raw?.[field])).filter(Boolean);
}

function firstValue(raw, fields) {
  return valuesFrom(raw, fields)[0] || "";
}

function numericValue(raw) {
  const text = clean(raw).replace(/,/g, "");
  if (!text) return 0;
  const match = text.match(/-?\d+(?:\.\d+)?/);
  const number = match ? Number(match[0]) : Number(text);
  return Number.isFinite(number) ? number : 0;
}

function displayPriceFrom(raw, price) {
  const explicit = firstValue(raw, PRODUCT_DISPLAY_PRICE_FIELDS);
  if (explicit) return explicit;

  const currency = firstValue(raw, PRODUCT_CURRENCY_FIELDS).toUpperCase();
  if (price > 0 && currency) return `${currency} ${price.toLocaleString()}`;
  if (price > 0) return price.toLocaleString();
  return "";
}

function imageFrom(raw) {
  for (const field of PRODUCT_IMAGE_FIELDS) {
    const candidate = imageCandidateFrom(raw?.[field]);
    if (candidate) return candidate;
  }
  return "";
}

function imageCandidateFrom(value) {
  if (!value) return "";

  if (Array.isArray(value)) {
    for (const item of value) {
      const candidate = imageCandidateFrom(item);
      if (candidate) return candidate;
    }
    return "";
  }

  if (typeof value === "object") {
    for (const field of [
      "src",
      "url",
      "image_url",
      "imageUrl",
      "image_src",
      "imageSrc",
      "thumbnail",
      "thumbnail_url",
      "featured_image",
      "featuredImage",
      "featured_image_url",
    ]) {
      const candidate = imageCandidateFrom(value[field]);
      if (candidate) return candidate;
    }
    return "";
  }

  return safeImageUrl(value);
}

function safeImageUrl(value) {
  const raw = clean(value);
  if (!raw || /^javascript:/i.test(raw)) return "";
  if (/^data:image\//i.test(raw)) return raw;

  try {
    const url = new URL(raw, window.location.origin);
    if (!["http:", "https:"].includes(url.protocol)) return "";
    return url.toString();
  } catch (_err) {
    return "";
  }
}

function sameOriginUrl(raw) {
  const value = clean(raw);
  if (!value) return "";

  try {
    const url = new URL(value, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}${url.hash}`;
  } catch (_err) {
    return "";
  }
}

function productUrlFrom(raw, handle, endpoint) {
  const explicitUrl = sameOriginUrl(firstValue(raw, PRODUCT_URL_FIELDS));
  if (explicitUrl) return explicitUrl;

  if (!HANDLE_PATTERN.test(handle) || !/[a-z]/i.test(handle)) return "";
  if (!endpoint?.routePrefix) return "";
  return `${endpoint.routePrefix}${encodeURIComponent(handle)}${PRODUCT_ROUTE_SUFFIX}`;
}

function normalizeProduct(raw, endpoint = {}) {
  if (!raw) return null;

  const id = firstValue(raw, PRODUCT_ID_FIELDS);
  const handle = clean(raw.handle || raw.slug || raw.product_handle);
  const name = firstValue(raw, PRODUCT_NAME_FIELDS);
  const price = numericValue(raw.price || raw.amount || raw.cost);
  const originalPrice = numericValue(firstValue(raw, PRODUCT_ORIGINAL_PRICE_FIELDS));
  if (!id && !handle) return null;

  return {
    id,
    handle,
    name,
    title: clean(raw.title || name),
    brand: firstValue(raw, PRODUCT_BRAND_FIELDS) || DEFAULT_PRODUCT_BRAND,
    category: firstValue(raw, PRODUCT_CATEGORY_FIELDS) || DEFAULT_PRODUCT_CATEGORY,
    description: firstValue(raw, PRODUCT_DESCRIPTION_FIELDS),
    price: Number.isFinite(price) ? price : 0,
    originalPrice: Number.isFinite(originalPrice) ? originalPrice : 0,
    displayPrice: displayPriceFrom(raw, price),
    currency: firstValue(raw, PRODUCT_CURRENCY_FIELDS),
    rating: numericValue(raw.rating || raw.review_rating),
    reviewCount: numericValue(raw.review_count || raw.reviews_count || raw.reviews),
    imageUrl: imageFrom(raw),
    url: productUrlFrom(raw, handle || id, endpoint),
  };
}

function productIdentifiers(product) {
  return valuesFrom(product, PRODUCT_ID_FIELDS);
}

function productNames(product) {
  return valuesFrom(product, PRODUCT_NAME_FIELDS).map(normalizeLookupText);
}

function productMatchesId(product, productId) {
  const target = clean(productId);
  return Boolean(target && productIdentifiers(product).includes(target));
}

function productMatchesQuery(product, searchQuery) {
  const terms = queryTerms(searchQuery);
  if (!terms.length) return false;
  const searchable = normalizeLookupText([
    product?.name,
    product?.title,
    product?.brand,
    product?.category,
    product?.category_name,
    product?.product_type,
    product?.description,
    product?.tags,
  ].join(" "));
  return terms.every((term) => searchable.includes(term) || searchable.includes(term.replace(/s$/, "")));
}

function productNamesMatch(hostProduct, hubProduct) {
  const hubNames = new Set(productNames(hubProduct));
  return productNames(hostProduct).some((name) => hubNames.has(name));
}

function productImagesMatch(hostProduct, hubProduct) {
  return Boolean(hostProduct?.imageUrl && hostProduct.imageUrl === hubProduct?.imageUrl);
}

function flattenCatalogPayload(payload) {
  if (Array.isArray(payload)) return payload;

  for (const field of CATALOG_ARRAY_FIELDS) {
    const value = payload?.[field];
    if (Array.isArray(value)) return value;
  }
  return [];
}

async function fetchCatalogEndpoint(endpoint) {
  try {
    const response = await fetch(new URL(endpoint.path, window.location.origin), {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return [];

    const payload = await response.json();
    return flattenCatalogPayload(payload)
      .map((product) => normalizeProduct(product, endpoint))
      .filter(Boolean);
  } catch (error) {
    console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${endpoint.path}:`, error);
    return [];
  }
}

async function hostCatalogProducts() {
  if (!hostCatalogPromise) {
    hostCatalogPromise = Promise.all(HOST_CATALOG_ENDPOINTS.map(fetchCatalogEndpoint))
      .then((groups) => groups.flat());
  }
  return hostCatalogPromise;
}

async function fetchHubProductsBySearch(searchQuery, limit = 120) {
  const terms = queryTerms(searchQuery);
  if (!terms.length) return [];

  const url = new URL("/v1/products", config.apiUrl);
  url.searchParams.set("site_id", config.siteId);
  url.searchParams.set("limit", String(limit));

  try {
    const response = await fetch(url.toString(), { headers: { Accept: "application/json" } });
    if (!response.ok) return [];
    return (await response.json())
      .map((product) => normalizeProduct(product))
      .filter(Boolean)
      .filter((product) => productMatchesQuery(product, searchQuery))
      .slice(0, 12);
  } catch (error) {
    console.warn("[AI Hub Widget] Hub product search fallback failed:", error);
    return [];
  }
}

export async function fetchProductsForDisplay(productIds, searchQuery = "") {
  const ids = (Array.isArray(productIds) ? productIds : []).map(clean).filter(Boolean);
  let products = [];
  let source = "";
  let reason = "";

  if (ids.length) {
    try {
      products = await fetchHubProductsByIds(ids);
      source = "hub_by_ids";
    } catch (error) {
      reason = "hub_product_lookup_failed";
      console.warn("[AI Hub Widget] Hub product ID lookup failed:", error);
    }
  }

  if (!products.length && ids.length) {
    const hostProducts = await hostCatalogProducts();
    products = ids
      .map((id) => hostProducts.find((product) => productMatchesId(product, id)))
      .filter(Boolean);
    if (products.length) source = "host_by_ids";
  }

  if (!products.length && searchQuery) {
    products = await fetchHubProductsBySearch(searchQuery);
    if (products.length) source = "hub_search";
  }

  if (!products.length && searchQuery) {
    const hostProducts = await hostCatalogProducts();
    products = hostProducts.filter((product) => productMatchesQuery(product, searchQuery)).slice(0, 12);
    if (products.length) source = "host_search";
  }

  return {
    products,
    source,
    reason: products.length ? "" : reason || "no_matching_products_rendered",
  };
}

export async function fetchHubProductsByIds(productIds) {
  const ids = (Array.isArray(productIds) ? productIds : [])
    .map(clean)
    .filter(Boolean);
  if (!ids.length) return [];

  const url = new URL(API_PATHS.PRODUCTS_BY_IDS, config.apiUrl);
  url.searchParams.set("site_id", config.siteId);
  url.searchParams.set("ids", ids.join(","));

  const response = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Failed to fetch products from AI Hub API");

  const products = (await response.json()).map((product) => normalizeProduct(product)).filter(Boolean);
  const byId = new Map(products.map((product) => [String(product.id), product]));
  return ids.map((id) => byId.get(id)).filter(Boolean);
}

export async function resolveProductDetailUrl(productId) {
  const targetId = clean(productId);
  if (!targetId) return "";

  const [hubProduct] = await fetchHubProductsByIds([targetId]);
  if (hubProduct?.url) return hubProduct.url;

  const hostProducts = await hostCatalogProducts();
  const directMatch = hostProducts.find((product) => productMatchesId(product, targetId));
  if (directMatch?.url) return directMatch.url;

  if (!hubProduct) return "";
  const equivalent = hostProducts.find(
    (product) => productNamesMatch(product, hubProduct) || productImagesMatch(product, hubProduct),
  );
  return equivalent?.url || "";
}
