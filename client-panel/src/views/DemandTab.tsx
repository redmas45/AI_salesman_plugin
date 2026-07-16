import type { DashboardResponse } from '../types';
import { DemandTrend } from '../components/DemandTrend';
import { OperationsPanel } from '../components/OperationsPanel';
import { RankPanel } from '../components/ui';
import { panelText } from '../verticalText';

export function DemandTab({ data }: { data: DashboardResponse }) {
  const { analytics, client } = data;
  const text = panelText(client);

  return (
    <div className="tab-stack tab-content fade-in">
      <div className="section-intro">
        <div>
          <p className="eyebrow">Demand</p>
          <h2>{text.demandHeading}</h2>
        </div>
        <span>{analytics.peak_day ? `Peak day: ${analytics.peak_day.date}` : 'No peak day yet'}</span>
      </div>

      <div className="dashboard-layout wide-left">
        <DemandTrend rows={analytics.series} peakDay={analytics.peak_day} />
        <OperationsPanel
          actionRate={analytics.metrics.action_rate ?? 0}
          errorRate={analytics.metrics.error_rate ?? 0}
          latencyRows={analytics.latency_buckets ?? []}
          transportRows={analytics.transport_mix ?? []}
        />
      </div>

      <div className="rank-grid">
        <RankPanel title={text.demandRankTitle} rows={analytics.top_products} />
        <RankPanel title="Intent mix" rows={analytics.top_intents} />
        <RankPanel title="Status mix" rows={analytics.status_mix ?? []} />
      </div>
    </div>
  );
}
