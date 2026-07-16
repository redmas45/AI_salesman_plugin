import { useMemo, useState } from 'react';
import { Activity, Database, MessageSquare, Gauge, Search, X, type LucideIcon } from 'lucide-react';
import type { Client, UsageEvent } from '../../types';
import { EmptyState } from '../../components/ui/EmptyState';
import { StatusPill } from '../../components/ui/Badge';
import { PaginationControl } from '../../components/shared/controls/PaginationControl';
import { usePagination } from '../../hooks/usePagination';
import { number, shortTime } from '../../utils/format';
import type { ClientWorkspaceTabId } from '../../verticals/types';

export interface UsageViewProps {
  clients: Client[];
  recentActivity: UsageEvent[];
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}

type UsageStatusFilter = 'all' | 'ok' | 'error';
type UsageLatencyFilter = 'all' | 'slow';

const USAGE_PAGE_SIZE = 6;

export function UsageView({ clients, recentActivity, onOpenClient }: UsageViewProps) {
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<UsageStatusFilter>('all');
  const [latencyFilter, setLatencyFilter] = useState<UsageLatencyFilter>('all');
  const normalizedQuery = query.trim().toLowerCase();
  const clientNames = useMemo(() => new Map(clients.map((client) => [client.site_id, client.name])), [clients]);
  const filteredActivity = useMemo(
    () =>
      recentActivity.filter((item) => {
        const isError = eventIsError(item);
        const isSlow = eventIsSlow(item);
        if (statusFilter === 'ok' && isError) return false;
        if (statusFilter === 'error' && !isError) return false;
        if (latencyFilter === 'slow' && !isSlow) return false;
        if (!normalizedQuery) return true;
        const searchable = [
          item.site_id,
          clientNames.get(item.site_id),
          item.session_id,
          item.transport,
          item.status,
          item.intent,
          item.transcript,
          item.response_text,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return searchable.includes(normalizedQuery);
      }),
    [clientNames, latencyFilter, normalizedQuery, recentActivity, statusFilter],
  );
  const errorEvents = recentActivity.filter(eventIsError).length;
  const slowEvents = recentActivity.filter(eventIsSlow).length;
  const activityPagination = usePagination(
    filteredActivity,
    USAGE_PAGE_SIZE,
    `${normalizedQuery}|${statusFilter}|${latencyFilter}`,
  );
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
        <span className="badge badge-muted">{number(filteredActivity.length)} of {number(recentActivity.length)} events</span>
      </section>
      <UsageSignalStrip
        totalEvents={recentActivity.length}
        errorEvents={errorEvents}
        slowEvents={slowEvents}
        statusFilter={statusFilter}
        latencyFilter={latencyFilter}
        onSelectAll={() => {
          setStatusFilter('all');
          setLatencyFilter('all');
        }}
        onSelectHealthy={() => {
          setStatusFilter('ok');
          setLatencyFilter('all');
        }}
        onSelectErrors={() => {
          setStatusFilter('error');
          setLatencyFilter('all');
        }}
        onSelectSlow={() => {
          setStatusFilter('all');
          setLatencyFilter('slow');
        }}
      />
      <div className="usage-kpi-grid">
        <KpiCard label="Total turns" value={totals.turns} icon={MessageSquare} tone="accent" onClick={() => setStatusFilter('all')} />
        <KpiCard label="Turns today" value={totals.today} icon={Activity} tone="green" onClick={() => setStatusFilter('all')} />
        <KpiCard label="Tokens used" value={totals.tokens} icon={Database} tone="blue" onClick={() => setStatusFilter('all')} />
        <KpiCard label="Tokens left" value={totals.remaining} icon={Gauge} tone="amber" onClick={() => setStatusFilter('all')} />
      </div>
      <section className="card usage-timeline-card">
        <div className="card-header">
          <div>
            <h2>Recent usage timeline</h2>
            <span className="card-meta">Latest assistant turns, transport status, and token cost</span>
          </div>
        </div>
        <section className="client-board-toolbar usage-toolbar" aria-label="Usage timeline filters">
          <label className="client-search">
            <Search size={15} aria-hidden="true" />
            <span className="sr-only">Search usage events</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search client, session, intent, transcript..."
            />
            {query ? (
              <button type="button" aria-label="Clear usage search" onClick={() => setQuery('')}>
                <X size={14} aria-hidden="true" />
              </button>
            ) : null}
          </label>
          <label className="data-filter-select">
            Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as UsageStatusFilter)}>
              <option value="all">All events</option>
              <option value="ok">Healthy only</option>
              <option value="error">Errors only</option>
            </select>
          </label>
          <div className="client-board-counts" aria-live="polite">
            <span>{number(filteredActivity.length)} matching</span>
            <span>{number(errorEvents)} errors</span>
            <span>{number(slowEvents)} slow</span>
          </div>
        </section>
        <UsageTimeline items={activityPagination.pageItems} onOpenClient={onOpenClient} />
        <PaginationControl
          page={activityPagination.page}
          pageCount={activityPagination.pageCount}
          pageSize={USAGE_PAGE_SIZE}
          totalItems={filteredActivity.length}
          itemLabel="events"
          onPageChange={activityPagination.setPage}
        />
      </section>
    </div>
  );
}

