import {
  CheckCircle2,
  Database,
  MessageSquare,
  Users,
  ArrowRight,
  Wifi,
  WifiOff,
  ExternalLink,
  Gauge,
  PackageOpen,
  AlertTriangle,
  ChevronDown,
  Info,
  Settings,
  WalletCards,
  type LucideIcon,
} from 'lucide-react';
import type { View, Overview, Client, AnalyticsResponse, HealthSnapshot, UsageEvent, ClientBoardSection } from '../types';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusPill } from '../components/ui/Badge';
import { ActivityList } from '../components/shared/ActivityList';
import { number, healthState, labelize } from '../utils/format';
import { rangeLabel } from '../utils/range';
import { RangeControl } from '../components/shared/RangeControl';
import { getCrmVertical } from '../verticals/registry';

export interface DashboardViewProps {
  overview: Overview;
  clients: Client[];
  analytics: AnalyticsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onOpenSettings?: (focusKey?: string) => void;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onOpenClient: (siteId: string) => void;
}

export function DashboardView({
  overview,
  clients,
  analytics,
  range,
  onRangeChange,
  onViewChange,
  onOpenSettings,
  onOpenClientBoardSection,
  onOpenClient,
}: DashboardViewProps) {
  const metrics = overview.metrics;
  const currentClientRows = clients.filter((client) => client.status !== 'available');
  const availableRows = clients.filter((client) => client.status === 'available');
  const currentClients = currentClientRows.length;
  const availableClients = availableRows.length;
  const onlineAvailable = availableRows.filter((client) => runtimeStatus(client) === 'online').length;
  const offlineAvailable = availableClients - onlineAvailable;
  const missingVectorClients = currentClientRows.filter((client) => client.catalog.missing_embeddings > 0).length;
  const degradedHealth = Object.values(overview.health).filter((value) => healthState(value) !== 'up').length;
  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Operations home</h2>
          <p className="mt-1 text-sm text-muted">Client state, live installs, data quality, and service health with direct drilldowns.</p>
        </div>
        <RangeControl value={range} onChange={onRangeChange} />
      </section>
      <DashboardOperationsBrief
        providerUsage={overview.provider_usage}
        currentClients={currentClients}
        availableClients={availableClients}
        onlineAvailable={onlineAvailable}
        offlineAvailable={offlineAvailable}
        missingVectorClients={missingVectorClients}
        degradedHealth={degradedHealth}
        turnsToday={metrics.voice_turns_today ?? 0}
        onOpenClientBoardSection={onOpenClientBoardSection}
        onViewChange={onViewChange}
        onOpenSettings={onOpenSettings}
      />
      <div className="dashboard-bento fade-in">
        <KpiCard className="bento-kpi" label="Current clients" value={currentClients} icon={Users} tone="accent" onClick={() => onOpenClientBoardSection('current')} />
        <KpiCard className="bento-kpi" label="Available installs" value={availableClients} icon={ArrowRight} tone="blue" onClick={() => onOpenClientBoardSection('available')} />
        <KpiCard className="bento-kpi" label="Turns today" value={metrics.voice_turns_today ?? 0} icon={MessageSquare} tone="green" onClick={() => onViewChange('conversations')} />
        <KpiCard className="bento-kpi" label="Knowledge items" value={metrics.products_indexed ?? 0} icon={Database} tone="amber" onClick={() => onViewChange('catalogs')} />

        <div className="bento-wide card">
          <ProviderUsagePanel
            providerUsage={overview.provider_usage}
            onOpenUsage={() => onViewChange('usage')}
            onOpenSettings={onOpenSettings}
          />
        </div>
        <div className="bento-wide card">
          <DashboardTrendChart analytics={analytics} range={range} onOpenAnalytics={() => onViewChange('analytics')} />
        </div>
        <div className="bento-narrow card">
          <ClientRegistryPanel clients={clients} onOpenClient={onOpenClient} onOpenSection={onOpenClientBoardSection} />
        </div>

        <div className="bento-half card">
          <RecentActivityFeed items={overview.recent_activity.slice(0, 30)} onOpen={() => onViewChange('conversations')} />
        </div>
        <div className="bento-half card">
          <HealthStatusPanel health={overview.health} onOpenHealth={() => onViewChange('health')} />
        </div>
      </div>
    </div>
  );
}

