const API_BASE = "/v1/admin";
const TOKEN_STORAGE_KEY = "aiHubCrmAdminToken";
const THEME_STORAGE_KEY = "aiHubCrmTheme";
const DEFAULT_VIEW = "dashboard";
const EMPTY_TEXT = "-";
const TOAST_TIMEOUT_MS = 2600;
const THEME_DARK = "dark";
const THEME_LIGHT = "light";
const DEFAULT_RANGE = "7d";

const RANGE_OPTIONS = [
  ["1d", "Last 1 day"],
  ["3d", "Last 3 days"],
  ["7d", "Last 7 days"],
  ["15d", "Last 15 days"],
  ["30d", "Last 30 days"],
  ["3m", "Last 3 months"],
  ["6m", "Last 6 months"],
  ["1y", "Last 1 year"],
  ["all", "All"],
];

const SETTING_GROUPS = [
  {
    title: "Speech-to-text",
    keys: ["STT_PROVIDER", "STT_MODEL", "GROQ_STT_MODEL"],
  },
  {
    title: "Text-to-speech",
    keys: ["TTS_PROVIDER", "TTS_MODEL", "TTS_VOICE", "GROQ_TTS_MODEL", "GROQ_TTS_VOICE"],
  },
  {
    title: "LLM",
    keys: ["OPENAI_API_KEY", "GROQ_API_KEY", "LLM_MODEL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS"],
  },
  {
    title: "Deployment",
    keys: ["DATABASE_URL", "PUBLIC_API_URL", "PUBLIC_STOREFRONT_ORIGIN", "VOICE_ORB_API_URL", "DEPLOYMENT_MODE", "HOST", "PORT", "STOREFRONT_PORT", "BACKEND_PORT", "HTTPS_PORT"],
  },
  {
    title: "Crawler",
    keys: ["CRAWL_MAX_PAGES", "CRAWL_MAX_DEPTH", "CRAWL_ON_STARTUP"],
  },
];

const state = {
  view: DEFAULT_VIEW,
  overview: null,
  clients: [],
  selectedClient: null,
  settings: null,
  conversations: null,
  analytics: null,
  range: DEFAULT_RANGE,
  theme: THEME_DARK,
};

const elements = {
  root: document.querySelector("#view-root"),
  title: document.querySelector("#page-title"),
  breadcrumb: document.querySelector("#breadcrumb"),
  hubStatus: document.querySelector("#hub-status"),
  addClientButton: document.querySelector("#add-client-button"),
  refreshButton: document.querySelector("#refresh-button"),
  themeToggleButton: document.querySelector("#theme-toggle-button"),
  clientDialog: document.querySelector("#client-dialog"),
  clientForm: document.querySelector("#client-form"),
  toast: document.querySelector("#toast"),
};

document.addEventListener("DOMContentLoaded", init);

function init() {
  applyTheme(storedTheme());
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  elements.addClientButton.addEventListener("click", openClientDialog);
  elements.refreshButton.addEventListener("click", refreshCurrentView);
  elements.themeToggleButton.addEventListener("click", toggleTheme);
  elements.clientForm.addEventListener("submit", createClient);
  elements.clientDialog.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => elements.clientDialog.close());
  });
  loadInitialData();
}

function storedTheme() {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  return savedTheme === THEME_LIGHT ? THEME_LIGHT : THEME_DARK;
}

function applyTheme(theme) {
  state.theme = theme === THEME_LIGHT ? THEME_LIGHT : THEME_DARK;
  document.body.dataset.theme = state.theme;
  localStorage.setItem(THEME_STORAGE_KEY, state.theme);
  elements.themeToggleButton.textContent = state.theme === THEME_DARK ? "Light mode" : "Dark mode";
  elements.themeToggleButton.setAttribute(
    "aria-label",
    state.theme === THEME_DARK ? "Switch to light theme" : "Switch to dark theme",
  );
}

function toggleTheme() {
  applyTheme(state.theme === THEME_DARK ? THEME_LIGHT : THEME_DARK);
}

async function loadInitialData() {
  try {
    await Promise.all([loadOverview(), loadSettings(), loadConversations(), loadAnalytics()]);
    render();
  } catch (error) {
    showToast(error.message || "CRM failed to load.");
  }
}

