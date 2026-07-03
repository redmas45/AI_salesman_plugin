import { ACTIONS, ACTION_PARAMS } from "../constants";

export function canExecuteNavigationAction(action) {
  return action.action === ACTIONS.NAVIGATE_TO && Boolean(pageToPath(action.parameters?.[ACTION_PARAMS.PAGE]));
}

export function executeNavigationAction(action) {
  window.location.href = pageToPath(action.parameters?.[ACTION_PARAMS.PAGE]);
  return true;
}

function pageToPath(page) {
  const rawPage = String(page || "").trim();
  if (!rawPage || isUnsafePath(rawPage) || /^https?:\/\//i.test(rawPage)) return "";
  if (rawPage === "home" || rawPage === "/") return "/";

  const mappedPath = routeMapPath(rawPage);
  if (mappedPath) return mappedPath;

  const path = rawPage.replace(/^\/+|\/+$/g, "");
  return path ? `/${path}` : "/";
}

function routeMapPath(page) {
  const routes = window.AIHubAdapterRuntime?.config?.adapter?.routes
    || window.AIHubAdapter?.config?.adapter?.routes
    || {};
  const routeKeys = routeAliases(page);

  for (const key of routeKeys) {
    const mapped = routes[key];
    const path = cleanSameOriginPath(mapped);
    if (path) return path;
  }

  for (const [key, value] of Object.entries(routes)) {
    if (!routeKeys.includes(normalizeRouteKey(key))) continue;
    const path = cleanSameOriginPath(value);
    if (path) return path;
  }

  return "";
}

function routeAliases(page) {
  const normalized = normalizeRouteKey(page);
  const trimmedPath = String(page || "").trim().replace(/^\/+|\/+$/g, "").toLowerCase();
  const lastSegment = trimmedPath.split("?")[0].split("#")[0].split("/").filter(Boolean).pop() || "";
  return Array.from(new Set([normalized, trimmedPath, normalizeRouteKey(lastSegment)].filter(Boolean)));
}

function normalizeRouteKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9/_\s-]+/g, " ")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\s+/g, "-");
}

function cleanSameOriginPath(value) {
  const text = String(value || "").trim();
  if (!text || isUnsafePath(text)) return "";
  if (/^https?:\/\//i.test(text)) {
    try {
      const url = new URL(text);
      if (url.origin !== window.location.origin) return "";
      return `${url.pathname || "/"}${url.search || ""}${url.hash || ""}`;
    } catch {
      return "";
    }
  }
  return text.startsWith("/") ? text : `/${text.replace(/^\/+/, "")}`;
}

function isUnsafePath(value) {
  return /^(?:javascript:|data:|\/\/)/i.test(String(value || "").trim());
}
