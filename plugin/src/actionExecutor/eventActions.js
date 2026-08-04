import { EVENTS } from "../core/constants";

export function executeBrowserEventAction(action) {
  window.dispatchEvent(new CustomEvent(EVENTS.MAYABOT_ACTION, { detail: action }));
  return {
    status: "requested",
    stage: "browser_event",
    reason: "event_dispatched_without_confirmation",
  };
}
