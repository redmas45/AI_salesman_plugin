import { EmptyState } from '../ui/EmptyState';
import { StatusPill } from '../ui/Badge';
import { shortTime, number } from '../../utils/format';
import type { UsageEvent } from '../../types';

export interface ActivityListProps {
  items: UsageEvent[];
}

export function ActivityList({ items }: ActivityListProps) {
  if (!items.length) return <EmptyState text="No activity yet." />;
  return (
    <div className="grid gap-3">
      {items.map((item, index) => (
        <div key={`${item.created_at}-${item.session_id}-${index}`} className="grid gap-1 border-b border-line pb-3 last:border-b-0 last:pb-0">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            <span>{shortTime(item.created_at)}</span>
            <StatusPill value={item.status || 'ok'} />
            <span>{number(item.latency_ms)} ms</span>
          </div>
          <strong className="text-sm">
            {item.site_id} {item.intent || 'turn'}
          </strong>
          <TurnText transcript={item.transcript} responseText={item.response_text} />
        </div>
      ))}
    </div>
  );
}

function TurnText({ transcript, responseText }: { transcript: string; responseText: string }) {
  if (!transcript && !responseText) return <p className="text-sm text-muted">-</p>;
  return (
    <div className="activity-turn-lines">
      {transcript ? (
        <p className="line-clamp-2 text-sm text-muted">
          <span>Customer</span>
          {transcript}
        </p>
      ) : null}
      {responseText ? (
        <p className="line-clamp-2 text-sm text-muted">
          <span>Maya</span>
          {responseText}
        </p>
      ) : null}
    </div>
  );
}
