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
  const normalizedAction = normalizeAction(action);
  if (window[RUNTIME_GLOBAL]?.executeAction) {
    return (await window[RUNTIME_GLOBAL].executeAction(normalizedAction)) === true;
  }
  if (window[ADAPTER_GLOBAL]?.handleAction) {
    return (await window[ADAPTER_GLOBAL].handleAction(normalizedAction)) === true;
  }
  return false;
}
