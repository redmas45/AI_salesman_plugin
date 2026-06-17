const currentScript = document.currentScript;
const embeddedApiUrl = "__AI_PUBLIC_API_URL__";
const embeddedSiteId = "__AI_DEFAULT_SITE_ID__";
const SESSION_STORAGE_PREFIX = "shopbot:session:";

function clean(value) {
  return String(value || "").trim();
}

function scriptUrl() {
  const src = clean(currentScript?.getAttribute("src"));
  if (!src) return null;
  try {
    return new URL(src, window.location.href);
  } catch (_err) {
    return null;
  }
}

function resolveSiteId(url) {
  return (
    clean(currentScript?.getAttribute("data-site-id")) ||
    clean(url?.searchParams.get("site")) ||
    clean(url?.searchParams.get("site_id")) ||
    clean(url?.searchParams.get("shop")) ||
    (embeddedSiteId.startsWith("__AI_") ? "" : embeddedSiteId) ||
    "site_1"
  );
}

function resolveApiUrl(url) {
  const fromAttribute = clean(currentScript?.getAttribute("data-api-url"));
  if (fromAttribute) return fromAttribute.replace(/\/+$/, "");

  if (!embeddedApiUrl.startsWith("__AI_")) {
    return embeddedApiUrl.replace(/\/+$/, "");
  }

  if (url?.origin) {
    const pathname = url.pathname.replace(/\/shopbot(?:-widget)?\.js$/, "");
    return `${url.origin}${pathname}`.replace(/\/+$/, "");
  }

  return window.location.origin.replace(/\/+$/, "");
}

function resolveSessionId(siteId) {
  const configuredSessionId = clean(window.ShopBotConfig?.sessionId);
  if (configuredSessionId) return configuredSessionId.slice(0, 120);

  const key = `${SESSION_STORAGE_PREFIX}${siteId}`;
  try {
    const currentValue = window.sessionStorage.getItem(key);
    if (currentValue) return currentValue;
    const nextValue = createSessionId(siteId);
    window.sessionStorage.setItem(key, nextValue);
    return nextValue;
  } catch (_err) {
    return createSessionId(siteId);
  }
}

function createSessionId(siteId) {
  const randomPart = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${siteId}-${randomPart}`.slice(0, 120);
}

const srcUrl = scriptUrl();
const siteId = resolveSiteId(srcUrl);

export const config = {
  siteId,
  get sessionId() {
    return resolveSessionId(siteId);
  },
  apiUrl: resolveApiUrl(srcUrl),
  useWebSocket: clean(currentScript?.getAttribute("data-use-websocket")).toLowerCase() !== "false",
  autoGreet: clean(currentScript?.getAttribute("data-auto-greet")).toLowerCase() !== "false",
  brandName: clean(currentScript?.getAttribute("data-brand")) || "AI-KART",
};
