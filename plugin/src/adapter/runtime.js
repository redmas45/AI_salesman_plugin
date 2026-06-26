import { adapterConfig, fetchRuntimeConfig } from "./config";
import { registerPageDiscovery } from "./discovery";
import { executeConfiguredAction, executeDomFallback, readPageContext } from "./domActions";
import { detectPlatform, executePlatformAction } from "./platforms";

const RUNTIME_VERSION = "1";
const RUNTIME_GLOBAL = "AIHubAdapterRuntime";
const ADAPTER_GLOBAL = "AIHubAdapter";

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
    this.ready = this.loadConfig();
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
      handleAction: (action) => this.executeAction(action),
    };
  }

  async loadConfig() {
    try {
      this.config = await fetchRuntimeConfig();
      this.registerDiscovery();
    } catch (err) {
      console.warn("[AIHubAdapter] Config load failed, using runtime fallback.", err);
      this.config = emptyRuntimeConfig();
    }
    return this.config;
  }

  registerDiscovery() {
    window.setTimeout(() => {
      registerPageDiscovery(this.apiUrl, this.siteId);
    }, 0);
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
      ...readPageContext(),
      capabilities: this.getCapabilities(),
      siteId: this.siteId,
    };
  }

  async executeAction(action) {
    await this.ready;
    const normalizedAction = normalizeAction(action);
    if (!normalizedAction.action || this.config?.enabled === false) return false;

    if (await this.executeExternalAdapter(normalizedAction)) return true;
    if (await executeConfiguredAction(normalizedAction, this.config)) return true;
    if (await executePlatformAction(normalizedAction)) return true;
    return executeDomFallback(normalizedAction, this.config);
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
}

export function installRuntime() {
  const existingRuntime = window[RUNTIME_GLOBAL];
  if (existingRuntime?.executeAction) return existingRuntime;

  const runtime = new AIHubAdapterRuntime();
  runtime.install();
  return runtime;
}
