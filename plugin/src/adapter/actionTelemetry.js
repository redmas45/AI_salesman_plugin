const ACTION_EVENT_PATH = "/v1/widget/action-event";

function clean(value) {
  return String(value || "").trim();
}

function apiUrl(path, apiBaseUrl) {
  return new URL(path, apiBaseUrl).toString();
}

function paramKeys(params) {
  if (!params || typeof params !== "object") return [];
  return Object.keys(params)
    .map((key) => clean(key))
    .filter(Boolean)
    .slice(0, 20);
}

function cleanEvidence(evidence) {
  if (!evidence || typeof evidence !== "object") return {};
  const safe = {};
  for (const [key, value] of Object.entries(evidence).slice(0, 20)) {
    const cleanKey = clean(key).slice(0, 80);
    if (!cleanKey) continue;
    if (typeof value === "boolean" || value === null) {
      safe[cleanKey] = value;
    } else if (typeof value === "number") {
      safe[cleanKey] = Number.isFinite(value) ? value : 0;
    } else {
      safe[cleanKey] = clean(value).slice(0, 240);
    }
  }
  return safe;
}

export async function reportActionExecution(apiBaseUrl, siteId, action, result) {
  if (!apiBaseUrl || !siteId || !action?.action) return;
  const payload = JSON.stringify({
    site_id: siteId,
    origin: window.location.origin,
    url: window.location.href,
    occurred_at: new Date().toISOString(),
    request_id: clean(action.request_id || action.action_request_id),
    turn_id: clean(action.turn_id),
    sequence: Number(action.sequence || 0),
    action: clean(action.action).toUpperCase(),
    status: clean(result?.status) || "unknown",
    stage: clean(result?.stage),
    reason: clean(result?.reason),
    duration_ms: Number(result?.duration_ms || 0),
    param_keys: paramKeys(action.parameters || action.params),
    requested_url: clean(result?.requested_url),
    final_url: clean(result?.final_url || window.location.href),
    evidence: cleanEvidence(result?.evidence),
  });
  const url = apiUrl(ACTION_EVENT_PATH, apiBaseUrl);
  if (sendBeaconJson(url, payload)) return;

  try {
    await fetch(url, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: payload,
      keepalive: true,
    });
  } catch (err) {
    console.warn("[AIHubAdapter] Action execution report failed.", err);
  }
}

function sendBeaconJson(url, payload) {
  if (typeof navigator === "undefined" || typeof navigator.sendBeacon !== "function" || typeof Blob !== "function") {
    return false;
  }
  try {
    return navigator.sendBeacon(url, new Blob([payload], { type: "application/json" }));
  } catch (_err) {
    return false;
  }
}
