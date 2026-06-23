import { Activity, Database, MessageSquare, Gauge, type LucideIcon } from 'lucide-react';
import type { Client, UsageEvent } from '../types';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusPill } from '../components/ui/Badge';
import { number, shortTime } from '../utils/format';

export interface UsageViewProps {
  clients: Client[];
  recentActivity: UsageEvent[];
}

export function UsageView({ clients, recentActivity }: UsageViewProps) {
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
              <p>{item.transcript || item.response_text || '-'}</p>
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
