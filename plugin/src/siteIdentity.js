const DEFAULT_SITE_ID = "site_1";
const EMBED_PLACEHOLDER_PREFIX = "__AI_";
const SITE_ID_MAX_LENGTH = 80;
const HASH_SEED = 2166136261;
const HASH_PRIME = 16777619;
const AUTO_SITE_STORAGE_PREFIX = "aihub:auto-site-id:";
const PATH_SCOPE_ATTRS = ["data-aihub-scope", "data-site-scope"];
const EXPLICIT_SITE_ATTRS = ["data-site-id", "data-aihub-site-id"];

function clean(value) {
  return String(value || "").trim();
}

export function trimTrailingSlash(value) {
  return clean(value).replace(/\/+$/, "");
}

export function resolveSiteId(currentScript, url, embeddedSiteId, fallback = DEFAULT_SITE_ID) {
  return (
    explicitSiteId(currentScript, url, embeddedSiteId) ||
    inferredSiteId() ||
    clean(fallback) ||
    DEFAULT_SITE_ID
  );
}

function explicitSiteId(currentScript, url, embeddedSiteId) {
  for (const attr of EXPLICIT_SITE_ATTRS) {
    const value = clean(currentScript?.getAttribute(attr));
    if (value) return value;
  }

  const queryValue =
    clean(url?.searchParams.get("site")) ||
    clean(url?.searchParams.get("site_id")) ||
    clean(url?.searchParams.get("shop"));
  if (queryValue) return queryValue;

  const embedded = clean(embeddedSiteId);
  if (embedded && !embedded.startsWith(EMBED_PLACEHOLDER_PREFIX)) return embedded;
  return "";
}

function inferredSiteId() {
  const source = siteIdentitySource();
  const storageKey = `${AUTO_SITE_STORAGE_PREFIX}${source}`;
  const stored = storageValue(storageKey);
  if (stored) return stored;

  const host = clean(window.location.host || window.location.hostname || "site");
  const scope = inferredPathScope();
  const slug = safeSiteSlug(`${host}${scope ? `_${scope.replace(/\//g, "_")}` : ""}`);
  const nextSiteId = truncateSiteId(`auto_${slug}_${hash36(source)}`);
  storeValue(storageKey, nextSiteId);
  return nextSiteId;
}

function siteIdentitySource() {
  return `${window.location.origin}${inferredPathScope()}`;
}

function inferredPathScope() {
  return explicitPathScope();
}

function explicitPathScope() {
  for (const attr of PATH_SCOPE_ATTRS) {
    const value = clean(currentScriptElement()?.getAttribute(attr));
    if (value) return normalizedScope(value);
  }

  const meta = document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");
  return normalizedScope(meta);
}

function currentScriptElement() {
  return document.currentScript;
}

function normalizedScope(value) {
  const cleaned = clean(value);
  if (!cleaned || cleaned === "/") return "";
  try {
    const url = new URL(cleaned, window.location.href);
    if (url.origin === window.location.origin) {
      const [firstSegment] = pathSegments(url.pathname);
      return firstSegment ? `/${firstSegment}` : "";
    }
  } catch (_err) {
    // Treat non-URL values as path-like scopes.
  }
  const [firstSegment] = cleaned.replace(/^\/+/, "").split("/");
  return firstSegment ? `/${firstSegment}` : "";
}

function pathSegments(pathname = window.location.pathname) {
  return clean(pathname)
    .split("/")
    .map((segment) => safeDecode(segment).trim())
    .filter(Boolean);
}

function safeDecode(value) {
  try {
    return decodeURIComponent(value);
  } catch (_err) {
    return String(value || "");
  }
}

function safeSiteSlug(value) {
  const slug = clean(value)
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug || "site";
}

function truncateSiteId(value) {
  return clean(value).slice(0, SITE_ID_MAX_LENGTH).replace(/_+$/g, "") || DEFAULT_SITE_ID;
}

function hash36(value) {
  let hash = HASH_SEED;
  const text = clean(value);
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, HASH_PRIME);
  }
  return (hash >>> 0).toString(36);
}

function storageValue(key) {
  try {
    return clean(window.localStorage.getItem(key));
  } catch (_err) {
    return "";
  }
}

function storeValue(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (_err) {
    // Storage can be disabled; deterministic generation still works without it.
  }
}
