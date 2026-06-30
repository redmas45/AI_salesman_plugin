import { ACTIONS, ACTION_PARAMS } from "../constants";
import { adapterConfig, fetchRuntimeConfig } from "./config";
import { reportActionExecution } from "./actionTelemetry";
import { isActionFallbackStop } from "./actionParams";
import { registerPageDiscovery } from "./discovery";
import { executeClientHookAction } from "./clientHooks";
import { executeConfiguredAction, executeDomFallback } from "./domActions";
import { installInteractionTracker } from "./interactionTracker";
import { readPageContext } from "./pageContext";
import { installPageObserver } from "./pageLifecycle";
import { storePendingAction, takePendingAction } from "./pendingAction";
import { detectPlatform, executePlatformAction } from "./platforms";
import { actionPolicyBlock, reportPolicyBlock } from "./policy";
import { resolveProductActionPath } from "./productNavigation";
import { executeProviderAction } from "./providerActions";
import { validateRuntimeActions } from "./validation";
import { handoffActionForPolicy, showHandoffOverlay } from "../handoffOverlay";

const RUNTIME_VERSION = "1";
const RUNTIME_GLOBAL = "AIHubAdapterRuntime";
const ADAPTER_GLOBAL = "AIHubAdapter";
const DOM_READY_TIMEOUT_MS = 2500;
const PRODUCT_NAVIGATION_TELEMETRY_GRACE_MS = 300;
const PRODUCT_PAGE_ACTIONS = new Set([
  ACTIONS.ADD_TO_CART,
  ACTIONS.REMOVE_FROM_CART,
  ACTIONS.UPDATE_CART_QUANTITY,
]);

function normalizeAction(action) {
  const params = action?.params || action?.parameters || {};
  return {
    ...(action || {}),
    action: String(action?.action || "").trim().toUpperCase(),
    params,
    parameters: params,
  };
}

function emptyRuntimeConfig() {
  return {
    site_id: adapterConfig.siteId,
    enabled: true,
    vertical: { key: "generic", label: "Generic", action_types: [] },
    adapter: { routes: {}, actions: {}, selectors: {} },
  };
}

export class AIHubAdapterRuntime {
  constructor() {
    this.apiUrl = adapterConfig.apiUrl;
    this.siteId = adapterConfig.siteId;
    this.config = emptyRuntimeConfig();
    this.externalAdapter = window[ADAPTER_GLOBAL] || null;
    this.discoveryStarted = false;
    this.discoveryInFlight = null;
    this.lastActionResult = null;
    this.ready = this.loadConfig().then((config) => {
      window.setTimeout(() => this.executePendingAction(), 0);
      return config;
    });
  }

  install() {
    window[RUNTIME_GLOBAL] = this;
    if (!window[ADAPTER_GLOBAL]) {
      window[ADAPTER_GLOBAL] = this.publicAdapter();
    }
  }

  publicAdapter() {
    return {
      siteId: this.siteId,
      version: RUNTIME_VERSION,
      getCapabilities: () => this.getCapabilities(),
      getContext: () => this.getContext(),
      refreshConfig: () => this.refreshRuntimeConfig("manual"),
      discoverPage: () => this.discoverAndRefresh("manual"),
      handleAction: (action) => this.executeAction(action),
    };
  }

  async loadConfig() {
    try {
      this.config = await fetchRuntimeConfig();
    } catch (err) {
      console.warn("[AIHubAdapter] Config load failed, using runtime fallback.", err);
      this.config = emptyRuntimeConfig();
    }
    await this.registerDiscovery();
    return this.config;
  }

  async registerDiscovery() {
    if (this.discoveryStarted) return;
    this.discoveryStarted = true;
    await waitForDocumentReady();
    installInteractionTracker(this.apiUrl, this.siteId);
    await this.discoverAndRefresh("initial");
    installPageObserver(
      () => this.discoverAndRefresh("navigation"),
      () => this.discoverAndRefresh("dom_mutation"),
    );
  }

  async discoverAndRefresh(reason) {
    if (this.discoveryInFlight) return this.discoveryInFlight;
    this.discoveryInFlight = this.runDiscoveryRefresh(reason);
    try {
      return await this.discoveryInFlight;
    } finally {
      this.discoveryInFlight = null;
    }
  }

  async runDiscoveryRefresh(reason) {
    const registration = await registerPageDiscovery(this.apiUrl, this.siteId);
    if (registration) {
      await this.refreshRuntimeConfig(reason);
    }
    await validateRuntimeActions(this.apiUrl, this.siteId, this.config);
  }

  async refreshRuntimeConfig(reason) {
    try {
      this.config = await fetchRuntimeConfig();
      return this.config;
    } catch (err) {
      console.warn(`[AIHubAdapter] Config refresh failed after ${reason} discovery.`, err);
      return this.config;
    }
  }

  getCapabilities() {
    const actions = this.config?.vertical?.action_types || [];
    return {
      actions,
      platform: detectPlatform(),
      vertical: this.config?.vertical?.key || "generic",
    };
  }

  getContext() {
    return {
      ...readPageContext(this.config),
      capabilities: this.getCapabilities(),
      siteId: this.siteId,
    };
  }

