/**
 * Continuity for an action whose result only becomes observable after the page
 * has navigated.
 *
 * When Maya opens a product page to act on it, the JavaScript context that
 * requested the action is destroyed before the outcome exists. Previously the
 * turn simply ended, so the next page had no way to tell whether the requested
 * state was ever reached - and any spoken claim about it was unverifiable.
 *
 * A single bounded record survives the navigation. It carries only what the
 * destination needs to re-check the postcondition: the action name, the record
 * ids involved, the requested route, and a timestamp. It is bound to one site
 * and one origin, expires quickly, is consumed exactly once, and is refused
 * outright for checkout, payment, and destructive actions - those must be
 * re-decided on the new page, never replayed from storage.
 */

export const PENDING_TTL_MS = 15000;
export const STORAGE_PREFIX = "aihub:pending-postcondition";

// Money movement and destructive state changes are never carried across a
// navigation boundary. A stale or duplicated record here would spend money or
// destroy a cart the customer did not ask about on this page.
const NEVER_REPLAYED = Object.freeze([
  "CHECKOUT",
  "CLEAR_CART",
  "REMOVE_FROM_CART",
  "UPDATE_CART_QUANTITY",
  "CLEAR_HISTORY",
  "SUBMIT_PAYMENT",
  "PLACE_ORDER",
]);

export function isReplayable(actionName) {
  return !NEVER_REPLAYED.includes(String(actionName || "").toUpperCase());
}

function storageKey(siteId) {
  return `${STORAGE_PREFIX}:${String(siteId || "site")}`;
}

function currentOrigin() {
  try {
    return String(window.location.origin || "");
  } catch (_err) {
    return "";
  }
}

function boundedIds(params) {
  const ids = [];
  for (const key of ["product_ids", "entity_ids"]) {
    if (Array.isArray(params?.[key])) ids.push(...params[key].slice(0, 8).map(String));
  }
  for (const key of ["product_id", "entity_id"]) {
    if (params?.[key]) ids.push(String(params[key]));
  }
  return ids.slice(0, 8);
}

/** Record a postcondition to re-check after same-origin navigation. */
export function storePendingPostcondition(siteId, action, targetPath) {
  const name = String(action?.action || "").toUpperCase();
  if (!name || !isReplayable(name)) return false;
  try {
    window.sessionStorage.setItem(
      storageKey(siteId),
      JSON.stringify({
        action: name,
        ids: boundedIds(action?.parameters || action?.params || {}),
        target_path: String(targetPath || ""),
        origin: currentOrigin(),
        site_id: String(siteId || ""),
        created_at: Date.now(),
      }),
    );
    return true;
  } catch (_err) {
    return false;
  }
}

/**
 * Consume the record for this site, exactly once.
 *
 * A record from another origin, another site, or one that has aged out is
 * discarded rather than honoured, and the slot is cleared either way so an
 * expired entry cannot linger in storage.
 */
export function takePendingPostcondition(siteId) {
  const key = storageKey(siteId);
  let raw = null;
  try {
    raw = window.sessionStorage.getItem(key);
    window.sessionStorage.removeItem(key);
  } catch (_err) {
    return null;
  }
  if (!raw) return null;
  try {
    const record = JSON.parse(raw);
    if (!record?.action || !isReplayable(record.action)) return null;
    if (record.origin && record.origin !== currentOrigin()) return null;
    if (String(record.site_id || "") !== String(siteId || "")) return null;
    if (Date.now() - Number(record.created_at || 0) > PENDING_TTL_MS) return null;
    return record;
  } catch (_err) {
    return null;
  }
}

/** Drop any expired record without consuming a live one. Safe to call on boot. */
export function cleanupExpiredPostconditions(siteId) {
  try {
    const raw = window.sessionStorage.getItem(storageKey(siteId));
    if (!raw) return false;
    const record = JSON.parse(raw);
    const expired = Date.now() - Number(record?.created_at || 0) > PENDING_TTL_MS;
    if (expired) window.sessionStorage.removeItem(storageKey(siteId));
    return expired;
  } catch (_err) {
    return false;
  }
}