async function refreshCurrentView() {
  try {
    await loadOverview();
    if (state.selectedClient) {
      await loadClientDetail(state.selectedClient.site_id);
    }
    if (state.view === "settings") {
      await loadSettings();
    }
    if (state.view === "conversations") {
      await loadConversations();
    }
    if (state.view === "analytics") {
      await loadAnalytics();
    }
    render();
    showToast("CRM refreshed.");
  } catch (error) {
    showToast(error.message || "Refresh failed.");
  }
}

async function loadOverview() {
  state.overview = await apiGet("/overview");
  state.clients = state.overview.clients || [];
  setHubStatus(state.overview.health || {});
}

async function loadSettings() {
  state.settings = await apiGet("/settings");
}

async function loadConversations() {
  state.conversations = await apiGet(`/conversations?range=${encodeURIComponent(state.range)}`);
}

async function loadAnalytics() {
  state.analytics = await apiGet(`/analytics?range=${encodeURIComponent(state.range)}`);
}

async function loadClientDetail(siteId) {
  const response = await apiGet(`/clients/${encodeURIComponent(siteId)}`);
  state.selectedClient = response.client;
}

async function apiGet(path) {
  return apiRequest(path, { method: "GET" });
}

async function apiRequest(path, options = {}, retryAfterToken = true) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (options.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    headers.set("x-crm-admin-token", token);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401 && retryAfterToken) {
    const nextToken = prompt("CRM admin token");
    if (!nextToken) {
      throw new Error("CRM admin token is required.");
    }
    localStorage.setItem(TOKEN_STORAGE_KEY, nextToken.trim());
    return apiRequest(path, options, false);
  }
  if (!response.ok) {
    const message = await responseMessage(response);
    throw new Error(message);
  }
  return response.json();
}

async function responseMessage(response) {
  try {
    const body = await response.json();
    return body.detail || `Request failed with status ${response.status}.`;
  } catch (_error) {
    return `Request failed with status ${response.status}.`;
  }
}

function setView(view) {
  state.view = view || DEFAULT_VIEW;
  document.querySelectorAll(".nav-item").forEach((button) => {
    const active = button.dataset.view === state.view || (state.view === "client-detail" && button.dataset.view === "clients");
    button.classList.toggle("active", active);
  });
  render();
}

function render() {
  const viewTitle = titleForView(state.view);
  elements.title.textContent = viewTitle;
  elements.breadcrumb.textContent = viewTitle;

  if (!state.overview) {
    elements.root.innerHTML = `<div class="empty">Loading CRM...</div>`;
    return;
  }

  const renderers = {
    dashboard: renderDashboard,
    clients: renderClients,
    "client-detail": renderClientDetail,
    catalogs: renderCatalogs,
    usage: renderUsage,
    conversations: renderConversations,
    analytics: renderAnalytics,
    adapters: renderAdapters,
    settings: renderSettings,
    health: renderHealth,
  };
  const renderer = renderers[state.view] || renderDashboard;
  elements.root.innerHTML = renderer();
  bindViewActions();
}

function titleForView(view) {
  const titles = {
    dashboard: "Dashboard",
    clients: "Clients",
    "client-detail": "Client detail",
    catalogs: "Catalogs",
    usage: "Usage",
    conversations: "Conversations",
    analytics: "Analytics",
    adapters: "Adapters",
    settings: "Settings",
    health: "Health",
  };
  return titles[view] || "Dashboard";
}

function renderDashboard() {
  const metrics = state.overview.metrics || {};
  return `
    <div class="metric-grid">
      ${metricCard("Active clients", metrics.active_clients, "+ live tenants")}
      ${metricCard("Voice turns today", metrics.voice_turns_today, `${formatNumber(metrics.total_voice_turns)} total`)}
      ${metricCard("Products indexed", metrics.products_indexed, "tenant catalogs")}
      ${metricCard("Avg pipeline", `${formatNumber(metrics.avg_latency_ms)} ms`, `${formatNumber(metrics.tokens_estimated)} est tokens`)}
    </div>
    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-header">
          <h2>Clients</h2>
          <button class="button small ghost" data-action="add-client" type="button">Add client</button>
        </div>
        <div class="table-wrap">${clientsTable(state.clients)}</div>
      </section>
      <section class="panel">
        <div class="panel-header"><h2>Recent activity</h2></div>
        <div class="panel-body">${activityList(state.overview.recent_activity || [])}</div>
      </section>
    </div>
    <div class="three-column">
      ${healthPanel()}
      ${summaryPanel("Crawler", crawlerSummary())}
      ${summaryPanel("One-line script", scriptSummary())}
    </div>
  `;
}

