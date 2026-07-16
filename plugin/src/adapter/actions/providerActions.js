import { ACTIONS, ACTION_PARAMS } from "../../core/constants";
import { queryElementsDeep } from "../dom/deepDom";
import {
  CALENDAR_PROVIDER_SIGNATURES,
  CONTACT_PROVIDER_SIGNATURES,
  MAP_PROVIDER_SIGNATURES,
  cleanProviderText,
  providerMatchesText,
} from "../discovery/providerSignatures";

const PROVIDER_TARGET_SELECTOR = "a[href], iframe[src]";
const CONTACT_TARGET_SELECTOR = "a[href]";

const HTTP_PROTOCOLS = new Set(["http:", "https:"]);
const CONTACT_PROTOCOLS = new Set(["mailto:", "tel:"]);

const URL_PARAM_KEYS = Object.freeze([
  ACTION_PARAMS.URL,
  "href",
  "link",
  "target_url",
  "provider_url",
  "booking_url",
  "appointment_url",
  "calendar_url",
  "map_url",
  "location_url",
  "contact_url",
]);

const MAP_ACTIONS = new Set([
  ACTIONS.OPEN_MAP,
  ACTIONS.OPEN_LOCATION,
  ACTIONS.SET_LOCATION,
]);

const CALENDAR_ACTIONS = new Set([
  ACTIONS.CHECK_APPOINTMENT_AVAILABILITY,
  ACTIONS.REQUEST_APPOINTMENT,
  ACTIONS.BOOK_APPOINTMENT_REQUEST,
  ACTIONS.REQUEST_CONSULTATION,
  ACTIONS.REQUEST_SITE_VISIT,
  ACTIONS.START_BOOKING,
]);

const CONTACT_ACTIONS = new Set([
  ACTIONS.OPEN_CONTACT,
  ACTIONS.CONTACT_AGENT,
  ACTIONS.REQUEST_CALLBACK,
  ACTIONS.REQUEST_COUNSELOR_CALLBACK,
  ACTIONS.HANDOFF_TO_ADVISOR,
  ACTIONS.HANDOFF_TO_AGENT,
  ACTIONS.HANDOFF_TO_CLINIC,
  ACTIONS.HANDOFF_TO_HUMAN,
  ACTIONS.HANDOFF_TO_LAWYER,
  ACTIONS.HANDOFF_TO_LICENSED_AGENT,
  ACTIONS.HANDOFF_TO_RECRUITER,
]);

export function canExecuteProviderAction(action) {
  const actionName = normalizedActionName(action);
  return MAP_ACTIONS.has(actionName) || CALENDAR_ACTIONS.has(actionName) || CONTACT_ACTIONS.has(actionName);
}

export async function executeProviderAction(action) {
  const actionName = normalizedActionName(action);
  if (MAP_ACTIONS.has(actionName)) {
    return openProviderForAction(action, MAP_PROVIDER_SIGNATURES, PROVIDER_TARGET_SELECTOR, isHttpProviderUrl);
  }
  if (CALENDAR_ACTIONS.has(actionName)) {
    return openProviderForAction(action, CALENDAR_PROVIDER_SIGNATURES, PROVIDER_TARGET_SELECTOR, isHttpProviderUrl);
  }
  if (CONTACT_ACTIONS.has(actionName)) {
    return openProviderForAction(action, CONTACT_PROVIDER_SIGNATURES, CONTACT_TARGET_SELECTOR, isContactProviderUrl);
  }
  return false;
}

function openProviderForAction(action, signatures, selector, isAllowedUrl) {
  const explicitTarget = providerUrlFromParams(action?.parameters || action?.params || {}, signatures, isAllowedUrl);
  if (explicitTarget) return openProviderUrl(explicitTarget);

  const discoveredTarget = discoverProviderTarget(selector, signatures, isAllowedUrl);
  if (!discoveredTarget) return false;
  return openProviderUrl(discoveredTarget);
}

function providerUrlFromParams(params, signatures, isAllowedUrl) {
  for (const key of URL_PARAM_KEYS) {
    const url = parsedUrl(params?.[key]);
    if (url && isAllowedUrl(url, signatures)) return url;
  }
  return null;
}

function discoverProviderTarget(selector, signatures, isAllowedUrl) {
  for (const element of queryElementsDeep(selector)) {
    const url = elementTargetUrl(element);
    if (!url || !isAllowedUrl(url, signatures)) continue;
    if (matchesProviderEvidence(url, element, signatures)) return url;
  }
  return null;
}

function elementTargetUrl(element) {
  return parsedUrl(element?.getAttribute?.("href") || element?.getAttribute?.("src"));
}

function isHttpProviderUrl(url, signatures) {
  return HTTP_PROTOCOLS.has(url.protocol) && providerMatchesText(url.href, signatures).length > 0;
}

function isContactProviderUrl(url, signatures) {
  if (CONTACT_PROTOCOLS.has(url.protocol)) return true;
  return isHttpProviderUrl(url, signatures);
}

function matchesProviderEvidence(url, element, signatures) {
  if (CONTACT_PROTOCOLS.has(url.protocol)) return true;
  const evidence = [
    url.href,
    element?.textContent || "",
    element?.getAttribute?.("aria-label") || "",
    element?.getAttribute?.("title") || "",
  ].join(" ");
  return providerMatchesText(cleanProviderText(evidence), signatures).length > 0;
}

function openProviderUrl(url) {
  if (CONTACT_PROTOCOLS.has(url.protocol) || url.origin === window.location.origin) {
    window.location.href = url.href;
    return true;
  }

  const openedWindow = window.open(url.href, "_blank", "noopener,noreferrer");
  if (openedWindow) {
    openedWindow.opener = null;
    return true;
  }
  window.location.href = url.href;
  return true;
}

function parsedUrl(value) {
  const target = String(value || "").trim();
  if (!target || target.startsWith("#")) return null;
  try {
    const url = new URL(target, window.location.href);
    if (HTTP_PROTOCOLS.has(url.protocol) || CONTACT_PROTOCOLS.has(url.protocol)) return url;
    return null;
  } catch (_err) {
    return null;
  }
}

function normalizedActionName(action) {
  return String(action?.action || "").trim().toUpperCase();
}
