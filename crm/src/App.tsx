import { useEffect, useMemo, useState } from 'react';
import type { ButtonHTMLAttributes, FormEvent, InputHTMLAttributes, ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Code2,
  Copy,
  Database,
  Eye,
  FileText,
  Gauge,
  HeartPulse,
  LayoutDashboard,
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

  async function removeClient(siteId: string) {
    if (!window.confirm(`Remove ${siteId}? Tenant data is kept.`)) return;
    setBusy(true);
    try {
      await crmApi.removeClient(siteId);
      setSelectedClient(null);
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
        setSelectedClient(response.client);
      }
      setToast(enabled ? 'Client enabled.' : 'Client disabled.');
    } catch (error) {
      showError(error, 'Client status update failed.');
    } finally {
      setBusy(false);
    }
  }

  async function triggerCrawl(siteId: string) {
    setBusy(true);
    try {
      await crmApi.crawlClient(siteId);
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === siteId) {
        const response = await crmApi.client(siteId);
        setSelectedClient(response.client);
      }
      setToast('Crawler started.');
    } catch (error) {
      showError(error, 'Crawler failed to start.');
    } finally {
      setBusy(false);
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
    <div className="min-h-dvh bg-page text-ink">
      <div className="grid min-h-dvh grid-cols-1 lg:grid-cols-[248px_minmax(0,1fr)]">
        <Sidebar view={view} setView={setView} />
        <main className="min-w-0">
          <Topbar
            title={pageTitle}
            health={overview?.health ?? {}}
            theme={theme}
            busy={busy}
            onRefresh={refreshCurrentView}
            onAddClient={() => setDialogOpen(true)}
            onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          />
          <section className="grid gap-4 px-4 py-4 sm:px-6 lg:px-8">
            {authRequired ? (
              <AdminTokenView busy={loading} error={loadError} onSubmit={submitAdminToken} />
            ) : loading || (!overview && !loadError) ? (
              <EmptyState text="Loading CRM..." />
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
                onRangeChange={updateRange}
                onViewChange={setView}
                onOpenClient={openClient}
                onCopyScript={copyScript}
                onTriggerCrawl={triggerCrawl}
                onRemoveClient={removeClient}
                onToggleClient={toggleClient}
                onSaveSettings={saveSettings}
                onGenerateSummary={generateSummary}
              />
            )}
          </section>
        </main>
      </div>
      <AddClientDialog open={dialogOpen} busy={busy} onClose={() => setDialogOpen(false)} onCreate={createClient} />
      <div className={`toast ${toast ? 'toast-visible' : ''}`}>{toast}</div>
    </div>
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

function Sidebar({ view, setView }: { view: View; setView: (view: View) => void }) {
  const grouped = groupNavItems();
  return (
    <aside className="border-r border-line bg-sidebar text-sidebar">
      <button
        type="button"
        className="flex w-full items-center gap-3 border-b border-sidebar-line px-4 py-5 text-left"
        onClick={() => setView(DEFAULT_VIEW)}
      >
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/10 text-sm font-semibold">AH</span>
        <span>
          <span className="block text-sm font-semibold">AI Hub CRM</span>
          <span className="block text-xs text-sidebar-muted">crawler and AI ops</span>
        </span>
      </button>
      <nav className="grid gap-2 p-3" aria-label="CRM navigation">
        {Object.entries(grouped).map(([section, items]) => (
          <div key={section} className="grid gap-1">
            <div className="px-2 pt-3 text-[11px] font-semibold uppercase text-sidebar-muted">{section}</div>
            {items.map((item) => {
              const Icon = item.icon;
              const active = view === item.view || (view === 'client-detail' && item.view === 'clients');
              return (
                <button
                  key={item.view}
                  type="button"
                  className={`nav-button ${active ? 'nav-button-active' : ''}`}
                  onClick={() => setView(item.view)}
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

function Topbar({
  title,
  health,
  theme,
  busy,
  onRefresh,
  onAddClient,
  onToggleTheme,
}: {
  title: string;
  health: HealthSnapshot;
  theme: Theme;
  busy: boolean;
  onRefresh: () => void;
  onAddClient: () => void;
  onToggleTheme: () => void;
}) {
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  return (
    <header className="topbar-panel sticky top-0 z-20 flex flex-col gap-3 border-b border-line px-4 py-3 backdrop-blur sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
      <div>
        <div className="text-xs font-semibold text-muted">AI Hub</div>
        <h1 className="mt-0.5 text-xl font-semibold tracking-normal">{title}</h1>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill value={healthy ? 'hub running' : 'hub degraded'} />
        <IconButton
          label={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          icon={theme === 'dark' ? Sun : Moon}
          onClick={onToggleTheme}
        />
        <IconButton label="Refresh" icon={RefreshCw} onClick={onRefresh} disabled={busy} />
        <Button onClick={onAddClient} icon={Plus}>
          Add client
        </Button>
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
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onOpenClient: (siteId: string) => void;
  onCopyScript: (client: Client) => void;
  onTriggerCrawl: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
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
      return <CatalogsView clients={props.clients} onOpenClient={props.onOpenClient} onTriggerCrawl={props.onTriggerCrawl} />;
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
    <>
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Store analytics</h2>
          <p className="mt-1 text-sm text-muted">Demand, catalog readiness, and assistant health at a glance.</p>
        </div>
        <RangeControl value={range} onChange={onRangeChange} />
      </section>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total voice turns"
          value={analyticsMetrics?.turns ?? 0}
          detail={rangeLabel(range)}
          onClick={() => onViewChange('conversations')}
        />
        <MetricCard
          label="Products indexed"
          value={metrics.products_indexed}
          detail="Catalog coverage"
          onClick={() => onViewChange('catalogs')}
        />
        <MetricCard
          label="Avg pipeline latency"
          value={`${number(analyticsMetrics?.avg_latency_ms ?? 0)} ms`}
          detail={rangeLabel(range)}
          onClick={() => onViewChange('usage')}
        />
        <MetricCard
          label="Est. tokens used"
          value={analyticsMetrics?.tokens ?? 0}
          detail={rangeLabel(range)}
          onClick={() => onViewChange('usage')}
        />
      </div>
      <div className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <IntentPanel rows={analytics?.top_intents ?? []} onClick={() => onViewChange('analytics')} />
        <RankPanel title="Top products by mentions" rows={analytics?.top_products ?? []} onClick={() => onViewChange('analytics')} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <ActiveClientsPanel clients={clients} onOpenClient={onOpenClient} onOpenClients={() => onViewChange('clients')} />
        <RecentActivityPanel items={overview.recent_activity} onClick={() => onViewChange('conversations')} />
      </div>
    </>
  );
}

function ClientsView({
  clients,
  onOpenClient,
  onRemoveClient,
  onToggleClient,
  onTriggerCrawl,
}: {
  clients: Client[];
  onOpenClient: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onTriggerCrawl: (siteId: string) => void;
}) {
  return (
    <Panel title="Clients">
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
            <tr key={client.site_id}>
              <td>
                <button className="link-strong" type="button" onClick={() => onOpenClient(client.site_id)}>
                  {client.name}
                </button>
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
                <div className="flex gap-2">
                  <IconButton label="Crawl now" icon={Play} onClick={() => onTriggerCrawl(client.site_id)} />
                  <IconButton
                    label={client.status === 'live' ? 'Disable' : 'Enable'}
                    icon={CheckCircle2}
                    onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
                  />
                  <IconButton
                    label="Remove client"
                    icon={Trash2}
                    tone="danger"
                    onClick={() => onRemoveClient(client.site_id)}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Panel>
  );
}

function ClientDetailView({
  client,
  recentActivity,
  onCopyScript,
  onTriggerCrawl,
  onRemoveClient,
  onToggleClient,
  onViewChange,
}: {
  client: Client;
  recentActivity: UsageEvent[];
  onCopyScript: (client: Client) => void;
  onTriggerCrawl: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
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
          <Button variant="secondary" icon={Copy} onClick={() => onCopyScript(client)}>
            Copy script
          </Button>
          <Button variant="secondary" icon={Play} onClick={() => onTriggerCrawl(client.site_id)}>
            Crawl now
          </Button>
          <Button variant="secondary" onClick={() => onToggleClient(client.site_id, client.status !== 'live')}>
            {client.status === 'live' ? 'Disable widget' : 'Enable widget'}
          </Button>
          <Button variant="danger" icon={Trash2} onClick={() => onRemoveClient(client.site_id)}>
            Remove
          </Button>
        </div>
      </section>
      <nav className="client-tabbar" aria-label="Client detail sections">
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
          onTriggerCrawl={() => onTriggerCrawl(client.site_id)}
        />
      ) : null}
      {activeTab === 'crawl' ? (
        <ClientCrawlTab client={client} crawlReport={crawlReport} onTriggerCrawl={() => onTriggerCrawl(client.site_id)} />
      ) : null}
      {activeTab === 'activity' ? <ClientActivityTab client={client} recentActivity={recentActivity} /> : null}
      {activeTab === 'controls' ? (
        <ClientControlsTab
          client={client}
          scanning={scanning}
          onCopyScript={onCopyScript}
          onTriggerCrawl={onTriggerCrawl}
          onRunScan={handleRunScan}
          onRemoveClient={onRemoveClient}
          onToggleClient={onToggleClient}
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
    <button className={`client-tab ${active ? 'client-tab-active' : ''}`} type="button" onClick={onClick}>
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
  onCopyScript,
  onTriggerCrawl,
  onRunScan,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  crawlReport: CrawlReport | null;
  scanning: boolean;
  onCopyScript: (client: Client) => void;
  onTriggerCrawl: (siteId: string) => void;
  onRunScan: () => void;
}) {
  return (
    <div className="grid gap-4">
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
            <Button variant="secondary" icon={Copy} onClick={() => onCopyScript(client)}>
              Copy
            </Button>
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
            <Button variant="secondary" icon={Play} onClick={() => onTriggerCrawl(client.site_id)}>
              Crawl now
            </Button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function CapabilitySnapshot({ capabilities }: { capabilities: CapabilitiesSummary | null }) {
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
        <MiniMetric label="Supported checks" value={capabilities.supported.length} />
        <MiniMetric label="Needs attention" value={capabilities.unsupported.length} />
      </div>
      <ActionChipGrid actions={capabilities.allowed_actions} />
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
    <div className="grid gap-4">
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
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
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
  onTriggerCrawl,
}: {
  products: DisplayProduct[];
  loading: boolean;
  error: string;
  fallbackCount: number;
  totalProducts: number;
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
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Catalog review</h2>
          <p className="mt-1 text-sm text-muted">
            Product media, price, stock, categories, and vector status in one focused view.
          </p>
        </div>
        <Button variant="secondary" icon={Play} onClick={onTriggerCrawl}>
          Crawl now
        </Button>
      </section>
      {error ? <NoticeBanner tone="info" message={`${error} ${fallbackCount ? `Using ${fallbackCount} preview rows.` : ''}`} /> : null}
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Loaded products" value={products.length} detail={`${number(totalProducts)} total active`} />
        <MetricCard label="Visible after filters" value={visibleProducts.length} detail={loading ? 'Loading catalog...' : `Page ${page} of ${pageCount}`} />
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
      ) : (
        <EmptyState text={loading ? 'Catalog is loading.' : 'No products match the selected filters.'} />
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
  if (pageCount <= 1) return null;
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
  onTriggerCrawl,
}: {
  client: Client;
  crawlReport: CrawlReport | null;
  onTriggerCrawl: () => void;
}) {
  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Crawl history</h2>
          <p className="mt-1 text-sm text-muted">Coverage, failures, blocked pages, and recent sync runs.</p>
        </div>
        <Button variant="secondary" icon={Play} onClick={onTriggerCrawl}>
          Start crawl
        </Button>
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
  if (!urls.length) return null;
  return (
    <details className="url-list">
      <summary>{title} ({urls.length})</summary>
      <div className="grid gap-2 pt-3">
        {urls.slice(0, 12).map((url) => (
          <code key={url}>{url}</code>
        ))}
      </div>
    </details>
  );
}

function ClientActivityTab({ client, recentActivity }: { client: Client; recentActivity: UsageEvent[] }) {
  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Total turns" value={client.usage.total_turns} detail="All time" />
        <MetricCard label="Turns today" value={client.usage.turns_today} detail="Since midnight" />
        <MetricCard label="Avg latency" value={`${number(client.usage.avg_latency_ms)} ms`} detail="Voice response" />
      </div>
      <Panel title="Recent customer activity">
        <ActivityList items={recentActivity} />
      </Panel>
    </div>
  );
}

function ClientControlsTab({
  client,
  scanning,
  onCopyScript,
  onTriggerCrawl,
  onRunScan,
  onRemoveClient,
  onToggleClient,
  onViewChange,
}: {
  client: Client;
  scanning: boolean;
  onCopyScript: (client: Client) => void;
  onTriggerCrawl: (siteId: string) => void;
  onRunScan: () => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onViewChange: (view: View) => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <Panel title="Operator controls">
        <div className="control-grid">
          <Button variant="secondary" icon={Copy} onClick={() => onCopyScript(client)}>
            Copy one-line script
          </Button>
          <Button variant="secondary" icon={Play} onClick={() => onTriggerCrawl(client.site_id)}>
            Run crawler
          </Button>
          <Button variant="secondary" icon={ClipboardCheck} disabled={scanning} onClick={onRunScan}>
            {scanning ? 'Scanning...' : 'Run readiness'}
          </Button>
          <Button variant="secondary" icon={Settings} onClick={() => onViewChange('settings')}>
            Global settings
          </Button>
          <Button variant="secondary" icon={Eye} onClick={() => onToggleClient(client.site_id, client.status !== 'live')}>
            {client.status === 'live' ? 'Disable widget' : 'Enable widget'}
          </Button>
          <Button variant="danger" icon={Trash2} onClick={() => onRemoveClient(client.site_id)}>
            Remove client
          </Button>
        </div>
      </Panel>
      <Panel title="Runtime limits and install">
        <KeyValue label="Client token limit" value={client.token_limit} />
        <KeyValue label="Session token limit" value={client.session_token_limit} />
        <KeyValue label="Widget status" value={client.status} />
        <KeyValue label="Crawler status" value={client.last_crawl_status || 'not_started'} />
        <pre className="code-block install-script mt-4">{client.script_tag}</pre>
      </Panel>
    </div>
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
  if (!data) return <EmptyState text="No technical report is available yet." />;
  return (
    <details className="technical-details">
      <summary>
        <Code2 size={16} aria-hidden="true" />
        <span>{title}</span>
      </summary>
      <pre className="code-block technical-json">{JSON.stringify(data, null, 2)}</pre>
    </details>
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
  onOpenClient,
  onTriggerCrawl,
}: {
  clients: Client[];
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
            <Button variant="secondary" icon={Play} onClick={() => onTriggerCrawl(client.site_id)}>
              Crawl now
            </Button>
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
    <>
      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Total turns" value={totals.turns} detail="All clients" />
        <MetricCard label="Turns today" value={totals.today} detail="Since midnight" />
        <MetricCard label="Tokens used" value={totals.tokens} detail="Estimated" />
        <MetricCard label="Tokens remaining" value={totals.remaining} detail="Configured quotas" />
      </div>
      <Panel title="Recent usage">
        <ActivityList items={recentActivity} />
      </Panel>
    </>
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
  return (
    <Panel title="Conversations" action={<RangeControl value={range} onChange={onRangeChange} />}>
      {!conversations?.groups.length ? (
        <EmptyState text="No conversations logged for this range." />
      ) : (
        <div className="grid gap-4">
          {conversations.groups.map((group) => (
            <section key={group.date} className="grid gap-3">
              <h3 className="text-xs font-semibold uppercase text-muted">{group.date}</h3>
              {group.sessions.map((session) => (
                <article key={`${session.site_id}-${session.session_id}`} className="rounded-lg border border-line bg-soft p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                    <div>
                      <strong>{session.site_id}</strong>
                      <code className="ml-2">{session.session_id}</code>
                    </div>
                    <span className="text-xs text-muted">
                      {number(session.turn_count)} turns / {number(session.tokens_used)} tokens
                    </span>
                  </div>
                  <div className="mt-3 grid gap-3">
                    {session.turns.map((turn) => (
                      <div key={`${turn.created_at}-${turn.transcript}`} className="rounded-lg border border-line bg-panel p-3">
                        <div className="flex flex-wrap gap-2 text-xs text-muted">
                          <span>{shortTime(turn.created_at)}</span>
                          <span>{turn.transport}</span>
                          <StatusPill value={turn.status || 'ok'} />
                          <span>{number(turn.tokens)} tokens</span>
                          <span>{number(turn.latency_ms)} ms</span>
                        </div>
                        <Dialogue label="User" text={turn.transcript} />
                        <Dialogue label="AI" text={turn.response_text} />
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </section>
          ))}
        </div>
      )}
    </Panel>
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
  if (!analytics) return <EmptyState text="Analytics are loading." />;

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
      <AnalyticsMetricGrid analytics={analytics} range={range} />
      <div className="grid gap-4 2xl:grid-cols-[1.35fr_0.65fr]">
        <AnalyticsTrendChart rows={analytics.series} peakDay={analytics.peak_day} />
        <OperationsPanel analytics={analytics} />
      </div>
      <SummaryCard text={analytics.summary} source={analytics.summary_source} />
      <div className="grid gap-4 xl:grid-cols-3">
        <RankPanel title="Catalog-backed demand" rows={analytics.top_products} />
        <RankPanel title="Intent mix" rows={analytics.top_intents} />
        <RankPanel title="Client/site mix" rows={analytics.site_mix ?? []} />
      </div>
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
  );
}

function AnalyticsMetricGrid({ analytics, range }: { analytics: AnalyticsResponse; range: string }) {
  const metrics = analytics.metrics;
  return (
    <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-6">
      <MetricCard label="Voice turns" value={metrics.turns} detail={rangeLabel(range)} />
      <MetricCard label="Sessions" value={metrics.sessions} detail="Unique shoppers" />
      <MetricCard label="Tokens" value={metrics.tokens} detail={`${number(metrics.tokens_per_turn ?? 0)} per turn`} />
      <MetricCard label="Actions" value={metrics.actions ?? 0} detail={`${number(metrics.action_rate ?? 0)}% action rate`} />
      <MetricCard label="Error rate" value={`${number(metrics.error_rate ?? 0)}%`} detail="Non-ok turns" />
      <MetricCard label="Avg latency" value={`${number(metrics.avg_latency_ms)} ms`} detail="Pipeline speed" />
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
          <div key={`${title}-${row.label}`} className="distribution-row">
            <span>{row.label}</span>
            <div>
              <i style={{ width: `${Math.max(7, (row.count / max) * 100)}%` }} />
            </div>
            <b>{number(row.count)}</b>
          </div>
        ))
      ) : (
        <EmptyState text="No data." />
      )}
    </div>
  );
}

function AdaptersView({ clients, onOpenClient }: { clients: Client[]; onOpenClient: (siteId: string) => void }) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {clients.map((client) => (
        <button key={client.site_id} className="panel text-left" type="button" onClick={() => onOpenClient(client.site_id)}>
          <strong className="block">{client.name}</strong>
          <span className="mt-2 block text-sm text-muted">{client.adapter_name}</span>
          <span className="mt-1 block text-sm text-muted">{client.allowed_origin}</span>
          <span className="mt-3 inline-flex">
            <StatusPill value={client.status} />
          </span>
        </button>
      ))}
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
    <form className="grid gap-4" onSubmit={submit}>
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Settings</h2>
          <p className="mt-1 text-sm text-muted">Changes are saved to .env and require a hub restart.</p>
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Save settings'}
        </Button>
      </section>
      {notice ? <NoticeBanner tone={notice.tone} message={notice.message} /> : null}
      <div className="grid gap-4 xl:grid-cols-2">
        {SETTING_GROUPS.map((group) => (
          <Panel key={group.title} title={group.title}>
            <div className="grid gap-3">
              {group.keys.map((key) => {
                const setting = byKey.get(key);
                return setting ? <SettingField key={key} setting={setting} /> : null;
              })}
            </div>
          </Panel>
        ))}
      </div>
    </form>
  );
}

function HealthView({ health, clients }: { health: HealthSnapshot; clients: Client[] }) {
  const products = clients.reduce((sum, client) => sum + client.catalog.active_products, 0);
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Panel title="System health">
        {Object.entries(health).map(([key, value]) => (
          <KeyValue key={key} label={labelize(key)} value={value || '-'} />
        ))}
      </Panel>
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
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/45 p-4">
      <form className="grid w-full max-w-xl gap-4 rounded-lg border border-line bg-panel p-5 shadow-xl" onSubmit={submit}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-xs font-semibold text-muted">Client</div>
            <h2 className="mt-1 text-lg font-semibold">Add client</h2>
          </div>
          <IconButton label="Close" onClick={onClose} />
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
        <div className="flex justify-end gap-2">
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
      <button className="panel text-left transition hover:border-accent" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <div className="panel">{content}</div>;
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
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </>
  );
  if (onClick) {
    return (
      <button className="panel text-left transition hover:border-accent" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <section className="panel">{content}</section>;
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

function Button({
  children,
  icon: Icon,
  variant = 'primary',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: typeof Plus;
  variant?: 'primary' | 'secondary' | 'danger';
}) {
  return (
    <button className={`button button-${variant}`} {...props}>
      {Icon ? <Icon size={15} aria-hidden="true" /> : null}
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
  icon?: typeof RefreshCw;
  tone?: 'default' | 'danger';
}) {
  return (
    <button className={`icon-button icon-button-${tone}`} type="button" title={label} aria-label={label} {...props}>
      {Icon ? <Icon size={16} aria-hidden="true" /> : <span>x</span>}
    </button>
  );
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill ${statusClass(value)}`}>{value || 'unknown'}</span>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-lg border border-dashed border-line bg-soft px-4 py-8 text-center text-sm text-muted">{text}</div>;
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

function number(value: unknown) {
  return new Intl.NumberFormat().format(Number(value || 0));
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
