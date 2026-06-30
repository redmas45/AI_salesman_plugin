const RUNTIME_GLOBAL = "AIHubAdapterRuntime";
const ADAPTER_GLOBAL = "AIHubAdapter";

function normalizeAction(action) {
  const params = action?.params || action?.parameters || {};
  return {
    ...(action || {}),
    params,
    parameters: params,
  };
}

export function hasAIHubAdapter() {
  return Boolean(
    window[RUNTIME_GLOBAL]?.executeAction ||
      window[ADAPTER_GLOBAL]?.handleAction,
  );
}

export async function executeWithAIHubAdapter(action) {
  return (await executeWithAIHubAdapterResult(action)).succeeded;
}

export async function executeWithAIHubAdapterResult(action) {
  const normalizedAction = normalizeAction(action);
  if (window[RUNTIME_GLOBAL]?.executeAction) {
    const runtime = window[RUNTIME_GLOBAL];
    const succeeded = (await runtime.executeAction(normalizedAction)) === true;
    const state = runtime.lastActionResult || {};
    return {
      succeeded,
      handled: state.handled === true || succeeded,
      status: state.status || (succeeded ? "ok" : "not_handled"),
      reason: state.reason || "",
      blocked: state.status === "blocked",
      disabled: state.status === "disabled",
    };
  }
  if (window[ADAPTER_GLOBAL]?.handleAction) {
    const succeeded = (await window[ADAPTER_GLOBAL].handleAction(normalizedAction)) === true;
    return {
      succeeded,
      handled: succeeded,
      status: succeeded ? "ok" : "not_handled",
      reason: "",
      blocked: false,
      disabled: false,
    };
  }
  return {
    succeeded: false,
    handled: false,
    status: "missing_adapter",
    reason: "",
    blocked: false,
    disabled: false,
  };
}
