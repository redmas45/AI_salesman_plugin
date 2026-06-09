const currentScript = document.currentScript;
export const config = {
  siteId: currentScript?.getAttribute("data-site-id") || "site_1",
  apiUrl: currentScript?.getAttribute("data-api-url") || "http://localhost:8000"
};
