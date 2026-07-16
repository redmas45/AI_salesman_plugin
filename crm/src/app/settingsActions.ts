import { crmApi } from '../api';
import type { AnalyticsResponse, SettingsResponse } from '../types';

interface SaveSettingsDeps {
  values: Record<string, string>;
  setBusy: (busy: boolean) => void;
  setSettings: (settings: SettingsResponse) => void;
  setToast: (message: string) => void;
  showError: (error: unknown, fallback: string) => void;
}

interface GenerateSummaryDeps {
  range: string;
  setBusy: (busy: boolean) => void;
  setAnalytics: (analytics: AnalyticsResponse) => void;
  setToast: (message: string) => void;
  showError: (error: unknown, fallback: string) => void;
}

export async function saveSettingsAction({
  values,
  setBusy,
  setSettings,
  setToast,
  showError,
}: SaveSettingsDeps): Promise<SettingsResponse> {
  setBusy(true);
  try {
    const nextSettings = await crmApi.updateSettings(values);
    setSettings(nextSettings);
    setToast(nextSettings.restart_required ? 'Settings saved. Restart required.' : 'Settings saved.');
    return nextSettings;
  } catch (error) {
    showError(error, 'Settings save failed.');
    throw error;
  } finally {
    setBusy(false);
  }
}

export async function generateSummaryAction({
  range,
  setBusy,
  setAnalytics,
  setToast,
  showError,
}: GenerateSummaryDeps) {
  setBusy(true);
  try {
    setAnalytics(await crmApi.analyticsSummary(range));
    setToast('Analytics summary updated.');
  } catch (error) {
    showError(error, 'Summary generation failed.');
  } finally {
    setBusy(false);
  }
}