function DashboardOperationsBrief({
  providerUsage,
  currentClients,
  availableClients,
  onlineAvailable,
  offlineAvailable,
  missingVectorClients,
  degradedHealth,
  turnsToday,
  onOpenClientBoardSection,
  onViewChange,
  onOpenSettings,
}: {
  providerUsage: Overview['provider_usage'];
  currentClients: number;
  availableClients: number;
  onlineAvailable: number;
  offlineAvailable: number;
  missingVectorClients: number;
  degradedHealth: number;
  turnsToday: number;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onViewChange: (view: View) => void;
  onOpenSettings?: (focusKey?: string) => void;
}) {
  const providerBlocked = providerUsage?.status === 'quota_exhausted' || providerUsage?.status === 'not_configured';
  const attentionCount = onlineAvailable + offlineAvailable + missingVectorClients + degradedHealth + (providerBlocked ? 1 : 0);
  return (
    <section className="dashboard-ops-console fade-in" aria-label="Operations center">
      <div className="dashboard-ops-top">
        <button className="dashboard-ops-primary" type="button" onClick={() => onOpenClientBoardSection('all')}>
          <span>Operating state</span>
          <strong>{attentionCount ? `${number(attentionCount)} item${attentionCount === 1 ? '' : 's'} need review` : 'No obvious blockers'}</strong>
          <small>
            {number(currentClients)} current clients, {number(availableClients)} available installs, {number(turnsToday)} turns today.
          </small>
          <em>Open client board</em>
        </button>
        {providerBlocked ? (
          <ProviderCompactAlert
            providerUsage={providerUsage}
            onOpenUsage={() => onViewChange('usage')}
            onOpenSettings={onOpenSettings}
          />
        ) : (
          <button className="dashboard-provider-ok" type="button" onClick={() => onViewChange('usage')}>
            <CheckCircle2 size={18} aria-hidden="true" />
            <span>AI provider</span>
            <strong>Runtime ready</strong>
            <small>Open usage and provider monitoring</small>
          </button>
        )}
      </div>
      <div className="dashboard-attention-grid" aria-label="Attention queue">
        <DashboardAttentionCard
          icon={Wifi}
          label="Online installs"
          value={onlineAvailable}
          detail="Reachable installs waiting for approval"
          tone="ok"
          action="Review online"
          onClick={() => onOpenClientBoardSection('online')}
        />
        <DashboardAttentionCard
          icon={WifiOff}
          label="Offline installs"
          value={offlineAvailable}
          detail="Detected before, unreachable right now"
          tone={offlineAvailable ? 'warn' : 'idle'}
          action="Open offline"
          onClick={() => onOpenClientBoardSection('offline')}
        />
        <DashboardAttentionCard
          icon={PackageOpen}
          label="Vector gaps"
          value={missingVectorClients}
          detail="Current clients with missing knowledge vectors"
          tone={missingVectorClients ? 'warn' : 'idle'}
          action="Open data"
          onClick={() => onViewChange('catalogs')}
        />
        <DashboardAttentionCard
          icon={Gauge}
          label="Health issues"
          value={degradedHealth}
          detail="Runtime checks not currently healthy"
          tone={degradedHealth ? 'bad' : 'idle'}
          action="Open health"
          onClick={() => onViewChange('health')}
        />
      </div>
    </section>
  );
}

