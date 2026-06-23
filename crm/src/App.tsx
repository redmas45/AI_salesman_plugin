import { useEffect, useState } from 'react';
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
  View,
} from './types';
import { Sidebar } from './components/shared/Sidebar';
import { Topbar } from './components/shared/Topbar';
import { AddClientDialog, ClientPanelPasswordDialog } from './components/shared/Dialogs';
import { ViewRenderer } from './views/ViewRenderer';

const THEME_STORAGE_KEY = 'aiHubCrmTheme';
const DEFAULT_VIEW: View = 'dashboard';
const DEFAULT_RANGE = '7d';

export function App() {
  const [view, setView] = useState<View>(DEFAULT_VIEW);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
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
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [crawlingSites, setCrawlingSites] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    document.body.dataset.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

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
      const [nextOverview, nextSettings, nextConversations, nextAnalytics] = await Promise.all([
        crmApi.overview(),
        crmApi.settings(),
        crmApi.conversations(range),
        crmApi.analytics(range),
      ]);
      setOverview(nextOverview);
      setSettings(nextSettings);
      setConversations(nextConversations);
      setAnalytics(nextAnalytics);
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

  async function openClient(siteId: string) {
    setBusy(true);
    try {
      const response = await crmApi.client(siteId);
      setSelectedClient(response.client);
      setView('client-detail');
    } catch (error) {
      showError(error, 'Client failed to load.');
    } finally {
      setBusy(false);
    }
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
    if (!window.confirm(`Remove ${siteId}? Tenant data is kept.`)) return;
    setBusy(true);
    try {
      await crmApi.removeClient(siteId);
      setSelectedClient(null);
      setPasswordDialogClient((current) => (current?.site_id === siteId ? null : current));
      setOverview(await crmApi.overview());
      setView('clients');
      setToast('Client removed.');
    } catch (error) {
      showError(error, 'Client removal failed.');
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
    setCrawlingSites((current) => new Set(current).add(siteId));
    setBusy(true);
    try {
      await crmApi.crawlClient(siteId);
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === siteId) {
        const response = await crmApi.client(siteId);
        setSelectedClient(response.client);
      }
      setToast('Crawler started.');
      void pollCrawlStatus(siteId);
    } catch (error) {
      setCrawlingSites((current) => {
        const next = new Set(current);
        next.delete(siteId);
        return next;
      });
      showError(error, 'Crawler failed to start.');
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

  async function copyScript(client: Client) {
    await navigator.clipboard.writeText(client.script_tag);
    setToast('Script copied.');
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
  const pageTitle = titleForView(view);

  return (
    <>
      <div className="crm-shell">
        <Sidebar
          view={view}
          setView={(nextView) => {
            setView(nextView);
            setMobileSidebarOpen(false);
          }}
          health={overview?.health ?? {}}
          selectedClient={selectedClient}
          open={mobileSidebarOpen}
        />
        <div className="crm-body">
          <Topbar
            title={pageTitle}
            health={overview?.health ?? {}}
            selectedClient={selectedClient}
            theme={theme}
            busy={busy}
            onToggleSidebar={() => setMobileSidebarOpen((open) => !open)}
            onRefresh={refreshCurrentView}
            onAddClient={() => setDialogOpen(true)}
            onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            onLogout={logoutAdmin}
            authenticated={!authRequired && Boolean(overview)}
          />
          <main className="crm-content">
            {authRequired ? (
              <AdminTokenView busy={loading} error={loadError} onSubmit={submitAdminToken} />
            ) : loading || (!overview && !loadError) ? (
              <SkeletonDashboard />
            ) : loadError && !overview ? (
              <LoadErrorView message={loadError} onRetry={loadInitial} />
            ) : (
              <ViewRenderer
                view={view}
                overview={overview as Overview}
                clients={clients}
                selectedClient={selectedClient}
                conversations={conversations}
                analytics={analytics}
                settings={settings}
                range={range}
                crawlingSites={crawlingSites}
                onRangeChange={updateRange}
                onViewChange={setView}
                onAddClient={() => setDialogOpen(true)}
                onOpenClient={openClient}
                onCopyScript={copyScript}
                onTriggerCrawl={triggerCrawl}
                onRemoveClient={removeClient}
                onToggleClient={toggleClient}
                onUpdateTokenLimits={updateClientTokenLimits}
                onOpenPasswordDialog={setPasswordDialogClient}
                onSaveSettings={saveSettings}
                onGenerateSummary={generateSummary}
              />
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
        <div className="text-xs font-semibold uppercase text-muted">Protected CRM</div>
        <h2 className="mt-2 text-lg font-semibold">Enter admin token</h2>
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
  return localStorage.getItem(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light';
}

function titleForView(view: View) {
  const titles: Record<View, string> = {
    dashboard: 'Dashboard',
    clients: 'Clients',
    'client-detail': 'Client detail',
    catalogs: 'Catalogs',
    usage: 'Usage',
    conversations: 'Conversations',
    analytics: 'Analytics',
    adapters: 'Adapters',
    settings: 'Settings',
    health: 'Health',
  };
  return titles[view];
}
