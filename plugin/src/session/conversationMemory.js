import { ACTION_PARAMS } from "../core/constants";

const ACTION_RESULT_SUMMARY_LIMIT = 4;
const ACTION_NAME_LIMIT = 40;
const ACTION_STATUS_LIMIT = 24;
const ACTION_REASON_LIMIT = 80;
const ACTION_PATH_LIMIT = 120;

// The latest exchanges are sent verbatim so the current task keeps full accuracy;
// everything older is condensed into one bounded summary so the request (and the
// prompt the model must read) does not grow with the length of the conversation.
const RECENT_VERBATIM_MESSAGES = 6; // ~3 user+assistant exchanges
const MAX_RETAINED_MESSAGES = 40; // internal bound; never unbounded
const SUMMARY_MAX_CHARS = 600;
const SUMMARY_MAX_ASKS = 6;
const SUMMARY_MAX_IDS = 12;
const PRODUCT_ID_TAG = /\[PRODUCT_IDS:\s*([^\]]+)\]/g;

export function createConversationMemory() {
  const history = [];

  function rememberConversation(role, content) {
    const cleanContent = String(content || "").trim();
    if (!cleanContent) return;
    history.push({ role, content: cleanContent });
    if (history.length > MAX_RETAINED_MESSAGES) {
      history.shift();
    }
  }

  return {
    history,
    /**
     * The bounded history to send on a turn: the most recent exchanges verbatim,
     * preceded (when older turns exist) by a single condensed summary. This keeps
     * the payload flat as the conversation grows while preserving the current
     * task's detail and the products already discussed.
     */
    historyForRequest() {
      if (history.length <= RECENT_VERBATIM_MESSAGES) return history.map((entry) => ({ ...entry }));
      const older = history.slice(0, history.length - RECENT_VERBATIM_MESSAGES);
      const recent = history.slice(history.length - RECENT_VERBATIM_MESSAGES).map((entry) => ({ ...entry }));
      const summary = summarizeOlderTurns(older);
      return summary ? [summary, ...recent] : recent;
    },
    /** Forget everything: conversation turns, action outcomes, and referents. */
    clear() {
      history.length = 0;
    },
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

/** One bounded `system` summary of the turns older than the verbatim window. */
function summarizeOlderTurns(older) {
  const asks = [];
  const productIds = [];
  for (const entry of older) {
    if (entry.role === "user" && asks.length < SUMMARY_MAX_ASKS) {
      asks.push(entry.content.replace(/\s+/g, " ").trim().slice(0, 80));
    }
    let match;
    PRODUCT_ID_TAG.lastIndex = 0;
    while ((match = PRODUCT_ID_TAG.exec(entry.content)) !== null) {
      appendUniqueIds(productIds, match[1].split(",").map((id) => id.trim()));
    }
  }
  const parts = [];
  if (asks.length) parts.push(`Earlier the customer asked: ${asks.join("; ")}.`);
  if (productIds.length) parts.push(`Products discussed: ${productIds.slice(0, SUMMARY_MAX_IDS).join(", ")}.`);
  if (!parts.length) return null;
  return {
    role: "system",
    content: `[CONVERSATION_SUMMARY] ${parts.join(" ")}`.slice(0, SUMMARY_MAX_CHARS),
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
