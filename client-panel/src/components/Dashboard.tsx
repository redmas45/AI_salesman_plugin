import { useState } from 'react';
import { DASHBOARD_TABS, type DashboardTab } from '../constants';
import type { ClientSummary, DashboardResponse } from '../types';
import { flattenedSessions, number, rangeLabel } from '../utils';
import { panelText } from '../verticalText';
import { CatalogTab } from '../views/CatalogTab';
import { ConversationTab } from '../views/ConversationTab';
import { DemandTab } from '../views/DemandTab';
import { OverviewTab } from '../views/OverviewTab';
import { PolicyTab } from '../views/PolicyTab';
import { MiniStat, StatusPill } from './ui';

export function Dashboard({
  data,
  range,
  onLimitUpdated,
}: {
  data: DashboardResponse;
  range: string;
  onLimitUpdated: (client: ClientSummary) => void;
}) {
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');
  const { client, analytics, conversations } = data;
  const sessions = flattenedSessions(conversations.groups);

  return (
    <>
      <ClientSummaryBar client={client} range={range} sessions={sessions.length} />
      <div className="client-panel-workspace">
        <TabBar activeTab={activeTab} onChange={setActiveTab} client={client} />
        <section className="client-panel-content" aria-live="polite">
          {activeTab === 'overview' ? (
            <OverviewTab data={data} sessions={sessions} onLimitUpdated={onLimitUpdated} />
          ) : null}
          {activeTab === 'demand' ? <DemandTab data={data} /> : null}
          {activeTab === 'conversations' ? <ConversationTab client={client} sessions={sessions} /> : null}
          {activeTab === 'catalog' ? <CatalogTab client={client} analytics={analytics} /> : null}
          {activeTab === 'policy' ? <PolicyTab client={client} analytics={analytics} onLimitUpdated={onLimitUpdated} /> : null}
        </section>
      </div>
      <footer className="client-footer">
        <span>Powered by <strong>AI Hub</strong></span>
        <span className="client-footer-sep">&middot;</span>
        <span>{new Date().getFullYear()}</span>
      </footer>
    </>
  );
}

function ClientSummaryBar({ client, range, sessions }: { client: ClientSummary; range: string; sessions: number }) {
  const text = panelText(client);
  return (
    <section className="client-summary-bar">
      <div>
        <p className="eyebrow">{panelText(client).verticalLabel} workspace</p>
        <h1>{client.name}</h1>
        <p>
          <a className="client-summary-link" href={client.store_url} target="_blank" rel="noopener noreferrer">
            {client.store_url}
          </a>
          <span aria-hidden="true"> - </span>
          <span>{rangeLabel(range)} - {number(sessions)} sessions</span>
        </p>
      </div>
      <div className="summary-strip">
        <StatusPill label={client.status} />
        <MiniStat label={text.entityPlural} value={client.catalog.active_products} />
        <MiniStat label="Tokens left" value={client.quota.client.remaining} />
      </div>
    </section>
  );
}

function TabBar({ activeTab, onChange, client }: { activeTab: DashboardTab; onChange: (tab: DashboardTab) => void; client: ClientSummary }) {
  const text = panelText(client);
  const labels: Record<DashboardTab, string> = {
    overview: 'Overview',
    demand: 'Demand',
    conversations: 'Conversations',
    catalog: text.dataTabLabel,
    policy: 'Usage policy',
  };
  return (
    <nav className="panel-tabs" aria-label="Client panel sections">
      <div className="panel-tabs-label">Workspace</div>
      {DASHBOARD_TABS.map(([value]) => (
        <button
          key={value}
          className={`panel-tab-btn ${value === activeTab ? 'active' : ''}`}
          type="button"
          onClick={() => onChange(value)}
        >
          {labels[value]}
        </button>
      ))}
    </nav>
  );
}
