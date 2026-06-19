import { useEffect, useMemo, useRef, useState } from 'react';
import type { ButtonHTMLAttributes, CSSProperties, FormEvent, InputHTMLAttributes, ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  ChevronDown,
  CheckCircle2,
  ClipboardCheck,
  Code2,
  Copy,
  Database,
  EllipsisVertical,
  ExternalLink,
  Eye,
  FileText,
  Gauge,
  HeartPulse,
  KeyRound,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Moon,
  PackageOpen,
  Play,
  Plug,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  Trash2,
  Users,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import { UnauthorizedError, clearStoredAdminToken, crmApi, getStoredAdminToken, setStoredAdminToken } from './api';
import type {
  AnalyticsResponse,
  CatalogProduct,
  CapabilitiesSummary,
  Client,
  ConversationsResponse,
  CrawlReport,
  CreateClientPayload,
  HealthSnapshot,
  Overview,
  ProductPreview,
  RankRow,
  ReadinessReport,
  SeriesRow,
  Setting,
  SettingsResponse,
  SyncRun,
  Theme,
  UsageEvent,
  View,
} from './types';

const THEME_STORAGE_KEY = 'aiHubCrmTheme';
const DEFAULT_VIEW: View = 'dashboard';
const DEFAULT_RANGE = '7d';
const CATALOG_PAGE_LIMIT = 160;
const CATALOG_PAGE_SIZE = 12;
const CONFIDENCE_PERCENT = 100;

type ClientWorkspaceTab = 'overview' | 'readiness' | 'catalog' | 'crawl' | 'activity' | 'controls';
type SettingNoticeTone = 'success' | 'error' | 'info';

interface SettingNotice {
  tone: SettingNoticeTone;
  message: string;
}

interface DisplayProduct {
  id: string;
  name: string;
  brand: string;
  category: string;
  description: string;
  price: number;
  stock: number | null;
  imageUrl: string;
  vectorized: boolean;
  rating: number | null;
  reviewCount: number | null;
}

const RANGE_OPTIONS = [
  ['1d', 'Last 1 day'],
  ['3d', 'Last 3 days'],
  ['7d', 'Last 7 days'],
  ['15d', 'Last 15 days'],
  ['30d', 'Last 30 days'],
  ['3m', 'Last 3 months'],
  ['6m', 'Last 6 months'],
  ['1y', 'Last 1 year'],
  ['all', 'All time'],
] as const;

const CLIENT_WORKSPACE_TABS: Array<{ id: ClientWorkspaceTab; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'readiness', label: 'Readiness', icon: ShieldCheck },
  { id: 'catalog', label: 'Catalog', icon: PackageOpen },
  { id: 'crawl', label: 'Crawl', icon: Gauge },
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'controls', label: 'Controls', icon: SlidersHorizontal },
];

const NUMERIC_SETTING_LABELS: Record<string, string> = {
  LLM_TEMPERATURE: 'LLM temperature',
  LLM_MAX_TOKENS: 'LLM max tokens',
  LLM_MAX_TOKENS_HARD_CAP: 'LLM hard token cap',
  RAG_TOP_K: 'RAG top K',
  RAG_TOP_N: 'RAG top N',
  CRAWL_MAX_PAGES: 'Crawler max pages',
  CRAWL_MAX_DEPTH: 'Crawler max depth',
  PORT: 'Hub port',
  STOREFRONT_PORT: 'Storefront port',
  BACKEND_PORT: 'Backend port',
  HTTPS_PORT: 'HTTPS port',
};

const ACTION_LABELS: Record<string, string> = {
  ADD_TO_CART: 'Add to cart',
  CHECKOUT: 'Checkout',
  CLEAR_CART: 'Clear cart',
  CLEAR_FILTERS: 'Clear filters',
  CLEAR_HISTORY: 'Clear history',
  FILTER_PRODUCTS: 'Filter products',
  NAVIGATE_TO: 'Navigate',
  REMOVE_FROM_CART: 'Remove from cart',
  SHOW_COMPARISON: 'Compare products',
  SHOW_PRODUCTS: 'Show products',
  SHOW_PRODUCT_DETAIL: 'Product detail',
  SORT_PRODUCTS: 'Sort products',
  UPDATE_CART_QUANTITY: 'Update quantity',
  UPDATE_PREFERENCES: 'Update preferences',
};

const SETTING_GROUPS = [
  {
    title: 'Speech-to-text',
    keys: ['STT_PROVIDER', 'STT_MODEL', 'GROQ_STT_MODEL', 'STT_LANGUAGE'],
  },
  {
    title: 'Text-to-speech',
    keys: [
      'TTS_PROVIDER',
      'TTS_MODEL',
      'FAST_TTS_MODEL',
      'TTS_VOICE',
      'GROQ_TTS_MODEL',
      'GROQ_TTS_VOICE',
      'GROQ_TTS_RESPONSE_FORMAT',
      'GROQ_FALLBACK_TO_OPENAI',
      'FAST_VOICE_MODE',
    ],
  },
  {
    title: 'LLM',
    keys: [
      'OPENAI_API_KEY',
      'GROQ_API_KEY',
      'LLM_MODEL',
      'LLM_TEMPERATURE',
      'LLM_MAX_TOKENS',
      'LLM_MAX_TOKENS_HARD_CAP',
    ],
  },
  {
    title: 'RAG',
    keys: ['EMBEDDING_MODEL', 'RAG_TOP_K', 'RAG_TOP_N'],
  },
  {
    title: 'Deployment',
    keys: [
      'HUB_PUBLIC_URL',
      'CLIENT_STORE_URL',
      'CURRENT_URL',
      'CURRENT_SITE_ID',
      'DEFAULT_SITE_ID',
      'AI_DEFAULT_SITE_ID',
      'DATABASE_URL',
      'PUBLIC_API_URL',
      'PUBLIC_STOREFRONT_ORIGIN',
      'PUBLIC_WIDGET_SCRIPT_URL',
      'PUBLIC_HTTPS_ORIGIN',
      'VOICE_ORB_API_URL',
      'DEPLOYMENT_MODE',
      'HOST',
      'PORT',
      'STOREFRONT_PORT',
      'BACKEND_PORT',
      'HTTPS_PORT',
      'HUB_TLS_CERT_FILE',
      'HUB_TLS_KEY_FILE',
      'CORS_ORIGINS',
    ],
  },
  {
    title: 'Crawler',
    keys: ['CRAWL_MAX_PAGES', 'CRAWL_MAX_DEPTH', 'CRAWL_ON_STARTUP', 'CRAWL_PERIODIC_ENABLED'],
  },
  {
    title: 'Client panel and CRM',
    keys: ['CRM_ADMIN_TOKEN', 'CLIENT_PANEL_DEFAULT_PASSWORD', 'CLIENT_PANEL_TOKEN_SECRET'],
  },
];

const NAV_ITEMS: Array<{ view: View; label: string; icon: typeof LayoutDashboard; section: string }> = [
  { view: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
  { view: 'clients', label: 'Clients', icon: Users, section: 'Overview' },
  { view: 'catalogs', label: 'Catalogs', icon: Database, section: 'Data' },
  { view: 'usage', label: 'Usage', icon: Activity, section: 'Data' },
  { view: 'conversations', label: 'Conversations', icon: MessageSquare, section: 'Data' },
  { view: 'analytics', label: 'Analytics', icon: BarChart3, section: 'Data' },
  { view: 'adapters', label: 'Adapters', icon: Plug, section: 'System' },
  { view: 'settings', label: 'Settings', icon: Settings, section: 'System' },
  { view: 'health', label: 'Health', icon: HeartPulse, section: 'System' },
];

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
        <Field
          label="CRM admin token"
          name="admin_token"
          type="password"
          autoComplete="current-password"
          autoFocus
          required
        />
        {error ? (
          <p className="text-sm" style={{ color: 'var(--red)' }}>
            {error}
          </p>
        ) : null}
        <Button type="submit" disabled={busy}>
          {busy ? 'Checking...' : 'Unlock CRM'}
        </Button>
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
        <Button variant="secondary" type="button" onClick={onRetry}>
          Retry
        </Button>
      </div>
    </section>
  );
}

