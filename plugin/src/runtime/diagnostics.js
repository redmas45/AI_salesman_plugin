import { config } from "../core/config";

const RUNTIME_EVENT_PATH = "/v1/widget/runtime-event";
const MAX_METADATA_ENTRIES = 16;

export function emitRuntimeEvent(event = {}) {
  const payload = JSON.stringify({
    site_id: config.siteId,
    origin: window.location.origin,
    occurred_at: new Date().toISOString(),
    session_id: config.sessionId,
    request_id: clean(event.request_id, 80),
    component: clean(event.component || "voice", 60),
    stage: clean(event.stage, 80),
    event_type: clean(event.event_type || "runtime_event", 80),
    severity: clean(event.severity || "info", 20),
    status: clean(event.status || "ok", 20),
    message_code: clean(event.message_code, 80),
    duration_ms: finiteNumber(event.duration_ms),
    metadata: safeMetadata(event.metadata),
  });
  const url = new URL(RUNTIME_EVENT_PATH, config.apiUrl).toString();
  void fetch(url, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: payload,
    keepalive: true,
  }).catch(() => {
    // Diagnostics must never interrupt the customer turn they observe.
  });
}

function safeMetadata(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const result = {};
  for (const [rawKey, rawValue] of Object.entries(raw).slice(0, MAX_METADATA_ENTRIES)) {
    const key = clean(rawKey, 60).toLowerCase();
    if (!key || isSensitiveKey(key)) continue;
    if (typeof rawValue === "boolean" || rawValue === null) result[key] = rawValue;
    else if (typeof rawValue === "number") result[key] = finiteNumber(rawValue);
    else if (typeof rawValue === "string") result[key] = clean(rawValue, 120);
  }
  return result;
}

function isSensitiveKey(key) {
  return ["audio", "transcript", "response", "error", "exception", "token", "secret"].some((term) => key.includes(term));
}

function clean(value, limit) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function finiteNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? Math.max(0, number) : 0;
}
