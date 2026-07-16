import { TokenForecast } from '../components/InsightPanels';
import { TokenPolicy } from '../components/TokenPolicy';
import type { ClientSummary, DashboardResponse } from '../types';
import { number } from '../utils';
import { KeyLine, PanelHeader } from '../components/ui';
import { panelText } from '../verticalText';

export function PolicyTab({
  client,
  analytics,
  onLimitUpdated,
}: {
  client: ClientSummary;
  analytics: DashboardResponse['analytics'];
  onLimitUpdated: (client: ClientSummary) => void;
}) {
  const text = panelText(client);
  return (
    <div className="tab-stack tab-content fade-in">
      <div className="section-intro">
        <div>
          <p className="eyebrow">Token policy</p>
          <h2>Control client usage</h2>
        </div>
        <span>{number(client.quota.client.remaining)} tokens remaining</span>
      </div>

      <div className="policy-layout">
        <div className="policy-stack">
          <div className="policy-explainer">
            <h3>Session token limit</h3>
            <p>
              Each {text.customerSingular} session can consume at most this many tokens from your purchased quota. Setting a lower value prevents any single session from exhausting your entire allocation. Typical recommendation: 2,000-5,000 tokens per session.
            </p>
          </div>
          <TokenPolicy client={client} onLimitUpdated={onLimitUpdated} />
        </div>
        <div className="policy-stack">
          <TokenForecast client={client} analytics={analytics} />
          <section className="panel">
            <PanelHeader title="Usage guardrails" detail={client.status} />
            <div className="guardrail-list">
              <KeyLine label="Purchased limit" value={number(client.quota.client.limit)} />
              <KeyLine label="Purchased used" value={number(client.quota.client.used)} />
              <KeyLine label="Per session limit" value={number(client.session_token_limit)} />
              <KeyLine label="Session remaining" value={number(client.quota.session.remaining)} />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
