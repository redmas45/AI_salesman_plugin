import { config } from "../core/config";
import { API_PATHS, WIDGET_STATUS_POLL_INTERVAL_MS } from "../core/constants";

let statusPollTimer = null;

export function startWidgetAvailabilityLoop(handlers) {
  if (statusPollTimer) return;
  syncWidgetAvailability(handlers);
  statusPollTimer = window.setInterval(
    () => syncWidgetAvailability(handlers),
    WIDGET_STATUS_POLL_INTERVAL_MS,
  );
}

async function syncWidgetAvailability({ boot, shutdownWidget }) {
  try {
    const enabled = await fetchWidgetEnabled();
    if (enabled) {
      boot();
      return;
    }
    shutdownWidget();
  } catch (_err) {
    boot();
  }
}

async function fetchWidgetEnabled() {
  const url = new URL(API_PATHS.WIDGET_STATUS, config.apiUrl);
  url.searchParams.set("site_id", config.siteId);
  const response = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) return true;
  const data = await response.json();
  return data.enabled !== false;
}