function metricCard(label, value, delta) {
  return `
    <section class="metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(formatValue(value))}</div>
      <div class="metric-delta">${escapeHtml(delta)}</div>
    </section>
  `;
}

function renderClients() {
  return `
    <section class="panel">
      <div class="panel-header">
        <h2>Clients</h2>
        <button class="button primary" data-action="add-client" type="button">Add client</button>
      </div>
      <div class="table-wrap">${clientsTable(state.clients)}</div>
    </section>
  `;
}

function clientsTable(clients) {
  if (!clients.length) {
    return `<div class="empty">No clients registered.</div>`;
  }
  const rows = clients.map((client) => `
    <tr class="clickable" data-action="open-client" data-site-id="${escapeAttr(client.site_id)}">
      <td>
        <div class="client-name">
          <span class="client-dot ${statusClass(client.status)}"></span>
          <span>${escapeHtml(client.name)}</span>
        </div>
      </td>
      <td><code>${escapeHtml(client.site_id)}</code></td>
      <td>${pill(client.status)}</td>
      <td>${formatNumber(client.catalog?.active_products || 0)}</td>
      <td>${formatNumber(client.usage?.turns_today || 0)}</td>
      <td>${formatNumber(client.usage?.tokens_estimated || 0)} / ${formatNumber(client.quota?.client?.limit || 0)}</td>
      <td>${escapeHtml(client.last_crawl_status || EMPTY_TEXT)}</td>
      <td class="actions-cell">
        <div class="table-actions">${clientToggleButton(client)}</div>
      </td>
    </tr>
  `).join("");
  return `
    <table>
      <thead>
        <tr>
          <th>Client</th>
          <th>Site ID</th>
          <th>Status</th>
          <th>Products</th>
          <th>Turns today</th>
          <th>Tokens</th>
          <th>Crawl</th>
          <th>AI widget</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function clientToggleButton(client) {
  const nextEnabledState = client.status !== "live";
  const label = nextEnabledState ? "Enable AI" : "Disable AI";
  const buttonClass = nextEnabledState ? "primary" : "soft-danger";
  return `
    <button
      class="button small ${buttonClass}"
      data-action="toggle-client"
      data-site-id="${escapeAttr(client.site_id)}"
      data-enabled="${nextEnabledState}"
      type="button"
    >${label}</button>
  `;
}

function renderClientDetail() {
  const client = state.selectedClient || state.clients[0];
  if (!client) {
    return `<div class="empty">Select a client.</div>`;
  }
  return `
    <div class="two-column">
      <section class="panel">
        <div class="panel-header">
          <div>
            <div class="eyebrow">${escapeHtml(client.site_id)}</div>
            <h2>${escapeHtml(client.name)} ${pill(client.status)}</h2>
          </div>
          <div class="topbar-actions">
            <button class="button small ghost" data-action="trigger-crawl" data-site-id="${escapeAttr(client.site_id)}" type="button">Trigger crawl</button>
            ${clientToggleButton(client)}
            <button class="button small danger" data-action="remove-client" data-site-id="${escapeAttr(client.site_id)}" type="button">Remove</button>
          </div>
        </div>
        <div class="panel-body key-value">
          ${keyRow("Store URL", client.store_url)}
          ${keyRow("Allowed origin", client.allowed_origin)}
          ${keyRow("Deploy mode", client.deploy_mode)}
          ${keyRow("Plan", client.plan)}
          ${keyRow("Adapter", client.adapter_name)}
          ${keyRow("Client token quota", quotaText(client.quota?.client))}
          ${keyRow("Session token quota", quotaText(client.quota?.session))}
          ${keyRow("Last crawl", crawlText(client))}
        </div>
      </section>
      <section class="panel">
        <div class="panel-header"><h2>Catalog</h2></div>
        <div class="panel-body key-value">
          ${keyRow("Products", formatNumber(client.catalog?.active_products || 0))}
          ${keyRow("Categories", formatNumber(client.catalog?.categories || 0))}
          ${keyRow("Vectorized", vectorizedText(client.catalog))}
          ${keyRow("Source", sourceText(client.catalog))}
          ${keyRow("Turns today", formatNumber(client.usage?.turns_today || 0))}
          ${keyRow("Avg latency", `${formatNumber(client.usage?.avg_latency_ms || 0)} ms`)}
        </div>
      </section>
    </div>
    <section class="panel">
      <div class="panel-header">
        <h2>Embed snippet</h2>
        <button class="button small ghost" data-action="copy-script" data-site-id="${escapeAttr(client.site_id)}" type="button">Copy</button>
      </div>
      <div class="panel-body">
        <div class="code-row">
          <div class="code-box">${escapeHtml(client.script_tag)}</div>
          <button class="button small" data-action="copy-script" data-site-id="${escapeAttr(client.site_id)}" type="button">Copy</button>
        </div>
      </div>
    </section>
    <section class="panel">
      <div class="panel-header"><h2>Catalog preview</h2></div>
      <div class="panel-body">${catalogPreview(client.catalog_preview || [])}</div>
    </section>
  `;
}

function renderCatalogs() {
  const cards = state.clients.map((client) => `
    <article class="mini-card clickable" data-action="open-client" data-site-id="${escapeAttr(client.site_id)}">
      <strong>${escapeHtml(client.name)}</strong>
      <span>${formatNumber(client.catalog?.active_products || 0)} products</span>
      <span>${formatNumber(client.catalog?.categories || 0)} categories</span>
      <span>${escapeHtml(sourceText(client.catalog))}</span>
    </article>
  `).join("");
  return `
    <section class="panel">
      <div class="panel-header"><h2>Tenant catalogs</h2></div>
      <div class="panel-body catalog-grid">${cards || `<div class="empty">No catalogs.</div>`}</div>
    </section>
  `;
}

function renderUsage() {
  const totals = usageTotals(state.clients);
  const rows = state.clients.map((client) => `
    <tr class="clickable" data-action="open-client" data-site-id="${escapeAttr(client.site_id)}">
      <td>${escapeHtml(client.name)}</td>
      <td><code>${escapeHtml(client.site_id)}</code></td>
      <td>${formatNumber(client.usage?.turns_today || 0)}</td>
      <td>${formatNumber(client.usage?.total_turns || 0)}</td>
      <td>${formatNumber(client.usage?.tokens_estimated || 0)}</td>
      <td>${formatNumber(client.usage?.avg_latency_ms || 0)} ms</td>
    </tr>
  `).join("");
  return `
    <div class="metric-grid usage-metrics">
      ${metricCard("Estimated tokens used", totals.tokens, `${formatNumber(totals.remainingTokens)} remaining`)}
      ${metricCard("Voice turns today", totals.today, `${formatNumber(totals.total)} total`)}
      ${metricCard("Avg latency", `${formatNumber(totals.avgLatency)} ms`, "across clients")}
      ${metricCard("Active clients", totals.activeClients, "live widget tenants")}
    </div>
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Usage</h2>
          <div class="table-meta">Token values are estimated from captured input and output text until provider usage metadata is wired in.</div>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Client</th>
              <th>Site ID</th>
              <th>Today</th>
              <th>Total</th>
              <th>Estimated tokens used</th>
              <th>Avg latency</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderConversations() {
  const groups = state.conversations?.groups || [];
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Conversation log</h2>
          <div class="table-meta">Grouped by date, then browser session.</div>
        </div>
        ${rangeControl()}
      </div>
      <div class="panel-body conversation-timeline">${conversationGroups(groups)}</div>
    </section>
  `;
}

function renderAnalytics() {
  const analytics = state.analytics || {};
  const metrics = analytics.metrics || {};
  const productMentions = analytics.top_products || analytics.top_terms || [];
  return `
    <div class="metric-grid">
      ${metricCard("Turns", metrics.turns || 0, `${formatNumber(metrics.sessions || 0)} sessions`)}
      ${metricCard("Tokens used", metrics.tokens || 0, "estimated")}
      ${metricCard("Avg latency", `${formatNumber(metrics.avg_latency_ms || 0)} ms`, selectedRangeLabel())}
      ${metricCard("Top intent", analytics.top_intents?.[0]?.label || EMPTY_TEXT, `${formatNumber(analytics.top_intents?.[0]?.count || 0)} turns`)}
    </div>
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Analytics</h2>
          <div class="table-meta">Demand signals, usage trends, and CRM summary for the selected range.</div>
        </div>
        <div class="topbar-actions">
          ${rangeControl()}
          <button class="button small ghost" data-action="generate-summary" type="button">Generate AI summary</button>
        </div>
      </div>
      <div class="panel-body analytics-grid">
        ${summaryCard("CRM summary", analytics.summary || "No summary yet.")}
        ${barChart("Turns by day", analytics.series || [], "turns")}
        ${rankList("Most mentioned products", productMentions)}
        ${rankList("Intent mix", analytics.top_intents || [])}
      </div>
    </section>
  `;
}

function renderAdapters() {
  const cards = state.clients.map((client) => `
    <article class="mini-card">
      <strong>${escapeHtml(client.name)}</strong>
      <span>${escapeHtml(client.adapter_name || EMPTY_TEXT)}</span>
      <span>${escapeHtml(client.allowed_origin || EMPTY_TEXT)}</span>
      <span>${pill(client.status)}</span>
    </article>
  `).join("");
  return `
    <section class="panel">
      <div class="panel-header"><h2>Adapters</h2></div>
      <div class="panel-body catalog-grid">${cards || `<div class="empty">No adapters.</div>`}</div>
    </section>
  `;
}

function renderSettings() {
  const settings = state.settings?.settings || [];
  const byKey = new Map(settings.map((item) => [item.key, item]));
  const groups = SETTING_GROUPS.map((group) => `
    <section class="settings-card">
      <h3>${escapeHtml(group.title)}</h3>
      <div class="settings-form">
        ${group.keys.map((key) => settingField(byKey.get(key))).join("")}
      </div>
    </section>
  `).join("");
  return `
    <form id="settings-form" class="settings-form">
      <div class="panel">
        <div class="panel-header">
          <div>
            <h2>Settings</h2>
            <div class="table-meta">Changes are saved to .env and need a hub restart.</div>
          </div>
          <button class="button primary" type="submit">Save settings</button>
        </div>
      </div>
      <div class="settings-grid">${groups}</div>
    </form>
  `;
}

function settingField(setting) {
  if (!setting) {
    return "";
  }
  const type = setting.is_secret ? "password" : "text";
  const value = setting.is_secret ? "" : escapeAttr(setting.value || "");
  const placeholder = setting.is_secret && setting.configured ? setting.value : "";
  return `
    <label class="field">
      <span>${escapeHtml(setting.key)}</span>
      <input data-setting-key="${escapeAttr(setting.key)}" data-secret="${setting.is_secret ? "1" : "0"}" type="${type}" value="${value}" placeholder="${escapeAttr(placeholder)}">
    </label>
  `;
}

function renderHealth() {
  return `
    <div class="three-column">
      ${healthPanel()}
      ${summaryPanel("Database", databaseSummary())}
      ${summaryPanel("Widget host", scriptSummary())}
    </div>
  `;
}

function healthPanel() {
  const health = state.overview.health || {};
  const rows = Object.entries(health).map(([key, value]) => htmlRow(labelize(key), pill(value))).join("");
  return `
    <section class="panel">
      <div class="panel-header"><h2>System health</h2></div>
      <div class="panel-body key-value">${rows}</div>
    </section>
  `;
}

function summaryPanel(title, rows) {
  return `
    <section class="panel">
      <div class="panel-header"><h2>${escapeHtml(title)}</h2></div>
      <div class="panel-body key-value">${rows}</div>
    </section>
  `;
}

function crawlerSummary() {
  const running = state.clients.filter((client) => client.last_crawl_status === "crawling").length;
  const indexed = state.clients.reduce((sum, client) => sum + Number(client.catalog?.active_products || 0), 0);
  return [
    keyRow("Running jobs", formatNumber(running)),
    keyRow("Indexed products", formatNumber(indexed)),
    keyRow("Clients", formatNumber(state.clients.length)),
  ].join("");
}

function scriptSummary() {
  const firstClient = state.selectedClient || state.clients[0];
  return [
    keyRow("Widget route", "/shopbot.js"),
    keyRow("CRM route", "/crm"),
    keyRow("Default site", firstClient?.site_id || EMPTY_TEXT),
  ].join("");
}

function databaseSummary() {
  const tenants = state.clients.length;
  const products = state.clients.reduce((sum, client) => sum + Number(client.catalog?.active_products || 0), 0);
  return [
    keyRow("Tenant schemas", formatNumber(tenants)),
    keyRow("Products", formatNumber(products)),
    keyRow("Vector store", "pgvector"),
  ].join("");
}

function usageTotals(clients) {
  const totalTurns = clients.reduce((sum, client) => sum + Number(client.usage?.total_turns || 0), 0);
  const today = clients.reduce((sum, client) => sum + Number(client.usage?.turns_today || 0), 0);
  const tokens = clients.reduce((sum, client) => sum + Number(client.usage?.tokens_estimated || 0), 0);
  const remainingTokens = clients.reduce((sum, client) => sum + Number(client.quota?.client?.remaining || 0), 0);
  const latencyValues = clients
    .map((client) => Number(client.usage?.avg_latency_ms || 0))
    .filter((value) => value > 0);
  const latencySum = latencyValues.reduce((sum, value) => sum + value, 0);
  return {
    total: totalTurns,
    today,
    tokens,
    remainingTokens,
    avgLatency: latencyValues.length ? Math.round(latencySum / latencyValues.length) : 0,
    activeClients: clients.filter((client) => client.status === "live").length,
  };
}

function quotaText(quota) {
  if (!quota) {
    return EMPTY_TEXT;
  }
  return `${formatNumber(quota.used)} used / ${formatNumber(quota.limit)} limit / ${formatNumber(quota.remaining)} remaining`;
}

function rangeControl() {
  return `
    <label class="range-control">
      <span>Range</span>
      <select data-range-select>
        ${RANGE_OPTIONS.map(([value, label]) => `
          <option value="${escapeAttr(value)}" ${value === state.range ? "selected" : ""}>${escapeHtml(label)}</option>
        `).join("")}
      </select>
    </label>
  `;
}

function selectedRangeLabel() {
  return RANGE_OPTIONS.find(([value]) => value === state.range)?.[1] || "Last 7 days";
}

function conversationGroups(groups) {
  if (!groups.length) {
    return `<div class="empty">No conversations logged for ${escapeHtml(selectedRangeLabel().toLowerCase())}.</div>`;
  }
  return groups.map((group) => `
    <section class="date-group">
      <h3>${escapeHtml(group.date)}</h3>
      <div class="session-list">
        ${(group.sessions || []).map(conversationSession).join("")}
      </div>
    </section>
  `).join("");
}

function conversationSession(session) {
  return `
    <article class="session-card">
      <div class="session-header">
        <div>
          <strong>${escapeHtml(session.site_id)}</strong>
          <code>${escapeHtml(session.session_id)}</code>
        </div>
        <div class="table-meta">${formatNumber(session.turn_count)} turns - ${formatNumber(session.tokens_used)} tokens</div>
      </div>
      <div class="turn-list">
        ${(session.turns || []).map(conversationTurn).join("")}
      </div>
    </article>
  `;
}

function conversationTurn(turn) {
  return `
    <div class="turn-card">
      <div class="turn-meta">
        <span>${escapeHtml(shortTime(turn.created_at))}</span>
        <span>${escapeHtml(turn.transport)}</span>
        <span>${pill(turn.status || "ok")}</span>
        <span>${formatNumber(turn.tokens || 0)} tokens</span>
        <span>${formatNumber(turn.latency_ms || 0)} ms</span>
      </div>
      <div class="dialogue-row">
        <span>User</span>
        <p>${escapeHtml(turn.transcript || EMPTY_TEXT)}</p>
      </div>
      <div class="dialogue-row">
        <span>AI</span>
        <p>${escapeHtml(turn.response_text || EMPTY_TEXT)}</p>
      </div>
    </div>
  `;
}

function summaryCard(title, text) {
  const items = summaryItems(text);
  return `
    <article class="analytics-card wide">
      <h3>${escapeHtml(title)}</h3>
      ${
        items.length
          ? `<ul class="summary-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
          : `<p>${escapeHtml(text)}</p>`
      }
    </article>
  `;
}

function summaryItems(text) {
  return String(text || "")
    .split(/\r?\n/)
    .map(cleanSummaryItem)
    .filter(Boolean);
}

function cleanSummaryItem(line) {
  return String(line || "")
    .trim()
    .replace(/^#{1,6}\s*/, "")
    .replaceAll("**", "")
    .replace(/^[-*]\s+/, "")
    .replace(/^\d+[\.)]\s+/, "")
    .trim();
}

function barChart(title, rows, key) {
  const maxValue = Math.max(...rows.map((row) => Number(row[key] || 0)), 1);
  return `
    <article class="analytics-card">
      <h3>${escapeHtml(title)}</h3>
      <div class="bar-chart">
        ${rows.map((row) => {
          const value = Number(row[key] || 0);
          const height = Math.max(6, Math.round((value / maxValue) * 100));
          return `
            <div class="bar-column" title="${escapeAttr(row.date)}: ${formatNumber(value)}">
              <div class="bar-fill" style="height:${height}%"></div>
              <span>${escapeHtml(String(row.date || "").slice(5))}</span>
            </div>
          `;
        }).join("") || `<div class="empty">No chart data.</div>`}
      </div>
    </article>
  `;
}

function rankList(title, rows) {
  return `
    <article class="analytics-card">
      <h3>${escapeHtml(title)}</h3>
      <div class="rank-list">
        ${rows.map((row) => `
          <div class="rank-row">
            <span>${escapeHtml(row.label)}</span>
            <strong>${formatNumber(row.count)}</strong>
          </div>
        `).join("") || `<div class="empty">No rows yet.</div>`}
      </div>
    </article>
  `;
}

function bindViewActions() {
  elements.root.querySelectorAll("[data-action]").forEach((element) => {
    element.addEventListener("click", handleAction);
  });
  elements.root.querySelectorAll("[data-range-select]").forEach((select) => {
    select.addEventListener("change", handleRangeChange);
  });
  const settingsForm = elements.root.querySelector("#settings-form");
  if (settingsForm) {
    settingsForm.addEventListener("submit", saveSettings);
  }
}

async function handleAction(event) {
  event.preventDefault();
  event.stopPropagation();
  const actionElement = event.target.closest("[data-action]");
  const action = actionElement?.dataset.action;
  if (!action) {
    return;
  }
  if (action === "add-client") {
    openClientDialog();
    return;
  }
  const siteId = actionElement.dataset.siteId;
  const actions = {
    "open-client": () => openClient(siteId),
    "copy-script": () => copyScript(siteId),
    "trigger-crawl": () => triggerCrawl(siteId),
    "remove-client": () => removeClient(siteId),
    "toggle-client": () => toggleClient(siteId, actionElement.dataset.enabled === "true"),
    "generate-summary": () => generateAnalyticsSummary(),
  };
  if (actions[action]) {
    await actions[action]();
  }
}

async function handleRangeChange(event) {
  state.range = event.currentTarget.value || DEFAULT_RANGE;
  try {
    await Promise.all([loadConversations(), loadAnalytics()]);
    render();
  } catch (error) {
    showToast(error.message || "Range update failed.");
  }
}

async function generateAnalyticsSummary() {
  try {
    state.analytics = await apiRequest("/analytics/summary", {
      method: "POST",
      body: JSON.stringify({ range: state.range }),
    });
    render();
    showToast("Analytics summary updated.");
  } catch (error) {
    showToast(error.message || "Summary generation failed.");
  }
}

async function openClient(siteId) {
  await loadClientDetail(siteId);
  setView("client-detail");
}

async function copyScript(siteId) {
  const client = clientBySiteId(siteId);
  if (!client) {
    showToast("Client not found.");
    return;
  }
  await navigator.clipboard.writeText(client.script_tag);
  showToast("Script copied.");
}

async function triggerCrawl(siteId) {
  await apiRequest(`/clients/${encodeURIComponent(siteId)}/crawl`, { method: "POST" });
  await loadOverview();
  if (state.selectedClient?.site_id === siteId) {
    await loadClientDetail(siteId);
  }
  render();
  showToast("Crawler started.");
}

async function removeClient(siteId) {
  if (!confirm(`Remove ${siteId}? Tenant data is kept.`)) {
    return;
  }
  await apiRequest(`/clients/${encodeURIComponent(siteId)}`, { method: "DELETE" });
  state.selectedClient = null;
  await loadOverview();
  setView("clients");
  showToast("Client removed.");
}

async function toggleClient(siteId, enabled) {
  await apiRequest(`/clients/${encodeURIComponent(siteId)}/status`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });
  await loadOverview();
  if (state.selectedClient?.site_id === siteId) {
    await loadClientDetail(siteId);
  }
  render();
  showToast(enabled ? "Client enabled." : "Client disabled.");
}

function openClientDialog() {
  elements.clientForm.reset();
  elements.clientForm.elements.deploy_mode.value = "intranet";
  elements.clientForm.elements.plan.value = "Commerce plan";
  elements.clientForm.elements.adapter_name.value = "generic_adapter.js";
  elements.clientDialog.showModal();
}

async function createClient(event) {
  event.preventDefault();
  const formData = new FormData(elements.clientForm);
  const payload = Object.fromEntries(formData.entries());
  if (!payload.site_id) {
    delete payload.site_id;
  }
  try {
    const response = await apiRequest("/clients", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    elements.clientDialog.close();
    await loadOverview();
    state.selectedClient = response.client;
    setView("client-detail");
    showToast("Client created.");
  } catch (error) {
    showToast(error.message || "Client creation failed.");
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const values = {};
  event.currentTarget.querySelectorAll("[data-setting-key]").forEach((input) => {
    const key = input.dataset.settingKey;
    const isSecret = input.dataset.secret === "1";
    if (isSecret && !input.value.trim()) {
      return;
    }
    values[key] = input.value.trim();
  });
  try {
    state.settings = await apiRequest("/settings", {
      method: "PATCH",
      body: JSON.stringify({ values }),
    });
    render();
    showToast("Settings saved. Restart required.");
  } catch (error) {
    showToast(error.message || "Settings save failed.");
  }
}

function clientBySiteId(siteId) {
  if (state.selectedClient?.site_id === siteId) {
    return state.selectedClient;
  }
  return state.clients.find((client) => client.site_id === siteId);
}

function catalogPreview(products) {
  if (!products.length) {
    return `<div class="empty">No catalog rows yet.</div>`;
  }
  return `
    <div class="catalog-grid">
      ${products.map((product) => `
        <article class="mini-card">
          <strong>${escapeHtml(product.name || EMPTY_TEXT)}</strong>
          <span>${escapeHtml(product.category || EMPTY_TEXT)}</span>
          <span>${money(product.price)}</span>
          <span>${product.has_embedding ? "vectorized" : "pending vector"}</span>
        </article>
      `).join("")}
    </div>
  `;
}

function activityList(items) {
  if (!items.length) {
    return `<div class="empty">No activity yet.</div>`;
  }
  return `
    <div class="activity-list">
      ${items.slice(0, 12).map((item) => `
        <div class="activity-item">
          <div class="activity-time">${escapeHtml(shortTime(item.created_at))}</div>
          <div class="activity-text">
            ${escapeHtml(item.site_id)} ${escapeHtml(item.transport)} ${escapeHtml(item.intent || "turn")}
            ${pill(item.status || "ok")} ${formatNumber(item.latency_ms || 0)} ms
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

function keyRow(label, value) {
  return `
    <div class="key-row">
      <span>${escapeHtml(label)}</span>
      <span>${escapeHtml(value == null ? EMPTY_TEXT : value)}</span>
    </div>
  `;
}

function htmlRow(label, valueHtml) {
  return `
    <div class="key-row">
      <span>${escapeHtml(label)}</span>
      <span>${valueHtml == null ? EMPTY_TEXT : valueHtml}</span>
    </div>
  `;
}

function pill(value) {
  const text = String(value || "unknown");
  return `<span class="pill ${statusClass(text)}">${escapeHtml(text)}</span>`;
}

function statusClass(value) {
  const text = String(value || "").toLowerCase();
  if (["live", "ok", "up", "ready"].includes(text)) {
    return text === "ready" ? "ok" : text;
  }
  if (["crawling", "running", "slow"].includes(text)) {
    return text;
  }
  if (["disabled", "offline", "down", "error"].includes(text)) {
    return text;
  }
  return "neutral";
}

function setHubStatus(health) {
  const isUp = Object.values(health).every((value) => value === "up" || value === "ready");
  elements.hubStatus.textContent = isUp ? "hub running" : "hub degraded";
  elements.hubStatus.className = `status-pill ${isUp ? "up" : "slow"}`;
}

function vectorizedText(catalog) {
  const activeProducts = Number(catalog?.active_products || 0);
  const missing = Number(catalog?.missing_embeddings || 0);
  return `${formatNumber(Math.max(activeProducts - missing, 0))} / ${formatNumber(activeProducts)}`;
}

function sourceText(catalog) {
  const source = catalog?.sources?.[0]?.source_name;
  return source || EMPTY_TEXT;
}

function crawlText(client) {
  const status = client.last_crawl_status || EMPTY_TEXT;
  const lastRun = client.last_crawl_at ? shortTime(client.last_crawl_at) : EMPTY_TEXT;
  return `${status} - ${lastRun}`;
}

function money(value) {
  const amount = Number(value || 0);
  return `$${amount.toFixed(2)}`;
}

function shortTime(value) {
  if (!value) {
    return EMPTY_TEXT;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 19);
  }
  return date.toLocaleString([], { dateStyle: "short", timeStyle: "short" });
}

function labelize(value) {
  return String(value || "").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatNumber(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat().format(number);
}

function formatValue(value) {
  if (value == null || value === "") {
    return EMPTY_TEXT;
  }
  return String(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.classList.remove("visible");
  }, TOAST_TIMEOUT_MS);
}
