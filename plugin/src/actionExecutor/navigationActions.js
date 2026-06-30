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
  if (!rawPage || /^https?:\/\//i.test(rawPage)) return "";
  if (rawPage === "home" || rawPage === "/") return "/";

  const path = rawPage.replace(/^\/+|\/+$/g, "");
  return path ? `/${path}/` : "/";
}
