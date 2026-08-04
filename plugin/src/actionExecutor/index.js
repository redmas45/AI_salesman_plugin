import { executePlatformAction } from "../adapter/discovery/platforms";
import { reportActionExecution } from "../adapter/runtime/actionTelemetry";
import { canExecuteProviderAction, executeProviderAction } from "../adapter/actions/providerActions";
import { config } from "../core/config";
import { canExecuteEntityAction, executeEntityAction } from "./entityActions";
import { canExecuteHandoffAction, executeHandoffAction } from "./handoffActions";
import { canExecuteNavigationAction, executeNavigationAction } from "./navigationActions";
import { normalizeAction } from "./normalize";
import { canExecuteProductAction, executeProductAction } from "./productActions";
import { canExecuteRuntimeAction, executeRuntimeAction, STOP_ACTION_FALLBACK } from "./runtimeAction";
import { executeBrowserEventAction } from "./eventActions";
import { observePage, verifyPostcondition } from "./postconditions";
import { canExecuteHostContractAction, executeHostContractAction } from "./hostContractActions";

const ACTION_EXECUTORS = Object.freeze([
  {
    // First: when the host publishes the vertical-neutral contract, search and
    // add-to-cart drive the real website and are verified against its DOM. Only
    // claims the action when the matching contract is present; else falls through.
    name: "host_contract",
    canExecute: canExecuteHostContractAction,
    execute: executeHostContractAction,
  },
  {
    name: "runtime_adapter",
    canExecute: canExecuteRuntimeAction,
    execute: executeRuntimeAction,
  },
  {
    name: "product_overlay",
    canExecute: canExecuteProductAction,
    execute: executeProductAction,
  },
  {
    name: "entity_overlay",
    canExecute: canExecuteEntityAction,
    execute: executeEntityAction,
  },
  {
    name: "handoff_overlay",
    canExecute: canExecuteHandoffAction,
    execute: executeHandoffAction,
  },
  {
    name: "platform_adapter",
    canExecute: () => true,
    execute: executePlatformAction,
  },
  {
    name: "provider_adapter",
    canExecute: canExecuteProviderAction,
    execute: executeProviderAction,
  },
  {
    name: "navigation",
    canExecute: canExecuteNavigationAction,
    execute: executeNavigationAction,
  },
  {
    name: "browser_event",
    canExecute: () => true,
    execute: executeBrowserEventAction,
  },
]);

export async function executeActions(actions) {
  const results = [];
  for (const rawAction of actions || []) {
    const action = normalizeAction(rawAction);
    const result = await executeActionWithTelemetry(action);
    if (result) results.push(result);
  }
  return results;
}

async function executeActionWithTelemetry(action) {
  if (!action.action) return;
  const startedAt = Date.now();
  const requestedUrl = window.location.href;
  // Observed BEFORE execution so "did anything actually change" is answerable.
  const beforeState = observePage();
  await reportActionExecution(config.apiUrl, config.siteId, action, {
    status: "requested",
    stage: "widget_dispatch",
    requested_url: requestedUrl,
    final_url: requestedUrl,
    evidence: actionEvidence(action, requestedUrl, requestedUrl),
  });
  await reportActionExecution(config.apiUrl, config.siteId, action, {
    status: "executing",
    stage: "widget_dispatch",
    requested_url: requestedUrl,
    final_url: window.location.href,
    evidence: actionEvidence(action, requestedUrl, window.location.href),
  });

  let result;
  try {
    result = await executeAction(action);
  } catch (err) {
    result = {
      status: "failed",
      stage: "widget_dispatch",
      reason: err instanceof Error ? err.message : "execution_error",
    };
  }

  // observe -> verify. A successful return is a claim; the postcondition is the
  // evidence. Anything the executor already failed stays failed. An executor that
  // performed its own DOM verification against the host contract (host_contract)
  // reports `self_verified`, so the generic postcondition does not re-check with a
  // different family and wrongly overturn a confirmed host action.
  const postcondition =
    result.status === "succeeded" && result.self_verified
      ? { family: result.stage || "host_contract", verified: true, reason: result.reason || "" }
      : result.status === "succeeded"
        ? await verifyPostcondition(action, beforeState)
        : { family: "none", verified: false, reason: result.reason || "execution_failed" };

  const finalUrl = window.location.href;
  const evidence = {
    ...actionEvidence(action, requestedUrl, finalUrl, result),
    postcondition_family: postcondition.family,
    postcondition_verified: postcondition.verified,
    postcondition_reason: postcondition.reason,
  };
  await reportActionExecution(config.apiUrl, config.siteId, action, {
    status: result.status,
    stage: result.stage,
    reason: result.reason,
    duration_ms: Date.now() - startedAt,
    requested_url: requestedUrl,
    final_url: finalUrl,
    evidence,
  });
  return {
    action: action.action,
    request_id: action.request_id || action.action_request_id || "",
    turn_id: action.turn_id || "",
    sequence: Number(action.sequence || 0),
    status: result.status,
    stage: result.stage,
    reason: result.reason,
    verified: postcondition.verified,
    postcondition: postcondition.family,
    requested_url: requestedUrl,
    final_url: finalUrl,
    evidence,
  };
}

async function executeAction(action) {
  if (!action.action) {
    return { status: "failed", stage: "normalization", reason: "missing_action" };
  }

  for (const executor of ACTION_EXECUTORS) {
    if (!executor.canExecute(action)) continue;
    const result = await executor.execute(action);
    const executionResult = normalizeExecutorResult(result, executor.name);
    if (executionResult) return executionResult;
  }
  return { status: "failed", stage: "all", reason: "no_executor_succeeded" };
}

function normalizeExecutorResult(result, executorName) {
  if (result === true) {
    return { status: "succeeded", stage: executorName, reason: "" };
  }
  if (result === STOP_ACTION_FALLBACK) {
    return { status: "blocked", stage: executorName, reason: "action_blocked" };
  }
  if (!result || typeof result !== "object") {
    return null;
  }

  const status = String(result.status || "").trim().toLowerCase();
  if (!status) return null;
  return {
    status,
    stage: String(result.stage || executorName).trim() || executorName,
    reason: String(result.reason || "").trim(),
    // An executor that already verified the host DOM says so, so the generic
    // postcondition does not re-check the same action with a different family.
    self_verified: Boolean(result.self_verified),
    evidence: result.evidence && typeof result.evidence === "object" ? result.evidence : {},
  };
}

function actionEvidence(action, requestedUrl, finalUrl, result = {}) {
  const params = action.parameters || action.params || {};
  const evidence = {
    requested_url: requestedUrl,
    final_url: finalUrl,
    url_changed: requestedUrl !== finalUrl,
    path_changed: safePath(requestedUrl) !== safePath(finalUrl),
    title: document.title || "",
    stage: result.stage || "",
    result_status: result.status || "",
  };
  if (params.page) evidence.target_page = params.page;
  if (params.product_id) evidence.product_id = params.product_id;
  if (params.entity_id) evidence.entity_id = params.entity_id;
  if (Array.isArray(params.product_ids)) evidence.product_count = params.product_ids.length;
  if (Array.isArray(params.entity_ids)) evidence.entity_count = params.entity_ids.length;
  return {
    ...evidence,
    ...(result.evidence && typeof result.evidence === "object" ? result.evidence : {}),
  };
}

function safePath(url) {
  try {
    return new URL(url, window.location.href).pathname;
  } catch (_err) {
    return "";
  }
}
