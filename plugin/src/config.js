const currentScript = document.currentScript;
const embeddedApiUrl = "__AI_PUBLIC_API_URL__";
const embeddedSiteId = "__AI_DEFAULT_SITE_ID__";

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

  if (url?.origin) return url.origin.replace(/\/+$/, "");

  if (!embeddedApiUrl.startsWith("__AI_")) {
    return embeddedApiUrl.replace(/\/+$/, "");
  }

  return window.location.origin.replace(/\/+$/, "");
}

const srcUrl = scriptUrl();

export const config = {
  siteId: resolveSiteId(srcUrl),
  apiUrl: resolveApiUrl(srcUrl),
  useWebSocket: clean(currentScript?.getAttribute("data-use-websocket")).toLowerCase() !== "false",
  autoGreet: clean(currentScript?.getAttribute("data-auto-greet")).toLowerCase() !== "false",
  brandName: clean(currentScript?.getAttribute("data-brand")) || "AI-KART",
};
