import { CatalogPanel } from '../components/CatalogPanel';
import { CatalogOpportunityMap } from '../components/InsightPanels';
import type { ClientSummary, DashboardResponse } from '../types';
import { Metric, PanelHeader, RankPanel } from '../components/ui';
import { panelText } from '../verticalText';

export function CatalogTab({ client, analytics }: { client: ClientSummary; analytics: DashboardResponse['analytics'] }) {
  const text = panelText(client);
  return (
    <div className="tab-stack tab-content fade-in">
      <div className="section-intro catalog-toolbar">
        <div>
          <p className="eyebrow">{text.dataLabel}</p>
          <h2>Coverage and indexing</h2>
        </div>
        <span>{client.plan}</span>
      </div>

      <div className="catalog-workspace">
        <CatalogPanel client={client} />
        <div className="catalog-workspace-side">
          <section className="panel">
            <PanelHeader title={text.dataSignalsTitle} detail="current range" />
            <div className="signal-grid">
              <Metric label={text.totalEntitiesLabel} value={client.catalog.total_products} detail={`All ${text.entityPlural} rows`} tone="ink" />
              <Metric label={text.activeEntitiesLabel} value={client.catalog.active_products} detail="Available to AI" tone="green" />
              <Metric label="Categories" value={client.catalog.categories} detail="Indexed groups" tone="blue" />
            </div>
          </section>
          <CatalogOpportunityMap client={client} topProducts={analytics.top_products} />
        </div>
      </div>

      <div className="rank-grid two">
        <RankPanel title={text.requestedEntitiesTitle} rows={analytics.top_products} />
        <RankPanel title={`Intent mix near ${text.dataLabel.toLowerCase()}`} rows={analytics.top_intents} />
      </div>
    </div>
  );
}
