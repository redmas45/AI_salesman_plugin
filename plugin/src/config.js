import { resolveSiteId, trimTrailingSlash } from "./siteIdentity";

const currentScript = document.currentScript;
const embeddedApiUrl = "__AI_PUBLIC_API_URL__";
const embeddedSiteId = "__AI_DEFAULT_SITE_ID__";
const SESSION_STORAGE_PREFIX = "mayabot:session:";
const DEFAULT_ASSISTANT_BRAND = "Maya";
const DEFAULT_ASSISTANT_TITLE = "AI Salesperson";
const DEFAULT_SPEECH_VOICE_PREFERENCE = "female";

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
    const pathname = url.pathname.replace(/\/mayabot(?:-widget)?\.js$/, "");
    return trimTrailingSlash(`${url.origin}${pathname}`);
  }

  return trimTrailingSlash(window.location.origin);
}

function resolveSessionId(siteId) {
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
const siteId = resolveSiteId(currentScript, srcUrl, embeddedSiteId);

export const config = {
  siteId,
  get sessionId() {
    return resolveSessionId(siteId);
  },
  apiUrl: resolveApiUrl(srcUrl),
  useWebSocket: clean(currentScript?.getAttribute("data-use-websocket")).toLowerCase() === "true",
  autoGreet: clean(currentScript?.getAttribute("data-auto-greet")).toLowerCase() !== "false",
  brandName: clean(currentScript?.getAttribute("data-brand")) || DEFAULT_ASSISTANT_BRAND,
  assistantTitle: clean(currentScript?.getAttribute("data-assistant-title")) || DEFAULT_ASSISTANT_TITLE,
  speechVoiceName: clean(currentScript?.getAttribute("data-speech-voice")),
  speechVoicePreference: clean(currentScript?.getAttribute("data-speech-voice-preference")) || DEFAULT_SPEECH_VOICE_PREFERENCE,
};
