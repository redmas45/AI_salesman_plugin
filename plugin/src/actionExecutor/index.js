import { executePlatformAction } from "../adapter/platforms";
import { canExecuteProviderAction, executeProviderAction } from "../adapter/providerActions";
import { canExecuteEntityAction, executeEntityAction } from "./entityActions";
import { canExecuteHandoffAction, executeHandoffAction } from "./handoffActions";
import { canExecuteNavigationAction, executeNavigationAction } from "./navigationActions";
import { normalizeAction } from "./normalize";
import { canExecuteProductAction, executeProductAction } from "./productActions";
import { canExecuteRuntimeAction, executeRuntimeAction, STOP_ACTION_FALLBACK } from "./runtimeAction";
import { executeBrowserEventAction } from "./eventActions";

const ACTION_EXECUTORS = Object.freeze([
  {
    canExecute: canExecuteRuntimeAction,
    execute: executeRuntimeAction,
  },
  {
    canExecute: canExecuteProductAction,
    execute: executeProductAction,
  },
  {
    canExecute: canExecuteEntityAction,
    execute: executeEntityAction,
  },
  {
    canExecute: canExecuteHandoffAction,
    execute: executeHandoffAction,
  },
  {
    canExecute: () => true,
    execute: executePlatformAction,
  },
  {
    canExecute: canExecuteProviderAction,
    execute: executeProviderAction,
  },
  {
    canExecute: canExecuteNavigationAction,
    execute: executeNavigationAction,
  },
  {
    canExecute: () => true,
    execute: executeBrowserEventAction,
  },
]);

export async function executeActions(actions) {
  for (const rawAction of actions || []) {
    await executeAction(normalizeAction(rawAction));
  }
}

async function executeAction(action) {
  if (!action.action) return;

  for (const executor of ACTION_EXECUTORS) {
    if (!executor.canExecute(action)) continue;
    const result = await executor.execute(action);
    if (result === true || result === STOP_ACTION_FALLBACK) return;
  }
}