function ProviderCompactAlert({
  providerUsage,
  onOpenUsage,
  onOpenSettings,
}: {
  providerUsage: Overview['provider_usage'];
  onOpenUsage: () => void;
  onOpenSettings?: (focusKey?: string) => void;
}) {
  const latest = providerUsage?.recent_events?.[0];
  const title = providerUsage?.status === 'quota_exhausted' ? 'OpenAI quota exhausted' : 'OpenAI key not configured';
  const detail = latest?.message || 'Maya cannot process new AI turns until provider access is restored.';
  const settingsKey = providerUsage?.status === 'not_configured' ? 'OPENAI_API_KEY' : 'OPENAI_MONTHLY_BUDGET_USD';
  return (
    <details className="dashboard-provider-alert" role="alert">
      <summary>
        <AlertTriangle size={18} aria-hidden="true" />
        <span>
          <strong>{title}</strong>
          <small>Customer AI turns are paused. Technical detail is collapsed.</small>
        </span>
        <ChevronDown size={16} aria-hidden="true" />
      </summary>
      <div className="dashboard-provider-alert-body">
        <p>{shortProviderMessage(detail)}</p>
        <div className="dashboard-provider-alert-actions">
          <button type="button" onClick={onOpenUsage}>Open usage</button>
          <button type="button" onClick={() => onOpenSettings?.(settingsKey)}>Configure</button>
        </div>
      </div>
    </details>
  );
}

function ProviderUsagePanel({
  providerUsage,
  onOpenUsage,
  onOpenSettings,
}: {
  providerUsage: Overview['provider_usage'];
  onOpenUsage: () => void;
  onOpenSettings?: (focusKey?: string) => void;
}) {
  if (!providerUsage) {
    return <EmptyState title="Provider usage unavailable" message="Refresh CRM to load AI provider monitoring." />;
  }

  const statusTone = providerUsage.status === 'quota_exhausted' || providerUsage.status === 'not_configured'
    ? 'bad'
    : providerUsage.status === 'usage_unavailable'
      ? 'warn'
      : 'ok';
  const budget = providerUsage.budget;
  const cost = providerUsage.openai_costs;
  const latest = providerUsage.recent_events?.[0];

  return (
    <section className="provider-usage-panel">
      <div className="provider-usage-head">
        <div>
          <span className="kpi-label">AI provider usage</span>
          <h3>OpenAI runtime monitor</h3>
        </div>
        <StatusPill value={providerStatusLabel(providerUsage.status)} />
      </div>
      <div className="provider-usage-grid">
        <ProviderMetric label="Model" value={providerUsage.llm_model || '-'} />
        <ProviderMetric label="Local tokens" value={number(providerUsage.local_tokens.estimated_total)} />
        <ProviderMetric label="Month spend" value={formatUsd(cost.month_to_date_usd)} />
        <ProviderMetric
          label="Budget left"
          value={budget.configured ? formatUsd(budget.remaining_budget_usd) : 'Set budget'}
          onClick={() => onOpenSettings?.('OPENAI_MONTHLY_BUDGET_USD')}
        />
      </div>
      <div className={`provider-usage-state ${statusTone}`}>
        <WalletCards size={18} />
        <div>
          <strong>{providerStatusMessage(providerUsage)}</strong>
          <span>{providerStatusDetail(providerUsage)}</span>
        </div>
      </div>
      <details className="crm-disclosure provider-usage-details">
        <summary>
          <Info size={15} aria-hidden="true" />
          <span>Data source and latest provider event</span>
          <ChevronDown size={15} aria-hidden="true" />
        </summary>
        <div className="provider-data-source">
          <div>
            <strong>Local tokens</strong>
            <span>CRM usage events recorded after widget turns.</span>
          </div>
          <div>
            <strong>Provider status</strong>
            <span>LLM provider events recorded by the runtime.</span>
          </div>
          <div>
            <strong>Month spend</strong>
            <span>{providerUsage.openai_admin_key_configured ? 'OpenAI cost reporting is enabled.' : 'Needs OPENAI_ADMIN_KEY to read OpenAI cost reporting.'}</span>
          </div>
          {latest ? <code>{shortProviderMessage(latest.message)}</code> : null}
        </div>
      </details>
      <div className="provider-usage-footer">
        <span>
          {providerUsage.openai_admin_key_configured
            ? `Cost API: ${cost.status}`
            : 'Set OPENAI_ADMIN_KEY for OpenAI cost API reporting.'}
        </span>
        <div className="provider-usage-actions">
          <button type="button" onClick={() => onOpenSettings?.('OPENAI_ADMIN_KEY')}>
            <Settings size={14} aria-hidden="true" />
            Configure
          </button>
          <button type="button" onClick={onOpenUsage}>Open usage</button>
        </div>
      </div>
    </section>
  );
}

