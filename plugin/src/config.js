const currentScript = document.currentScript;
const embeddedApiUrl = "__AI_PUBLIC_API_URL__";
const fallbackApiUrl = embeddedApiUrl.startsWith("__AI_")
  ? window.location.origin
  : embeddedApiUrl;

export const config = {
  siteId: currentScript?.getAttribute("data-site-id") || "__AI_DEFAULT_SITE_ID__",
  apiUrl: currentScript?.getAttribute("data-api-url") || fallbackApiUrl
};
