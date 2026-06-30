export function normalizeAction(action) {
  const params = action?.params || action?.parameters || {};
  return {
    ...(action || {}),
    action: String(action?.action || "").trim().toUpperCase(),
    params,
    parameters: params,
  };
}
