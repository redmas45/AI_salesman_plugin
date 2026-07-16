import type { Client, UsageEvent } from '../../../types';
import { Panel } from '../../../components/ui/Panel';
import { ActivityList } from '../../../components/shared/ActivityList';
import { number } from '../../../utils/format';
import { KeyValue, MetricCard } from '../components/workspaceCards';

export function ClientActivityTab({ client, recentActivity }: { client: Client; recentActivity: UsageEvent[] }) {
  const tokenLimit = client.quota.client.limit || client.token_limit || 0;
  const tokenUsed = client.quota.client.used || client.usage.tokens_estimated || 0;
  const tokenRemaining = client.quota.client.remaining || Math.max(0, tokenLimit - tokenUsed);
  const tokenPct = tokenLimit ? Math.round((tokenUsed / tokenLimit) * 100) : 0;

  return (
    <div className="tab-content fade-in">
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Total turns" value={client.usage.total_turns} detail="All time" />
        <MetricCard label="Turns today" value={client.usage.turns_today} detail="Since midnight" />
        <MetricCard label="Avg latency" value={`${number(client.usage.avg_latency_ms)} ms`} detail="Voice response" />
      </div>
      <div className="activity-insight-grid">
        <Panel title="Recent customer activity">
          <ActivityList items={recentActivity} />
          {recentActivity.length > 0 && recentActivity.length < 5 ? (
            <div className="activity-nudge">
              More activity will appear as your AI widget receives traffic.
            </div>
          ) : null}
        </Panel>
        <section className="card token-burn-card">
          <div className="card-header">
            <div>
              <h3>Token burn</h3>
              <span className="card-meta">Client quota pressure</span>
            </div>
            <span className="badge badge-blue">{number(tokenPct)}%</span>
          </div>
          <div className="token-burn-meter">
            <span style={{ width: `${Math.max(3, Math.min(100, tokenPct))}%` }} />
          </div>
          <div className="token-burn-stats">
            <KeyValue label="Used" value={`${number(tokenUsed)} tokens`} />
            <KeyValue label="Remaining" value={`${number(tokenRemaining)} tokens`} />
            <KeyValue label="Session cap" value={`${number(client.session_token_limit ?? 0)} tokens`} />
          </div>
        </section>
      </div>
    </div>
  );
}
