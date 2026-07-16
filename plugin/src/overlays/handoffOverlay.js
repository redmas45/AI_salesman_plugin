import { ACTION_PARAMS, ACTIONS, OVERLAY_COLLAPSE_DELAY_MS } from "../core/constants";

const PANEL_ID = "mayabot-handoff-panel";
const STYLES_ID = "mayabot-handoff-overlay-styles";
const CONTACT_ROUTE_KEYS = Object.freeze(["contact", "support", "help"]);
const CHECKOUT_ROUTE_KEYS = Object.freeze(["checkout", "cart"]);

export const HANDOFF_ACTIONS = new Set([
  ACTIONS.CHECKOUT_HANDOFF,
  ACTIONS.HANDOFF_TO_ADVISOR,
  ACTIONS.HANDOFF_TO_AGENT,
  ACTIONS.HANDOFF_TO_CLINIC,
  ACTIONS.HANDOFF_TO_HUMAN,
  ACTIONS.HANDOFF_TO_LAWYER,
  ACTIONS.HANDOFF_TO_LICENSED_AGENT,
  ACTIONS.HANDOFF_TO_RECRUITER,
]);

const HANDOFF_COPY = Object.freeze({
  [ACTIONS.CHECKOUT_HANDOFF]: {
    title: "Checkout needs your confirmation",
    body: "This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",
    primary: "Open checkout",
  },
  [ACTIONS.HANDOFF_TO_ADVISOR]: {
    title: "Advisor handoff",
    body: "This request needs a qualified advisor. I can open the contact path so the site team can continue.",
    primary: "Contact advisor",
  },
  [ACTIONS.HANDOFF_TO_AGENT]: {
    title: "Agent handoff",
    body: "This step needs an agent or account-specific help. I can open the contact path for follow-up.",
    primary: "Contact agent",
  },
  [ACTIONS.HANDOFF_TO_CLINIC]: {
    title: "Clinic handoff",
    body: "This request needs clinic confirmation. I can open the appointment or contact path for the next step.",
    primary: "Contact clinic",
  },
  [ACTIONS.HANDOFF_TO_HUMAN]: {
    title: "Human handoff",
    body: "This step needs human confirmation. I can open the most relevant contact path.",
    primary: "Open contact",
  },
  [ACTIONS.HANDOFF_TO_LAWYER]: {
    title: "Legal handoff",
    body: "This request needs a legal professional. I can open the consultation or contact path.",
    primary: "Contact lawyer",
  },
  [ACTIONS.HANDOFF_TO_LICENSED_AGENT]: {
    title: "Licensed agent handoff",
    body: "This request needs a licensed agent. I can open the quote or contact path for follow-up.",
    primary: "Contact agent",
  },
  [ACTIONS.HANDOFF_TO_RECRUITER]: {
    title: "Recruiter handoff",
    body: "This request needs recruiter review. I can open the application or contact path.",
    primary: "Contact recruiter",
  },
});

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function clean(value) {
  return String(value || "").trim();
}

function ensureStyles() {
  if (document.getElementById(STYLES_ID)) return;

  const style = document.createElement("style");
  style.id = STYLES_ID;
  style.textContent = `
    #${PANEL_ID} {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483639;
      width: min(calc(100vw - 32px), 460px);
      transform: translate(-50%, calc(100% + 32px));
      opacity: 0;
      pointer-events: none;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.98);
      box-shadow: 0 24px 70px rgba(22, 22, 21, 0.18);
      color: #161615;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
    }
    #${PANEL_ID}.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    .mayabot-handoff-body {
      display: grid;
      gap: 12px;
      padding: 16px;
    }
    .mayabot-handoff-top {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
    }
    .mayabot-handoff-title {
      margin: 0;
      color: #161615;
      font-size: 16px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .mayabot-handoff-close {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      flex: 0 0 auto;
      border: 1px solid rgba(22, 22, 21, 0.14);
      border-radius: 8px;
      background: #ffffff;
      color: #161615;
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
    }
    .mayabot-handoff-text {
      margin: 0;
      color: #534d44;
      font-size: 14px;
      line-height: 1.45;
    }
    .mayabot-handoff-reason {
      margin: 0;
      border-left: 3px solid #d9b66f;
      padding: 8px 10px;
      background: #fbf6ea;
      color: #534d44;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-handoff-meta {
      display: grid;
      gap: 4px;
      margin: 0;
      color: #6f665b;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-handoff-meta strong {
      color: #161615;
      font-weight: 760;
    }
    .mayabot-handoff-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .mayabot-handoff-actions button {
      min-height: 38px;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 13px;
      font-weight: 760;
      line-height: 1;
      padding: 0 14px;
    }
    .mayabot-handoff-actions button.secondary {
      background: #ffffff;
      color: #161615;
    }
    @media (max-width: 430px) {
      #${PANEL_ID} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `;
  document.head.appendChild(style);
}

