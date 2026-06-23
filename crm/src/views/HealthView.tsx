import type { HealthSnapshot, Client } from '../types';
import { Panel } from '../components/ui/Panel';
import { StatusPill } from '../components/ui/Badge';
import { number, healthState, labelize } from '../utils/format';

export interface HealthViewProps {
  health: HealthSnapshot;
  clients: Client[];
}

export function HealthView({ health, clients }: HealthViewProps) {
  const products = clients.reduce((sum, client) => sum + client.catalog.active_products, 0);
  const liveClients = clients.filter((client) => client.status === 'live').length;
  return (
    <div className="grid gap-4">
      <Panel title="System health">
        <div className="health-grid">
          {Object.entries(health).map(([key, value]) => {
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
      </Panel>
      <div className="health-summary-grid">
        <section className="card health-summary-card">
          <span className="kpi-label">Last checked</span>
          <strong className="kpi-value">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
          <p className="text-sm text-muted">Use the topbar refresh control to run a fresh health and client snapshot.</p>
        </section>
        <section className="card health-summary-card">
          <span className="kpi-label">Live clients</span>
          <strong className="kpi-value">{number(liveClients)}</strong>
          <p className="text-sm text-muted">{number(clients.length)} total tenant schemas are configured.</p>
        </section>
        <section className="card health-summary-card">
          <span className="kpi-label">Catalog coverage</span>
          <strong className="kpi-value">{number(products)}</strong>
          <p className="text-sm text-muted">Active products available to retrieval and shopping actions.</p>
        </section>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Database">
        <KeyValue label="Tenant schemas" value={clients.length} />
        <KeyValue label="Products" value={products} />
        <KeyValue label="Vector store" value="pgvector" />
      </Panel>
      <Panel title="Crawler">
        <KeyValue label="Startup crawl" value="enabled by deployment config" />
        <KeyValue label="Periodic crawl" value="120 seconds" />
        <KeyValue label="Manual trigger" value="available per client" />
      </Panel>
      </div>
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
