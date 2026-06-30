import { config } from "./config";
import { API_PATHS } from "./constants";

const HOST_CATALOG_ENDPOINTS = Object.freeze([
  { path: "/api/products.json", routePrefix: "" },
  { path: "/products.json", routePrefix: "/products/" },
  { path: "/collections/all/products.json", routePrefix: "/products/" },
]);
const CATALOG_ARRAY_FIELDS = Object.freeze(["products", "data", "items", "results"]);
const PRODUCT_ID_FIELDS = Object.freeze(["id", "product_id", "handle", "sku"]);
const PRODUCT_NAME_FIELDS = Object.freeze(["name", "title"]);
const PRODUCT_URL_FIELDS = Object.freeze(["url", "href", "permalink", "product_url"]);
const PRODUCT_IMAGE_FIELDS = Object.freeze(["image_url", "image", "thumbnail", "featured_image"]);
const PRODUCT_BRAND_FIELDS = Object.freeze(["brand", "vendor"]);
const PRODUCT_CATEGORY_FIELDS = Object.freeze(["category", "category_name", "product_type"]);
const PRODUCT_DESCRIPTION_FIELDS = Object.freeze(["description", "summary", "body_html"]);
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

function valuesFrom(raw, fields) {
  return fields.map((field) => clean(raw?.[field])).filter(Boolean);
}

function firstValue(raw, fields) {
  return valuesFrom(raw, fields)[0] || "";
}

function imageFrom(raw) {
  const direct = firstValue(raw, PRODUCT_IMAGE_FIELDS);
  if (direct) return direct;

  const singleImage = raw?.image || raw?.featured_image;
  if (singleImage && typeof singleImage === "object") {
    return clean(singleImage.src || singleImage.url);
  }

  if (Array.isArray(raw?.images)) {
    return clean(raw.images[0]?.src || raw.images[0]?.url || raw.images[0]);
  }
  return "";
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
  const price = Number(raw.price || raw.amount || raw.cost || 0);
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
