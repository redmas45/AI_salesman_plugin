/**
 * Logout / session reset contract for the host website.
 *
 * When a customer signs out, everything Maya remembers about them is still in
 * the page: the conversation, the records she referred to, the open socket, the
 * queued audio, and the session id that ties the next turn to the previous one.
 * Signing out of the store did nothing about any of it, so the next visitor on
 * the same browser could continue the previous person's conversation.
 *
 * The contract is explicit and vertical-independent. The host calls
 * `window.AIHub.resetSession()` (or dispatches the documented event) at the
 * moment it considers the session over. Nothing here guesses: no logout link is
 * intercepted, no host click is watched, and no storage key outside AI Hub's own
 * namespaces is touched - the host's cart, theme, and consent state survive
 * untouched, because they are not ours to clear.
 */

export const SESSION_RESET_EVENT = "aihub:session-reset";
export const HOST_GLOBAL = "AIHub";
// Only keys under these prefixes belong to AI Hub. Everything else on the origin
// belongs to the host website and is left exactly as it was.
export const HUB_STORAGE_PREFIXES = Object.freeze(["mayabot:", "aihub:"]);

function ownedKeys(storage) {
  const keys = [];
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key && HUB_STORAGE_PREFIXES.some((prefix) => key.startsWith(prefix))) keys.push(key);
  }
  return keys;
}

function clearOwnedKeys(storage) {
  if (!storage) return [];
  try {
    const keys = ownedKeys(storage);
    for (const key of keys) storage.removeItem(key);
    return keys;
  } catch (_err) {
    return [];
  }
}

/** Remove AI Hub's own storage keys from both web storages. Returns what went. */
export function clearHubStorage() {
  const removed = [];
  try {
    removed.push(...clearOwnedKeys(window.sessionStorage));
  } catch (_err) {
    // Storage can be unavailable in privacy modes; a reset must still proceed.
  }
  try {
    removed.push(...clearOwnedKeys(window.localStorage));
  } catch (_err) {
    // Same: unavailable storage is not a reason to skip the rest of the reset.
  }
  return removed;
}

/**
 * Build the reset routine from the pieces that own each kind of state.
 *
 * Every dependency is optional so the same contract works for a host that
 * embeds only part of the runtime, and so a missing collaborator degrades to
 * "that part was already not running" rather than throwing mid-reset.
 */
export function createSessionReset({
  cancelRecording,
  stopPlayback,
  resetTransport,
  conversationMemory,
  clearOverlays,
  rotateSessionId,
} = {}) {
  return function resetSession() {
    const outcome = { stopped_recording: false, stopped_audio: false, cleared_keys: [], session_id: "" };
    outcome.stopped_recording = safeCall(cancelRecording);
    outcome.stopped_audio = safeCall(stopPlayback);
    safeCall(resetTransport);
    safeCall(() => conversationMemory?.clear?.());
    safeCall(clearOverlays);
    outcome.cleared_keys = clearHubStorage();
    outcome.session_id = String(safeCall(rotateSessionId) || "");
    return outcome;
  };
}

function safeCall(fn) {
  if (typeof fn !== "function") return false;
  try {
    const value = fn();
    return value === undefined ? true : value;
  } catch (err) {
    console.warn("[AI Hub Widget] Session reset step failed:", err);
    return false;
  }
}

/**
 * Publish the contract. The host opts in by calling it; AI Hub never decides on
 * its own that a session ended.
 */
export function installSessionResetContract(resetSession) {
  const namespace = window[HOST_GLOBAL] || {};
  namespace.resetSession = resetSession;
  window[HOST_GLOBAL] = namespace;
  const handler = () => resetSession();
  window.addEventListener(SESSION_RESET_EVENT, handler);
  return () => {
    window.removeEventListener(SESSION_RESET_EVENT, handler);
    if (window[HOST_GLOBAL]?.resetSession === resetSession) {
      delete window[HOST_GLOBAL].resetSession;
    }
  };
}
