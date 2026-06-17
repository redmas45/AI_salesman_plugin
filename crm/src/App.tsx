import { useEffect, useMemo, useState } from 'react';
import type { ButtonHTMLAttributes, FormEvent, InputHTMLAttributes, ReactNode } from 'react';
import {
  Activity,
  BarChart3,
  CheckCircle2,
  Copy,
  Database,
  HeartPulse,
  LayoutDashboard,
  MessageSquare,
  Moon,
  Play,
  Plug,
  Plus,
  RefreshCw,
  Settings,
  Sun,
  Trash2,
  Users,
} from 'lucide-react';
import { crmApi } from './api';
import type {
  AnalyticsResponse,
  Client,
  ConversationsResponse,
  CreateClientPayload,
  HealthSnapshot,
  Overview,
  ProductPreview,
  RankRow,
  SeriesRow,
  Setting,
  SettingsResponse,
  Theme,
  UsageEvent,
  View,
} from './types';

const THEME_STORAGE_KEY = 'aiHubCrmTheme';
const DEFAULT_VIEW: View = 'dashboard';
const DEFAULT_RANGE = '7d';

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

const SETTING_GROUPS = [
  {
    title: 'Speech-to-text',
    keys: ['STT_PROVIDER', 'STT_MODEL', 'GROQ_STT_MODEL'],
  },
  {
    title: 'Text-to-speech',
    keys: ['TTS_PROVIDER', 'TTS_MODEL', 'TTS_VOICE', 'GROQ_TTS_MODEL', 'GROQ_TTS_VOICE'],
  },
  {
    title: 'LLM',
    keys: ['OPENAI_API_KEY', 'GROQ_API_KEY', 'LLM_MODEL', 'LLM_TEMPERATURE', 'LLM_MAX_TOKENS'],
  },
  {
    title: 'Deployment',
    keys: [
      'DATABASE_URL',
      'PUBLIC_API_URL',
      'PUBLIC_STOREFRONT_ORIGIN',
      'VOICE_ORB_API_URL',
      'DEPLOYMENT_MODE',
      'HOST',
      'PORT',
      'STOREFRONT_PORT',
      'BACKEND_PORT',
      'HTTPS_PORT',
    ],
  },
  {
    title: 'Crawler',
    keys: ['CRAWL_MAX_PAGES', 'CRAWL_MAX_DEPTH', 'CRAWL_ON_STARTUP', 'CRAWL_PERIODIC_ENABLED'],
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
    setLoading(true);
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
    } catch (error) {
      showError(error, 'CRM failed to load.');
    } finally {
      setLoading(false);
    }
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

  async function saveSettings(values: Record<string, string>) {
    setBusy(true);
    try {
      setSettings(await crmApi.updateSettings(values));
      setToast('Settings saved. Restart required.');
    } catch (error) {
      showError(error, 'Settings save failed.');
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
            {loading || !overview ? (
              <EmptyState text="Loading CRM..." />
            ) : (
              <ViewRenderer
                view={view}
                overview={overview}
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
    <header className="sticky top-0 z-20 flex flex-col gap-3 border-b border-line bg-panel/92 px-4 py-3 backdrop-blur sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
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
  onSaveSettings: (values: Record<string, string>) => void;
  onGenerateSummary: () => void;
}) {
  switch (props.view) {
    case 'clients':
      return <ClientsView {...props} />;
    case 'client-detail':
      return props.selectedClient ? <ClientDetailView {...props} client={props.selectedClient} /> : <ClientsView {...props} />;
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
          <h2 className="text-base font-semibold">Store manager analytics</h2>
          <p className="mt-1 text-sm text-muted">Demand, catalog readiness, and AI operations at a glance.</p>
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
  onToggleClient,
  onTriggerCrawl,
}: {
  clients: Client[];
  onOpenClient: (siteId: string) => void;
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
  onCopyScript,
  onTriggerCrawl,
  onRemoveClient,
  onToggleClient,
}: {
  client: Client;
  onCopyScript: (client: Client) => void;
  onTriggerCrawl: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
}) {
  return (
    <>
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">{client.name}</h2>
          <p className="mt-1 text-sm text-muted">{client.store_url}</p>
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
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel title="Client details">
          <KeyValue label="Site ID" value={client.site_id} />
          <KeyValue label="Origin" value={client.allowed_origin} />
          <KeyValue label="Deploy mode" value={client.deploy_mode} />
          <KeyValue label="Plan" value={client.plan} />
          <KeyValue label="Adapter" value={client.adapter_name} />
          <KeyValue label="Crawler" value={client.last_crawl_status || 'not_started'} />
          <KeyValue label="Last crawl" value={shortTime(client.last_crawl_at)} />
        </Panel>
        <Panel title="One-line client script">
          <pre className="code-block">{client.script_tag}</pre>
        </Panel>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Catalog preview">
          <ProductPreviewGrid products={client.catalog_preview ?? []} />
        </Panel>
        <Panel title="Sync runs">
          <Table compact>
            <thead>
              <tr>
                <th>Source</th>
                <th>Changed</th>
                <th>Vectorized</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {(client.sync_runs ?? []).map((run) => (
                <tr key={`${run.id}-${run.created_at}`}>
                  <td>{run.source_name || '-'}</td>
                  <td>{number(run.changed_count)}</td>
                  <td>{number(run.vectorized_count)}</td>
                  <td>{shortTime(run.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Panel>
      </div>
    </>
  );
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
  return (
    <Panel
      title="Analytics"
      action={
        <div className="flex flex-wrap gap-2">
          <RangeControl value={range} onChange={onRangeChange} />
          <Button variant="secondary" onClick={onGenerateSummary}>
            Generate AI summary
          </Button>
        </div>
      }
    >
      {!analytics ? (
        <EmptyState text="Analytics are loading." />
      ) : (
        <div className="grid gap-4">
          <SummaryCard text={analytics.summary} source={analytics.summary_source} />
          <div className="grid gap-4 xl:grid-cols-3">
            <TrendBars rows={analytics.series} />
            <RankPanel title="Most mentioned products" rows={analytics.top_products} />
            <RankPanel title="Intent mix" rows={analytics.top_intents} />
          </div>
        </div>
      )}
    </Panel>
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
  onSave: (values: Record<string, string>) => void;
}) {
  const byKey = useMemo(() => new Map((settings?.settings ?? []).map((setting) => [setting.key, setting])), [settings]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const values: Record<string, string> = {};
    formData.forEach((value, key) => {
      const text = String(value).trim();
      const setting = byKey.get(key);
      if (setting?.is_secret && !text) return;
      values[key] = text;
    });
    onSave(values);
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Settings</h2>
          <p className="mt-1 text-sm text-muted">Changes are saved to .env and require a hub restart.</p>
        </div>
        <Button type="submit">Save settings</Button>
      </section>
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
            <select name="deploy_mode" defaultValue="intranet">
              <option value="intranet">intranet</option>
              <option value="domain">domain</option>
              <option value="public-ip">public-ip</option>
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

function TrendBars({ rows }: { rows: SeriesRow[] }) {
  const max = Math.max(...rows.map((row) => row.turns), 1);
  return (
    <Panel title="Turns by day">
      {rows.length ? (
        <div className="flex min-h-[190px] items-end gap-2">
          {rows.map((row) => (
            <div key={row.date} className="grid flex-1 grid-rows-[1fr_auto] gap-2">
              <span
                className="self-end rounded-t-md bg-info"
                title={`${row.date}: ${number(row.turns)}`}
                style={{ height: `${Math.max(8, (row.turns / max) * 150)}px` }}
              />
              <small className="truncate text-center text-[10px] text-muted">{row.date.slice(5)}</small>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="No chart data." />
      )}
    </Panel>
  );
}

function ProductPreviewGrid({ products }: { products: ProductPreview[] }) {
  if (!products.length) return <EmptyState text="No catalog rows yet." />;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {products.map((product, index) => (
        <div key={`${product.id}-${index}`} className="rounded-lg border border-line bg-soft p-3">
          <strong className="block truncate text-sm">{product.name || '-'}</strong>
          <span className="mt-1 block text-xs text-muted">{product.category || '-'}</span>
          <span className="mt-1 block text-xs text-muted">{money(product.price)}</span>
          <span className="mt-2 inline-flex">
            <StatusPill value={product.has_embedding ? 'vectorized' : 'pending vector'} />
          </span>
        </div>
      ))}
    </div>
  );
}

function SettingField({ setting }: { setting: Setting }) {
  return (
    <label className="field">
      <span>{setting.key}</span>
      <input
        name={setting.key}
        type={setting.is_secret ? 'password' : 'text'}
        defaultValue={setting.is_secret ? '' : setting.value || ''}
        placeholder={setting.is_secret && setting.configured ? setting.value : ''}
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
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  icon?: typeof RefreshCw;
}) {
  return (
    <button className="icon-button" type="button" title={label} aria-label={label} {...props}>
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
  if (['live', 'ok', 'up', 'ready', 'vectorized', 'hub running'].includes(text)) return 'ok';
  if (['crawling', 'running', 'slow', 'pending vector'].includes(text)) return 'warn';
  if (['disabled', 'offline', 'down', 'error', 'hub degraded'].includes(text)) return 'bad';
  return 'neutral';
}

function number(value: unknown) {
  return new Intl.NumberFormat().format(Number(value || 0));
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
