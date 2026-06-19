import type {
  AnalyticsResponse,
  CatalogProduct,
  CapabilitiesSummary,
  Client,
  ConversationsResponse,
  CrawlReport,
  CreateClientPayload,
  Overview,
  ReadinessReport,
  SettingsResponse,
  TokenLimitsPayload,
} from './types';

const TOKEN_STORAGE_KEY = 'aiHubCrmAdminToken';
const TOKEN_CREATED_AT_KEY = 'aiHubCrmAdminTokenCreatedAt';
const ADMIN_TOKEN_MAX_AGE_MS = 12 * 60 * 60 * 1000;

export class UnauthorizedError extends Error {
  constructor(message = 'CRM admin token is required.') {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

export function getStoredAdminToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(TOKEN_CREATED_AT_KEY);

  const token = sessionStorage.getItem(TOKEN_STORAGE_KEY) ?? '';
  const createdAt = Number(sessionStorage.getItem(TOKEN_CREATED_AT_KEY) || 0);
  if (!token || !createdAt || Date.now() - createdAt > ADMIN_TOKEN_MAX_AGE_MS) {
    clearStoredAdminToken();
    return '';
  }
  return token;
}

export function setStoredAdminToken(token: string) {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(TOKEN_CREATED_AT_KEY);
  sessionStorage.setItem(TOKEN_STORAGE_KEY, token.trim());
  sessionStorage.setItem(TOKEN_CREATED_AT_KEY, String(Date.now()));
}

export function clearStoredAdminToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(TOKEN_CREATED_AT_KEY);
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  sessionStorage.removeItem(TOKEN_CREATED_AT_KEY);
}

function appPrefix() {
  const marker = '/crm';
  const index = window.location.pathname.indexOf(marker);
  return index > 0 ? window.location.pathname.slice(0, index) : '';
}

const API_BASE = `${appPrefix()}/v1/admin`;
const PUBLIC_API_BASE = `${appPrefix()}/v1`;

async function responseMessage(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail || `Request failed with status ${response.status}.`;
  } catch {
    return `Request failed with status ${response.status}.`;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (options.body) headers.set('Content-Type', 'application/json');

  const token = getStoredAdminToken();
  if (token) headers.set('x-crm-admin-token', token);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) throw new UnauthorizedError(await responseMessage(response));
  if (!response.ok) throw new Error(await responseMessage(response));
  return response.json() as Promise<T>;
}

async function publicRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (options.body) headers.set('Content-Type', 'application/json');

  const response = await fetch(`${PUBLIC_API_BASE}${path}`, { ...options, headers });
  if (!response.ok) throw new Error(await responseMessage(response));
  return response.json() as Promise<T>;
}

export const crmApi = {
  overview: () => request<Overview>('/overview'),
  settings: () => request<SettingsResponse>('/settings'),
  conversations: (range: string, siteId = '') =>
    request<ConversationsResponse>(
      `/conversations?range=${encodeURIComponent(range)}&site_id=${encodeURIComponent(siteId)}`,
    ),
  analytics: (range: string, siteId = '') =>
    request<AnalyticsResponse>(
      `/analytics?range=${encodeURIComponent(range)}&site_id=${encodeURIComponent(siteId)}`,
    ),
  analyticsSummary: (range: string, siteId = '') =>
    request<AnalyticsResponse>('/analytics/summary', {
      method: 'POST',
      body: JSON.stringify({ range, site_id: siteId }),
    }),
  client: (siteId: string) => request<{ client: Client }>(`/clients/${encodeURIComponent(siteId)}`),
  createClient: (payload: CreateClientPayload) =>
    request<{ client: Client }>('/clients', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  removeClient: (siteId: string) =>
    request<{ status: string }>(`/clients/${encodeURIComponent(siteId)}`, { method: 'DELETE' }),
  setClientEnabled: (siteId: string, enabled: boolean) =>
    request<{ client: Client }>(`/clients/${encodeURIComponent(siteId)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    }),
  updateClientTokenLimits: (siteId: string, payload: TokenLimitsPayload) =>
    request<{ client: Client }>(`/clients/${encodeURIComponent(siteId)}/token-limits`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  crawlClient: (siteId: string) =>
    request<{ status: string; message: string }>(`/clients/${encodeURIComponent(siteId)}/crawl`, {
      method: 'POST',
    }),
  scanClient: (siteId: string) =>
    request<{ report: ReadinessReport }>(`/scan/${encodeURIComponent(siteId)}`, {
      method: 'POST',
    }),
  getScanReport: (siteId: string) =>
    request<{ report: ReadinessReport }>(`/scan/${encodeURIComponent(siteId)}`),
  getCapabilities: (siteId: string) =>
    request<CapabilitiesSummary>(`/capabilities/${encodeURIComponent(siteId)}`),
  getCrawlReport: (siteId: string) =>
    request<{ report: CrawlReport }>(`/crawl-report/${encodeURIComponent(siteId)}`),
  catalogProducts: (siteId: string, limit = 120) =>
    publicRequest<CatalogProduct[]>(
      `/products?site_id=${encodeURIComponent(siteId)}&limit=${encodeURIComponent(String(limit))}`,
    ),
  updateSettings: (values: Record<string, string>) =>
    request<SettingsResponse>('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ values }),
    }),
};
