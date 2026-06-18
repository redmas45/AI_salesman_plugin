import type {
  AnalyticsResponse,
  CapabilitiesSummary,
  Client,
  ConversationsResponse,
  CrawlReport,
  CreateClientPayload,
  Overview,
  ReadinessReport,
  SettingsResponse,
} from './types';

const TOKEN_STORAGE_KEY = 'aiHubCrmAdminToken';

export class UnauthorizedError extends Error {
  constructor(message = 'CRM admin token is required.') {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

export function getStoredAdminToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY) ?? '';
}

export function setStoredAdminToken(token: string) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token.trim());
}

export function clearStoredAdminToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function appPrefix() {
  const marker = '/crm';
  const index = window.location.pathname.indexOf(marker);
  return index > 0 ? window.location.pathname.slice(0, index) : '';
}

const API_BASE = `${appPrefix()}/v1/admin`;

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

  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) headers.set('x-crm-admin-token', token);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) throw new UnauthorizedError(await responseMessage(response));
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
  updateSettings: (values: Record<string, string>) =>
    request<SettingsResponse>('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ values }),
    }),
};