function ProviderMetric({ label, value, onClick }: { label: string; value: string | number; onClick?: () => void }) {
  const content = (
    <>
      <span>{label}</span>
      <strong>{value}</strong>
    </>
  );
  if (onClick) {
    return (
      <button className="provider-usage-metric interactive" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <div className="provider-usage-metric">{content}</div>;
}

function providerStatusLabel(status: string) {
  if (status === 'quota_exhausted') return 'quota exhausted';
  if (status === 'not_configured') return 'not configured';
  if (status === 'usage_unavailable') return 'usage check failed';
  return status || 'unknown';
}

function providerStatusMessage(providerUsage: NonNullable<Overview['provider_usage']>) {
  if (providerUsage.status === 'quota_exhausted') return 'OpenAI quota is exhausted. Customer AI turns are blocked.';
  if (providerUsage.status === 'not_configured') return 'OpenAI API key is missing.';
  if (!providerUsage.openai_admin_key_configured) return 'Runtime key exists; cost reporting needs an admin key.';
  if (!providerUsage.budget.configured) return 'Cost reporting is active. Set a monthly budget to show remaining balance.';
  return `${providerUsage.budget.percent_used}% of monthly budget used.`;
}

function providerStatusDetail(providerUsage: NonNullable<Overview['provider_usage']>) {
  if (providerUsage.status === 'quota_exhausted') return 'The runtime key exists, but OpenAI is rejecting LLM calls for quota or billing.';
  if (providerUsage.status === 'not_configured') return 'Set OPENAI_API_KEY before Maya can answer customer turns.';
  if (providerUsage.status === 'usage_unavailable') return 'Runtime may still answer, but provider usage reporting could not be refreshed.';
  if (!providerUsage.openai_admin_key_configured) return 'Local usage is tracked. Add OPENAI_ADMIN_KEY to show OpenAI month-to-date spend.';
  return providerUsage.openai_costs.message || 'Provider usage is being monitored from CRM.';
}

function shortProviderMessage(message: string) {
  return message.replace(/\s+/g, ' ').trim().slice(0, 260);
}

function formatUsd(value: number | undefined) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function DashboardAttentionCard({
  icon: Icon,
  label,
  value,
  detail,
  tone,
  action,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  detail: string;
  tone: 'ok' | 'warn' | 'bad' | 'idle';
  action: string;
  onClick: () => void;
}) {
  return (
    <button className={`dashboard-attention-card ${tone}`} type="button" onClick={onClick}>
      <Icon size={17} aria-hidden="true" />
      <span>{label}</span>
      <strong>{number(value)}</strong>
      <small>{detail}</small>
      <em>{action}</em>
    </button>
  );
}
function KpiCard({
  label,
  value,
  icon: Icon,
  tone,
  className = '',
  onClick,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  tone: 'accent' | 'blue' | 'green' | 'amber';
  className?: string;
  onClick?: () => void;
}) {
  const content = (
    <>
      <div className="kpi-icon-bg">
        <Icon size={40} aria-hidden="true" />
      </div>
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{typeof value === 'number' ? number(value) : value}</strong>
      <span className="kpi-action">Open</span>
    </>
  );
  if (onClick) {
    return (
      <button className={`card kpi-card kpi-${tone} interactive ${className}`} type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return (
    <section className={`card kpi-card kpi-${tone} ${className}`}>
      {content}
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
  const chart = buildDemandLineChart(visibleRows, maxTurns);
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
        <div className="demand-line-chart">
          <svg className="demand-line-svg" viewBox="0 0 720 260" role="img" aria-label={`Demand trend for ${rangeLabel(range)}`}>
            <defs>
              <linearGradient id="demand-line-fill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#5d5fef" stopOpacity="0.26" />
                <stop offset="100%" stopColor="#20c8ee" stopOpacity="0.02" />
              </linearGradient>
              <linearGradient id="demand-line-stroke" x1="0" x2="1" y1="0" y2="0">
                <stop offset="0%" stopColor="#20c8ee" />
                <stop offset="55%" stopColor="#5d5fef" />
                <stop offset="100%" stopColor="#b067ff" />
              </linearGradient>
            </defs>
            {[0, 1, 2, 3].map((line) => (
              <line key={line} x1="34" x2="696" y1={28 + line * 49} y2={28 + line * 49} className="demand-line-grid" />
            ))}
            <path d={chart.areaPath} className="demand-line-area" />
            <path d={chart.linePath} className="demand-line-path" />
            {chart.points.map((point) => (
              <g key={point.date}>
                <circle cx={point.x} cy={point.y} r="4.5" className="demand-line-dot-halo" />
                <circle cx={point.x} cy={point.y} r="2.7" className="demand-line-dot">
                  <title>{`${point.date}: ${number(point.turns)} turns, ${number(point.tokens)} tokens`}</title>
                </circle>
              </g>
            ))}
          </svg>
          <div className="demand-line-axis" aria-hidden="true">
            {chart.points.map((point) => (
              <span key={point.date}>{point.date.slice(5)}</span>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState text="No trend data yet." />
      )}
    </>
  );
}

function buildDemandLineChart(rows: AnalyticsResponse['series'], maxTurns: number) {
  const width = 720;
  const height = 260;
  const padding = { top: 28, right: 24, bottom: 34, left: 34 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const denominator = Math.max(rows.length - 1, 1);
  const baseline = height - padding.bottom;
  const points = rows.map((row, index) => {
    const x = rows.length === 1 ? padding.left + plotWidth / 2 : padding.left + (index / denominator) * plotWidth;
    const y = padding.top + plotHeight - (row.turns / maxTurns) * plotHeight;
    return { ...row, x, y };
  });
  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
  const areaPath = points.length
    ? `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${baseline} L ${points[0].x.toFixed(1)} ${baseline} Z`
    : '';
  return { points, linePath, areaPath };
}

function ClientRegistryPanel({
  clients,
  onOpenClient,
  onOpenSection,
}: {
  clients: Client[];
  onOpenClient: (siteId: string) => void;
  onOpenSection: (section: ClientBoardSection) => void;
}) {
  const currentClients = clients.filter((client) => client.status !== 'available').length;
  const availableClients = clients.length - currentClients;
  const currentClientRows = clients.filter((client) => client.status !== 'available').slice(0, 4);
  const availableRows = clients.filter((client) => client.status === 'available');
  const onlineInstalls = availableRows.filter((client) => runtimeStatus(client) === 'online');
  const offlineInstalls = availableRows.length - onlineInstalls.length;
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Client registry</h2>
          <span className="card-meta">
            {number(currentClients)} current / {number(availableClients)} available
          </span>
        </div>
        <Button variant="ghost" type="button" onClick={() => onOpenSection('all')}>
          Open all
        </Button>
      </div>
      {clients.length ? (
        <div className="client-registry-panel">
          <div className="client-registry-section">
            <div className="client-registry-section-head">
              <span>
                <CheckCircle2 size={14} aria-hidden="true" />
                Current clients
              </span>
              <button type="button" onClick={() => onOpenSection('current')}>
                {number(currentClients)} open
              </button>
            </div>
            {currentClientRows.length ? (
              <div className="client-mini-list">
                {currentClientRows.map((client, index) => (
                  <ClientMiniRow
                    key={client.site_id}
                    client={client}
                    index={index}
                    onOpenClient={onOpenClient}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No current clients"
                message="Approve an available install before Maya crawls, runs setup, or controls a website."
                action={
                  <Button variant="secondary" size="sm" type="button" onClick={() => onOpenSection('available')}>
                    Open available installs
                  </Button>
                }
              />
            )}
          </div>
          <div className="client-registry-section">
            <div className="client-registry-section-head">
              <span>
                <Users size={14} aria-hidden="true" />
                Available installs
              </span>
              <button type="button" onClick={() => onOpenSection('available')}>
                {number(availableClients)} review
              </button>
            </div>
            <div className="install-status-grid">
              <InstallStatusButton
                icon={Wifi}
                label="Online"
                count={onlineInstalls.length}
                detail="Reachable now"
                tone="online"
                onClick={() => onOpenSection('online')}
              />
              <InstallStatusButton
                icon={WifiOff}
                label="Offline"
                count={offlineInstalls}
                detail="Detected earlier"
                tone="offline"
                onClick={() => onOpenSection('offline')}
              />
            </div>
          </div>
        </div>
      ) : (
        <EmptyState title="No clients yet" message="Detected installs and current clients will appear here after the AI Hub script reports in." />
      )}
    </>
  );
}

function ClientMiniRow({
  client,
  index,
  onOpenClient,
}: {
  client: Client;
  index: number;
  onOpenClient: (siteId: string) => void;
}) {
  const vertical = getCrmVertical(client.vertical_key);
  const runtime = runtimeStatus(client);
  return (
    <button
      className="client-mini-row"
      type="button"
      onClick={() => onOpenClient(client.site_id)}
      style={{ animationDelay: `${index * 30}ms` }}
    >
      <span className="client-mini-avatar">{client.site_id.slice(0, 2).toUpperCase()}</span>
      <div className="client-mini-copy">
        <strong title={client.name}>{client.name}</strong>
        <span title={client.store_url}>{number(client.catalog.active_products)} active {vertical.entityLabelPlural}</span>
        <a
          className="client-mini-url"
          href={client.store_url}
          target="_blank"
          rel="noopener noreferrer"
          title={client.store_url}
          onClick={(event) => event.stopPropagation()}
        >
          {client.store_url}
          <ExternalLink size={11} aria-hidden="true" />
        </a>
      </div>
      <span className="client-mini-statuses">
        <StatusPill value={client.status} />
        <span className={`status-pill runtime-${runtime}`}>{runtime}</span>
      </span>
      <ArrowRight size={14} aria-hidden="true" className="client-mini-arrow" />
    </button>
  );
}

function InstallStatusButton({
  icon: Icon,
  label,
  count,
  detail,
  tone,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  count: number;
  detail: string;
  tone: 'online' | 'offline';
  onClick: () => void;
}) {
  return (
    <button className={`install-status-button ${tone}`} type="button" onClick={onClick}>
      <span className="install-status-icon">
        <Icon size={16} aria-hidden="true" />
      </span>
      <span>
        <strong>{number(count)}</strong>
        <small>{label}</small>
      </span>
      <em>{detail}</em>
    </button>
  );
}

function runtimeStatus(client: Client) {
  return String(client.runtime_status?.status || 'unknown').toLowerCase();
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

function HealthStatusPanel({ health, onOpenHealth }: { health: HealthSnapshot; onOpenHealth: () => void }) {
  const entries = Object.entries(health);
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Quick health</h2>
          <span className="card-meta">{number(entries.length)} checks</span>
        </div>
        <Button variant="ghost" type="button" onClick={onOpenHealth}>
          Open health
        </Button>
      </div>
      {entries.length ? (
        <div className="health-compact-list">
          {entries.map(([key, value]) => {
            const state = healthState(value);
            return (
              <button key={key} className={`health-compact-row ${state}`} type="button" onClick={onOpenHealth}>
                <span className="health-compact-name">{labelize(key)}</span>
                <span className="health-compact-status">
                  <StatusPill value={value || 'unknown'} />
                </span>
                <ArrowRight size={14} aria-hidden="true" />
              </button>
            );
          })}
        </div>
      ) : (
        <EmptyState text="No health checks returned." />
      )}
    </>
  );
}