  async executeAction(action) {
    await this.ready;
    const startedAt = Date.now();
    const normalizedAction = normalizeAction(action);
    this.lastActionResult = null;
    if (!normalizedAction.action) return false;
    if (this.config?.enabled === false) {
      this.rememberActionResult({ handled: true, status: "disabled", reason: "widget_disabled" });
      return false;
    }

    const policyBlock = actionPolicyBlock(normalizedAction, this.config);
    if (policyBlock) {
      console.warn("[AIHubAdapter] Action blocked by runtime policy.", policyBlock);
      await reportPolicyBlock(this.apiUrl, this.siteId, normalizedAction, policyBlock);
      await this.reportActionResult(normalizedAction, {
        status: "blocked",
        stage: "policy",
        reason: policyBlock.reason,
        duration_ms: Date.now() - startedAt,
      });
      showHandoffOverlay(handoffActionForPolicy(policyBlock), {
        reason: policyBlock.reason,
        blocked_action: normalizedAction.action,
        handoff_flow: policyBlock.handoff_flow,
      });
      this.rememberActionResult({ handled: true, status: "blocked", reason: policyBlock.reason });
      return false;
    }

    const stages = [
      ["external_adapter", () => this.executeExternalAdapter(normalizedAction)],
      ["client_hook", () => executeClientHookAction(normalizedAction)],
      ["product_page_resume", () => this.prepareProductPageAction(normalizedAction)],
      ["configured_action", () => executeConfiguredAction(normalizedAction, this.config)],
      ["platform_adapter", () => executePlatformAction(normalizedAction)],
      ["provider_adapter", () => executeProviderAction(normalizedAction)],
      ["dom_fallback", () => executeDomFallback(normalizedAction, this.config)],
    ];
    for (const [stage, execute] of stages) {
      try {
        const result = await execute();
        if (isActionFallbackStop(result)) {
          await this.reportActionResult(normalizedAction, {
            status: result.status || "blocked",
            stage,
            reason: result.reason || "action_blocked",
            duration_ms: Date.now() - startedAt,
          });
          this.rememberActionResult({
            handled: true,
            status: result.status || "blocked",
            stage,
            reason: result.reason || "action_blocked",
          });
          return false;
        }
        if (result) {
          await this.reportActionResult(normalizedAction, {
            status: "ok",
            stage,
            reason: "",
            duration_ms: Date.now() - startedAt,
          });
          this.rememberActionResult({ handled: true, status: "ok", stage });
          return true;
        }
      } catch (err) {
        console.warn(`[AIHubAdapter] ${stage} action execution failed.`, err);
        await this.reportActionResult(normalizedAction, {
          status: "error",
          stage,
          reason: err instanceof Error ? err.message : "execution_error",
          duration_ms: Date.now() - startedAt,
        });
      }
    }
    await this.reportActionResult(normalizedAction, {
      status: "failed",
      stage: "all",
      reason: "no_executor_succeeded",
      duration_ms: Date.now() - startedAt,
    });
    this.rememberActionResult({ handled: true, status: "failed", reason: "no_executor_succeeded" });
    return false;
  }

  rememberActionResult(result) {
    this.lastActionResult = result;
  }

  async reportActionResult(action, result) {
    await reportActionExecution(this.apiUrl, this.siteId, action, result);
  }

  async executeExternalAdapter(action) {
    if (!this.externalAdapter || typeof this.externalAdapter.handleAction !== "function") {
      return false;
    }

    try {
      return (await this.externalAdapter.handleAction(action, this)) === true;
    } catch (err) {
      console.warn("[AIHubAdapter] Client adapter action failed.", err);
      return false;
    }
  }

  async prepareProductPageAction(action) {
    if (!PRODUCT_PAGE_ACTIONS.has(action.action)) return false;
    const productId = String(action.parameters?.[ACTION_PARAMS.PRODUCT_ID] || "").trim();
    if (!productId || currentProductId() === productId) return false;

    const targetPath = await resolveProductActionPath(productId);
    if (!targetPath || targetPath === currentPagePath()) return false;
    if (!storePendingAction(this.siteId, action)) return false;

    window.setTimeout(() => {
      window.location.href = targetPath;
    }, PRODUCT_NAVIGATION_TELEMETRY_GRACE_MS);
    return true;
  }

  async executePendingAction() {
    const action = takePendingAction(this.siteId);
    if (!action) return;
    await waitForDocumentReady();
    await this.executeAction(action);
  }
}

function currentPagePath() {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function currentProductId() {
  const element = document.querySelector("[data-product-id], [data-product], [itemprop='sku']");
  const explicit = String(
    element?.getAttribute("data-product-id") ||
      element?.getAttribute("data-product") ||
      element?.textContent ||
      "",
  ).trim();
  if (explicit) return explicit;
  const match = window.location.pathname.match(/\/product\/([^/?#]+)/i);
  return match ? decodeURIComponent(match[1]) : "";
}

function waitForDocumentReady() {
  if (document.readyState !== "loading") return Promise.resolve();
  return new Promise((resolve) => {
    const done = () => {
      window.clearTimeout(timer);
      document.removeEventListener("DOMContentLoaded", done);
      resolve();
    };
    const timer = window.setTimeout(done, DOM_READY_TIMEOUT_MS);
    document.addEventListener("DOMContentLoaded", done);
  });
}

export function installRuntime() {
  const existingRuntime = window[RUNTIME_GLOBAL];
  if (existingRuntime?.executeAction) return existingRuntime;

  const runtime = new AIHubAdapterRuntime();
  runtime.install();
  return runtime;
}
