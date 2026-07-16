import type { CSSProperties } from 'react';
import type { AnalyticsResponse, RankRow, UsageEvent } from '../../types';
import { EmptyState } from '../../components/ui/EmptyState';
import { Panel } from '../../components/ui/Panel';
import { number, shortTime } from '../../utils/format';
import type { ClientWorkspaceTabId } from '../../verticals/types';
import type { HealthSignalKind, HealthSignalSelection } from './healthSignals';

export function HealthSignalBoard({
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

export function RecentActivityPanel({
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

function DistributionRows({
  kind,
  title,
  rows,
  activeSignal,
  onSelect,
}: {
  kind: HealthSignalKind;
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
          const active = Boolean(activeSignal && activeSignal.kind === kind && activeSignal.label === row.label);
          return (
            <button
              key={`${title}-${row.label}`}
              className={`distribution-row-button ${active ? 'active' : ''}`}
              type="button"
              aria-pressed={active}
              title={`${title}: ${row.label} - ${number(row.count)}`}
              onClick={() => onSelect?.({ kind, title, label: row.label, count: row.count })}
              style={{ '--bar-width': `${Math.max(2, (row.count / max) * 100)}%` } as CSSProperties}
            >
              <span className="distribution-row-label">{row.label}</span>
              <div className="distribution-row-track">
                <span />
              </div>
              <b>{number(row.count)}</b>
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
              <EventDialogue transcript={event.transcript} responseText={event.response_text} compact />
              <small>{event.status} / {event.transport} / {number(event.latency_ms)} ms</small>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
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
          <span>
            <b>{event.intent || 'unknown'}</b>
            <EventDialogue transcript={event.transcript} responseText={event.response_text} />
          </span>
          <em>{event.status} / {event.transport} / {number(event.latency_ms)} ms</em>
        </button>
      ))}
    </div>
  );
}

function EventDialogue({
  transcript,
  responseText,
  compact = false,
}: {
  transcript: string;
  responseText: string;
  compact?: boolean;
}) {
  if (!transcript && !responseText) return null;
  return (
    <small className={`health-event-dialogue ${compact ? 'compact' : ''}`}>
      {transcript ? <span>Customer: {transcript}</span> : null}
      {responseText ? <span>Maya: {responseText}</span> : null}
    </small>
  );
}
