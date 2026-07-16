import { ACTION_PARAMS, CONVERSATION_HISTORY_LIMIT } from "../core/constants";

const ACTION_RESULT_SUMMARY_LIMIT = 4;
const ACTION_NAME_LIMIT = 40;
const ACTION_STATUS_LIMIT = 24;
const ACTION_REASON_LIMIT = 80;
const ACTION_PATH_LIMIT = 120;

export function createConversationMemory() {
  const history = [];

  function rememberConversation(role, content) {
    const cleanContent = String(content || "").trim();
    if (!cleanContent) return;
    history.push({ role, content: cleanContent });
    if (history.length > CONVERSATION_HISTORY_LIMIT) {
      history.shift();
    }
  }

  return {
    history,
    rememberUserMessage(text) {
      rememberConversation("user", text);
    },
    rememberAssistantMessage(text, uiActions) {
      rememberConversation("assistant", assistantContent(text, uiActions));
    },
    rememberActionResults(results) {
      const content = actionResultContent(results);
      if (content) rememberConversation("assistant", content);
    },
  };
}

function assistantContent(text, uiActions) {
  const productIds = productIdsFromActions(uiActions);
  if (!productIds.length) return text;
  return `${text} [PRODUCT_IDS: ${productIds.join(",")}]`;
}

function productIdsFromActions(uiActions) {
  const productIds = [];
  for (const action of uiActions || []) {
    const params = action.params || {};
    appendUniqueIds(productIds, params[ACTION_PARAMS.PRODUCT_IDS]);
    appendUniqueIds(productIds, [params[ACTION_PARAMS.PRODUCT_ID]]);
  }
  return productIds;
}

function appendUniqueIds(target, values) {
  for (const value of Array.isArray(values) ? values : []) {
    if (value && !target.includes(value)) target.push(value);
  }
}

function actionResultContent(results) {
  const rows = (Array.isArray(results) ? results : [])
    .map(actionResultSummary)
    .filter(Boolean)
    .slice(0, ACTION_RESULT_SUMMARY_LIMIT);
  return rows.length ? `[BROWSER_ACTION_RESULTS: ${rows.join(" | ")}]` : "";
}

function actionResultSummary(result) {
  if (!result || typeof result !== "object" || !result.action) return "";
  const parts = [
    cleanActionResultText(result.action, ACTION_NAME_LIMIT),
    `status=${cleanActionResultText(result.status, ACTION_STATUS_LIMIT) || "unknown"}`,
  ];
  const finalPath = urlPath(result.final_url);
  if (finalPath) parts.push(`final_path=${cleanActionResultText(finalPath, ACTION_PATH_LIMIT)}`);
  if (result.reason) parts.push(`reason=${cleanActionResultText(result.reason, ACTION_REASON_LIMIT)}`);
  appendEvidenceCounts(parts, result.evidence);
  return parts.join(" ");
}

function appendEvidenceCounts(parts, evidence = {}) {
  if (evidence.rendered_product_count !== undefined) {
    parts.push(`rendered_products=${Number(evidence.rendered_product_count || 0)}`);
  }
  if (evidence.rendered_entity_count !== undefined) {
    parts.push(`rendered_records=${Number(evidence.rendered_entity_count || 0)}`);
  }
}

function cleanActionResultText(value, limit) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function urlPath(value) {
  try {
    const url = new URL(String(value || ""), window.location.href);
    return `${url.pathname}${url.search}${url.hash}`;
  } catch (_err) {
    return "";
  }
}
