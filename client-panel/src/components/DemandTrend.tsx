import { TREND_BAR_LIMIT } from '../constants';
import type { SeriesRow } from '../types';
import { number, percent } from '../utils';
import { EmptyState, PanelHeader } from './ui';

export function DemandTrend({ rows, peakDay }: { rows: SeriesRow[]; peakDay?: SeriesRow | null }) {
  const visibleRows = rows.slice(-TREND_BAR_LIMIT);
  const maxTurns = Math.max(...visibleRows.map((row) => row.turns), 1);
  const maxTokens = Math.max(...visibleRows.map((row) => row.tokens), 1);

  return (
    <section className="panel">
      <PanelHeader title="Demand trend" detail={peakDay ? `Peak ${peakDay.date}` : 'No peak yet'} />
      {visibleRows.length ? (
        <div className="demand-chart">
          {visibleRows.map((row, index) => (
            <div key={row.date} className="demand-column">
              <span className="trend-tooltip">
                {row.date}: {number(row.turns)} turns, {number(row.tokens)} tokens
              </span>
              <i className="token-dot" style={{ bottom: `${Math.max(8, percent(row.tokens, maxTokens))}%` }} />
              <span
                className="demand-bar"
                style={{
                  height: `${Math.max(8, percent(row.turns, maxTurns))}%`,
                  animationDelay: `${index * 25}ms`,
                }}
                title={`${row.date}: ${number(row.turns)} turns`}
              />
              <small>{row.date.slice(5)}</small>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No demand yet" message="Demand trends will appear after customers start using the assistant." />
      )}
    </section>
  );
}
