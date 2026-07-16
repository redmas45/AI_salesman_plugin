// Runtime policy reports explain why an action was blocked without exposing visitor input.
const POLICY_EVENT_PATH = "/v1/widget/policy-event";

function clean(value) {
  return String(value || "").trim();
}

function list(value) {
  return Array.isArray(value) ? value.map((item) => clean(item).toUpperCase()).filter(Boolean) : [];
}

function records(value) {
  return Array.isArray(value)
    ? value.filter((item) => item && typeof item === "object").slice(0, 12)
    : [];
}

function apiUrl(path, apiBaseUrl) {
  return new URL(path, apiBaseUrl).toString();
}

function handoffFlowForPolicy(policy) {
  const handoffFlows = records(policy.handoff_flows);
  const handoffActions = new Set(list(policy.handoff_actions));
  return (
    handoffFlows.find((flow) => handoffActions.has(clean(flow.action).toUpperCase())) ||
    handoffFlows[0] ||
    null
  );
}

export function actionPolicyBlock(action, runtimeConfig) {
  const actionName = clean(action?.action).toUpperCase();
  if (!actionName) return null;

  const policy = runtimeConfig?.adapter?.action_policy || {};
  const blockedActions = new Set(list(policy.blocked_actions));
  if (!blockedActions.has(actionName)) return null;

  const runtimeBlockedActions = new Set(list(policy.runtime_blocked_actions));
  const reason = runtimeBlockedActions.has(actionName)
    ? "blocked_by_action_health"
    : "blocked_by_barrier_policy";
  return {
    action: actionName,
    reason,
    blocked_actions: list(policy.blocked_actions),
    runtime_blocked_actions: list(policy.runtime_blocked_actions),
    handoff_actions: list(policy.handoff_actions),
    handoff_flow: handoffFlowForPolicy(policy),
    handoff_flows: records(policy.handoff_flows),
    notes: Array.isArray(policy.notes) ? policy.notes.slice(0, 8) : [],
  };
}

export async function reportPolicyBlock(apiBaseUrl, siteId, action, block) {
  if (!block || !apiBaseUrl || !siteId) return;
  try {
    await fetch(apiUrl(POLICY_EVENT_PATH, apiBaseUrl), {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        site_id: siteId,
        origin: window.location.origin,
        url: window.location.href,
        occurred_at: new Date().toISOString(),
        action: block.action || clean(action?.action).toUpperCase(),
        status: "blocked",
        reason: block.reason,
        policy: {
          blocked_actions: block.blocked_actions || [],
          runtime_blocked_actions: block.runtime_blocked_actions || [],
          handoff_actions: block.handoff_actions || [],
          handoff_flow: block.handoff_flow || null,
          handoff_flows: block.handoff_flows || [],
          notes: block.notes || [],
        },
      }),
      keepalive: true,
    });
  } catch (err) {
    console.warn("[AIHubAdapter] Policy block report failed.", err);
  }
}
