import type { HealthSnapshot, Client, VerticalDefinition, View, ClientBoardSection } from '../types';
import { Panel } from '../components/ui/Panel';
import { StatusPill } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { number, healthState, labelize } from '../utils/format';

export interface HealthViewProps {
  health: HealthSnapshot;
  clients: Client[];
  verticals: VerticalDefinition[];
  onViewChange: (view: View) => void;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
}

export function HealthView({
  health,
  clients,
  verticals,
  onViewChange,
  onOpenClientBoardSection,
}: HealthViewProps) {
  const knowledgeItems = clients.reduce((sum, client) => sum + client.catalog.active_products, 0);
  const currentClients = clients.filter((client) => client.status !== 'available').length;
  const availableClients = clients.length - currentClients;
  const liveClients = clients.filter((client) => client.status === 'live').length;
  const healthEntries = Object.entries(health);
  const verticalCount = verticals.length;
  const actionCount = new Set(verticals.flatMap((vertical) => vertical.action_types)).size;
  return (
    <div className="grid gap-4">
      <Panel title="System health">
        {healthEntries.length ? (
          <div className="health-grid" id="system-health-checks">
            {healthEntries.map(([key, value]) => {
              const state = healthState(value);
              return (
                <article key={key} className={`health-item ${state}`}>
                  <span className="health-item-label">{labelize(key)}</span>
                  <span className="health-item-status">
                    <StatusPill value={value || 'unknown'} />
                  </span>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState text="No health checks returned." />
        )}
      </Panel>
      <div className="health-summary-grid">
        <HealthActionCard
          label="System checks"
          value={healthEntries.length}
          text="Jump to transport, database, crawler, and runtime checks."
          action="Inspect checks"
          onClick={() => scrollToHealthSection('system-health-checks')}
        />
        <HealthActionCard
          label="Current clients"
          value={currentClients}
          text="Open clients that Maya can crawl, set up, and operate."
          action="Open current"
          onClick={() => onOpenClientBoardSection('current')}
        />
        <HealthActionCard
          label="Available installs"
          value={availableClients}
          text="Review detected websites before approving automation."
          action="Review installs"
          onClick={() => onOpenClientBoardSection('available')}
        />
        <HealthActionCard
          label="Knowledge coverage"
          value={knowledgeItems}
          text="Inspect source-backed records, vectors, and stale data."
          action="Open data"
          onClick={() => onViewChange('catalogs')}
        />
        <HealthActionCard
          label="Domain contracts"
          value={verticalCount}
          text={`${number(actionCount)} expected action types are registered for readiness checks.`}
          action="Inspect contracts"
          onClick={() => scrollToHealthSection('domain-action-contracts')}
        />
      </div>
      <DomainContractMatrix verticals={verticals} />
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Client lifecycle">
          <KeyValue label="Current" value={currentClients} />
          <KeyValue label="Available" value={availableClients} />
          <KeyValue label="Live" value={liveClients} />
          <KeyValue label="Automation gate" value="available clients stay inspection-only" />
        </Panel>
        <Panel title="Database">
          <KeyValue label="Tenant schemas" value={clients.length} />
          <KeyValue label="Knowledge items" value={knowledgeItems} />
          <KeyValue label="Vector store" value="pgvector" />
        </Panel>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Crawler">
          <KeyValue label="Startup crawl" value="off unless deployment enables it" />
          <KeyValue label="Periodic crawl" value="off unless deployment enables it" />
          <KeyValue label="Manual trigger" value="current clients only" />
        </Panel>
        <Panel title="Startup flow">
          <KeyValue label="Script install" value="creates an Available client" />
          <KeyValue label="Move to Current" value="admin action only, no crawl" />
          <KeyValue label="Crawl" value="manual trigger after Current" />
        </Panel>
      </div>
    </div>
  );
}

function HealthActionCard({
  label,
  value,
  text,
  action,
  onClick,
}: {
  label: string;
  value: string | number;
  text: string;
  action: string;
  onClick: () => void;
}) {
  return (
    <button className="card health-summary-card interactive" type="button" onClick={onClick}>
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{typeof value === 'number' ? number(value) : value}</strong>
      <p className="text-sm text-muted">{text}</p>
      <span className="kpi-action">{action}</span>
    </button>
  );
}

function scrollToHealthSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function DomainContractMatrix({ verticals }: { verticals: VerticalDefinition[] }) {
  const ordered = [...verticals].sort((a, b) => {
    if (a.key === 'generic') return 1;
    if (b.key === 'generic') return -1;
    return a.label.localeCompare(b.label);
  });
  return (
    <div id="domain-action-contracts">
      <Panel title="Domain action contracts">
      {ordered.length ? (
        <div className="domain-contract-grid">
          {ordered.map((vertical) => (
            <article key={vertical.key} className="domain-contract-card">
              <div className="domain-contract-head">
                <div>
                  <strong>{vertical.label}</strong>
                  <span>{vertical.entity_label_plural}</span>
                </div>
                <StatusPill value={`${vertical.risk_level} risk`} />
              </div>
              <div className="domain-contract-metrics">
                <small>{number(vertical.action_types.length)} actions</small>
                <small>{number(vertical.readiness_checks.length)} checks</small>
                <small>{number(vertical.crm_tabs.length)} tabs</small>
              </div>
              <div className="domain-contract-chipset">
                {vertical.action_types.slice(0, 8).map((action) => (
                  <span key={action}>{labelize(action)}</span>
                ))}
                {vertical.action_types.length > 8 ? <span>+{number(vertical.action_types.length - 8)} more</span> : null}
              </div>
              <p>
                Readiness: {vertical.readiness_checks.map(labelize).join(', ') || 'not configured'}.
              </p>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="No domain contracts loaded" message="Refresh CRM to load backend vertical action contracts." />
      )}
      </Panel>
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}
