import type { ClientSummary, DashboardResponse } from './types';
import { clientSlugFromUrl } from './utils';

const API_BASE = (import.meta.env.VITE_AI_HUB_API_BASE || '').replace(/\/+$/, '');
const LEGACY_TOKEN_KEY = 'clientPanelToken';

function tokenKey(siteId = clientSlugFromUrl()): string {
  return `clientPanelToken:${siteId}`;
}

export function storedToken(): string {
  return localStorage.getItem(tokenKey()) ?? '';
}

export function clearToken(): void {
  localStorage.removeItem(tokenKey());
  localStorage.removeItem(LEGACY_TOKEN_KEY);
}

export async function login(siteId: string, password: string): Promise<ClientSummary> {
  const response = await request<{ token: string; client: ClientSummary }>('/v1/client-panel/login', {
    method: 'POST',
    body: JSON.stringify({ site_id: siteId, password }),
  });
  localStorage.setItem(tokenKey(siteId), response.token);
  localStorage.setItem(tokenKey(response.client.site_id), response.token);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  return response.client;
}

/**
 * End the session on the server, then locally.
 *
 * Clearing browser storage alone left the token valid until it expired, so a
 * copied token still worked after signing out. The local token is dropped even
 * if the server call fails, so the user is never stuck signed in.
 */
export async function logout(): Promise<void> {
  try {
    if (storedToken()) {
      await request<{ status: string }>('/v1/client-panel/logout', { method: 'POST' });
    }
  } catch {
    // Best effort: the token is cleared locally regardless.
  } finally {
    clearToken();
  }
}

export async function dashboard(range: string): Promise<DashboardResponse> {
  return request<DashboardResponse>(`/v1/client-panel/dashboard?range=${encodeURIComponent(range)}`);
}

export async function updateSessionLimit(sessionTokenLimit: number): Promise<ClientSummary> {
  const response = await request<{ client: ClientSummary }>('/v1/client-panel/token-policy', {
    method: 'PATCH',
    body: JSON.stringify({ session_token_limit: sessionTokenLimit }),
  });
  return response.client;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (options.body) headers.set('Content-Type', 'application/json');
  const token = storedToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<T>;
}

// A 503 from sign-in means the server cannot sign tokens, which is a deployment
// problem rather than a bad password. Saying "invalid credentials" there sends the
// account owner on a password hunt they cannot win.
const SERVICE_UNAVAILABLE_MESSAGE =
  'Sign-in is temporarily unavailable because secure login is not configured on the server. ' +
  'Your password may be correct - no change is needed. Please contact your AI Hub administrator.';
const INVALID_CREDENTIALS_MESSAGE = 'Account ID or password is incorrect. Please check both and try again.';

async function errorMessage(response: Response): Promise<string> {
  if (response.status === 503) return SERVICE_UNAVAILABLE_MESSAGE;
  if (response.status === 401) return INVALID_CREDENTIALS_MESSAGE;
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail || `Request failed with status ${response.status}.`;
  } catch {
    return `Request failed with status ${response.status}.`;
  }
}
