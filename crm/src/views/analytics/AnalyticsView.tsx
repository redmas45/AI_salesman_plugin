import { useState } from 'react';
import type { AnalyticsResponse, AnalyticsSectionId } from '../../types';
import { Button } from '../../components/ui/Button';
import { Panel } from '../../components/ui/Panel';
import { RangeControl } from '../../components/shared/RangeControl';
import { rangeLabel } from '../../utils/range';
import type { ClientWorkspaceTabId } from '../../verticals/types';
import { HealthSignalBoard, RecentActivityPanel } from './HealthPanels';
import { defaultHealthSignal, type HealthSignalSelection } from './healthSignals';
import {
  AnalyticsMetricGrid,
  AnalyticsSkeleton,
  AnalyticsTrendChart,
  OperationsPanel,
  RankPanel,
  SummaryCard,
} from './OverviewPanels';

export interface AnalyticsViewProps {
  analytics: AnalyticsResponse | null;
  range: string;
  activeSection: AnalyticsSectionId;
  onRangeChange: (range: string) => void;
  onGenerateSummary: () => void;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}

export function AnalyticsView({
  analytics,
  range,
  activeSection,
  onRangeChange,
  onGenerateSummary,
  onOpenClient,
}: AnalyticsViewProps) {
  const [selectedHealthSignal, setSelectedHealthSignal] = useState<HealthSignalSelection | null>(null);

  if (!analytics) return <AnalyticsSkeleton />;

  const activeHealthSignal = selectedHealthSignal ?? defaultHealthSignal(analytics);

  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Analytics</h2>
          <p className="mt-1 text-sm text-muted">
            Demand, voice performance, knowledge signals, and service quality for {rangeLabel(range)}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <RangeControl value={range} onChange={onRangeChange} />
          <Button variant="secondary" onClick={onGenerateSummary}>
            Generate AI summary
          </Button>
        </div>
      </section>

      {activeSection === 'overview' && (
        <section
          id={analyticsSectionPanelId('overview')}
          className="tab-content fade-in"
          role="region"
          aria-label={analyticsSectionLabel('overview')}
        >
          <AnalyticsMetricGrid analytics={analytics} />
          <div className="grid gap-4 2xl:grid-cols-[1.35fr_0.65fr]">
            <AnalyticsTrendChart rows={analytics.series} peakDay={analytics.peak_day} />
            <OperationsPanel analytics={analytics} />
          </div>
          <SummaryCard text={analytics.summary} source={analytics.summary_source} />
        </section>
      )}

      {activeSection === 'quality' && (
        <section
          id={analyticsSectionPanelId('quality')}
          className="tab-content fade-in"
          role="region"
          aria-label={analyticsSectionLabel('quality')}
        >
          <div className="analytics-health-layout">
            <Panel title="Transport and response health">
              <HealthSignalBoard
                analytics={analytics}
                activeHealthSignal={activeHealthSignal}
                onSelect={setSelectedHealthSignal}
                onOpenClient={onOpenClient}
              />
            </Panel>
            <RecentActivityPanel items={analytics.recent_events ?? []} onOpenClient={onOpenClient} />
          </div>
        </section>
      )}

      {activeSection === 'details' && (
        <section
          id={analyticsSectionPanelId('details')}
          className="tab-content fade-in"
          role="region"
          aria-label={analyticsSectionLabel('details')}
        >
          <div className="grid gap-4 xl:grid-cols-3">
            <RankPanel title="Knowledge-backed demand" rows={analytics.top_products} />
            <RankPanel title="Intent mix" rows={analytics.top_intents} />
            <RankPanel title="Client/site mix" rows={analytics.site_mix ?? []} />
          </div>
        </section>
      )}
    </div>
  );
}

function analyticsSectionLabel(sectionId: AnalyticsSectionId) {
  const labels: Record<AnalyticsSectionId, string> = {
    overview: 'Analytics overview',
    quality: 'Analytics quality and health',
    details: 'Analytics details',
  };
  return labels[sectionId];
}

function analyticsSectionPanelId(sectionId: AnalyticsSectionId) {
  return `analytics-section-${sectionId}`;
}
