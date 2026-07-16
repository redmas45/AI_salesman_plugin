export type Theme = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'aiHubClientPanelTheme';

export function storedTheme(): Theme {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // The active theme still applies when storage is unavailable.
  }
}
