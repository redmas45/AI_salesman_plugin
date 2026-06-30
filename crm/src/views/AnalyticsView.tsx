import { useState, type CSSProperties } from 'react';
import { Activity, Gauge, MessageSquare, Users, Database, AlertTriangle, type LucideIcon } from 'lucide-react';
import type { AnalyticsResponse, SeriesRow, RankRow, UsageEvent, AnalyticsSectionId } from '../types';
import { Button } from '../components/ui/Button';
import { Panel } from '../components/ui/Panel';
import { EmptyState } from '../components/ui/EmptyState';
import { RangeControl } from '../components/shared/RangeControl';
import { number, shortTime } from '../utils/format';
import { rangeLabel } from '../utils/range';
import type { ClientWorkspaceTabId } from '../verticals/types';

type HealthSignalKind = 'transport' | 'status' | 'latency';

interface HealthSignalSelection {
  kind: HealthSignalKind;
  title: string;
  label: string;
  count: number;
}

export interface AnalyticsViewProps {
  analytics: AnalyticsResponse | null;
  range: string;
  activeSection: AnalyticsSectionId;
  onRangeChange: (range: string) => void;
  onGenerateSummary: () => void;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}

export function AnalyticsView({
  analytics,
  range,
  activeSection,
  onRangeChange,
  onGenerateSummary,
  onOpenClient,
}: AnalyticsViewProps) {
  const [selectedHealthSignal, setSelectedHealthSignal] = useState<HealthSignalSelection | null>(null);

  if (!analytics) return <AnalyticsSkeleton />;

  const activeHealthSignal = selectedHealthSignal ?? defaultHealthSignal(analytics);

  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Analytics</h2>
          <p className="mt-1 text-sm text-muted">
            Demand, voice performance, knowledge signals, and service quality for {rangeLabel(range)}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <RangeControl value={range} onChange={onRangeChange} />
          <Button variant="secondary" onClick={onGenerateSummary}>
            Generate AI summary
          </Button>
        </div>
      </section>

      {activeSection === 'overview' && (
        <section
          id={analyticsSectionPanelId('overview')}
          className="tab-content fade-in"
          role="region"
          aria-label={analyticsSectionLabel('overview')}
        >
          <AnalyticsMetricGrid analytics={analytics} />
          <div className="grid gap-4 2xl:grid-cols-[1.35fr_0.65fr]">
            <AnalyticsTrendChart rows={analytics.series} peakDay={analytics.peak_day} />
            <OperationsPanel analytics={analytics} />
          </div>
          <SummaryCard text={analytics.summary} source={analytics.summary_source} />
        </section>
      )}

      {activeSection === 'quality' && (
        <section
          id={analyticsSectionPanelId('quality')}
          className="tab-content fade-in"
          role="region"
          aria-label={analyticsSectionLabel('quality')}
        >
          <div className="analytics-health-layout">
            <Panel title="Transport and response health">
              <HealthSignalBoard
                analytics={analytics}
                activeHealthSignal={activeHealthSignal}
                onSelect={setSelectedHealthSignal}
                onOpenClient={onOpenClient}
              />
            </Panel>
            <RecentActivityPanel items={analytics.recent_events ?? []} onOpenClient={onOpenClient} />
          </div>
        </section>
      )}

      {activeSection === 'details' && (
        <section
          id={analyticsSectionPanelId('details')}
          className="tab-content fade-in"
          role="region"
          aria-label={analyticsSectionLabel('details')}
        >
          <div className="grid gap-4 xl:grid-cols-3">
            <RankPanel title="Knowledge-backed demand" rows={analytics.top_products} />
            <RankPanel title="Intent mix" rows={analytics.top_intents} />
            <RankPanel title="Client/site mix" rows={analytics.site_mix ?? []} />
          </div>
        </section>
      )}
    </div>
  );
}

