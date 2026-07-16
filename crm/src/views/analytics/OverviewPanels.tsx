import type { CSSProperties } from 'react';
import { Activity, AlertTriangle, Database, Gauge, MessageSquare, Users, type LucideIcon } from 'lucide-react';
import type { AnalyticsResponse, RankRow, SeriesRow } from '../../types';
import { EmptyState } from '../../components/ui/EmptyState';
import { Panel } from '../../components/ui/Panel';
import { number, shortTime } from '../../utils/format';

export function AnalyticsMetricGrid({ analytics }: { analytics: AnalyticsResponse }) {
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

export function AnalyticsTrendChart({ rows, peakDay }: { rows: SeriesRow[]; peakDay?: SeriesRow | null }) {
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

export function OperationsPanel({ analytics }: { analytics: AnalyticsResponse }) {
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

export function RankPanel({ title, rows, onClick }: { title: string; rows: RankRow[]; onClick?: () => void }) {
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

export function SummaryCard({ text, source }: { text: string; source?: string }) {
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

export function AnalyticsSkeleton() {
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

function DistributionRows({ title, rows }: { title: string; rows: RankRow[] }) {
  const max = Math.max(...rows.map((row) => row.count), 1);
  return (
    <div className="distribution-group">
      <h3>{title}</h3>
      {rows.length ? (
        rows.map((row) => (
          <div
            key={`${title}-${row.label}`}
            className="distribution-row-button distribution-row-static"
            title={`${title}: ${row.label} - ${number(row.count)}`}
            style={{ '--bar-width': `${Math.max(2, (row.count / max) * 100)}%` } as CSSProperties}
          >
            <span className="distribution-row-label">{row.label}</span>
            <div className="distribution-row-track">
              <span />
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

function SkeletonCard({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 'var(--radius)' }} />;
}
