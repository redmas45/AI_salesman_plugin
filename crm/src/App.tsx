import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { UnauthorizedError, clearStoredAdminToken, crmApi, getStoredAdminToken, setStoredAdminToken } from './api';
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
} from './types';
import type { ClientWorkspaceTabId } from './verticals/types';
import { Sidebar } from './components/shared/Sidebar';
import { Topbar } from './components/shared/Topbar';
import { AddClientDialog, ClientPanelPasswordDialog } from './components/shared/Dialogs';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { ViewRenderer } from './views/ViewRenderer';

const THEME_STORAGE_KEY = 'aiHubCrmTheme';
const DEFAULT_VIEW: View = 'dashboard';
const DEFAULT_RANGE = '7d';

export function App() {
  const [view, setView] = useState<View>(DEFAULT_VIEW);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [verticals, setVerticals] = useState<VerticalDefinition[]>([]);
  const [conversations, setConversations] = useState<ConversationsResponse | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [range, setRange] = useState(DEFAULT_RANGE);
  const [theme] = useState<Theme>(storedTheme());
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

  useEffect(() => {
    document.body.dataset.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    document.title =
      view === 'client-detail' && selectedClient
        ? `AI Hub - Client: ${selectedClient.site_id}`
        : `AI Hub - ${pageTitle}`;
  }, [pageTitle, selectedClient, view]);

  useEffect(() => {
    loadInitial();
    // The initial load intentionally runs once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, left: 0 });
  }, [view, selectedClient?.site_id, clientInitialTab, analyticsSection]);

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

  function syncClient(client: Client) {
    setSelectedClient((current) => (current?.site_id === client.site_id ? client : current));
    setPasswordDialogClient((current) => (current?.site_id === client.site_id ? client : current));
  }

  async function removeClient(siteId: string) {
    if (!window.confirm(`Move ${siteId} out of Current clients? Tenant data is kept.`)) return;
    setBusy(true);
    try {
      await crmApi.removeClient(siteId);
      setSelectedClient(null);
      setPasswordDialogClient((current) => (current?.site_id === siteId ? null : current));
      setOverview(await crmApi.overview());
      setClientBoardSection('available');
      setView('clients');
      setToast('Client moved to Available.');
    } catch (error) {
      showError(error, 'Client removal failed.');
    } finally {
      setBusy(false);
    }
  }

  async function activateClient(siteId: string) {
    setBusy(true);
    try {
      const response = await crmApi.activateClient(siteId);
      setSelectedClient(response.client);
      setClientInitialTab('overview');
      setOverview(await crmApi.overview());
      setView('client-detail');
      setToast('Client moved to Current.');
    } catch (error) {
      showError(error, 'Client activation failed.');
    } finally {
      setBusy(false);
    }
  }

  async function toggleClient(siteId: string, enabled: boolean) {
    setBusy(true);
    try {
      await crmApi.setClientEnabled(siteId, enabled);
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === siteId) {
        const response = await crmApi.client(siteId);
        syncClient(response.client);
      }
      setToast(enabled ? 'Client enabled.' : 'Client disabled.');
    } catch (error) {
      showError(error, 'Client status update failed.');
    } finally {
      setBusy(false);
    }
  }

  async function updateClientTokenLimits(siteId: string, tokenLimit: number, sessionTokenLimit: number) {
    setBusy(true);
    try {
      const response = await crmApi.updateClientTokenLimits(siteId, {
        token_limit: tokenLimit,
        session_token_limit: sessionTokenLimit,
      });
      syncClient(response.client);
      setOverview(await crmApi.overview());
      setToast('Token limits saved.');
    } catch (error) {
      showError(error, 'Token limit update failed.');
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function updateClientPanelPassword(siteId: string, password: string, autoGenerate: boolean) {
    setBusy(true);
    try {
      const response = await crmApi.updateClientPanelPassword(siteId, {
        password: autoGenerate ? undefined : password,
        auto_generate: autoGenerate,
      });
      syncClient(response.client);
      setOverview(await crmApi.overview());
      setToast(autoGenerate ? 'Panel password generated.' : 'Panel password updated.');
      return response.generated_password || '';
    } catch (error) {
      showError(error, 'Client panel password update failed.');
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function revokeClientPanelPassword(siteId: string) {
    setBusy(true);
    try {
      const response = await crmApi.revokeClientPanelPassword(siteId);
      syncClient(response.client);
      setOverview(await crmApi.overview());
      setToast('Panel password revoked.');
    } catch (error) {
      showError(error, 'Client panel password revoke failed.');
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function triggerCrawl(siteId: string) {
    const cleanSiteId = typeof siteId === 'string' ? siteId.trim() : '';
    if (!cleanSiteId) {
      setToast('Crawler could not start because the client site ID was missing.');
      return;
    }
    setCrawlingSites((current) => new Set(current).add(cleanSiteId));
    setBusy(true);
    try {
      await crmApi.crawlClient(cleanSiteId);
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === cleanSiteId) {
        const response = await crmApi.client(cleanSiteId);
        setSelectedClient(response.client);
      }
      setToast('Crawler started.');
      void pollCrawlStatus(cleanSiteId);
    } catch (error) {
      setCrawlingSites((current) => {
        const next = new Set(current);
        next.delete(cleanSiteId);
        return next;
      });
      showError(error, 'Crawler failed to start.');
    } finally {
      setBusy(false);
    }
  }

  async function triggerAutoIntegration(siteId: string) {
    setAutoIntegratingSites((current) => new Set(current).add(siteId));
    setBusy(true);
    try {
      await crmApi.autoIntegrateClient(siteId);
      setToast('Setup run queued.');
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === siteId) {
        const response = await crmApi.client(siteId);
        syncClient(response.client);
      }
      void pollAutoIntegrationStatus(siteId);
    } catch (error) {
      setAutoIntegratingSites((current) => {
        const next = new Set(current);
        next.delete(siteId);
        return next;
      });
      showError(error, 'Setup run failed to start.');
    } finally {
      setBusy(false);
    }
  }

  async function pollCrawlStatus(siteId: string) {
    const startedAt = Date.now();
    try {
      while (Date.now() - startedAt < 60000) {
        await delay(5000);
        const response = await crmApi.client(siteId);
        syncClient(response.client);
        const status = String(response.client.last_crawl_status || '').toLowerCase();
        if (status && status !== 'running' && status !== 'crawling') break;
      }
      setOverview(await crmApi.overview());
    } catch (error) {
      showError(error, 'Crawler status refresh failed.');
    } finally {
      setCrawlingSites((current) => {
        const next = new Set(current);
        next.delete(siteId);
        return next;
      });
    }
  }

  async function pollAutoIntegrationStatus(siteId: string) {
    const startedAt = Date.now();
    try {
      while (Date.now() - startedAt < 30 * 60 * 1000) {
        await delay(10000);
        const response = await crmApi.client(siteId);
        syncClient(response.client);
        const initialization = response.client.vertical_config?.initialization as Record<string, unknown> | undefined;
        const status = String(initialization?.status || '').toLowerCase();
        if (status && status !== 'running') break;
      }
      setOverview(await crmApi.overview());
    } catch (error) {
      showError(error, 'Setup status refresh failed.');
    } finally {
      setAutoIntegratingSites((current) => {
        const next = new Set(current);
        next.delete(siteId);
        return next;
      });
    }
  }

  async function saveSettings(values: Record<string, string>): Promise<SettingsResponse> {
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

  async function generateSummary() {
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

  function showError(error: unknown, fallback: string) {
    if (error instanceof UnauthorizedError) {
      clearStoredAdminToken();
      setAuthRequired(true);
      setLoadError(error.message);
      return;
    }
    setToast(error instanceof Error ? error.message : fallback);
  }

  const clients = overview?.clients ?? [];
  const viewResetKey = `${view}:${selectedClient?.site_id ?? 'all'}`;
  const openView = (nextView: View) => {
    if (nextView !== 'client-detail') {
      setSelectedClient(null);
      setClientInitialTab('overview');
    }
    if (nextView !== 'settings') setSettingsFocusKey('');
    setView(nextView);
    setMobileSidebarOpen(false);
  };
  const openSettings = (focusKey = '') => {
    setSelectedClient(null);
    setClientInitialTab('overview');
    setSettingsFocusKey(focusKey);
    setView('settings');
    setMobileSidebarOpen(false);
  };
  const openClientBoardSection = (section: ClientBoardSection) => {
    setClientBoardSection(section);
    setSelectedClient(null);
    setClientInitialTab('overview');
    setView('clients');
    setMobileSidebarOpen(false);
  };
  const openAnalyticsSection = (section: AnalyticsSectionId) => {
    setAnalyticsSection(section);
    setSelectedClient(null);
    setClientInitialTab('overview');
    setView('analytics');
    setMobileSidebarOpen(false);
  };

  return (
    <>
      <div className="crm-shell">
        <Sidebar
          view={view}
          setView={openView}
          health={overview?.health ?? {}}
          selectedClient={selectedClient}
          activeClientTab={clientInitialTab}
          clientBoardSection={clientBoardSection}
          analyticsSection={analyticsSection}
          open={mobileSidebarOpen}
          onOpenClientBoardSection={openClientBoardSection}
          onOpenClientTab={openCurrentClientTab}
          onOpenAnalyticsSection={openAnalyticsSection}
        />
        <div className="crm-body">
          <Topbar
            title={pageTitle}
            view={view}
            health={overview?.health ?? {}}
            selectedClient={selectedClient}
            activeClientTab={clientInitialTab}
            busy={busy}
            onToggleSidebar={() => setMobileSidebarOpen((open) => !open)}
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
            authenticated={!authRequired && Boolean(overview)}
          />
          <main className="crm-content" ref={contentRef}>
            {authRequired ? (
              <AdminTokenView busy={loading} error={loadError} onSubmit={submitAdminToken} />
            ) : loading || (!overview && !loadError) ? (
              <SkeletonDashboard />
            ) : loadError && !overview ? (
              <LoadErrorView message={loadError} onRetry={loadInitial} />
            ) : (
              <ErrorBoundary resetKey={viewResetKey}>
                <ViewRenderer
                  view={view}
                  overview={overview as Overview}
                  clients={clients}
                  selectedClient={selectedClient}
                  clientInitialTab={clientInitialTab}
                  clientTabRequestKey={clientTabRequestKey}
                  clientBoardSection={clientBoardSection}
                  analyticsSection={analyticsSection}
                  conversations={conversations}
                  analytics={analytics}
                  settings={settings}
                  settingsFocusKey={settingsFocusKey}
                  verticals={verticals}
                  range={range}
                  busy={busy}
                  crawlingSites={crawlingSites}
                  autoIntegratingSites={autoIntegratingSites}
                  onRangeChange={updateRange}
                  onViewChange={setView}
                  onOpenSettings={openSettings}
                  onOpenClientBoardSection={openClientBoardSection}
                  onOpenAnalyticsSection={openAnalyticsSection}
                  onAddClient={() => setDialogOpen(true)}
                  onOpenClient={openClient}
                  onClientWorkspaceTabChange={setClientInitialTab}
                  onActivateClient={activateClient}
                  onTriggerCrawl={triggerCrawl}
                  onAutoIntegrate={triggerAutoIntegration}
                  onRemoveClient={removeClient}
                  onToggleClient={toggleClient}
                  onUpdateTokenLimits={updateClientTokenLimits}
                  onOpenPasswordDialog={setPasswordDialogClient}
                  onSaveSettings={saveSettings}
                  onGenerateSummary={generateSummary}
                />
              </ErrorBoundary>
            )}
          </main>
        </div>
        {mobileSidebarOpen ? (
          <button
            className="fixed inset-0 z-40 border-0 bg-black/30 lg:hidden"
            type="button"
            aria-label="Close navigation"
            onClick={() => setMobileSidebarOpen(false)}
          />
        ) : null}
      </div>
      <AddClientDialog open={dialogOpen} busy={busy} onClose={() => setDialogOpen(false)} onCreate={createClient} />
      <ClientPanelPasswordDialog
        client={passwordDialogClient}
        busy={busy}
        onClose={() => setPasswordDialogClient(null)}
        onUpdatePassword={updateClientPanelPassword}
        onRevokePassword={revokeClientPanelPassword}
      />
      <div className={`toast ${toast ? 'visible' : ''}`}>{toast}</div>
    </>
  );
}

function AdminTokenView({
  busy,
  error,
  onSubmit,
}: {
  busy: boolean;
  error: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <section className="mx-auto mt-12 grid w-full max-w-md gap-4 rounded-lg border border-line bg-panel p-5 shadow-xl">
      <div>
        <div className="text-xs font-semibold uppercase text-muted">AI Hub CRM</div>
        <h2 className="mt-2 text-lg font-semibold">Unlock Maya operations</h2>
        <p className="mt-1 text-sm text-muted">Use the admin token to manage clients, prompts, adapters, and runtime health.</p>
      </div>
      <form className="grid gap-3" onSubmit={onSubmit}>
        <label className="field">
          <span>CRM admin token</span>
          <input
            name="admin_token"
            type="password"
            autoComplete="current-password"
            autoFocus
            required
          />
        </label>
        {error ? (
          <p className="text-sm" style={{ color: 'var(--red)' }}>
            {error}
          </p>
        ) : null}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Checking...' : 'Unlock CRM'}
        </button>
      </form>
    </section>
  );
}

function LoadErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="mx-auto mt-12 grid w-full max-w-xl gap-4 rounded-lg border border-line bg-panel p-5 text-center shadow-xl">
      <div>
        <div className="text-xs font-semibold uppercase text-muted">CRM load failed</div>
        <h2 className="mt-2 text-lg font-semibold">Could not load AI Hub CRM</h2>
      </div>
      <p className="text-sm text-muted">{message}</p>
      <div className="flex justify-center">
        <button className="btn btn-secondary" type="button" onClick={onRetry}>
          Retry
        </button>
      </div>
    </section>
  );
}

function SkeletonCard({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 'var(--radius)' }} />;
}

function SkeletonKpiStrip() {
  return (
    <div className="dashboard-bento">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="bento-kpi">
          <SkeletonCard height={116} />
        </div>
      ))}
    </div>
  );
}

function SkeletonDashboard() {
  return (
    <div className="grid gap-4">
      <SkeletonCard height={76} />
      <SkeletonKpiStrip />
      <div className="dashboard-bento">
        <div className="bento-wide">
          <SkeletonCard height={340} />
        </div>
        <div className="bento-narrow">
          <SkeletonCard height={340} />
        </div>
      </div>
    </div>
  );
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function storedTheme(): Theme {
  localStorage.setItem(THEME_STORAGE_KEY, 'light');
  return 'light';
}

function titleForView(view: View) {
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