function ensurePanel() {
  ensureStyles();
  let panel = document.getElementById(PANEL_ID);
  if (panel) return panel;

  panel = document.createElement("div");
  panel.id = PANEL_ID;
  panel.setAttribute("aria-live", "polite");
  document.body.appendChild(panel);
  return panel;
}

function runtimeRoutes() {
  return window.AIHubAdapterRuntime?.config?.adapter?.routes || window.AIHubAdapter?.config?.adapter?.routes || {};
}

function routeFor(actionName, params) {
  const explicit = sameOriginPath(params[ACTION_PARAMS.URL] || params.path || params.href || params.handoff_flow?.page_url);
  if (explicit) return explicit;

  const routes = runtimeRoutes();
  const keys = actionName === ACTIONS.CHECKOUT_HANDOFF ? CHECKOUT_ROUTE_KEYS : CONTACT_ROUTE_KEYS;
  for (const key of keys) {
    const route = sameOriginPath(routes[key]);
    if (route) return route;
  }
  return "";
}

function sameOriginPath(value) {
  const raw = clean(value);
  if (!raw) return "";
  try {
    const url = new URL(raw, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}${url.hash}` || "/";
  } catch (_error) {
    return "";
  }
}

function actionCopy(actionName) {
  return HANDOFF_COPY[actionName] || HANDOFF_COPY[ACTIONS.HANDOFF_TO_HUMAN];
}

function handoffFlow(value) {
  return value && typeof value === "object" ? value : {};
}

function flowTitle(flow, fallback) {
  return clean(flow.title) || fallback;
}

function flowMessage(flow, params, fallback) {
  return clean(params[ACTION_PARAMS.MESSAGE]) || clean(flow.handling) || fallback;
}

function flowReason(flow, params) {
  return clean(params[ACTION_PARAMS.REASON] || params.reason || params.blocked_reason || flow.key);
}

function flowMetaMarkup(flow) {
  const rows = [
    ["Provider", flow.provider_label || flow.provider],
    ["Boundary", flow.automation_boundary],
    ["Recovery", flow.recovery],
    ["Evidence", flow.evidence],
    ["Page", flow.page_url],
  ].filter(([, value]) => clean(value));

  if (!rows.length) return "";
  return `
    <p class="mayabot-handoff-meta">
      ${rows.map(([label, value]) => `<span><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</span>`).join("")}
    </p>
  `;
}

function closePanel(panel) {
  panel.classList.remove("active");
}

function collapseVoiceBubble() {
  window.setTimeout(() => {
    const chat = document.getElementById("mayabot-chat");
    const messages = document.getElementById("mayabot-msgs");
    if (messages) messages.innerHTML = "";
    if (chat) chat.classList.remove("visible");
  }, OVERLAY_COLLAPSE_DELAY_MS);
}

export function handoffActionForPolicy(block) {
  const flowAction = clean(block?.handoff_flow?.action).toUpperCase();
  if (HANDOFF_ACTIONS.has(flowAction)) return flowAction;
  const handoff = Array.isArray(block?.handoff_actions) ? block.handoff_actions[0] : "";
  return HANDOFF_ACTIONS.has(handoff) ? handoff : ACTIONS.HANDOFF_TO_HUMAN;
}

export function showHandoffOverlay(actionName, params = {}) {
  const normalizedAction = clean(actionName).toUpperCase();
  const copy = actionCopy(normalizedAction);
  const flow = handoffFlow(params.handoff_flow);
  const panel = ensurePanel();
  const targetPath = routeFor(normalizedAction, params);
  const title = flowTitle(flow, copy.title);
  const message = flowMessage(flow, params, copy.body);
  const reason = flowReason(flow, params);

  panel.innerHTML = `
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${escapeHtml(title)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${escapeHtml(message)}</p>
      ${flowMetaMarkup(flow)}
      ${reason ? `<p class="mayabot-handoff-reason">${escapeHtml(reason)}</p>` : ""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${targetPath ? `<button type="button" data-open-handoff>${escapeHtml(copy.primary)}</button>` : ""}
      </div>
    </div>
  `;
  panel.querySelector(".mayabot-handoff-close")?.addEventListener("click", () => closePanel(panel));
  panel.querySelector("[data-close-handoff]")?.addEventListener("click", () => closePanel(panel));
  panel.querySelector("[data-open-handoff]")?.addEventListener("click", () => {
    window.location.href = targetPath;
  });
  panel.classList.add("active");
  collapseVoiceBubble();
  return true;
}
