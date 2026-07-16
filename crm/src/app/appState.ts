import type { Theme, View } from '../types';

export const THEME_STORAGE_KEY = 'aiHubCrmTheme';
export const DEFAULT_VIEW: View = 'dashboard';
export const DEFAULT_RANGE = '7d';

export function storedTheme(): Theme {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function titleForView(view: View) {
  const titles: Record<View, string> = {
    dashboard: 'Dashboard',
    clients: 'Clients',
    'client-detail': 'Client detail',
    catalogs: 'Data storage',
    usage: 'Usage',
    conversations: 'Conversations',
    analytics: 'Analytics',
    adapters: 'Adapters',
    settings: 'Settings',
    health: 'Health',
  };
  return titles[view];
}
