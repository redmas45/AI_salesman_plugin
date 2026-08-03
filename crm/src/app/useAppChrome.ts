import { useEffect } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { Theme, View } from '../types';
import { THEME_STORAGE_KEY } from './appState';

const TOAST_DISMISS_DELAY_MS = 2600;

interface UseAppChromeParams {
  pageTitle: string;
  selectedClientSiteId: string;
  setToast: Dispatch<SetStateAction<string>>;
  theme: Theme;
  toast: string;
  view: View;
}

export function useAppChrome({
  pageTitle,
  selectedClientSiteId,
  setToast,
  theme,
  toast,
  view,
}: UseAppChromeParams) {
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // The active theme still applies when storage is unavailable.
    }
  }, [theme]);

  useEffect(() => {
    document.title =
      view === 'client-detail' && selectedClientSiteId
        ? `AI Hub - Client: ${selectedClientSiteId}`
        : `AI Hub - ${pageTitle}`;
  }, [pageTitle, selectedClientSiteId, view]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), TOAST_DISMISS_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [setToast, toast]);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0 });
  }, [selectedClientSiteId, view]);
}