function Sidebar({
  view,
  setView,
  health,
  selectedClient,
  open,
}: {
  view: View;
  setView: (view: View) => void;
  health: HealthSnapshot;
  selectedClient: Client | null;
  open: boolean;
}) {
  const grouped = groupNavItems();
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  return (
    <aside className={`crm-sidebar ${open ? 'open' : ''}`}>
      <button
        type="button"
        className="sidebar-brand"
        onClick={() => setView(DEFAULT_VIEW)}
      >
        <span className="sidebar-brand-mark">AK</span>
        <span className="sidebar-brand-text">
          <strong>
            AI Hub CRM
            <i className={`health-dot ${healthy ? 'ok' : ''}`} aria-label={healthy ? 'Healthy' : 'Degraded'} />
          </strong>
          <span>crawler and AI ops</span>
        </span>
      </button>
      <nav className="sidebar-nav" aria-label="CRM navigation">
        {Object.entries(grouped).map(([section, items]) => (
          <div key={section}>
            <div className="sidebar-section-label">{section}</div>
            {items.map((item) => {
              const Icon = item.icon;
              const active = view === item.view || (view === 'client-detail' && item.view === 'clients');
              return (
                <button
                  key={item.view}
                  type="button"
                  className={`sidebar-item ${active ? 'active' : ''}`}
                  onClick={() => setView(item.view)}
                >
                  <Icon className="sidebar-item-icon" aria-hidden="true" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        {selectedClient ? (
          <div className="sidebar-client-pin">
            <div className="sidebar-client-pin-label">Current client</div>
            <div className="sidebar-client-pin-id">{selectedClient.site_id}</div>
            <div className="sidebar-client-pin-url" title={selectedClient.store_url}>
              {selectedClient.store_url}
            </div>
          </div>
        ) : (
          <div className="sidebar-client-card">
            <span>Workspace</span>
            <strong>All clients</strong>
            <span>Admin overview</span>
          </div>
        )}
      </div>
    </aside>
  );
}

function Topbar({
  title,
  health,
  selectedClient,
  theme,
  busy,
  authenticated,
  onToggleSidebar,
  onRefresh,
  onAddClient,
  onToggleTheme,
  onLogout,
}: {
  title: string;
  health: HealthSnapshot;
  selectedClient: Client | null;
  theme: Theme;
  busy: boolean;
  authenticated: boolean;
  onToggleSidebar: () => void;
  onRefresh: () => void;
  onAddClient: () => void;
  onToggleTheme: () => void;
  onLogout: () => void;
}) {
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  return (
    <header className="crm-topbar">
      <div className="flex items-center gap-3">
        <button className="btn btn-secondary btn-icon mobile-menu-btn" type="button" aria-label="Open navigation" onClick={onToggleSidebar}>
          <Menu size={17} aria-hidden="true" />
        </button>
        <div className="crm-topbar-title" aria-label={`AI Hub, ${title}${selectedClient ? `, ${selectedClient.site_id}` : ''}`}>
          <span className="topbar-crumb-muted">AI Hub</span>
          <span className="topbar-crumb-separator">›</span>
          <span>{title}</span>
          {selectedClient ? (
            <>
              <span className="topbar-crumb-separator">›</span>
              <span className="topbar-crumb-client">{selectedClient.site_id}</span>
            </>
          ) : null}
        </div>
      </div>
      <div className="crm-topbar-actions">
        <span className={`topbar-live-badge ${healthy ? '' : 'degraded'}`}>
          <span className="topbar-live-dot" />
          {healthy ? 'Live' : 'Degraded'}
        </span>
        <IconButton
          label={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          icon={theme === 'dark' ? Sun : Moon}
          onClick={onToggleTheme}
        />
        {authenticated ? <IconButton label="Refresh" icon={RefreshCw} onClick={onRefresh} disabled={busy} /> : null}
        {authenticated ? (
          <Button onClick={onAddClient} icon={Plus}>
            Add client
          </Button>
        ) : null}
        {authenticated ? (
          <Button variant="secondary" onClick={onLogout}>
            Logout
          </Button>
        ) : null}
      </div>
    </header>
  );
}

function ViewRenderer(props: {
  view: View;
  overview: Overview;
  clients: Client[];
  selectedClient: Client | null;
  conversations: ConversationsResponse | null;
  analytics: AnalyticsResponse | null;
  settings: SettingsResponse | null;
  range: string;
  crawlingSites: Set<string>;
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onAddClient: () => void;
  onOpenClient: (siteId: string) => void;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onSaveSettings: (values: Record<string, string>) => Promise<SettingsResponse>;
  onGenerateSummary: () => void;
}) {
  switch (props.view) {
    case 'clients':
      return <ClientsView {...props} />;
    case 'client-detail':
      return props.selectedClient ? (
        <ClientDetailView
          {...props}
          client={props.selectedClient}
          recentActivity={props.overview.recent_activity.filter((item) => item.site_id === props.selectedClient?.site_id)}
        />
      ) : (
        <ClientsView {...props} />
      );
    case 'catalogs':
      return (
        <CatalogsView
          clients={props.clients}
          crawlingSites={props.crawlingSites}
          onOpenClient={props.onOpenClient}
          onTriggerCrawl={props.onTriggerCrawl}
        />
      );
    case 'usage':
      return <UsageView clients={props.clients} recentActivity={props.overview.recent_activity} />;
    case 'conversations':
      return (
        <ConversationsView
          conversations={props.conversations}
          range={props.range}
          onRangeChange={props.onRangeChange}
        />
      );
    case 'analytics':
      return (
        <AnalyticsView
          analytics={props.analytics}
          range={props.range}
          onRangeChange={props.onRangeChange}
          onGenerateSummary={props.onGenerateSummary}
        />
      );
    case 'adapters':
      return <AdaptersView clients={props.clients} onOpenClient={props.onOpenClient} />;
    case 'settings':
      return <SettingsView settings={props.settings} onSave={props.onSaveSettings} />;
    case 'health':
      return <HealthView health={props.overview.health} clients={props.clients} />;
    default:
      return <DashboardView {...props} />;
  }
}

function DashboardView({
  overview,
  clients,
  analytics,
  range,
  onRangeChange,
  onViewChange,
  onOpenClient,
}: {
  overview: Overview;
  clients: Client[];
  analytics: AnalyticsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onOpenClient: (siteId: string) => void;
}) {
  const metrics = overview.metrics;
  const analyticsMetrics = analytics?.metrics;
  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Store analytics</h2>
          <p className="mt-1 text-sm text-muted">Demand, catalog readiness, and assistant health at a glance.</p>
        </div>
        <RangeControl value={range} onChange={onRangeChange} />
      </section>
      <div className="dashboard-bento fade-in">
        <KpiCard className="bento-kpi" label="Total clients" value={clients.length} icon={Users} tone="accent" />
        <KpiCard className="bento-kpi" label="Active sessions" value={analyticsMetrics?.sessions ?? 0} icon={Activity} tone="blue" />
        <KpiCard className="bento-kpi" label="Turns today" value={metrics.voice_turns_today ?? 0} icon={MessageSquare} tone="green" />
        <KpiCard className="bento-kpi" label="Catalog items" value={metrics.products_indexed ?? 0} icon={Database} tone="amber" />

        <div className="bento-wide card">
          <DashboardTrendChart analytics={analytics} range={range} onOpenAnalytics={() => onViewChange('analytics')} />
        </div>
        <div className="bento-narrow card">
          <ActiveClientsList clients={clients.slice(0, 5)} onOpenClient={onOpenClient} onOpenClients={() => onViewChange('clients')} />
        </div>

        <div className="bento-half card">
          <RecentActivityFeed items={overview.recent_activity.slice(0, 30)} onOpen={() => onViewChange('conversations')} />
        </div>
        <div className="bento-half card">
          <HealthStatusPanel health={overview.health} />
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  icon: Icon,
  tone,
  className = '',
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  tone: 'accent' | 'blue' | 'green' | 'amber';
  className?: string;
}) {
  return (
    <section className={`card kpi-card kpi-${tone} ${className}`}>
      <div className="kpi-icon-bg">
        <Icon size={40} aria-hidden="true" />
      </div>
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{typeof value === 'number' ? number(value) : value}</strong>
    </section>
  );
}

function DashboardTrendChart({
  analytics,
  range,
  onOpenAnalytics,
}: {
  analytics: AnalyticsResponse | null;
  range: string;
  onOpenAnalytics: () => void;
}) {
  const visibleRows = (analytics?.series ?? []).slice(-14);
  const maxTurns = Math.max(...visibleRows.map((row) => row.turns), 1);
  const maxTokens = Math.max(...visibleRows.map((row) => row.tokens), 1);
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Demand trend</h2>
          <span className="card-meta">{rangeLabel(range)}</span>
        </div>
        <Button variant="ghost" type="button" onClick={onOpenAnalytics}>
          View analytics
        </Button>
      </div>
      {visibleRows.length ? (
        <div className="analytics-trend">
          {visibleRows.map((row) => (
            <div key={row.date} className="trend-column">
              <span className="trend-tooltip">
                {row.date}: {number(row.turns)} turns, {number(row.tokens)} tokens
              </span>
              <span className="trend-token" style={{ bottom: `${Math.max(8, (row.tokens / maxTokens) * 88)}%` }} />
              <span className="trend-bar" style={{ height: `${Math.max(8, (row.turns / maxTurns) * 100)}%` }} />
              <small>{row.date.slice(5)}</small>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="No trend data yet." />
      )}
    </>
  );
}

function ActiveClientsList({
  clients,
  onOpenClient,
  onOpenClients,
}: {
  clients: Client[];
  onOpenClient: (siteId: string) => void;
  onOpenClients: () => void;
}) {
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Active clients</h2>
          <span className="card-meta">{number(clients.length)} shown</span>
        </div>
        <Button variant="ghost" type="button" onClick={onOpenClients}>
          Open all
        </Button>
      </div>
      {clients.length ? (
        <div className="client-mini-list">
          {clients.map((client, index) => (
            <button
              key={client.site_id}
              className="client-mini-row"
              type="button"
              onClick={() => onOpenClient(client.site_id)}
              style={{ animationDelay: `${index * 30}ms` }}
            >
              <span className="client-mini-avatar">{client.site_id.slice(0, 2).toUpperCase()}</span>
              <div className="client-mini-copy">
                <strong title={client.name}>{client.name}</strong>
                <span title={client.store_url}>{number(client.catalog.active_products)} products · {client.store_url}</span>
              </div>
              <StatusPill value={client.status} />
              <ArrowRight size={14} aria-hidden="true" className="client-mini-arrow" />
            </button>
          ))}
        </div>
      ) : (
        <EmptyState title="No clients yet" message="Add a client to start crawling products and tracking voice assistant demand." />
      )}
    </>
  );
}

function RecentActivityFeed({ items, onOpen }: { items: UsageEvent[]; onOpen: () => void }) {
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Recent activity</h2>
          <span className="card-meta">Latest {number(items.length)} events</span>
        </div>
        <Button variant="ghost" type="button" onClick={onOpen}>
          Open conversations
        </Button>
      </div>
      <ActivityList items={items.slice(0, 6)} />
      {items.length > 6 ? (
        <div className="mt-4">
          <Button variant="secondary" type="button" onClick={onOpen}>
            Load more
          </Button>
        </div>
      ) : null}
    </>
  );
}

function HealthStatusPanel({ health }: { health: HealthSnapshot }) {
  const entries = Object.entries(health);
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Quick health</h2>
          <span className="card-meta">{number(entries.length)} checks</span>
        </div>
      </div>
      {entries.length ? (
        <div className="health-grid">
          {entries.map(([key, value]) => {
            const state = healthState(value);
            return (
              <article key={key} className={`health-item ${state}`}>
                <span className="health-item-label">{labelize(key)}</span>
                <span className="health-item-status">
                  <StatusPill value={value || 'unknown'} />
                </span>
              </article>
            );
          })}
        </div>
      ) : (
        <EmptyState text="No health checks returned." />
      )}
    </>
  );
}

function ClientsView({
  clients,
  crawlingSites,
  onAddClient,
  onOpenClient,
  onRemoveClient,
  onToggleClient,
  onTriggerCrawl,
  onOpenPasswordDialog,
}: {
  clients: Client[];
  crawlingSites: Set<string>;
  onAddClient: () => void;
  onOpenClient: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onTriggerCrawl: (siteId: string) => void;
  onOpenPasswordDialog: (client: Client) => void;
}) {
  const useCards = clients.length <= 8;
  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Clients</h2>
          <p>Manage tenants, crawler state, catalog coverage, and client panel access.</p>
        </div>
        <Button icon={Plus} type="button" onClick={onAddClient}>
          Add client
        </Button>
      </div>
      {!clients.length ? (
        <div className="card">
          <div className="empty-state">
            <Users size={48} className="empty-icon" aria-hidden="true" />
            <h3>No clients yet</h3>
            <p>Add your first client to start crawling and serving the AI widget.</p>
            <Button icon={Plus} type="button" onClick={onAddClient}>
              Add client
            </Button>
          </div>
        </div>
      ) : useCards ? (
        <div className="client-grid">
          {clients.map((client, index) => (
            <ClientCard
              key={client.site_id}
              client={client}
              crawling={crawlingSites.has(client.site_id)}
              style={{ animationDelay: `${index * 40}ms` }}
              onOpenClient={onOpenClient}
              onToggleClient={onToggleClient}
              onTriggerCrawl={onTriggerCrawl}
            />
          ))}
        </div>
      ) : (
        <Panel title="Client directory">
          <Table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Site ID</th>
                <th>Status</th>
                <th>Products</th>
                <th>Turns</th>
                <th>Tokens</th>
                <th>Crawler</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((client) => (
                <tr key={client.site_id} className="clickable-row" onClick={() => onOpenClient(client.site_id)}>
                  <td>
                    <strong>{client.name}</strong>
                    <span className="mt-1 block text-xs text-muted truncate-text" title={client.store_url}>
                      {client.store_url}
                    </span>
                  </td>
                  <td>
                    <code>{client.site_id}</code>
                  </td>
                  <td>
                    <StatusPill value={client.status} />
                  </td>
                  <td>{number(client.catalog.active_products)}</td>
                  <td>{number(client.usage.total_turns)}</td>
                  <td>{number(client.usage.tokens_estimated)}</td>
                  <td>
                    <StatusPill value={client.last_crawl_status || 'not_started'} />
                  </td>
                  <td>
                    <div className="flex gap-2" onClick={(event) => event.stopPropagation()}>
                      <CrawlButton
                        siteId={client.site_id}
                        label="Crawl"
                        active={crawlingSites.has(client.site_id)}
                        onTriggerCrawl={onTriggerCrawl}
                        compact
                      />
                      <IconButton
                        label={client.status === 'live' ? 'Disable' : 'Enable'}
                        icon={CheckCircle2}
                        onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
                      />
                      <ClientActionMenu
                        client={client}
                        onOpenClient={onOpenClient}
                        onOpenPasswordDialog={onOpenPasswordDialog}
                        onRemoveClient={onRemoveClient}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Panel>
      )}
    </div>
  );
}

function ClientCard({
  client,
  crawling,
  style,
  onOpenClient,
  onToggleClient,
  onTriggerCrawl,
}: {
  client: Client;
  crawling: boolean;
  style?: CSSProperties;
  onOpenClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onTriggerCrawl: (siteId: string) => void;
}) {
  return (
    <article className="client-card" style={style} role="button" tabIndex={0} onClick={() => onOpenClient(client.site_id)} onKeyDown={(event) => {
      if (event.key === 'Enter' || event.key === ' ') onOpenClient(client.site_id);
    }}>
      <div className="client-card-head">
        <div className="min-w-0">
          <div className="client-card-id">{client.site_id}</div>
          <div className="client-card-url" title={client.store_url}>{client.store_url}</div>
        </div>
        <StatusPill value={client.status} />
      </div>
      <div className="client-card-chips">
        <span className="badge badge-muted">{number(client.catalog.active_products)} catalog items</span>
        <StatusPill value={client.last_crawl_status || 'not_started'} />
      </div>
      <div className="grid gap-1 text-sm">
        <strong>{client.name}</strong>
        <span className="text-muted">Last crawl: {shortTime(client.last_crawl_at)}</span>
      </div>
      <div className="client-card-actions" onClick={(event) => event.stopPropagation()}>
        <Button
          variant="secondary"
          size="sm"
          type="button"
          onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
        >
          {client.status === 'live' ? 'Disable' : 'Enable'}
        </Button>
        <CrawlButton
          siteId={client.site_id}
          label="Crawl"
          active={crawling}
          onTriggerCrawl={onTriggerCrawl}
          compact
        />
        <Button variant="secondary" size="sm" type="button" icon={Eye} onClick={() => onOpenClient(client.site_id)}>
          View
        </Button>
      </div>
    </article>
  );
}

function ClientActionMenu({
  client,
  onOpenClient,
  onOpenPasswordDialog,
  onRemoveClient,
}: {
  client: Client;
  onOpenClient: (siteId: string) => void;
  onOpenPasswordDialog: (client: Client) => void;
  onRemoveClient: (siteId: string) => void;
}) {
  return (
    <ActionMenu
      items={[
        { label: 'Open client', icon: Eye, onClick: () => onOpenClient(client.site_id) },
        { label: 'Panel password', icon: KeyRound, onClick: () => onOpenPasswordDialog(client) },
        { label: 'Remove client', icon: Trash2, onClick: () => onRemoveClient(client.site_id), danger: true },
      ]}
    />
  );
}

function ActionMenu({
  items,
}: {
  items: { label: string; icon: LucideIcon; onClick: () => void; danger?: boolean }[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handle(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  return (
    <div ref={ref} className="action-menu-wrapper" role="menu">
      <button
        className="btn btn-secondary btn-icon"
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <EllipsisVertical size={16} aria-hidden="true" />
      </button>
      {open ? (
        <div className="action-menu-panel">
          {items.map(({ label, icon: Icon, onClick, danger }) => (
            <button
              key={label}
              className={`action-menu-item ${danger ? 'danger' : ''}`}
              type="button"
              onClick={() => {
                onClick();
                setOpen(false);
              }}
            >
              <Icon size={15} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ClientDetailView({
  client,
  recentActivity,
  crawlingSites,
  onCopyScript,
  onTriggerCrawl,
  onRemoveClient,
  onToggleClient,
  onUpdateTokenLimits,
  onOpenPasswordDialog,
  onViewChange,
}: {
  client: Client;
  recentActivity: UsageEvent[];
  crawlingSites: Set<string>;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onViewChange: (view: View) => void;
}) {
  const [activeTab, setActiveTab] = useState<ClientWorkspaceTab>('overview');
  const [capabilities, setCapabilities] = useState<CapabilitiesSummary | null>(null);
  const [scanReport, setScanReport] = useState<ReadinessReport | null>(null);
  const [crawlReport, setCrawlReport] = useState<CrawlReport | null>(null);
  const [catalogProducts, setCatalogProducts] = useState<CatalogProduct[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [reportError, setReportError] = useState('');
  const [scanning, setScanning] = useState(false);
  const crawling = crawlingSites.has(client.site_id);

  useEffect(() => {
    let cancelled = false;
    setReportError('');
    Promise.allSettled([
      crmApi.getCapabilities(client.site_id),
      crmApi.getScanReport(client.site_id),
      crmApi.getCrawlReport(client.site_id),
    ]).then(([capabilityResult, scanResult, crawlResult]) => {
      if (cancelled) return;
      if (capabilityResult.status === 'fulfilled') setCapabilities(capabilityResult.value);
      if (scanResult.status === 'fulfilled') setScanReport(scanResult.value.report);
      if (crawlResult.status === 'fulfilled') setCrawlReport(crawlResult.value.report);
      if ([capabilityResult, scanResult, crawlResult].some((result) => result.status === 'rejected')) {
        setReportError('Some client reports could not be loaded. Run a scan or refresh after the next crawl.');
      }
    });
    return () => {
      cancelled = true;
    };
  }, [client.site_id]);

  useEffect(() => {
    let cancelled = false;
    setCatalogLoading(true);
    setCatalogError('');
    crmApi
      .catalogProducts(client.site_id, CATALOG_PAGE_LIMIT)
      .then((products) => {
        if (!cancelled) setCatalogProducts(products);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setCatalogProducts([]);
        setCatalogError(error instanceof Error ? error.message : 'Full catalog failed to load. Showing preview data.');
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [client.site_id]);

  async function handleRunScan() {
    setScanning(true);
    try {
      const res = await crmApi.scanClient(client.site_id);
      setScanReport(res.report);
      const nextCapabilities = await crmApi.getCapabilities(client.site_id);
      setCapabilities(nextCapabilities);
      setReportError('');
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Readiness scan failed.');
    } finally {
      setScanning(false);
    }
  }

  const displayedProducts = catalogProducts.length
    ? catalogProducts.map(normalizeCatalogProduct)
    : (client.catalog_preview ?? []).map(normalizeCatalogProduct);

  return (
    <div className="client-detail">
      <section className="client-hero">
        <div>
          <span className="text-xs font-semibold uppercase text-muted">Client detail</span>
          <h2 className="mt-1 text-xl font-semibold">{client.name}</h2>
          <p className="mt-1 text-sm text-muted">{client.store_url}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusPill value={client.status} />
            <StatusPill value={client.last_crawl_status || 'not_started'} />
            <span className="client-hero-chip">{number(client.catalog.active_products)} products</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyScriptButton client={client} onCopyScript={onCopyScript} />
          <CrawlButton siteId={client.site_id} label="Crawl now" active={crawling} onTriggerCrawl={onTriggerCrawl} />
          <Button variant="secondary" icon={KeyRound} onClick={() => onOpenPasswordDialog(client)}>
            Panel password
          </Button>
          <Button variant="secondary" onClick={() => onToggleClient(client.site_id, client.status !== 'live')}>
            {client.status === 'live' ? 'Disable widget' : 'Enable widget'}
          </Button>
          <Button variant="danger" icon={Trash2} onClick={() => onRemoveClient(client.site_id)}>
            Remove
          </Button>
        </div>
      </section>
      <nav className="client-tabs" aria-label="Client detail sections">
        {CLIENT_WORKSPACE_TABS.map((tab) => (
          <ClientTabButton key={tab.id} tab={tab} active={activeTab === tab.id} onClick={() => setActiveTab(tab.id)} />
        ))}
      </nav>
      {reportError ? <NoticeBanner tone="error" message={reportError} /> : null}
      {activeTab === 'overview' ? (
        <ClientOverviewTab
          client={client}
          capabilities={capabilities}
          crawlReport={crawlReport}
          onCopyScript={onCopyScript}
          onTriggerCrawl={onTriggerCrawl}
          onRunScan={handleRunScan}
          scanning={scanning}
          crawling={crawling}
        />
      ) : null}
      {activeTab === 'readiness' ? (
        <ClientReadinessTab
          capabilities={capabilities}
          scanReport={scanReport}
          scanning={scanning}
          onRunScan={handleRunScan}
        />
      ) : null}
      {activeTab === 'catalog' ? (
        <ClientCatalogTab
          products={displayedProducts}
          loading={catalogLoading}
          error={catalogError}
          fallbackCount={client.catalog_preview?.length ?? 0}
          totalProducts={client.catalog.active_products}
          crawling={crawling}
          onTriggerCrawl={() => onTriggerCrawl(client.site_id)}
        />
      ) : null}
      {activeTab === 'crawl' ? (
        <ClientCrawlTab client={client} crawlReport={crawlReport} crawling={crawling} onTriggerCrawl={() => onTriggerCrawl(client.site_id)} />
      ) : null}
      {activeTab === 'activity' ? <ClientActivityTab client={client} recentActivity={recentActivity} /> : null}
      {activeTab === 'controls' ? (
        <ClientControlsTab
          client={client}
          scanning={scanning}
          crawling={crawling}
          onCopyScript={onCopyScript}
          onTriggerCrawl={onTriggerCrawl}
          onRunScan={handleRunScan}
          onRemoveClient={onRemoveClient}
          onToggleClient={onToggleClient}
          onUpdateTokenLimits={onUpdateTokenLimits}
          onOpenPasswordDialog={onOpenPasswordDialog}
          onViewChange={onViewChange}
        />
      ) : null}
    </div>
  );
}

function ClientTabButton({
  tab,
  active,
  onClick,
}: {
  tab: (typeof CLIENT_WORKSPACE_TABS)[number];
  active: boolean;
  onClick: () => void;
}) {
  const Icon = tab.icon;
  return (
    <button className={`client-tab-btn ${active ? 'active' : ''}`} type="button" onClick={onClick}>
      <Icon size={15} aria-hidden="true" />
      <span>{tab.label}</span>
    </button>
  );
}

function ClientOverviewTab({
  client,
  capabilities,
  crawlReport,
  scanning,
  crawling,
  onCopyScript,
  onTriggerCrawl,
  onRunScan,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  crawlReport: CrawlReport | null;
  scanning: boolean;
  crawling: boolean;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onRunScan: () => void;
}) {
  return (
    <div className="tab-content fade-in">
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <MetricCard label="Active products" value={client.catalog.active_products} detail={`${number(client.catalog.categories ?? 0)} categories`} />
        <MetricCard label="Missing vectors" value={client.catalog.missing_embeddings} detail="Needs RAG sync" />
        <MetricCard label="Voice turns" value={client.usage.total_turns} detail={`${number(client.usage.turns_today)} today`} />
        <MetricCard label="Crawl coverage" value={`${percent(crawlReport?.coverage_score ?? 0)}%`} detail={client.last_crawl_status || 'not started'} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Client identity">
          <KeyValue label="Site ID" value={client.site_id} />
          <KeyValue label="Origin" value={client.allowed_origin} />
          <KeyValue label="Deploy mode" value={client.deploy_mode} />
          <KeyValue label="Plan" value={client.plan} />
          <KeyValue label="Adapter" value={client.adapter_name} />
          <KeyValue label="Last crawl" value={shortTime(client.last_crawl_at)} />
        </Panel>
        <Panel
          title="One-line client script"
          action={
            <CopyScriptButton client={client} onCopyScript={onCopyScript} compact />
          }
        >
          <pre className="code-block install-script">{client.script_tag}</pre>
        </Panel>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Readiness at a glance">
          <CapabilitySnapshot capabilities={capabilities} />
        </Panel>
        <Panel title="Next useful checks">
          <div className="action-board">
            <ActionTile icon={ShieldCheck} title="Run a readiness scan" text="Confirm products, variants, cart, and checkout before a client demo." />
            <ActionTile icon={PackageOpen} title="Spot-check catalog" text="Review product names, images, stock, and vector state." />
            <ActionTile icon={Gauge} title="Refresh crawl data" text="Run a crawl after product or layout changes." />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" disabled={scanning} onClick={onRunScan}>
              {scanning ? 'Scanning...' : 'Run readiness'}
            </Button>
            <CrawlButton siteId={client.site_id} label="Crawl now" active={crawling} onTriggerCrawl={onTriggerCrawl} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function CapabilitySnapshot({ capabilities }: { capabilities: CapabilitiesSummary | null }) {
  const [filter, setFilter] = useState<'supported' | 'unsupported'>('supported');
  if (!capabilities) return <EmptyState text="No readiness scan is available yet." />;
  const confidence = percent(capabilities.platform_confidence);
  return (
    <div className="readiness-snapshot">
      <div>
        <span className="text-xs font-semibold uppercase text-muted">Detected platform</span>
        <strong>{capabilities.platform || 'unknown'}</strong>
        <small>{confidence}% confidence</small>
      </div>
      <Meter label="Platform confidence" value={confidence} tone="accent" />
      <div className="grid gap-3 sm:grid-cols-2">
        <button
          className={`card interactive text-left p-3 ${filter === 'supported' ? 'ring-2 ring-accent' : ''}`}
          onClick={() => setFilter('supported')}
          type="button"
        >
          <span className="text-xs text-muted">Supported checks</span>
          <strong className="mt-1 block text-xl">{capabilities.supported.length}</strong>
        </button>
        <button
          className={`card interactive text-left p-3 ${filter === 'unsupported' ? 'ring-2 ring-accent' : ''}`}
          onClick={() => setFilter('unsupported')}
          type="button"
        >
          <span className="text-xs text-muted">Needs attention</span>
          <strong className="mt-1 block text-xl">{capabilities.unsupported.length}</strong>
        </button>
      </div>
      <ActionChipGrid actions={filter === 'supported' ? capabilities.supported : capabilities.unsupported} />
    </div>
  );
}

function ActionTile({ icon: Icon, title, text }: { icon: typeof ShieldCheck; title: string; text: string }) {
  return (
    <article className="action-tile">
      <Icon size={18} aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </article>
  );
}

function ClientReadinessTab({
  capabilities,
  scanReport,
  scanning,
  onRunScan,
}: {
  capabilities: CapabilitiesSummary | null;
  scanReport: ReadinessReport | null;
  scanning: boolean;
  onRunScan: () => void;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Readiness checks</h2>
          <p className="mt-1 text-sm text-muted">Plain checks for product extraction, variants, cart, checkout, and allowed actions.</p>
        </div>
        <Button variant="secondary" disabled={scanning} icon={ShieldCheck} onClick={onRunScan}>
          {scanning ? 'Scanning...' : 'Run readiness scan'}
        </Button>
      </section>
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Platform" value={scanReport?.platform || capabilities?.platform || 'unknown'} detail={`${percent(scanReport?.platform_confidence ?? capabilities?.platform_confidence ?? 0)}% confidence`} />
        <MetricCard label="Supported checks" value={capabilities?.supported.length ?? 0} detail="Ready for AI actions" />
        <MetricCard label="Unsupported checks" value={capabilities?.unsupported.length ?? 0} detail="Needs adapter or crawl work" />
      </div>
      <Panel title="Capability report">
        {scanReport?.capabilities.length ? (
          <div className="capability-grid">
            {scanReport.capabilities.map((capability) => (
              <CapabilityReportCard key={capability.name} capability={capability} />
            ))}
          </div>
        ) : (
          <EmptyState text="Run the readiness scanner to generate a readable capability report." />
        )}
      </Panel>
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr] items-start">
        <Panel title="Supported customer actions">
          <ActionChipGrid actions={capabilities?.allowed_actions ?? []} />
        </Panel>
        <TechnicalDetails title="Advanced readiness JSON" data={scanReport} />
      </div>
    </div>
  );
}

function CapabilityReportCard({ capability }: { capability: ReadinessReport['capabilities'][number] }) {
  const Icon = capability.supported ? CheckCircle2 : capability.confidence >= 0.5 ? AlertTriangle : XCircle;
  const tone = capability.supported ? 'ok' : capability.confidence >= 0.5 ? 'warn' : 'bad';
  return (
    <article className={`capability-card capability-card-${tone}`}>
      <div className="capability-card-head">
        <Icon size={18} aria-hidden="true" />
        <StatusPill value={capability.supported ? 'supported' : 'needs work'} />
      </div>
      <h3>{labelize(capability.name)}</h3>
      <strong>{percent(capability.confidence)}% confidence</strong>
      <p>{capability.evidence || 'No scanner evidence was saved for this check.'}</p>
    </article>
  );
}

function ActionChipGrid({ actions }: { actions: string[] }) {
  if (!actions.length) return <EmptyState text="No UI actions are allowed yet." />;
  return (
    <div className="action-chip-grid">
      {actions.map((action) => (
        <span key={action} className="action-chip">
          {ACTION_LABELS[action] || labelize(action)}
        </span>
      ))}
    </div>
  );
}

function ClientCatalogTab({
  products,
  loading,
  error,
  fallbackCount,
  totalProducts,
  crawling,
  onTriggerCrawl,
}: {
  products: DisplayProduct[];
  loading: boolean;
  error: string;
  fallbackCount: number;
  totalProducts: number;
  crawling: boolean;
  onTriggerCrawl: () => void;
}) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [vectorFilter, setVectorFilter] = useState('all');
  const [page, setPage] = useState(1);
  const categories = useMemo(() => uniqueProductCategories(products), [products]);
  const visibleProducts = useMemo(
    () => filterProducts(products, query, category, vectorFilter),
    [category, products, query, vectorFilter],
  );
  const pageCount = Math.max(1, Math.ceil(visibleProducts.length / CATALOG_PAGE_SIZE));
  const pageProducts = visibleProducts.slice((page - 1) * CATALOG_PAGE_SIZE, page * CATALOG_PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [category, query, vectorFilter]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Catalog review</h2>
          <p className="mt-1 text-sm text-muted">
            Product media, price, stock, categories, and vector status in one focused view.
          </p>
        </div>
        <CrawlButton label="Crawl now" active={crawling} onTriggerCrawl={onTriggerCrawl} />
      </section>
      {error ? <NoticeBanner tone="info" message={`${error} ${fallbackCount ? `Using ${fallbackCount} preview rows.` : ''}`} /> : null}
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Loaded products" value={products.length} detail={`${number(totalProducts)} total active`} />
        <MetricCard label="Visible after filters" value={visibleProducts.length} detail={loading ? 'Refreshing catalog' : `Page ${page} of ${pageCount}`} />
        <MetricCard label="Categories" value={categories.length} detail="Detected in loaded products" />
      </div>
      <div className="catalog-toolbar">
        <label className="field catalog-search-field">
          <span>Search products</span>
          <div className="input-with-icon">
            <Search size={15} aria-hidden="true" />
            <input value={query} placeholder="Name, brand, or description" onChange={(event) => setQuery(event.currentTarget.value)} />
          </div>
        </label>
        <label className="field">
          <span>Category</span>
          <select value={category} onChange={(event) => setCategory(event.currentTarget.value)}>
            <option value="all">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Vector state</span>
          <select value={vectorFilter} onChange={(event) => setVectorFilter(event.currentTarget.value)}>
            <option value="all">All rows</option>
            <option value="vectorized">Vectorized</option>
            <option value="pending">Pending vector</option>
            <option value="in_stock">In stock</option>
            <option value="out_of_stock">Out of stock</option>
          </select>
        </label>
      </div>
      {pageProducts.length ? (
        <>
          <div className="product-gallery">
            {pageProducts.map((product) => (
              <CatalogProductCard key={product.id} product={product} />
            ))}
          </div>
          <PaginationControl page={page} pageCount={pageCount} onPageChange={setPage} />
        </>
      ) : loading ? (
        <div className="product-gallery">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkeletonCard key={index} height={320} />
          ))}
        </div>
      ) : (
        <EmptyState title="No products match" message="Adjust the search, category, or vector filters to widen this catalog view." />
      )}
    </div>
  );
}

function CatalogProductCard({ product }: { product: DisplayProduct }) {
  return (
    <article className="catalog-product-card">
      <ProductImage product={product} />
      <div className="catalog-product-body">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="text-xs font-semibold uppercase text-muted">{product.brand || product.category}</span>
            <h3>{product.name}</h3>
          </div>
          <StatusPill value={product.vectorized ? 'vectorized' : 'pending vector'} />
        </div>
        <p>{product.description || `${product.category} product indexed for AI shopping.`}</p>
        <div className="catalog-product-meta">
          <strong>{money(product.price)}</strong>
          <span>{product.stock == null ? 'Stock unknown' : `${number(product.stock)} in stock`}</span>
          {product.rating != null ? <span>{product.rating.toFixed(1)} rating</span> : null}
        </div>
      </div>
    </article>
  );
}

function PaginationControl({
  page,
  pageCount,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="pagination-control">
      <Button variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        Previous
      </Button>
      <span>
        Page {page} of {pageCount}
      </span>
      <Button variant="secondary" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
        Next
      </Button>
    </div>
  );
}

function ProductImage({ product }: { product: DisplayProduct }) {
  const [failed, setFailed] = useState(false);
  if (!product.imageUrl || failed) {
    return (
      <div className="catalog-product-fallback">
        <PackageOpen size={28} aria-hidden="true" />
        <span>{product.category || 'Product'}</span>
      </div>
    );
  }
  return <img className="catalog-product-image" src={product.imageUrl} alt={product.name} loading="lazy" onError={() => setFailed(true)} />;
}

function ClientCrawlTab({
  client,
  crawlReport,
  crawling,
  onTriggerCrawl,
}: {
  client: Client;
  crawlReport: CrawlReport | null;
  crawling: boolean;
  onTriggerCrawl: () => void;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Crawl history</h2>
          <p className="mt-1 text-sm text-muted">Coverage, failures, blocked pages, and recent sync runs.</p>
        </div>
        <CrawlButton label="Start crawl" active={crawling} onTriggerCrawl={onTriggerCrawl} />
      </section>
      <CrawlReportSummary report={crawlReport} />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Priority crawl details">
          {crawlReport ? (
            <div className="grid gap-4">
              <Meter label="Coverage score" value={percent(crawlReport.coverage_score)} tone="accent" />
              <div className="grid gap-3 sm:grid-cols-3">
                <MiniMetric label="Visited pages" value={crawlReport.pages_visited} />
                <MiniMetric label="Failed pages" value={crawlReport.pages_failed} />
                <MiniMetric label="Blocked pages" value={crawlReport.pages_blocked} />
              </div>
              <UrlList title="Failed URLs" urls={crawlReport.failed_urls} />
              <UrlList title="Blocked URLs" urls={crawlReport.blocked_urls} />
              <TechnicalDetails title="Advanced crawl JSON" data={crawlReport} />
            </div>
          ) : (
            <EmptyState text="No crawl report is saved yet. Run a crawl to generate one." />
          )}
        </Panel>
        <Panel title="Sync run history">
          <SyncRunTimeline runs={client.sync_runs ?? []} />
        </Panel>
      </div>
    </div>
  );
}

function CrawlReportSummary({ report }: { report: CrawlReport | null }) {
  if (!report) return <EmptyState text="Crawl report will appear here after the next priority crawl." />;
  return (
    <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-5">
      <MetricCard label="Products found" value={report.product_count} detail="Extracted catalog rows" />
      <MetricCard label="Variants found" value={report.variant_count} detail="Product options" />
      <MetricCard label="Categories found" value={report.category_count} detail="Navigation coverage" />
      <MetricCard label="Duration" value={`${number(report.duration_ms)} ms`} detail={shortTime(report.created_at)} />
      <MetricCard label="Stopped by limit" value={report.stopped_by_limit ? 'Yes' : 'No'} detail={report.source_type || 'crawler'} />
    </div>
  );
}

function SyncRunTimeline({ runs }: { runs: SyncRun[] }) {
  if (!runs.length) return <EmptyState text="No sync runs are recorded yet." />;
  return (
    <div className="sync-timeline">
      {runs.map((run) => (
        <article key={`${run.id}-${run.created_at}`} className="sync-run-card">
          <div className="sync-run-dot" />
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <strong>{run.source_name || 'catalog sync'}</strong>
              <span className="text-xs text-muted">{shortTime(run.created_at)}</span>
            </div>
            <div className="sync-run-metrics">
              <span>{number(run.source_count)} sourced</span>
              <span>{number(run.changed_count)} changed</span>
              <span>{number(run.vectorized_count)} vectorized</span>
              <span>{number(run.deactivated_count)} inactive</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function UrlList({ title, urls }: { title: string; urls: string[] }) {
  const [open, setOpen] = useState(false);
  if (!urls.length) return null;
  return (
    <div className="url-list">
      <button className="summary-toggle" type="button" onClick={() => setOpen((current) => !current)}>
        <ChevronDown className={open ? 'open' : ''} size={16} aria-hidden="true" />
        <span>{title} ({urls.length})</span>
      </button>
      {open ? (
        <div className="grid gap-2 pt-3">
        {urls.slice(0, 12).map((url) => (
          <code key={url}>{url}</code>
        ))}
        </div>
      ) : null}
    </div>
  );
}

function ClientActivityTab({ client, recentActivity }: { client: Client; recentActivity: UsageEvent[] }) {
  const tokenLimit = client.quota.client.limit || client.token_limit || 0;
  const tokenUsed = client.quota.client.used || client.usage.tokens_estimated || 0;
  const tokenRemaining = client.quota.client.remaining || Math.max(0, tokenLimit - tokenUsed);
  const tokenPct = tokenLimit ? Math.round((tokenUsed / tokenLimit) * 100) : 0;

  return (
    <div className="tab-content fade-in">
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Total turns" value={client.usage.total_turns} detail="All time" />
        <MetricCard label="Turns today" value={client.usage.turns_today} detail="Since midnight" />
        <MetricCard label="Avg latency" value={`${number(client.usage.avg_latency_ms)} ms`} detail="Voice response" />
      </div>
      <div className="activity-insight-grid">
        <Panel title="Recent customer activity">
          <ActivityList items={recentActivity} />
          {recentActivity.length > 0 && recentActivity.length < 5 ? (
            <div className="activity-nudge">
              More activity will appear as your AI widget receives traffic.
            </div>
          ) : null}
        </Panel>
        <section className="card token-burn-card">
          <div className="card-header">
            <div>
              <h3>Token burn</h3>
              <span className="card-meta">Client quota pressure</span>
            </div>
            <span className="badge badge-blue">{number(tokenPct)}%</span>
          </div>
          <div className="token-burn-meter">
            <span style={{ width: `${Math.max(3, Math.min(100, tokenPct))}%` }} />
          </div>
          <div className="token-burn-stats">
            <KeyValue label="Used" value={`${number(tokenUsed)} tokens`} />
            <KeyValue label="Remaining" value={`${number(tokenRemaining)} tokens`} />
            <KeyValue label="Session cap" value={`${number(client.session_token_limit ?? 0)} tokens`} />
          </div>
        </section>
      </div>
    </div>
  );
}

function ClientControlsTab({
  client,
  scanning,
  crawling,
  onCopyScript,
  onTriggerCrawl,
  onRunScan,
  onRemoveClient,
  onToggleClient,
  onUpdateTokenLimits,
  onOpenPasswordDialog,
  onViewChange,
}: {
  client: Client;
  scanning: boolean;
  crawling: boolean;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onRunScan: () => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onViewChange: (view: View) => void;
}) {
  return (
    <div className="tab-content fade-in">
      <div className="control-card-grid">
        <Panel title="Operator controls">
          <div className="control-grid">
            <CopyScriptButton client={client} onCopyScript={onCopyScript} />
            <CrawlButton siteId={client.site_id} label="Run crawler" active={crawling} onTriggerCrawl={onTriggerCrawl} />
            <Button variant="secondary" icon={ClipboardCheck} disabled={scanning} onClick={onRunScan}>
              {scanning ? 'Scanning...' : 'Run readiness'}
            </Button>
            <Button variant="secondary" icon={Settings} onClick={() => onViewChange('settings')}>
              Global settings
            </Button>
            <Button variant="secondary" icon={Eye} onClick={() => onToggleClient(client.site_id, client.status !== 'live')}>
              {client.status === 'live' ? 'Disable widget' : 'Enable widget'}
            </Button>
          </div>
        </Panel>
        <div className="card">
          <div className="card-header">
            <h3>Client Panel</h3>
            <span className="card-meta">Client-facing</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 14px' }}>
            Direct your client to their analytics panel. They log in with their site ID and the panel password you set.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <a
              href={`/client-panel/${client.site_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
            >
              <Eye size={14} aria-hidden="true" /> Open client panel
            </a>
            <button className="btn btn-ghost" type="button" onClick={() => onOpenPasswordDialog(client)}>
              <KeyRound size={14} aria-hidden="true" /> Manage password
            </button>
          </div>
        </div>
      </div>
      <div className="control-card-grid">
        <TokenLimitsPanel client={client} onUpdateTokenLimits={onUpdateTokenLimits} />
        <Panel title="Runtime limits and install">
          <KeyValue label="Client token limit" value={client.token_limit} />
          <KeyValue label="Session token limit" value={client.session_token_limit} />
          <KeyValue label="Panel password" value={panelPasswordLabel(client)} />
          <KeyValue label="Widget status" value={client.status} />
          <KeyValue label="Crawler status" value={client.last_crawl_status || 'not_started'} />
          <pre className="code-block install-script mt-4">{client.script_tag}</pre>
        </Panel>
      </div>
      <section className="card danger-zone">
        <div className="card-header">
          <h3>Danger zone</h3>
          <span className="card-meta">Destructive actions</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="danger" icon={Trash2} onClick={() => onRemoveClient(client.site_id)}>
            Remove client
          </Button>
          <Button variant="danger" icon={KeyRound} onClick={() => onOpenPasswordDialog(client)}>
            Manage password revoke
          </Button>
        </div>
      </section>
    </div>
  );
}

function TokenLimitsPanel({
  client,
  onUpdateTokenLimits,
}: {
  client: Client;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
}) {
  const [tokenLimit, setTokenLimit] = useState(String(client.token_limit ?? client.quota.client.limit ?? 5000));
  const [sessionTokenLimit, setSessionTokenLimit] = useState(
    String(client.session_token_limit ?? client.quota.session.limit ?? 1000),
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    setTokenLimit(String(client.token_limit ?? client.quota.client.limit ?? 5000));
    setSessionTokenLimit(String(client.session_token_limit ?? client.quota.session.limit ?? 1000));
    setMessage('');
  }, [client.site_id, client.token_limit, client.session_token_limit, client.quota.client.limit, client.quota.session.limit]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextTokenLimit = Number(tokenLimit);
    const nextSessionTokenLimit = Number(sessionTokenLimit);
    if (!Number.isInteger(nextTokenLimit) || nextTokenLimit < 1) {
      setMessage('Client token limit must be a positive whole number.');
      return;
    }
    if (!Number.isInteger(nextSessionTokenLimit) || nextSessionTokenLimit < 1) {
      setMessage('Session token limit must be a positive whole number.');
      return;
    }
    if (nextSessionTokenLimit > nextTokenLimit) {
      setMessage('Session token limit cannot be greater than the client token limit.');
      return;
    }

    setSaving(true);
    setMessage('');
    try {
      await onUpdateTokenLimits(client.site_id, nextTokenLimit, nextSessionTokenLimit);
      setMessage('Saved.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Token limit update failed.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Panel title="Token limits">
      <form className="grid gap-3" onSubmit={submit}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field
            label="Client total token limit"
            type="number"
            min={1}
            step={1}
            value={tokenLimit}
            onChange={(event) => setTokenLimit(event.currentTarget.value)}
            onBlur={() => setTokenLimit(normalizePositiveInteger(tokenLimit))}
          />
          <Field
            label="Per shopper/session limit"
            type="number"
            min={1}
            step={1}
            value={sessionTokenLimit}
            onChange={(event) => setSessionTokenLimit(event.currentTarget.value)}
            onBlur={() => setSessionTokenLimit(normalizePositiveInteger(sessionTokenLimit))}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-3 py-2">
          <div className="flex flex-col gap-1 border-b border-line pb-2 sm:border-0 sm:pb-0">
            <span className="text-xs text-muted">Used</span>
            <strong className="text-lg text-ink">{client.quota.client.used}</strong>
          </div>
          <div className="flex flex-col gap-1 border-b border-line pb-2 sm:border-0 sm:pb-0">
            <span className="text-xs text-muted">Remaining</span>
            <strong className="text-lg text-ink">{client.quota.client.remaining}</strong>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted">Session remaining</span>
            <strong className="text-lg text-ink">{client.quota.session.remaining}</strong>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save token limits'}
          </Button>
          {message ? <span className="text-sm text-muted">{message}</span> : null}
        </div>
      </form>
    </Panel>
  );
}

function NoticeBanner({ tone, message }: { tone: SettingNoticeTone; message: string }) {
  return (
    <div className={`notice-banner notice-banner-${tone}`}>
      {tone === 'success' ? <CheckCircle2 size={17} aria-hidden="true" /> : null}
      {tone === 'error' ? <AlertTriangle size={17} aria-hidden="true" /> : null}
      {tone === 'info' ? <FileText size={17} aria-hidden="true" /> : null}
      <span>{message}</span>
    </div>
  );
}

function TechnicalDetails({ title, data }: { title: string; data: unknown }) {
  const [open, setOpen] = useState(false);
  if (!data) return <EmptyState text="No technical report is available yet." />;
  return (
    <div className="technical-details">
      <button className="summary-toggle" type="button" onClick={() => setOpen((current) => !current)}>
        <ChevronDown className={open ? 'open' : ''} size={16} aria-hidden="true" />
        <Code2 size={16} aria-hidden="true" />
        <span>{title}</span>
      </button>
      {open ? <pre className="code-block technical-json">{JSON.stringify(data, null, 2)}</pre> : null}
    </div>
  );
}

function normalizeCatalogProduct(product: CatalogProduct | ProductPreview, index: number): DisplayProduct {
  const productId = 'product_id' in product ? product.product_id : undefined;
  const id = String(product.id ?? productId ?? `product-${index}`);
  const category = firstText(product.category_name, product.category, 'Uncategorized');
  return {
    id,
    name: firstText(product.name, `Product ${index + 1}`),
    brand: firstText(product.brand, ''),
    category,
    description: 'description' in product ? firstText(product.description, '') : '',
    price: Number(product.price ?? 0),
    stock: typeof product.stock === 'number' ? product.stock : null,
    imageUrl: firstText(product.image_url, ''),
    vectorized: 'has_embedding' in product ? Boolean(product.has_embedding) : true,
    rating: 'rating' in product && typeof product.rating === 'number' ? product.rating : null,
    reviewCount: 'review_count' in product && typeof product.review_count === 'number' ? product.review_count : null,
  };
}

function uniqueProductCategories(products: DisplayProduct[]) {
  return Array.from(new Set(products.map((product) => product.category).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right),
  );
}

function filterProducts(products: DisplayProduct[], query: string, category: string, vectorFilter: string) {
  const search = query.trim().toLowerCase();
  return products.filter((product) => {
    const matchesSearch =
      !search ||
      [product.name, product.brand, product.category, product.description].some((value) =>
        value.toLowerCase().includes(search),
      );
    const matchesCategory = category === 'all' || product.category === category;
    const matchesVector =
      vectorFilter === 'all' ||
      (vectorFilter === 'vectorized' && product.vectorized) ||
      (vectorFilter === 'pending' && !product.vectorized) ||
      (vectorFilter === 'in_stock' && (product.stock ?? 0) > 0) ||
      (vectorFilter === 'out_of_stock' && product.stock === 0);
    return matchesSearch && matchesCategory && matchesVector;
  });
}

function firstText(...values: Array<string | number | null | undefined>) {
  for (const value of values) {
    const text = String(value ?? '').trim();
    if (text) return text;
  }
  return '';
}

function CatalogsView({
  clients,
  crawlingSites,
  onOpenClient,
  onTriggerCrawl,
}: {
  clients: Client[];
  crawlingSites: Set<string>;
  onOpenClient: (siteId: string) => void;
  onTriggerCrawl: (siteId: string) => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {clients.map((client) => (
        <Panel key={client.site_id} title={client.name}>
          <div className="grid gap-3 sm:grid-cols-3">
            <MiniMetric label="Products" value={client.catalog.active_products} />
            <MiniMetric label="Categories" value={client.catalog.categories ?? 0} />
            <MiniMetric label="Missing vectors" value={client.catalog.missing_embeddings} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => onOpenClient(client.site_id)}>
              Open detail
            </Button>
            <CrawlButton
              siteId={client.site_id}
              label="Crawl now"
              active={crawlingSites.has(client.site_id)}
              onTriggerCrawl={onTriggerCrawl}
            />
          </div>
        </Panel>
      ))}
    </div>
  );
}

function UsageView({ clients, recentActivity }: { clients: Client[]; recentActivity: UsageEvent[] }) {
  const totals = clients.reduce(
    (acc, client) => ({
      turns: acc.turns + client.usage.total_turns,
      today: acc.today + client.usage.turns_today,
      tokens: acc.tokens + client.usage.tokens_estimated,
      remaining: acc.remaining + client.quota.client.remaining,
    }),
    { turns: 0, today: 0, tokens: 0, remaining: 0 },
  );
  return (
    <div className="usage-page fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Usage</h2>
          <p className="mt-1 text-sm text-muted">Quota pressure, voice turns, and recent assistant events across clients.</p>
        </div>
        <span className="badge badge-muted">{number(recentActivity.length)} recent events</span>
      </section>
      <div className="usage-kpi-grid">
        <KpiCard label="Total turns" value={totals.turns} icon={MessageSquare} tone="accent" />
        <KpiCard label="Turns today" value={totals.today} icon={Activity} tone="green" />
        <KpiCard label="Tokens used" value={totals.tokens} icon={Database} tone="blue" />
        <KpiCard label="Tokens left" value={totals.remaining} icon={Gauge} tone="amber" />
      </div>
      <section className="card usage-timeline-card">
        <div className="card-header">
          <div>
            <h2>Recent usage timeline</h2>
            <span className="card-meta">Latest voice turns and policy signals</span>
          </div>
        </div>
        <UsageTimeline items={recentActivity} />
      </section>
    </div>
  );
}

function UsageTimeline({ items }: { items: UsageEvent[] }) {
  if (!items.length) {
    return <EmptyState title="No usage events yet" message="Usage events will appear here after shoppers start talking to the assistant." />;
  }

  return (
    <div className="usage-timeline">
      {items.slice(0, 24).map((item, index) => {
        const tokenTotal = Number(item.input_tokens || 0) + Number(item.output_tokens || 0);
        return (
          <article key={`${item.created_at}-${item.session_id}-${index}`} className="usage-event-row">
            <span className="usage-event-dot" aria-hidden="true" />
            <div className="usage-event-main">
              <div className="usage-event-head">
                <strong>{item.site_id}</strong>
                <StatusPill value={item.status || 'ok'} />
              </div>
              <p>{item.transcript || item.response_text || 'Assistant turn recorded.'}</p>
              <div className="usage-event-meta">
                <span>{shortTime(item.created_at)}</span>
                <span>{item.intent || 'turn'}</span>
                <span>{number(tokenTotal)} tokens</span>
                <span>{number(item.latency_ms)} ms</span>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function ConversationsView({
  conversations,
  range,
  onRangeChange,
}: {
  conversations: ConversationsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const sessions = useMemo(
    () =>
      (conversations?.groups ?? []).flatMap((group) =>
        group.sessions.map((session) => ({
          ...session,
          date: group.date,
        })),
      ),
    [conversations],
  );
  const filteredSessions = useMemo(() => {
    const search = query.trim().toLowerCase();
    if (!search) return sessions;
    return sessions.filter((session) => {
      const haystack = [
        session.site_id,
        session.session_id,
        session.date,
        ...session.turns.flatMap((turn) => [turn.intent, turn.transcript, turn.response_text]),
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(search);
    });
  }, [query, sessions]);
  const pageCount = Math.max(1, Math.ceil(filteredSessions.length / 20));
  const pageSessions = filteredSessions.slice((page - 1) * 20, page * 20);

  useEffect(() => {
    setPage(1);
  }, [query, range]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Conversations</h2>
          <p className="mt-1 text-sm text-muted">Search and inspect shopper sessions for the selected range.</p>
        </div>
        <RangeControl value={range} onChange={onRangeChange} />
      </section>
      <div className="convo-toolbar card">
        <label className="field" style={{ minWidth: 280, flex: '1 1 320px' }}>
          <span>Search conversations</span>
          <input value={query} placeholder="Site, session, transcript, response, or intent" onChange={(event) => setQuery(event.currentTarget.value)} />
        </label>
        <span className="badge badge-muted">{number(filteredSessions.length)} sessions</span>
      </div>
      {!pageSessions.length ? (
        <EmptyState title="No conversations logged" message="Try a wider range or wait for new shopper sessions to arrive." />
      ) : (
        <div className="grid gap-4">
          {pageSessions.map((session) => (
            <CrmConversationCard key={`${session.site_id}-${session.session_id}`} session={session} />
          ))}
          <PaginationControl page={page} pageCount={pageCount} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}

function CrmConversationCard({
  session,
}: {
  session: ConversationsResponse['groups'][number]['sessions'][number] & { date: string };
}) {
  const [open, setOpen] = useState(false);
  const turns = open ? session.turns : session.turns.slice(0, 1);
  return (
    <article className="convo-card">
      <button className="convo-header" type="button" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <div className="convo-header-copy">
          <div className="convo-title-row">
            <strong>{session.site_id}</strong>
            <code>{session.session_id}</code>
          </div>
          <span>
            {session.date} · {number(session.turn_count)} turns · {number(session.tokens_used)} tokens
          </span>
        </div>
        <span className={`convo-expand-btn ${open ? 'open' : ''}`} aria-hidden="true">
          <ChevronDown size={16} />
        </span>
      </button>
      <div className="convo-turns">
        {turns.map((turn) => (
          <div key={`${turn.created_at}-${turn.transcript}`} className="grid gap-3">
            <div className="turn-user">
              <span className="turn-avatar">U</span>
              <div className="turn-body">
                <p>{turn.transcript || '-'}</p>
                <div className="turn-meta">
                  <span>{shortTime(turn.created_at)}</span>
                  <span>{turn.transport}</span>
                  <StatusPill value={turn.status || 'ok'} />
                </div>
              </div>
            </div>
            <div className="turn-ai">
              <span className="turn-avatar">AI</span>
              <div className="turn-body">
                <p>{turn.response_text || '-'}</p>
                <div className="turn-meta">
                  <span>{turn.intent || 'unknown'}</span>
                  <span>{number(turn.tokens)} tokens</span>
                  <span>{number(turn.latency_ms)} ms</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        {session.turns.length > 1 ? (
          <Button variant="ghost" size="sm" type="button" onClick={() => setOpen((current) => !current)}>
            {open ? 'Show less' : `Show ${session.turns.length - 1} more turns`}
          </Button>
        ) : null}
      </div>
    </article>
  );
}

function AnalyticsView({
  analytics,
  range,
  onRangeChange,
  onGenerateSummary,
}: {
  analytics: AnalyticsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
  onGenerateSummary: () => void;
}) {
  const [activeTab, setActiveTab] = useState<'overview' | 'quality' | 'details'>('overview');

  if (!analytics) return <AnalyticsSkeleton />;

  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Analytics</h2>
          <p className="mt-1 text-sm text-muted">
            Demand, voice performance, product signals, and service quality for {rangeLabel(range)}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <RangeControl value={range} onChange={onRangeChange} />
          <Button variant="secondary" onClick={onGenerateSummary}>
            Generate AI summary
          </Button>
        </div>
      </section>

      <nav className="client-tabs" aria-label="Analytics sections">
        <button className={`client-tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')} type="button">
          <Activity size={15} aria-hidden="true" />
          <span>Overview</span>
        </button>
        <button className={`client-tab-btn ${activeTab === 'quality' ? 'active' : ''}`} onClick={() => setActiveTab('quality')} type="button">
          <Gauge size={15} aria-hidden="true" />
          <span>Quality & Health</span>
        </button>
        <button className={`client-tab-btn ${activeTab === 'details' ? 'active' : ''}`} onClick={() => setActiveTab('details')} type="button">
          <BarChart3 size={15} aria-hidden="true" />
          <span>Details</span>
        </button>
      </nav>

      {activeTab === 'overview' && (
        <div className="tab-content fade-in">
          <AnalyticsMetricGrid analytics={analytics} range={range} />
          <div className="grid gap-4 2xl:grid-cols-[1.35fr_0.65fr]">
            <AnalyticsTrendChart rows={analytics.series} peakDay={analytics.peak_day} />
            <OperationsPanel analytics={analytics} />
          </div>
          <SummaryCard text={analytics.summary} source={analytics.summary_source} />
        </div>
      )}

      {activeTab === 'quality' && (
        <div className="tab-content fade-in">
          <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
            <Panel title="Transport and response health">
              <div className="grid gap-4 md:grid-cols-3">
                <DistributionRows title="Transport" rows={analytics.transport_mix ?? []} />
                <DistributionRows title="Status" rows={analytics.status_mix ?? []} />
                <DistributionRows title="Latency" rows={analytics.latency_buckets ?? []} />
              </div>
            </Panel>
            <RecentActivityPanel items={analytics.recent_events ?? []} />
          </div>
        </div>
      )}

      {activeTab === 'details' && (
        <div className="tab-content fade-in">
          <div className="grid gap-4 xl:grid-cols-3">
            <RankPanel title="Catalog-backed demand" rows={analytics.top_products} />
            <RankPanel title="Intent mix" rows={analytics.top_intents} />
            <RankPanel title="Client/site mix" rows={analytics.site_mix ?? []} />
          </div>
        </div>
      )}
    </div>
  );
}

function AnalyticsMetricGrid({ analytics, range }: { analytics: AnalyticsResponse; range: string }) {
  const metrics = analytics.metrics;
  return (
    <div className="analytics-kpi-grid">
      <KpiCard label="Voice turns" value={metrics.turns} icon={MessageSquare} tone="accent" />
      <KpiCard label="Sessions" value={metrics.sessions ?? 0} icon={Users} tone="blue" />
      <KpiCard label="Tokens" value={metrics.tokens} icon={Database} tone="green" />
      <KpiCard label="Actions" value={metrics.actions ?? 0} icon={Activity} tone="amber" />
      <KpiCard label="Error rate" value={`${number(metrics.error_rate ?? 0)}%`} icon={AlertTriangle} tone="amber" />
      <KpiCard label="Avg latency" value={`${number(metrics.avg_latency_ms)} ms`} icon={Gauge} tone="blue" />
    </div>
  );
}

function AnalyticsTrendChart({ rows, peakDay }: { rows: SeriesRow[]; peakDay?: SeriesRow | null }) {
  const visibleRows = rows.slice(-14);
  const maxTurns = Math.max(...visibleRows.map((row) => row.turns), 1);
  const maxTokens = Math.max(...visibleRows.map((row) => row.tokens), 1);
  return (
    <Panel
      title="Voice demand trend"
      action={<span className="text-xs text-muted">Peak {peakDay ? `${peakDay.date} / ${number(peakDay.turns)} turns` : '-'}</span>}
    >
      {visibleRows.length ? (
        <div className="analytics-trend">
          {visibleRows.map((row) => (
            <div key={row.date} className="trend-column" title={`${row.date}: ${number(row.turns)} turns, ${number(row.tokens)} tokens`}>
              <span className="trend-tooltip">
                {row.date}: {number(row.turns)} turns, {number(row.tokens)} tokens
              </span>
              <span className="trend-token" style={{ bottom: `${Math.max(8, (row.tokens / maxTokens) * 88)}%` }} />
              <span className="trend-bar" style={{ height: `${Math.max(8, (row.turns / maxTurns) * 100)}%` }} />
              <small>{row.date.slice(5)}</small>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="No trend data yet." />
      )}
    </Panel>
  );
}

function OperationsPanel({ analytics }: { analytics: AnalyticsResponse }) {
  const actionRate = analytics.metrics.action_rate ?? 0;
  const errorRate = analytics.metrics.error_rate ?? 0;
  return (
    <Panel title="Operations">
      <div className="grid gap-4">
        <Meter label="Action completion" value={actionRate} tone="accent" />
        <Meter label="Error pressure" value={errorRate} tone="danger" />
        <KeyValue label="Tokens / turn" value={number(analytics.metrics.tokens_per_turn ?? 0)} />
        <KeyValue label="Generated" value={shortTime(analytics.generated_at)} />
        <DistributionRows title="Latency bands" rows={analytics.latency_buckets ?? []} />
      </div>
    </Panel>
  );
}

function Meter({ label, value, tone }: { label: string; value: number; tone: 'accent' | 'danger' }) {
  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-muted">{label}</span>
        <strong>{number(value)}%</strong>
      </div>
      <div className={`meter meter-${tone}`}>
        <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function DistributionRows({ title, rows }: { title: string; rows: RankRow[] }) {
  const max = Math.max(...rows.map((row) => row.count), 1);
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold uppercase text-muted">{title}</h3>
      {rows.length ? (
        rows.map((row) => (
          <div key={`${title}-${row.label}`} className="flex items-center gap-3 text-xs">
            <span className="flex-[1] min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-ink">{row.label}</span>
            <div className="flex-[1.5] h-[8px] rounded-full bg-soft overflow-hidden">
              <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${Math.max(2, (row.count / max) * 100)}%` }} />
            </div>
            <b className="w-[42px] text-right text-[11px] text-muted">{number(row.count)}</b>
          </div>
        ))
      ) : (
        <EmptyState text="No data." />
      )}
    </div>
  );
}

function AdaptersView({ clients, onOpenClient }: { clients: Client[]; onOpenClient: (siteId: string) => void }) {
  if (!clients.length) {
    return <EmptyState title="No adapters yet" message="Add a client before configuring storefront adapters." />;
  }

  return (
    <div className="adapter-grid fade-in">
      {clients.map((client) => {
        const configured = Boolean(client.adapter_name && client.adapter_name !== '-');
        return (
          <article key={client.site_id} className="card adapter-card interactive">
            <div className="adapter-card-top">
              <div>
                <span className="adapter-eyebrow">{client.deploy_mode || 'storefront'}</span>
                <h2>{client.name}</h2>
              </div>
              <StatusPill value={client.status} />
            </div>
            <div className="adapter-detail-list">
              <KeyValue label="Adapter" value={configured ? client.adapter_name : 'Not configured'} />
              <KeyValue label="Origin" value={client.allowed_origin || client.store_url || '-'} />
              <KeyValue label="Products" value={number(client.catalog.active_products)} />
            </div>
            {!configured ? (
              <div className="adapter-empty-note">
                <strong>No adapter configured</strong>
                <span>Open the client workspace to finish adapter setup.</span>
              </div>
            ) : null}
            <div className="adapter-actions">
              <Button variant="secondary" size="sm" type="button" onClick={() => onOpenClient(client.site_id)}>
                Test connection
              </Button>
              <Button
                variant="ghost"
                size="sm"
                type="button"
                icon={ExternalLink}
                onClick={() => window.open(client.store_url, '_blank', 'noopener,noreferrer')}
              >
                Open store
              </Button>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function SettingsView({
  settings,
  onSave,
}: {
  settings: SettingsResponse | null;
  onSave: (values: Record<string, string>) => Promise<SettingsResponse>;
}) {
  const [notice, setNotice] = useState<SettingNotice | null>(null);
  const [saving, setSaving] = useState(false);
  const [pendingChanges, setPendingChanges] = useState(false);
  const byKey = useMemo(() => new Map((settings?.settings ?? []).map((setting) => [setting.key, setting])), [settings]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const values: Record<string, string> = {};
    formData.forEach((value, key) => {
      const text = String(value).trim();
      const setting = byKey.get(key);
      if (setting?.is_secret && !text) return;
      values[key] = text;
    });
    const validationError = validateSettings(values);
    if (validationError) {
      setNotice({ tone: 'error', message: validationError });
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      const response = await onSave(values);
      setNotice({
        tone: 'success',
        message: response.restart_required
          ? 'Settings saved. Restart AI Hub to apply runtime model changes.'
          : 'Settings saved.',
      });
      setPendingChanges(false);
    } catch (error) {
      setNotice({
        tone: 'error',
        message:
          error instanceof Error
            ? `${error.message} Refresh settings before retrying; some deployment files may already have changed.`
            : 'Settings save failed. Refresh settings before retrying.',
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="settings-grid" onSubmit={submit} onChange={() => setPendingChanges(true)}>
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Settings</h2>
          <p className="mt-1 text-sm text-muted">Changes are saved to .env and require a hub restart.</p>
        </div>
        <Button type="submit" disabled={saving || !pendingChanges}>
          {saving ? 'Saving...' : 'Save settings'}
        </Button>
      </section>
      {pendingChanges ? (
        <div className="pending-banner">
          <span>You have unsaved changes.</span>
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      ) : null}
      {notice ? <NoticeBanner tone={notice.tone} message={notice.message} /> : null}
      <div className="settings-grid">
        {SETTING_GROUPS.map((group) => (
          <div key={group.title} className="settings-section">
            <div className="sticky-section-header">
              <h3>{group.title}</h3>
              <span>{number(group.keys.length)} settings</span>
            </div>
            <section className="card settings-group">
              <div className="settings-fields">
                {group.keys.map((key) => {
                  const setting = byKey.get(key);
                  return setting ? <SettingField key={key} setting={setting} /> : null;
                })}
              </div>
            </section>
          </div>
        ))}
      </div>
    </form>
  );
}

function HealthView({ health, clients }: { health: HealthSnapshot; clients: Client[] }) {
  const products = clients.reduce((sum, client) => sum + client.catalog.active_products, 0);
  const liveClients = clients.filter((client) => client.status === 'live').length;
  return (
    <div className="grid gap-4">
      <Panel title="System health">
        <div className="health-grid">
          {Object.entries(health).map(([key, value]) => {
            const state = healthState(value);
            return (
              <article key={key} className={`health-item ${state}`}>
                <span className="health-item-label">{labelize(key)}</span>
                <span className="health-item-status">
                  <StatusPill value={value || 'unknown'} />
                </span>
              </article>
            );
          })}
        </div>
      </Panel>
      <div className="health-summary-grid">
        <section className="card health-summary-card">
          <span className="kpi-label">Last checked</span>
          <strong className="kpi-value">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
          <p className="text-sm text-muted">Use the topbar refresh control to run a fresh health and client snapshot.</p>
        </section>
        <section className="card health-summary-card">
          <span className="kpi-label">Live clients</span>
          <strong className="kpi-value">{number(liveClients)}</strong>
          <p className="text-sm text-muted">{number(clients.length)} total tenant schemas are configured.</p>
        </section>
        <section className="card health-summary-card">
          <span className="kpi-label">Catalog coverage</span>
          <strong className="kpi-value">{number(products)}</strong>
          <p className="text-sm text-muted">Active products available to retrieval and shopping actions.</p>
        </section>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Database">
        <KeyValue label="Tenant schemas" value={clients.length} />
        <KeyValue label="Products" value={products} />
        <KeyValue label="Vector store" value="pgvector" />
      </Panel>
      <Panel title="Crawler">
        <KeyValue label="Startup crawl" value="enabled by deployment config" />
        <KeyValue label="Periodic crawl" value="120 seconds" />
        <KeyValue label="Manual trigger" value="available per client" />
      </Panel>
      </div>
    </div>
  );
}

function AddClientDialog({
  open,
  busy,
  onClose,
  onCreate,
}: {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onCreate: (payload: CreateClientPayload) => void;
}) {
  if (!open) return null;
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const payload = Object.fromEntries(formData.entries()) as unknown as CreateClientPayload;
    if (!payload.site_id) delete payload.site_id;
    onCreate(payload);
  }
  return (
    <div className="modal-backdrop">
      <form className="modal modal-wide" onSubmit={submit}>
        <div className="modal-header">
          <div>
            <div className="text-xs font-semibold text-muted">Client</div>
            <h2>Add client</h2>
          </div>
          <button className="modal-close" type="button" aria-label="Close" onClick={onClose}>
            x
          </button>
        </div>
        <Field label="Client name" name="name" placeholder="AI-KART" required />
        <Field label="Website URL" name="store_url" placeholder="https://client-store.com" required />
        <Field label="Site ID" name="site_id" placeholder="auto generated" />
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field">
            <span>Deploy mode</span>
            <select name="deploy_mode" defaultValue="public-ip">
              <option value="public-ip">public IP / path route</option>
              <option value="domain">domain</option>
              <option value="custom">custom</option>
            </select>
          </label>
          <Field label="Plan" name="plan" defaultValue="Commerce plan" />
        </div>
        <Field label="Adapter" name="adapter_name" defaultValue="generic_adapter.js" />
        <div className="modal-footer">
          <Button variant="secondary" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            Create
          </Button>
        </div>
      </form>
    </div>
  );
}

function ClientPanelPasswordDialog({
  client,
  busy,
  onClose,
  onUpdatePassword,
  onRevokePassword,
}: {
  client: Client | null;
  busy: boolean;
  onClose: () => void;
  onUpdatePassword: (siteId: string, password: string, autoGenerate: boolean) => Promise<string>;
  onRevokePassword: (siteId: string) => Promise<void>;
}) {
  const [password, setPassword] = useState('');
  const [generatedPassword, setGeneratedPassword] = useState('');
  const [message, setMessage] = useState('');
  const [working, setWorking] = useState(false);

  useEffect(() => {
    setPassword('');
    setGeneratedPassword('');
    setMessage('');
  }, [client?.site_id]);

  if (!client) return null;
  const activeClient = client;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPassword = password.trim();
    if (nextPassword.length < 12) {
      setMessage('Password must be at least 12 characters.');
      return;
    }
    setWorking(true);
    setGeneratedPassword('');
    setMessage('');
    try {
      await onUpdatePassword(activeClient.site_id, nextPassword, false);
      setPassword('');
      setMessage('Password updated.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password update failed.');
    } finally {
      setWorking(false);
    }
  }

  async function generateAndSetPassword() {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    let nextPassword = '';
    for (let i = 0; i < 16; i++) {
      nextPassword += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setGeneratedPassword(nextPassword);
    setPassword(nextPassword);
    setWorking(true);
    try {
      await onUpdatePassword(activeClient.site_id, nextPassword, false);
      setMessage('Password generated and updated automatically.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password update failed.');
    } finally {
      setWorking(false);
    }
  }

  async function revokePassword() {
    setWorking(true);
    setGeneratedPassword('');
    setMessage('');
    try {
      await onRevokePassword(activeClient.site_id);
      setPassword('');
      setMessage('Client panel login is revoked.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password revoke failed.');
    } finally {
      setWorking(false);
    }
  }

  async function copyGeneratedPassword() {
    if (!generatedPassword) return;
    await navigator.clipboard.writeText(generatedPassword);
    setMessage('Generated password copied.');
  }

  const disabled = busy || working;
  const messageTone: SettingNoticeTone =
    message.toLowerCase().includes('failed') || message.toLowerCase().includes('must') ? 'error' : 'info';

  return (
    <div className="modal-backdrop">
      <form className="modal modal-wide" onSubmit={submit}>
        <div className="modal-header">
          <div>
            <div className="text-xs font-semibold text-muted">Client panel password</div>
            <h2>{client.name}</h2>
            <p className="mt-1 text-sm text-muted">
              {client.site_id} - {panelPasswordLabel(client)}
            </p>
          </div>
          <button className="modal-close" type="button" aria-label="Close" onClick={onClose}>
            x
          </button>
        </div>
        <Field
          label="New password"
          type="password"
          minLength={12}
          value={password}
          onChange={(event) => setPassword(event.currentTarget.value)}
          placeholder="Minimum 12 characters"
          autoComplete="new-password"
        />
        {generatedPassword ? (
          <div className="generated-password-box">
            <div>
              <span className="text-xs font-semibold uppercase text-muted">Generated password</span>
              <code>{generatedPassword}</code>
            </div>
            <Button type="button" variant="secondary" icon={Copy} onClick={copyGeneratedPassword}>
              Copy
            </Button>
          </div>
        ) : null}
        {message ? <NoticeBanner tone={messageTone} message={message} /> : null}
        <div className="modal-footer">
          <Button type="button" variant="danger" icon={Trash2} disabled={disabled} onClick={revokePassword}>
            Revoke password
          </Button>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" disabled={disabled} icon={RefreshCw} onClick={generateAndSetPassword}>
              Generate and set
            </Button>
            <Button type="submit" disabled={disabled}>
              Set password
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

function ActiveClientsPanel({
  clients,
  onOpenClient,
  onOpenClients,
}: {
  clients: Client[];
  onOpenClient: (siteId: string) => void;
  onOpenClients: () => void;
}) {
  return (
    <Panel title="Active clients" action={<Button variant="secondary" onClick={onOpenClients}>Open clients</Button>}>
      <Table compact>
        <thead>
          <tr>
            <th>Status</th>
            <th>Client</th>
            <th>Products</th>
            <th>Turns</th>
            <th>Tokens</th>
          </tr>
        </thead>
        <tbody>
          {clients.slice(0, 5).map((client) => (
            <tr key={client.site_id}>
              <td>
                <StatusPill value={client.status} />
              </td>
              <td>
                <button
                  className="link-strong"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onOpenClient(client.site_id);
                  }}
                >
                  {client.name}
                </button>
              </td>
              <td>{number(client.catalog.active_products)}</td>
              <td>{number(client.usage.total_turns)}</td>
              <td>{number(client.usage.tokens_estimated)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Panel>
  );
}

function RecentActivityPanel({ items, onClick }: { items: UsageEvent[]; onClick?: () => void }) {
  return (
    <Panel title="Recent activity" onClick={onClick}>
      <ActivityList items={items.slice(0, 6)} />
    </Panel>
  );
}

function ActivityList({ items }: { items: UsageEvent[] }) {
  if (!items.length) return <EmptyState text="No activity yet." />;
  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <div key={`${item.created_at}-${item.session_id}`} className="grid gap-1 border-b border-line pb-3 last:border-b-0 last:pb-0">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            <span>{shortTime(item.created_at)}</span>
            <StatusPill value={item.status || 'ok'} />
            <span>{number(item.latency_ms)} ms</span>
          </div>
          <strong className="text-sm">
            {item.site_id} {item.intent || 'turn'}
          </strong>
          <p className="line-clamp-2 text-sm text-muted">{item.transcript || item.response_text || '-'}</p>
        </div>
      ))}
    </div>
  );
}

function IntentPanel({ rows, onClick }: { rows: RankRow[]; onClick?: () => void }) {
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <Panel title="Intent mix" onClick={onClick}>
      <div className="grid gap-4 sm:grid-cols-[138px_minmax(0,1fr)] sm:items-center">
        <div className="donut">
          <span>
            <strong>{number(total)}</strong>
            <small>turns</small>
          </span>
        </div>
        <div className="grid gap-2">
          {rows.length ? (
            rows.slice(0, 6).map((row) => (
              <div key={row.label} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 text-sm">
                <span className="truncate">{row.label}</span>
                <strong>{number(row.count)}</strong>
              </div>
            ))
          ) : (
            <EmptyState text="No intent data yet." />
          )}
        </div>
      </div>
    </Panel>
  );
}

function RankPanel({ title, rows, onClick }: { title: string; rows: RankRow[]; onClick?: () => void }) {
  const max = Math.max(...rows.map((row) => row.count), 1);
  return (
    <Panel title={title} onClick={onClick}>
      {rows.length ? (
        <div className="grid gap-3">
          {rows.slice(0, 8).map((row) => (
            <div key={row.label} className="grid gap-1.5">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate">{row.label}</span>
                <strong>{number(row.count)}</strong>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-soft">
                <span className="block h-full rounded-full bg-accent" style={{ width: `${Math.max(8, (row.count / max) * 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="No rows yet." />
      )}
    </Panel>
  );
}

function SummaryCard({ text, source }: { text: string; source?: string }) {
  const items = text
    .split(/\r?\n/)
    .map((line) => line.replace(/^[-*]\s+/, '').trim())
    .filter(Boolean);
  return (
    <div className="rounded-lg border border-line bg-soft p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">CRM summary</h3>
        {source ? <span className="text-xs text-muted">{source}</span> : null}
      </div>
      <ul className="grid gap-2">
        {items.map((item) => (
          <li key={item} className="rounded-md border-l-2 border-accent bg-panel px-3 py-2 text-sm">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function validateSettings(values: Record<string, string>) {
  const temperature = values.LLM_TEMPERATURE;
  if (temperature && !isNumberInRange(temperature, 0, 2)) {
    return 'LLM temperature must be a number between 0 and 2. Example: 0.3';
  }
  for (const [key, label] of Object.entries(NUMERIC_SETTING_LABELS)) {
    if (key === 'LLM_TEMPERATURE') continue;
    const value = values[key];
    if (value && !Number.isFinite(Number(value))) return `${label} must be numeric.`;
  }
  return '';
}

function isNumberInRange(value: string, min: number, max: number) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue >= min && numberValue <= max;
}

function SettingField({ setting }: { setting: Setting }) {
  const placeholder = setting.is_secret && setting.configured ? setting.value : 'Not configured';
  const source = setting.source || (setting.configured ? 'env' : 'empty');
  return (
    <label className="field">
      <span className="flex items-center justify-between gap-3">
        <span>{setting.key}</span>
        <small className={`setting-source setting-source-${source.replace(/\s+/g, '-')}`}>{source}</small>
      </span>
      <input
        name={setting.key}
        type={setting.is_secret ? 'password' : 'text'}
        defaultValue={setting.is_secret ? '' : setting.value || ''}
        placeholder={placeholder}
      />
    </label>
  );
}

function Field(props: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, ...inputProps } = props;
  return (
    <label className="field">
      <span>{label}</span>
      <input {...inputProps} />
    </label>
  );
}

function MetricCard({
  label,
  value,
  detail,
  onClick,
}: {
  label: string;
  value: string | number;
  detail: string;
  onClick?: () => void;
}) {
  const content = (
    <>
      <span className="text-xs font-semibold text-muted">{label}</span>
      <strong className="mt-2 block truncate text-2xl font-semibold">{typeof value === 'number' ? number(value) : value}</strong>
      <small className="mt-1 block text-xs text-muted">{detail}</small>
    </>
  );
  if (onClick) {
    return (
      <button className="card interactive text-left" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <div className="card">{content}</div>;
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-line bg-soft p-3">
      <span className="text-xs text-muted">{label}</span>
      <strong className="mt-1 block text-xl">{number(value)}</strong>
    </div>
  );
}

function Panel({
  title,
  action,
  children,
  onClick,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  onClick?: () => void;
}) {
  const content = (
    <>
      <div className="card-header">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </>
  );
  if (onClick) {
    return (
      <button className="card interactive text-left" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <section className="card">{content}</section>;
}

function Table({ children, compact = false }: { children: ReactNode; compact?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className={compact ? 'table-compact' : ''}>{children}</table>
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}

function Dialogue({ label, text }: { label: string; text: string }) {
  return (
    <div className="mt-3 grid gap-1 sm:grid-cols-[56px_minmax(0,1fr)]">
      <span className="text-xs font-semibold text-muted">{label}</span>
      <p className="text-sm">{text || '-'}</p>
    </div>
  );
}

function RangeControl({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid grid-cols-[auto_160px] items-center gap-2 text-xs font-semibold text-muted">
      <span>Range</span>
      <select value={value} onChange={(event) => onChange(event.currentTarget.value)}>
        {RANGE_OPTIONS.map(([optionValue, label]) => (
          <option key={optionValue} value={optionValue}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}

function CopyScriptButton({
  client,
  onCopyScript,
  compact = false,
}: {
  client: Client;
  onCopyScript: (client: Client) => Promise<void>;
  compact?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await onCopyScript(client);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Button
      variant="secondary"
      size={compact ? 'sm' : undefined}
      icon={copied ? CheckCircle2 : Copy}
      type="button"
      onClick={handleCopy}
    >
      {copied ? 'Copied!' : compact ? 'Copy' : 'Copy script'}
    </Button>
  );
}

function CrawlButton({
  siteId,
  label,
  active,
  compact = false,
  onTriggerCrawl,
}: {
  siteId?: string;
  label: string;
  active: boolean;
  compact?: boolean;
  onTriggerCrawl: (siteId: string) => void;
} | {
  siteId?: never;
  label: string;
  active: boolean;
  compact?: boolean;
  onTriggerCrawl: () => void;
}) {
  return (
    <Button
      variant="secondary"
      size={compact ? 'sm' : undefined}
      icon={active ? RefreshCw : Play}
      spinning={active}
      disabled={active}
      type="button"
      onClick={() => {
        if (siteId) {
          (onTriggerCrawl as (nextSiteId: string) => void)(siteId);
        } else {
          (onTriggerCrawl as () => void)();
        }
      }}
    >
      {active ? 'Crawling...' : label}
    </Button>
  );
}

function Button({
  children,
  icon: Icon,
  variant = 'primary',
  size,
  spinning = false,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: LucideIcon;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'lg';
  spinning?: boolean;
}) {
  const sizeClass = size ? ` btn-${size}` : '';
  return (
    <button className={`btn btn-${variant}${sizeClass}${className ? ` ${className}` : ''}`} {...props}>
      {Icon ? <Icon className={spinning ? 'spin' : ''} size={15} aria-hidden="true" /> : null}
      <span>{children}</span>
    </button>
  );
}

function IconButton({
  label,
  icon: Icon,
  tone = 'default',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  icon?: LucideIcon;
  tone?: 'default' | 'danger';
}) {
  return (
    <button
      className={`btn ${tone === 'danger' ? 'btn-danger' : 'btn-secondary'} btn-icon`}
      type="button"
      title={label}
      aria-label={label}
      {...props}
    >
      {Icon ? <Icon size={16} aria-hidden="true" /> : <span>x</span>}
    </button>
  );
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill ${statusClass(value)}`}>{value || 'unknown'}</span>;
}

function EmptyState({
  text,
  title,
  message,
  action,
  icon: Icon = PackageOpen,
}: {
  text?: string;
  title?: string;
  message?: string;
  action?: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon-wrap">
        <Icon size={30} aria-hidden="true" />
      </div>
      <h3>{title || text || 'Nothing here yet'}</h3>
      {message ? <p>{message}</p> : text && title ? <p>{text}</p> : null}
      {action}
    </div>
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

function AnalyticsSkeleton() {
  return (
    <div className="grid gap-4">
      <SkeletonCard height={76} />
      <div className="analytics-kpi-grid">
        {Array.from({ length: 6 }).map((_, index) => (
          <SkeletonCard key={index} height={116} />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <SkeletonCard height={360} />
        <SkeletonCard height={360} />
      </div>
    </div>
  );
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function normalizePositiveInteger(value: string) {
  const normalized = Math.max(1, Math.round(Number(value)));
  return String(Number.isFinite(normalized) ? normalized : 1);
}

function healthState(value?: string) {
  const text = String(value || '').toLowerCase();
  if (text === 'up' || text === 'ready' || text === 'ok') return 'up';
  if (text === 'slow' || text === 'degraded' || text === 'warn' || text === 'warning') return 'warn';
  return 'down';
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

function groupNavItems() {
  return NAV_ITEMS.reduce<Record<string, typeof NAV_ITEMS>>((groups, item) => {
    groups[item.section] = groups[item.section] || [];
    groups[item.section].push(item);
    return groups;
  }, {});
}

function rangeLabel(range: string) {
  return RANGE_OPTIONS.find(([value]) => value === range)?.[1] || 'Last 7 days';
}

function statusClass(value: string) {
  const text = String(value || '').toLowerCase();
  if (['live', 'ok', 'up', 'ready', 'vectorized', 'hub running', 'supported'].includes(text)) return 'ok';
  if (['crawling', 'running', 'slow', 'pending vector', 'needs work'].includes(text)) return 'warn';
  if (['disabled', 'offline', 'down', 'error', 'hub degraded', 'failed'].includes(text)) return 'bad';
  return 'neutral';
}

function panelPasswordLabel(client: Client) {
  const status = String(client.panel_password_status || '').toLowerCase();
  if (status === 'revoked') return 'revoked';
  if (client.panel_password_configured || status === 'configured') return 'configured';
  return 'not configured';
}

function fmt(n: number | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (n == null) return '-';
  return new Intl.NumberFormat('en-US', opts).format(n);
}

function number(value: unknown) {
  return fmt(Number(value || 0));
}

function percent(value: unknown) {
  const numericValue = Number(value || 0);
  const normalizedValue = numericValue <= 1 ? numericValue * CONFIDENCE_PERCENT : numericValue;
  return Math.round(Math.max(0, Math.min(CONFIDENCE_PERCENT, normalizedValue)));
}

function money(value: unknown) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function shortTime(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 19);
  return date.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
}

function labelize(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}
