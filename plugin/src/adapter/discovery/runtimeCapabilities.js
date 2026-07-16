// Capability probes are bounded because browsers may leave permission queries unresolved.
const STORAGE_TEST_KEY = "__aihub_capability_probe__";
const PERMISSION_TIMEOUT_MS = 1200;
const MAX_TEXT_LENGTH = 220;

export async function collectRuntimeCapabilities() {
  const microphonePermission = await microphonePermissionState();
  return {
    reported_at: new Date().toISOString(),
    script_loaded: true,
    origin: safeText(window.location.origin),
    url: safeText(window.location.href),
    protocol: safeText(window.location.protocol),
    secure_context: Boolean(window.isSecureContext),
    top_level_window: isTopLevelWindow(),
    document_ready_state: safeText(document.readyState),
    fetch_api: typeof window.fetch === "function",
    permissions_api: Boolean(navigator.permissions?.query),
    microphone_permission: microphonePermission,
    media_devices_api: Boolean(navigator.mediaDevices),
    get_user_media_api: Boolean(navigator.mediaDevices?.getUserMedia),
    session_storage: storageState("sessionStorage"),
    local_storage: storageState("localStorage"),
    cookies_enabled: Boolean(navigator.cookieEnabled),
    shadow_dom_api: Boolean(Element.prototype.attachShadow),
    custom_elements_api: Boolean(window.customElements),
    mutation_observer_api: Boolean(window.MutationObserver),
    iframe_count: document.querySelectorAll("iframe").length,
    language: safeText(navigator.language),
    user_agent: safeText(navigator.userAgent),
  };
}

async function microphonePermissionState() {
  if (!navigator.permissions?.query) return "unsupported";
  try {
    const permission = await withTimeout(
      navigator.permissions.query({ name: "microphone" }),
      PERMISSION_TIMEOUT_MS,
    );
    return safeText(permission?.state || "unknown");
  } catch (_error) {
    return "unknown";
  }
}

function withTimeout(promise, timeoutMs) {
  return Promise.race([
    promise,
    new Promise((resolve) => {
      window.setTimeout(() => resolve({ state: "timeout" }), timeoutMs);
    }),
  ]);
}

function storageState(storageName) {
  try {
    const storage = window[storageName];
    if (!storage) return "unavailable";
    storage.setItem(STORAGE_TEST_KEY, "1");
    storage.removeItem(STORAGE_TEST_KEY);
    return "available";
  } catch (_error) {
    return "blocked";
  }
}

function isTopLevelWindow() {
  try {
    return window.top === window.self;
  } catch (_error) {
    return false;
  }
}

function safeText(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, MAX_TEXT_LENGTH);
}
