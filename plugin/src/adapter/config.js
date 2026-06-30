import { resolveSiteId, trimTrailingSlash } from "../siteIdentity";

const currentScript = document.currentScript;
const embeddedApiUrl = "__AI_PUBLIC_API_URL__";
const embeddedSiteId = "__AI_DEFAULT_SITE_ID__";

const WIDGET_CONFIG_PATH = "/v1/widget/config";

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

function configUrl(apiUrl, siteId) {
  const url = new URL(WIDGET_CONFIG_PATH, apiUrl);
  url.searchParams.set("site_id", siteId);
  return url.toString();
}

const srcUrl = scriptUrl();

export const adapterConfig = Object.freeze({
  apiUrl: resolveApiUrl(srcUrl),
  siteId: resolveSiteId(currentScript, srcUrl, embeddedSiteId),
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
