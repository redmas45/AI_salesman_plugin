const MAX_PENDING_ACTION_AGE_MS = 15000;

function keyFor(siteId) {
  return `aihub:pending-action:${String(siteId || "site")}`;
}

function now() {
  return Date.now();
}

export function storePendingAction(siteId, action) {
  if (!action?.action) return false;
  try {
    window.sessionStorage.setItem(
      keyFor(siteId),
      JSON.stringify({
        action,
        created_at: now(),
      }),
    );
    return true;
  } catch (_err) {
    return false;
  }
}

export function takePendingAction(siteId) {
  try {
    const key = keyFor(siteId);
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    window.sessionStorage.removeItem(key);

    const parsed = JSON.parse(raw);
    if (!parsed?.action || now() - Number(parsed.created_at || 0) > MAX_PENDING_ACTION_AGE_MS) {
      return null;
    }
    return parsed.action;
  } catch (_err) {
    return null;
  }
}
