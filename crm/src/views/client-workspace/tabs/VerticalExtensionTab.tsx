import type { ReactNode } from 'react';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { EmptyState } from '../../../components/ui/EmptyState';
import type { ClientWorkspaceTabDefinition, ClientWorkspaceTabId, CrmVerticalDefinition } from '../../../verticals/types';

export function VerticalExtensionTab({
  tab,
  vertical,
  renderActions,
}: {
  tab: ClientWorkspaceTabDefinition;
  vertical: CrmVerticalDefinition;
  renderActions: (actions: string[]) => ReactNode;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">{tab.label}</h2>
          <p className="mt-1 text-sm text-muted">
            {extensionTabDescription(tab.id, vertical)}
          </p>
        </div>
        <StatusPill value={vertical.riskLevel} />
      </section>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Entity model">
          {renderActions(vertical.entityTypes)}
        </Panel>
        <Panel title="Readiness focus">
          {renderActions(vertical.readinessChecks)}
        </Panel>
      </div>
      <Panel title={`${tab.label} records`}>
        <EmptyState
          title="No records yet"
          message={extensionTabEmptyMessage(tab.id, tab.label)}
        />
      </Panel>
    </div>
  );
}

function extensionTabDescription(tabId: ClientWorkspaceTabId, vertical: CrmVerticalDefinition) {
  if (tabId === 'leads') {
    return 'Leads are visitor intents Maya can capture or hand off: quote requests, callbacks, applications, appointment requests, and contact details. They are not completed purchases, policies, approvals, or claims.';
  }
  if (tabId === 'quote_flows') {
    return 'Quote flows show the fields and steps Maya can prepare for the website without claiming eligibility, premium finality, or policy issuance.';
  }
  if (tabId === 'compliance') {
    return 'Compliance tracks high-risk boundaries, confirmation rules, disclosures, and handoff requirements for this vertical.';
  }
  return `${vertical.label} workspace for ${vertical.entityLabelPlural}.`;
}

function extensionTabEmptyMessage(tabId: ClientWorkspaceTabId, label: string) {
  if (tabId === 'leads') {
    return 'No lead events are loaded yet. When visitors ask Maya for callbacks, quotes, applications, or contact handoff, those intents can appear here.';
  }
  if (tabId === 'quote_flows') {
    return 'No quote flow records are loaded yet. Run setup to rediscover forms, required fields, and safe handoff boundaries.';
  }
  return `No ${label.toLowerCase()} records are loaded for this client yet.`;
}
