import { HANDOFF_ACTIONS, showHandoffOverlay } from "../handoffOverlay";

export function canExecuteHandoffAction(action) {
  return HANDOFF_ACTIONS.has(action.action);
}

export function executeHandoffAction(action) {
  return showHandoffOverlay(action.action, action.parameters || {});
}
