import { queryElementsDeep } from "./deepDom";
import {
  CAPTCHA_PROVIDER_SIGNATURES,
  CALENDAR_PROVIDER_SIGNATURES,
  MAP_PROVIDER_SIGNATURES,
  PAYMENT_PROVIDER_SIGNATURES,
  providerMatchesText,
} from "./providerSignatures";

const MAX_SOURCES = 20;
const MAX_HOSTS = 20;
const PROVIDER_TEXT_LIMIT = 12000;

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

export function collectBarrierHints() {
  const iframeSources = sourceList("iframe[src]");
  const scriptSources = sourceList("script[src]");
  const externalTargets = externalActionTargets();
  const actionText = pageProviderText(iframeSources, scriptSources, externalTargets);
  const captchaProviders = providerMatchesText(actionText, CAPTCHA_PROVIDER_SIGNATURES);
  return {
    iframe_count: iframeSources.length,
    iframe_sources: iframeSources.slice(0, MAX_SOURCES),
    password_inputs: queryElementsDeep("input[type='password']").length,
    file_uploads: queryElementsDeep("input[type='file']").length,
    date_inputs: queryElementsDeep("input[type='date'], input[type='datetime-local'], input[type='time']").length,
    captcha: hasCaptcha(actionText, captchaProviders),
    captcha_providers: captchaProviders,
    payment_providers: providerMatchesText(actionText, PAYMENT_PROVIDER_SIGNATURES),
    calendar_providers: providerMatchesText(actionText, CALENDAR_PROVIDER_SIGNATURES),
    map_providers: providerMatchesText(actionText, MAP_PROVIDER_SIGNATURES),
    external_action_hosts: hostList(externalTargets).slice(0, MAX_HOSTS),
  };
}

function sourceList(selector) {
  return queryElementsDeep(selector)
    .map((element) => clean(element.getAttribute("src")))
    .filter(Boolean)
    .slice(0, MAX_SOURCES);
}

function pageProviderText(iframeSources, scriptSources, externalTargets) {
  return [
    document.body?.innerText || "",
    document.documentElement?.innerHTML || "",
    ...iframeSources,
    ...scriptSources,
    ...externalTargets.map((url) => url.href),
  ]
    .join(" ")
    .toLowerCase()
    .slice(0, PROVIDER_TEXT_LIMIT);
}

function hasCaptcha(text, providers) {
  return (
    providers.length > 0 ||
    text.includes("captcha") ||
    text.includes("recaptcha") ||
    text.includes("hcaptcha") ||
    text.includes("turnstile") ||
    Boolean(document.querySelector(".g-recaptcha, .h-captcha, [data-sitekey], iframe[src*='recaptcha'], iframe[src*='hcaptcha'], iframe[src*='turnstile']"))
  );
}

function externalActionTargets() {
  const targets = [];
  for (const element of queryElementsDeep("a[href], form[action]")) {
    const url = externalUrl(element.getAttribute("href") || element.getAttribute("action"));
    if (url) targets.push(url);
  }
  return targets;
}

function hostList(targets) {
  return Array.from(new Set(targets.map((url) => url.host)));
}

function externalUrl(value) {
  const target = clean(value);
  if (!target) return null;
  try {
    const url = new URL(target, window.location.href);
    if (!["http:", "https:"].includes(url.protocol)) return null;
    if (url.origin === window.location.origin) return null;
    return url;
  } catch (_err) {
    return null;
  }
}
