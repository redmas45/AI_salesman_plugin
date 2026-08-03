/**
 * Typed transport failures for the voice turn.
 *
 * The widget used to throw a bare `Error("AI Hub API request failed")` for every
 * non-ok response, and the message matcher then turned all of them into
 * "Connection issue". A provider outage, a rate limit, an oversized recording and
 * an actual network drop were indistinguishable to both the customer and support.
 *
 * A `VoiceTransportError` therefore carries the safe facts needed for diagnosis
 * (status, category, error code, correlation id) while the customer-facing string
 * stays a fixed phrase per category. Server text is never rendered, so a leaked
 * traceback or connection string cannot reach the page.
 */

export const TRANSPORT_CATEGORY = Object.freeze({
  NETWORK: "network",
  TIMEOUT: "timeout",
  ACCESS_DENIED: "access_denied",
  INVALID_REQUEST: "invalid_request",
  PAYLOAD_TOO_LARGE: "payload_too_large",
  UNSUPPORTED_MEDIA: "unsupported_media",
  RATE_LIMITED: "rate_limited",
  PROVIDER_UNAVAILABLE: "provider_unavailable",
  SERVER_ERROR: "server_error",
  MICROPHONE: "microphone",
  UNKNOWN: "unknown",
});

// Short enough for the widget status line, and free of server-supplied text.
const CATEGORY_MESSAGES = Object.freeze({
  [TRANSPORT_CATEGORY.NETWORK]: "Connection issue",
  [TRANSPORT_CATEGORY.TIMEOUT]: "Timed out",
  [TRANSPORT_CATEGORY.ACCESS_DENIED]: "Access denied",
  [TRANSPORT_CATEGORY.INVALID_REQUEST]: "Try again",
  [TRANSPORT_CATEGORY.PAYLOAD_TOO_LARGE]: "Recording too long",
  [TRANSPORT_CATEGORY.UNSUPPORTED_MEDIA]: "Audio not supported",
  [TRANSPORT_CATEGORY.RATE_LIMITED]: "Service busy",
  [TRANSPORT_CATEGORY.PROVIDER_UNAVAILABLE]: "Service unavailable",
  [TRANSPORT_CATEGORY.SERVER_ERROR]: "Service error",
  [TRANSPORT_CATEGORY.MICROPHONE]: "Mic unavailable",
  [TRANSPORT_CATEGORY.UNKNOWN]: "Try again",
});

const MAX_CODE_CHARS = 64;

export class VoiceTransportError extends Error {
  constructor(category, { status = 0, code = "", requestId = "", stage = "" } = {}) {
    super(`voice_transport_${category}`);
    this.name = "VoiceTransportError";
    this.category = category;
    this.status = Number(status) || 0;
    this.code = String(code || "").slice(0, MAX_CODE_CHARS);
    this.requestId = String(requestId || "").slice(0, MAX_CODE_CHARS);
    this.stage = stage;
  }

  get customerMessage() {
    return customerMessageForCategory(this.category);
  }

  /** Safe, bounded fields for diagnostics. Never includes server text. */
  toDiagnostics() {
    return {
      category: this.category,
      status: this.status,
      code: this.code,
      request_id: this.requestId,
      stage: this.stage,
    };
  }
}

export function customerMessageForCategory(category) {
  return CATEGORY_MESSAGES[category] || CATEGORY_MESSAGES[TRANSPORT_CATEGORY.UNKNOWN];
}

/** Map an HTTP status onto a category. Status is authoritative here. */
export function categoryForStatus(status) {
  const code = Number(status) || 0;
  if (code === 401 || code === 403) return TRANSPORT_CATEGORY.ACCESS_DENIED;
  if (code === 408) return TRANSPORT_CATEGORY.TIMEOUT;
  if (code === 413) return TRANSPORT_CATEGORY.PAYLOAD_TOO_LARGE;
  if (code === 415) return TRANSPORT_CATEGORY.UNSUPPORTED_MEDIA;
  if (code === 429) return TRANSPORT_CATEGORY.RATE_LIMITED;
  if (code === 502 || code === 503 || code === 504) return TRANSPORT_CATEGORY.PROVIDER_UNAVAILABLE;
  if (code >= 500) return TRANSPORT_CATEGORY.SERVER_ERROR;
  if (code >= 400) return TRANSPORT_CATEGORY.INVALID_REQUEST;
  return TRANSPORT_CATEGORY.UNKNOWN;
}

/**
 * Classify a thrown value from `fetch` or the surrounding turn.
 *
 * A rejected `fetch` means the request never completed: DNS failure, TLS failure,
 * a blocked CORS preflight, or a dropped connection. Those are all genuinely
 * "connection" problems, which is the one case the old message was right about.
 */
export function classifyThrownError(error) {
  if (error instanceof VoiceTransportError) return error;

  const text = String(error?.message || error || "").toLowerCase();
  if (error?.name === "AbortError" || text.includes("abort") || text.includes("timeout") || text.includes("timed out")) {
    return new VoiceTransportError(TRANSPORT_CATEGORY.TIMEOUT);
  }
  if (text.includes("microphone") || text.includes("permission") || text.includes("notallowed")) {
    return new VoiceTransportError(TRANSPORT_CATEGORY.MICROPHONE);
  }
  if (error?.name === "TypeError" || text.includes("failed to fetch") || text.includes("network") || text.includes("load failed")) {
    return new VoiceTransportError(TRANSPORT_CATEGORY.NETWORK);
  }
  return new VoiceTransportError(TRANSPORT_CATEGORY.UNKNOWN);
}

/**
 * Build a typed error from a non-ok response.
 *
 * Only the status, a short machine code, and a correlation id are kept. The
 * response body is inspected solely for a bounded `code`/`error_code` field; free
 * text is deliberately discarded.
 */
export function errorForResponse(response, payload = null) {
  const status = Number(response?.status) || 0;
  const requestId =
    response?.headers?.get?.("x-request-id") || response?.headers?.get?.("x-correlation-id") || "";
  const rawCode = payload && typeof payload === "object" ? payload.code || payload.error_code || "" : "";
  const code = /^[A-Za-z0-9_.:-]{1,64}$/.test(String(rawCode || "")) ? String(rawCode) : "";
  return new VoiceTransportError(categoryForStatus(status), { status, code, requestId, stage: "http_response" });
}
