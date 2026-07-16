import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { UnauthorizedError, clearStoredAdminToken, crmApi, getStoredAdminToken, setStoredAdminToken } from '../api';
import type {
  AnalyticsResponse,
  Client,
  ConversationsResponse,
  CreateClientPayload,
  Overview,
  SettingsResponse,
  Theme,
  VerticalDefinition,
  View,
  ClientBoardSection,
  AnalyticsSectionId,
} from '../types';
import type { ClientWorkspaceTabId } from '../verticals/types';
import { AppShell } from './AppShell';
import { DEFAULT_RANGE, DEFAULT_VIEW, storedTheme, titleForView } from './appState';
import { generateSummaryAction, saveSettingsAction } from './settingsActions';
import { useAppChrome } from './useAppChrome';
import { useClientOperations } from './useClientOperations';
import { useCrmNavigation } from './useCrmNavigation';
import { createViewRendererProps } from './viewRendererProps';

export function App() {
  const [view, setView] = useState<View>(DEFAULT_VIEW);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [verticals, setVerticals] = useState<VerticalDefinition[]>([]);
  const [conversations, setConversations] = useState<ConversationsResponse | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [range, setRange] = useState(DEFAULT_RANGE);
  const [theme, setTheme] = useState<Theme>(storedTheme());
  const [loading, setLoading] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [passwordDialogClient, setPasswordDialogClient] = useState<Client | null>(null);
  const [clientInitialTab, setClientInitialTab] = useState<ClientWorkspaceTabId>('overview');
  const [clientTabRequestKey, setClientTabRequestKey] = useState(0);
  const [clientBoardSection, setClientBoardSection] = useState<ClientBoardSection>('all');
  const [analyticsSection, setAnalyticsSection] = useState<AnalyticsSectionId>('overview');
  const [settingsFocusKey, setSettingsFocusKey] = useState('');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [crawlingSites, setCrawlingSites] = useState<Set<string>>(() => new Set());
  const [autoIntegratingSites, setAutoIntegratingSites] = useState<Set<string>>(() => new Set());
  const contentRef = useRef<HTMLElement | null>(null);
  const pageTitle = titleForView(view);

  useAppChrome({
    analyticsSection,
    clientInitialTab,
    contentRef,
    pageTitle,
    selectedClientSiteId: selectedClient?.site_id ?? '',
    setToast,
    theme,
    toast,
    view,
  });

  useEffect(() => {
    loadInitial();
    // The initial load intentionally runs once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadInitial() {
    if (!getStoredAdminToken()) {
      setLoading(false);
      setAuthRequired(true);
      setLoadError('');
      return;
    }

    setLoading(true);
    setLoadError('');
    try {
      const [nextOverview, nextSettings, nextConversations, nextAnalytics, nextVerticals] = await Promise.all([
        crmApi.overview(),
        crmApi.settings(),
        crmApi.conversations(range),
        crmApi.analytics(range),
        crmApi.verticals(),
      ]);
      setOverview(nextOverview);
      setSettings(nextSettings);
      setConversations(nextConversations);
      setAnalytics(nextAnalytics);
      setVerticals(nextVerticals.verticals);
      setAuthRequired(false);
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        clearStoredAdminToken();
        setAuthRequired(true);
        setLoadError(error.message);
      } else {
        const message = error instanceof Error ? error.message : 'CRM failed to load.';
        setLoadError(message);
        showError(error, 'CRM failed to load.');
      }
    } finally {
      setLoading(false);
    }
  }

  async function submitAdminToken(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const token = String(formData.get('admin_token') || '').trim();
    if (!token) {
      setLoadError('Enter the CRM admin token.');
      return;
    }
    setStoredAdminToken(token);
    await loadInitial();
  }

  function logoutAdmin() {
    clearStoredAdminToken();
    setOverview(null);
    setSettings(null);
    setConversations(null);
    setAnalytics(null);
    setSelectedClient(null);
    setPasswordDialogClient(null);
    setAuthRequired(true);
    setLoadError('');
    setView(DEFAULT_VIEW);
  }

  async function refreshCurrentView() {
    setBusy(true);
    try {
      const nextOverview = await crmApi.overview();
      setOverview(nextOverview);
      if (selectedClient) {
        const response = await crmApi.client(selectedClient.site_id);
        setSelectedClient(response.client);
      }
      if (view === 'settings') setSettings(await crmApi.settings());
      if (view === 'health') setVerticals((await crmApi.verticals()).verticals);
      if (view === 'dashboard' || view === 'conversations') setConversations(await crmApi.conversations(range));
      if (view === 'dashboard' || view === 'analytics') setAnalytics(await crmApi.analytics(range));
      setToast('CRM refreshed.');
    } catch (error) {
      showError(error, 'Refresh failed.');
    } finally {
      setBusy(false);
    }
  }

  async function updateRange(nextRange: string) {
    setRange(nextRange);
    setBusy(true);
    try {
      const [nextConversations, nextAnalytics] = await Promise.all([
        crmApi.conversations(nextRange),
        crmApi.analytics(nextRange),
      ]);
      setConversations(nextConversations);
      setAnalytics(nextAnalytics);
    } catch (error) {
      showError(error, 'Range update failed.');
    } finally {
      setBusy(false);
    }
  }

  async function openClient(siteId: string, initialTab: ClientWorkspaceTabId = 'overview') {
    setBusy(true);
    try {
      const response = await crmApi.client(siteId);
      setSelectedClient(response.client);
      setClientInitialTab(initialTab);
      setView('client-detail');
    } catch (error) {
      showError(error, 'Client failed to load.');
    } finally {
      setBusy(false);
    }
  }

  function openCurrentClientTab(tabId: ClientWorkspaceTabId) {
    if (!selectedClient) return;
    setClientInitialTab(tabId);
    setClientTabRequestKey((key) => key + 1);
    setView('client-detail');
    setMobileSidebarOpen(false);
  }

  async function createClient(payload: CreateClientPayload) {
    setBusy(true);
    try {
      const response = await crmApi.createClient(payload);
      setDialogOpen(false);
      setSelectedClient(response.client);
      setOverview(await crmApi.overview());
      setView('client-detail');
      setToast('Client created.');
    } catch (error) {
      showError(error, 'Client creation failed.');
    } finally {
      setBusy(false);
    }
  }

  async function saveSettings(values: Record<string, string>): Promise<SettingsResponse> {
    return saveSettingsAction({ values, setBusy, setSettings, setToast, showError });
  }

  async function generateSummary() {
    return generateSummaryAction({ range, setBusy, setAnalytics, setToast, showError });
  }

  function showError(error: unknown, fallback: string) {
    if (error instanceof UnauthorizedError) {
      clearStoredAdminToken();
      setAuthRequired(true);
      setLoadError(error.message);
      return;
    }
    setToast(error instanceof Error ? error.message : fallback);
  }

  const {
    activateClient,
    moveClientToAvailable,
    removeClient,
    revokeClientPanelPassword,
    toggleClient,
    triggerAutoIntegration,
    triggerCrawl,
    updateClientPanelPassword,
    updateClientTokenLimits,
  } = useClientOperations({
    selectedClient,
    setAutoIntegratingSites,
    setBusy,
    setClientBoardSection,
    setClientInitialTab,
    setCrawlingSites,
    setOverview,
    setPasswordDialogClient,
    setSelectedClient,
    setToast,
    setView,
    showError,
  });

  const clients = overview?.clients ?? [];
  const viewResetKey = `${view}:${selectedClient?.site_id ?? 'all'}`;
  const { openView, openSettings, openClientBoardSection, openAnalyticsSection } = useCrmNavigation({
    setSelectedClient,
    setClientInitialTab,
    setSettingsFocusKey,
    setView,
    setMobileSidebarOpen,
    setClientBoardSection,
    setAnalyticsSection,
  });

  const viewRendererProps = createViewRendererProps(
    {
      analytics,
      analyticsSection,
      autoIntegratingSites,
      busy,
      clientBoardSection,
      clientInitialTab,
      clientTabRequestKey,
      clients,
      conversations,
      crawlingSites,
      overview: overview as Overview,
      range,
      selectedClient,
      settings,
      settingsFocusKey,
      verticals,
      view,
    },
    {
      onActivateClient: activateClient,
      onAddClient: () => setDialogOpen(true),
      onAutoIntegrate: triggerAutoIntegration,
      onClientWorkspaceTabChange: setClientInitialTab,
      onGenerateSummary: generateSummary,
      onMoveClientToAvailable: moveClientToAvailable,
      onOpenAnalyticsSection: openAnalyticsSection,
      onOpenClient: openClient,
      onOpenClientBoardSection: openClientBoardSection,
      onOpenPasswordDialog: setPasswordDialogClient,
      onOpenSettings: openSettings,
      onRangeChange: updateRange,
      onRemoveClient: removeClient,
      onSaveSettings: saveSettings,
      onToggleClient: toggleClient,
      onTriggerCrawl: triggerCrawl,
      onUpdateTokenLimits: updateClientTokenLimits,
      onViewChange: setView,
    },
  );

  return (
    <AppShell
      pageTitle={pageTitle}
      view={view}
      overview={overview}
      selectedClient={selectedClient}
      clientInitialTab={clientInitialTab}
      clientBoardSection={clientBoardSection}
      analyticsSection={analyticsSection}
      mobileSidebarOpen={mobileSidebarOpen}
      contentRef={contentRef}
      authRequired={authRequired}
      loading={loading}
      loadError={loadError}
      busy={busy}
      viewResetKey={viewResetKey}
      viewRendererProps={viewRendererProps}
      dialogOpen={dialogOpen}
      passwordDialogClient={passwordDialogClient}
      toast={toast}
      theme={theme}
      onSubmitAdminToken={submitAdminToken}
      onToggleTheme={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
      onRetryLoad={loadInitial}
      onToggleSidebar={() => setMobileSidebarOpen((open) => !open)}
      onCloseSidebar={() => setMobileSidebarOpen(false)}
      onRefresh={refreshCurrentView}
      onLogout={logoutAdmin}
      onOpenDashboard={() => openView('dashboard')}
      onOpenClients={() => openClientBoardSection('all')}
      onOpenView={openView}
      onOpenClient={(siteId, initialTab) => {
        if (selectedClient?.site_id === siteId) {
          openCurrentClientTab(initialTab ?? clientInitialTab);
          return;
        }
        void openClient(siteId, initialTab);
      }}
      onOpenClientBoardSection={openClientBoardSection}
      onOpenClientTab={openCurrentClientTab}
      onOpenAnalyticsSection={openAnalyticsSection}
      onCloseAddClient={() => setDialogOpen(false)}
      onCreateClient={createClient}
      onClosePasswordDialog={() => setPasswordDialogClient(null)}
      onUpdatePassword={updateClientPanelPassword}
      onRevokePassword={revokeClientPanelPassword}
    />
  );
}
