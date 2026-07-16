import type { RankRow } from '../types';
import { Meter, MiniRank, PanelHeader } from './ui';

export function OperationsPanel({
  actionRate,
  errorRate,
  latencyRows,
  transportRows,
}: {
  actionRate: number;
  errorRate: number;
  latencyRows: RankRow[];
  transportRows: RankRow[];
}) {
  return (
    <section className="panel">
      <PanelHeader title="Assistant health" detail="current range" />
      <div className="meter-stack">
        <Meter label="Action rate" value={actionRate} />
        <Meter label="Error rate" value={errorRate} danger />
      </div>
      <div className="operations-ranks">
        <MiniRank title="Latency" rows={latencyRows} />
        <MiniRank title="Transport" rows={transportRows} />
      </div>
    </section>
  );
}