function UsageSignalStrip({
  totalEvents,
  errorEvents,
  slowEvents,
  statusFilter,
  latencyFilter,
  onSelectAll,
  onSelectHealthy,
  onSelectErrors,
  onSelectSlow,
}: {
  totalEvents: number;
  errorEvents: number;
  slowEvents: number;
  statusFilter: UsageStatusFilter;
  latencyFilter: UsageLatencyFilter;
  onSelectAll: () => void;
  onSelectHealthy: () => void;
  onSelectErrors: () => void;
  onSelectSlow: () => void;
}) {
  const healthyEvents = Math.max(0, totalEvents - errorEvents);
  return (
    <section className="usage-signal-strip" aria-label="Usage event filters">
      <UsageSignalCard
        label="All events"
        value={totalEvents}
        detail="Complete recent timeline"
        active={statusFilter === 'all' && latencyFilter === 'all'}
        onClick={onSelectAll}
      />
      <UsageSignalCard
        label="Healthy"
        value={healthyEvents}
        detail="No error status"
        active={statusFilter === 'ok' && latencyFilter === 'all'}
        onClick={onSelectHealthy}
      />
      <UsageSignalCard
        label="Errors"
        value={errorEvents}
        detail="Failed, timed out, or blocked"
        tone={errorEvents ? 'bad' : 'idle'}
        active={statusFilter === 'error'}
        onClick={onSelectErrors}
      />
      <UsageSignalCard
        label="Slow"
        value={slowEvents}
        detail="Over 3 seconds latency"
        tone={slowEvents ? 'warn' : 'idle'}
        active={latencyFilter === 'slow'}
        onClick={onSelectSlow}
      />
    </section>
  );
}

function UsageSignalCard({
  label,
  value,
  detail,
  tone = 'neutral',
  active,
  onClick,
}: {
  label: string;
  value: number;
  detail: string;
  tone?: 'neutral' | 'warn' | 'bad' | 'idle';
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button className={`usage-signal-card ${tone} ${active ? 'active' : ''}`} type="button" aria-pressed={active} onClick={onClick}>
      <span>{label}</span>
      <strong>{number(value)}</strong>
      <small>{detail}</small>
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

function UsageTimeline({
  items,
  onOpenClient,
}: {
  items: UsageEvent[];
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  if (!items.length) {
    return <EmptyState title="No usage events found" message="Adjust the search or status filter, or wait for visitors to start talking to the assistant." />;
  }

  return (
    <div className="usage-timeline">
      {items.map((item, index) => {
        const tokenTotal = Number(item.input_tokens || 0) + Number(item.output_tokens || 0);
        return (
          <button
            key={`${item.created_at}-${item.session_id}-${index}`}
            className="usage-event-row"
            type="button"
            onClick={() => onOpenClient(item.site_id, 'activity')}
          >
            <span className="usage-event-dot" aria-hidden="true" />
            <div className="usage-event-main">
              <div className="usage-event-head">
                <strong>{item.site_id}</strong>
                <StatusPill value={item.status || 'ok'} />
                <span className="usage-event-open">Open activity</span>
              </div>
              <TurnDialogue transcript={item.transcript} responseText={item.response_text} />
              <div className="usage-event-meta">
                <span>{shortTime(item.created_at)}</span>
                <span>{item.intent || 'turn'}</span>
                <span>{number(tokenTotal)} tokens</span>
                <span>{number(item.latency_ms)} ms</span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function TurnDialogue({ transcript, responseText }: { transcript: string; responseText: string }) {
  if (!transcript && !responseText) return <p>-</p>;
  return (
    <div className="usage-event-dialogue">
      {transcript ? (
        <p>
          <span>Customer</span>
          {transcript}
        </p>
      ) : null}
      {responseText ? (
        <p>
          <span>Maya</span>
          {responseText}
        </p>
      ) : null}
    </div>
  );
}

function eventIsError(item: UsageEvent) {
  const status = (item.status || 'ok').toLowerCase();
  return ['error', 'failed', 'failure', 'timeout', 'blocked'].some((token) => status.includes(token));
}

function eventIsSlow(item: UsageEvent) {
  return Number(item.latency_ms || 0) >= 3000;
}
