const currentScript = document.currentScript;
const embeddedApiUrl = "__AI_PUBLIC_API_URL__";
const embeddedSiteId = "__AI_DEFAULT_SITE_ID__";

const WIDGET_CONFIG_PATH = "/v1/widget/config";
const DEFAULT_SITE_ID = "site_1";

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
    DEFAULT_SITE_ID
  );
}

function resolveApiUrl(url) {
  const fromAttribute = clean(currentScript?.getAttribute("data-api-url"));
  if (fromAttribute) return trimTrailingSlash(fromAttribute);

  if (!embeddedApiUrl.startsWith("__AI_")) {
    return trimTrailingSlash(embeddedApiUrl);
  }

  if (url?.origin) {
    const pathname = url.pathname.replace(/\/shopbot-adapter\.js$/, "");
    return trimTrailingSlash(`${url.origin}${pathname}`);
  }

  return trimTrailingSlash(window.location.origin);
}

function trimTrailingSlash(value) {
  return clean(value).replace(/\/+$/, "");
}

function configUrl(apiUrl, siteId) {
  const url = new URL(WIDGET_CONFIG_PATH, apiUrl);
  url.searchParams.set("site_id", siteId);
  return url.toString();
}

const srcUrl = scriptUrl();

export const adapterConfig = Object.freeze({
  apiUrl: resolveApiUrl(srcUrl),
  siteId: resolveSiteId(srcUrl),
});

export async function fetchRuntimeConfig() {
  const response = await fetch(configUrl(adapterConfig.apiUrl, adapterConfig.siteId), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error("AI Hub adapter config request failed.");
  }
  return response.json();
}
