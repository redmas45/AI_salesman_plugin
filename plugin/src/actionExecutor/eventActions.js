import { EVENTS } from "../constants";

export function executeBrowserEventAction(action) {
  window.dispatchEvent(new CustomEvent(EVENTS.SHOPBOT_ACTION, { detail: action }));
  return true;
}
