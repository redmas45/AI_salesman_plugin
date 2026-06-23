import { Activity, Database, MessageSquare, Users, ArrowRight, type LucideIcon } from 'lucide-react';
import type { View, Overview, Client, AnalyticsResponse, HealthSnapshot, UsageEvent } from '../types';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusPill } from '../components/ui/Badge';
import { ActivityList } from '../components/shared/ActivityList';
import { number, healthState, labelize } from '../utils/format';
import { rangeLabel } from '../utils/range';
import { RangeControl } from '../components/shared/RangeControl';

export interface DashboardViewProps {
  overview: Overview;
  clients: Client[];
  analytics: AnalyticsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onOpenClient: (siteId: string) => void;
}

export function DashboardView({
  overview,
  clients,
  analytics,
  range,
  onRangeChange,
  onViewChange,
  onOpenClient,
}: DashboardViewProps) {
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
