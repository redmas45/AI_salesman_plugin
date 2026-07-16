import type { ClientSummary, DashboardResponse } from '../types';
import { number, type ConversationPreview } from '../utils';
import { RecentConversations } from '../components/ConversationPanel';
import { TodayBrief } from '../components/InsightPanels';
import { IntegrationHealth } from '../components/IntegrationHealth';
import { StoreSummary } from '../components/StoreSummary';
import { TokenSnapshot } from '../components/TokenPolicy';
import { KpiCard, RankPanel } from '../components/ui';
import { panelText } from '../verticalText';

export function OverviewTab({
  data,
  sessions,
  onLimitUpdated,
}: {
  data: DashboardResponse;
  sessions: ConversationPreview[];
  onLimitUpdated: (client: ClientSummary) => void;
}) {
  const { client, analytics } = data;
  const text = panelText(client);

  return (
    <div className="tab-stack tab-content fade-in">
      <div className="overview-layout">
        <TodayBrief client={client} analytics={analytics} sessions={sessions} />

        <div className="kpi-strip">
          <KpiCard label="Turns" value={analytics.metrics.turns} tone="accent" icon="T" />
          <KpiCard label="Sessions" value={analytics.metrics.sessions ?? sessions.length} tone="blue" icon="S" />
          <KpiCard label="Avg response" value={`${number(Math.round(analytics.metrics.avg_latency_ms))} ms`} tone="green" icon="A" />
          <KpiCard label="Setup" value={`${number(data.integration?.score ?? 0)}%`} tone="amber" icon="S" />
        </div>

        <div className="overview-main">
          <StoreSummary title={text.summaryTitle} summary={analytics.summary} source={analytics.summary_source || 'heuristic'} />
          <TokenSnapshot client={client} onLimitUpdated={onLimitUpdated} />
          <IntegrationHealth integration={data.integration} />
        </div>

        <div className="overview-lower">
          <RankPanel title={`${text.entityPlural} customers asked about`} rows={analytics.top_products} />
          <RecentConversations client={client} sessions={sessions.slice(0, 3)} />
        </div>
      </div>
    </div>
  );
}