function HealthSignalBoard({
  analytics,
  activeHealthSignal,
  onSelect,
  onOpenClient,
}: {
  analytics: AnalyticsResponse;
  activeHealthSignal: HealthSignalSelection | null;
  onSelect: (signal: HealthSignalSelection) => void;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  const statusSignal = firstSignal('status', 'Status', analytics.status_mix ?? []);
  const transportSignal = firstSignal('transport', 'Transport', analytics.transport_mix ?? []);
  const latencySignal = firstSignal('latency', 'Latency', analytics.latency_buckets ?? []);
  return (
    <div className="analytics-health-board">
      <div className="health-signal-overview" aria-label="Health signal summary">
        <HealthSignalSummaryButton
          label="Status"
          signal={statusSignal}
          detail={statusSignal ? 'Largest response status bucket' : 'No status rows yet'}
          activeSignal={activeHealthSignal}
          onSelect={onSelect}
        />
        <HealthSignalSummaryButton
          label="Transport"
          signal={transportSignal}
          detail={transportSignal ? 'Most common delivery channel' : 'No transport rows yet'}
          activeSignal={activeHealthSignal}
          onSelect={onSelect}
        />
        <HealthSignalSummaryButton
          label="Latency"
          signal={latencySignal}
          detail={latencySignal ? 'Largest response-time band' : 'No latency rows yet'}
          activeSignal={activeHealthSignal}
          onSelect={onSelect}
        />
      </div>
      <div className="transport-health-stack">
        <DistributionRows
          kind="transport"
          title="Transport"
          rows={analytics.transport_mix ?? []}
          activeSignal={activeHealthSignal}
          onSelect={onSelect}
        />
        <DistributionRows
          kind="status"
          title="Status"
          rows={analytics.status_mix ?? []}
          activeSignal={activeHealthSignal}
          onSelect={onSelect}
        />
        <DistributionRows
          kind="latency"
          title="Latency"
          rows={analytics.latency_buckets ?? []}
          activeSignal={activeHealthSignal}
          onSelect={onSelect}
        />
      </div>
      <FocusedHealthSignal signal={activeHealthSignal} analytics={analytics} onOpenClient={onOpenClient} />
    </div>
  );
}

function HealthSignalSummaryButton({
  label,
  signal,
  detail,
  activeSignal,
  onSelect,
}: {
  label: string;
  signal: HealthSignalSelection | null;
  detail: string;
  activeSignal: HealthSignalSelection | null;
  onSelect: (signal: HealthSignalSelection) => void;
}) {
  const active = Boolean(signal && activeSignal?.kind === signal.kind && activeSignal.label === signal.label);
  return (
    <button
      className={`health-signal-summary-card ${active ? 'active' : ''}`}
      type="button"
      disabled={!signal}
      aria-pressed={active}
      onClick={() => signal && onSelect(signal)}
    >
      <span>{label}</span>
      <strong>{signal ? signal.label : 'No data'}</strong>
      <small>{signal ? `${number(signal.count)} turns` : detail}</small>
      {signal ? <em>{detail}</em> : null}
    </button>
  );
}

function firstSignal(kind: HealthSignalKind, title: string, rows: RankRow[]): HealthSignalSelection | null {
  const first = rows[0];
  if (!first) return null;
  return { kind, title, label: first.label, count: first.count };
}

function analyticsSectionLabel(sectionId: AnalyticsSectionId) {
  const labels: Record<AnalyticsSectionId, string> = {
    overview: 'Analytics overview',
    quality: 'Analytics quality and health',
    details: 'Analytics details',
  };
  return labels[sectionId];
}

function analyticsSectionPanelId(sectionId: AnalyticsSectionId) {
  return `analytics-section-${sectionId}`;
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

function AnalyticsMetricGrid({ analytics }: { analytics: AnalyticsResponse }) {
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

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}

function DistributionRows({
  kind,
  title,
  rows,
  activeSignal,
  onSelect,
}: {
  kind?: HealthSignalKind;
  title: string;
  rows: RankRow[];
  activeSignal?: HealthSignalSelection | null;
  onSelect?: (signal: HealthSignalSelection) => void;
}) {
  const max = Math.max(...rows.map((row) => row.count), 1);
  return (
    <div className="distribution-group">
      <h3>{title}</h3>
      {rows.length ? (
        rows.map((row) => {
          const interactive = Boolean(kind && onSelect);
          const active = Boolean(activeSignal && activeSignal.kind === kind && activeSignal.label === row.label);
          const rowStyle = { '--bar-width': `${Math.max(2, (row.count / max) * 100)}%` } as CSSProperties;
          const rowContent = (
            <>
              <span className="distribution-row-label">{row.label}</span>
              <div className="distribution-row-track">
                <span />
              </div>
              <b>{number(row.count)}</b>
            </>
          );
          if (!interactive) {
            return (
              <div
                key={`${title}-${row.label}`}
                className="distribution-row-button distribution-row-static"
                title={`${title}: ${row.label} - ${number(row.count)}`}
                style={rowStyle}
              >
                {rowContent}
              </div>
            );
          }
          return (
            <button
              key={`${title}-${row.label}`}
              className={`distribution-row-button ${active ? 'active' : ''}`}
              type="button"
              aria-pressed={active}
              title={`${title}: ${row.label} - ${number(row.count)}`}
              onClick={() => onSelect?.({ kind: kind!, title, label: row.label, count: row.count })}
              style={rowStyle}
            >
              {rowContent}
            </button>
          );
        })
      ) : (
        <EmptyState text="No data." />
      )}
    </div>
  );
}

function FocusedHealthSignal({
  signal,
  analytics,
  onOpenClient,
}: {
  signal: HealthSignalSelection | null;
  analytics: AnalyticsResponse;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  if (!signal) {
    return (
      <div className="focused-health-signal">
        <span>Focused signal</span>
        <strong>No signal selected</strong>
        <p>Select a transport, status, or latency row above to inspect matching recent turns.</p>
      </div>
    );
  }
  const events = matchingHealthEvents(signal, analytics.recent_events ?? []);
  const total = Math.max(analytics.metrics.turns || 0, signal.count);
  const share = total ? Math.round((signal.count / total) * 100) : 0;
  return (
    <div className="focused-health-signal">
      <span>Focused signal</span>
      <strong>{signal.title}: {signal.label}</strong>
      <p>
        {number(signal.count)} matching turns in this range, about {number(share)}% of total demand.
        {events.length ? ` ${number(events.length)} recent matching event${events.length === 1 ? '' : 's'} loaded below.` : ' No matching recent event is currently loaded.'}
      </p>
      {events.length ? (
        <div className="focused-health-events">
          {events.slice(0, 3).map((event) => (
            <button
              key={`${event.session_id}-${event.created_at}`}
              type="button"
              onClick={() => onOpenClient(event.site_id, 'activity')}
            >
              <span>{shortTime(event.created_at)} - {event.site_id}</span>
              <strong>{event.intent || 'unknown intent'}</strong>
              <small>{event.status} / {event.transport} / {number(event.latency_ms)} ms</small>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function defaultHealthSignal(analytics: AnalyticsResponse): HealthSignalSelection | null {
  const firstStatus = analytics.status_mix?.[0];
  if (firstStatus) return { kind: 'status', title: 'Status', label: firstStatus.label, count: firstStatus.count };
  const firstTransport = analytics.transport_mix?.[0];
  if (firstTransport) return { kind: 'transport', title: 'Transport', label: firstTransport.label, count: firstTransport.count };
  const firstLatency = analytics.latency_buckets?.[0];
  if (firstLatency) return { kind: 'latency', title: 'Latency', label: firstLatency.label, count: firstLatency.count };
  return null;
}

function matchingHealthEvents(signal: HealthSignalSelection, events: UsageEvent[]) {
  return events.filter((event) => {
    if (signal.kind === 'transport') return event.transport === signal.label;
    if (signal.kind === 'status') return event.status === signal.label;
    return latencyBucketLabel(event.latency_ms) === signal.label;
  });
}

function latencyBucketLabel(latencyMs: number) {
  if (!latencyMs || latencyMs <= 0) return 'No timing';
  if (latencyMs < 1000) return 'Under 1s';
  if (latencyMs <= 3000) return '1s to 3s';
  return 'Over 3s';
}

function RecentActivityPanel({
  items,
  onOpenClient,
}: {
  items: UsageEvent[];
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  return (
    <Panel title="Recent activity">
      <HealthEventList items={items.slice(0, 8)} onOpenClient={onOpenClient} />
    </Panel>
  );
}

function HealthEventList({
  items,
  onOpenClient,
}: {
  items: UsageEvent[];
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  if (!items.length) return <EmptyState text="No recent health events are loaded for this range." />;
  return (
    <div className="health-event-list">
      {items.map((event, index) => (
        <button
          key={`${event.created_at}-${event.session_id}-${index}`}
          className="health-event-row"
          type="button"
          onClick={() => onOpenClient(event.site_id, 'activity')}
        >
          <span>
            <strong>{event.site_id}</strong>
            <small>{shortTime(event.created_at)}</small>
          </span>
          <b>{event.intent || 'unknown'}</b>
          <em>{event.status} / {event.transport} / {number(event.latency_ms)} ms</em>
        </button>
      ))}
    </div>
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

function SkeletonCard({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 'var(--radius)' }} />;
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
