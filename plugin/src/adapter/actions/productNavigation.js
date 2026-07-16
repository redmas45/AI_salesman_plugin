import { API_PATHS } from "../../core/constants";
import { adapterConfig } from "../runtime/config";
import { detectPlatform } from "../discovery/platforms";

const CUSTOM_CATALOG_ENDPOINTS = Object.freeze([
  { path: "/api/products?per_page=96", routePrefix: "" },
  { path: "/api/products.json", routePrefix: "" },
]);
const SHOPIFY_CATALOG_ENDPOINTS = Object.freeze([
  { path: "/products.json", routePrefix: "/products/" },
  { path: "/collections/all/products.json", routePrefix: "/products/" },
]);
const WOOCOMMERCE_CATALOG_ENDPOINTS = Object.freeze([
  { path: "/wp-json/wc/store/products?per_page=96", routePrefix: "" },
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
const HANDLE_PATTERN = /^[a-z0-9][a-z0-9-]*$/i;
const PRODUCT_ROUTE_PREFIX = "/product/";

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

function sameOriginPath(value) {
  const raw = clean(value);
  if (!raw) return "";
  try {
    const url = new URL(raw, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}${url.hash}`;
  } catch (_err) {
    return "";
  }
}

function productUrlFrom(raw, handle, endpoint) {
  const explicitUrl = sameOriginPath(firstValue(raw, PRODUCT_URL_FIELDS));
  if (explicitUrl) return explicitUrl;
  if (!endpoint?.routePrefix || !HANDLE_PATTERN.test(handle) || !/[a-z]/i.test(handle)) return "";
  return `${endpoint.routePrefix}${encodeURIComponent(handle)}/`;
}

function normalizeProduct(raw, endpoint = {}) {
  if (!raw || typeof raw !== "object") return null;
  const id = firstValue(raw, PRODUCT_ID_FIELDS);
  const handle = clean(raw.handle || raw.slug || raw.product_handle);
  const name = firstValue(raw, PRODUCT_NAME_FIELDS);
  if (!id && !handle) return null;
  return {
    id,
    handle,
    name,
    title: clean(raw.title || name),
    imageUrl: imageFrom(raw),
    url: productUrlFrom(raw, handle || id, endpoint),
  };
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
    return flattenCatalogPayload(await response.json())
      .map((product) => normalizeProduct(product, endpoint))
      .filter(Boolean);
  } catch (_err) {
    return [];
  }
}

function hostCatalogProducts() {
  if (!hostCatalogPromise) {
    hostCatalogPromise = fetchFirstAvailableHostCatalog(catalogEndpointsForPlatform(detectPlatform()));
  }
  return hostCatalogPromise;
}

async function fetchFirstAvailableHostCatalog(endpoints) {
  for (const endpoint of endpoints) {
    const products = await fetchCatalogEndpoint(endpoint);
    if (products.length) return products;
  }
  return [];
}

function catalogEndpointsForPlatform(platform) {
  if (platform === "shopify") return SHOPIFY_CATALOG_ENDPOINTS;
  if (platform === "woocommerce") return WOOCOMMERCE_CATALOG_ENDPOINTS;
  return CUSTOM_CATALOG_ENDPOINTS;
}

async function fetchHubProduct(productId) {
  const id = clean(productId);
  if (!id) return null;
  try {
    const url = new URL(API_PATHS.PRODUCTS_BY_IDS, adapterConfig.apiUrl);
    url.searchParams.set("site_id", adapterConfig.siteId);
    url.searchParams.set("ids", id);
    const response = await fetch(url.toString(), { headers: { Accept: "application/json" } });
    if (!response.ok) return null;
    const [product] = (await response.json()).map((item) => normalizeProduct(item)).filter(Boolean);
    return product || null;
  } catch (_err) {
    return null;
  }
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

export async function resolveProductActionPath(productId) {
  const targetId = clean(productId);
  if (!targetId) return "";

  const hubProduct = await fetchHubProduct(targetId);
  if (hubProduct?.url) return hubProduct.url;

  const hostProducts = await hostCatalogProducts();
  const directMatch = hostProducts.find((product) => productMatchesId(product, targetId));
  if (directMatch?.url) return directMatch.url;

  if (hubProduct) {
    const equivalent = hostProducts.find(
      (product) => productNamesMatch(product, hubProduct) || productImagesMatch(product, hubProduct),
    );
    if (equivalent?.url) return equivalent.url;
  }

  if (HANDLE_PATTERN.test(targetId)) return `${PRODUCT_ROUTE_PREFIX}${encodeURIComponent(targetId)}`;
  return "";
}
