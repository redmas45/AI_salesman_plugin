import { useMemo, useState } from 'react';
import { ExternalLink, Search, X } from 'lucide-react';
import type { Client } from '../../types';
import { Button } from '../../components/ui/Button';
import { StatusPill } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ui/EmptyState';
import { UniversalInstallerPanel } from '../../components/shared/UniversalInstallerPanel';
import { number } from '../../utils/format';
import { clientPanelHref } from '../../utils/clientLinks';
import { getCrmVertical } from '../../verticals/registry';
import type { ClientWorkspaceTabId } from '../../verticals/types';
import { PaginationControl } from '../../components/shared/controls/PaginationControl';
import { usePagination } from '../../hooks/usePagination';

const ADAPTER_PAGE_SIZE = 6;

export interface AdaptersViewProps {
  clients: Client[];
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}

export function AdaptersView({ clients, onOpenClient }: AdaptersViewProps) {
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'current' | 'available'>('all');
  const normalizedQuery = query.trim().toLowerCase();
  const filteredClients = useMemo(() => {
    return clients.filter((client) => {
      const vertical = getCrmVertical(client.vertical_key);
      const statusBucket = client.status === 'available' ? 'available' : 'current';
      if (statusFilter !== 'all' && statusBucket !== statusFilter) return false;
      if (!normalizedQuery) return true;
      return [
        client.site_id,
        client.name,
        client.store_url,
        client.status,
        client.adapter_name,
        client.deploy_mode,
        client.vertical_key,
        client.vertical_label,
        vertical.label,
      ].some((value) => String(value || '').toLowerCase().includes(normalizedQuery));
    });
  }, [clients, normalizedQuery, statusFilter]);
  const totalCurrent = clients.filter((client) => client.status !== 'available').length;
  const totalAvailable = clients.filter((client) => client.status === 'available').length;
  const configuredCount = filteredClients.filter((client) => Boolean(client.adapter_name && client.adapter_name !== '-')).length;
  const pagination = usePagination(filteredClients, ADAPTER_PAGE_SIZE, `${normalizedQuery}|${statusFilter}`);

  return (
    <div className="fade-in grid gap-4">
      <section className="section-header">
        <div>
          <h2>Adapters</h2>
          <p>Runtime install, origin binding, generated adapter state, and workspace links for every independent client.</p>
        </div>
      </section>
      <UniversalInstallerPanel />
      <section className="client-board-toolbar" aria-label="Adapter filters">
        <label className="client-search">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search adapters</span>
          <input
            value={query}
            placeholder="Search clients, URLs, adapters, verticals, or status"
            onChange={(event) => setQuery(event.currentTarget.value)}
          />
          {query ? (
            <button type="button" aria-label="Clear adapter search" onClick={() => setQuery('')}>
              <X size={14} aria-hidden="true" />
            </button>
          ) : null}
        </label>
        <label className="data-filter-select">
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.currentTarget.value as typeof statusFilter)}>
            <option value="all">All clients</option>
            <option value="current">Current only</option>
            <option value="available">Available only</option>
          </select>
        </label>
        <div className="client-board-counts">
          <span>{number(totalCurrent)} current</span>
          <span>{number(totalAvailable)} available</span>
          <span>{number(configuredCount)} configured</span>
          <span>{number(filteredClients.length)} shown</span>
        </div>
      </section>
      {!clients.length ? (
        <EmptyState
          title="No connected sites yet"
          message="Paste the universal installer into a website and refresh this page after the first visit."
        />
      ) : !filteredClients.length ? (
        <EmptyState title="No matching adapters" message="Clear the search or change the status filter." />
      ) : (
        <>
          <div className="adapter-grid">
            {pagination.pageItems.map((client) => (
              <AdapterClientCard
                key={client.site_id}
                client={client}
                onOpenClient={onOpenClient}
              />
            ))}
          </div>
          <PaginationControl
            page={pagination.page}
            pageCount={pagination.pageCount}
            pageSize={ADAPTER_PAGE_SIZE}
            totalItems={filteredClients.length}
            itemLabel="adapters"
            onPageChange={pagination.setPage}
          />
        </>
      )}
    </div>
  );
}

const ADAPTER_GENERATION_STAGES = [
  'Installer connected',
  'Runtime identity received',
  'Domain profile selected',
  'Adapter shell generated',
  'Ready for validation',
];
type AdapterGenerationStageStatus = 'complete' | 'running' | 'pending';

function AdapterClientCard({
  client,
  onOpenClient,
}: {
  client: Client;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  const configured = Boolean(client.adapter_name && client.adapter_name !== '-');
  const vertical = getCrmVertical(client.vertical_key);
  const panelUrl = clientPanelHref(client.site_id);
  const stageStates = adapterGenerationStages(client, configured);
  return (
    <article className="card adapter-card">
      <button
        className="adapter-card-hit-target"
        type="button"
        aria-label={`Open ${client.name} adapter workspace`}
        onClick={() => onOpenClient(client.site_id, 'adapter')}
      />
      <div className="adapter-card-top">
        <div className="min-w-0">
          <span className="adapter-eyebrow">{client.deploy_mode || 'auto-detected'}</span>
          <h2>{client.name}</h2>
          <button className="adapter-site-id" type="button" onClick={() => onOpenClient(client.site_id, 'overview')}>
            {client.site_id}
          </button>
        </div>
        <div className="data-client-badges">
          <span className="badge badge-muted">{vertical.label}</span>
          <StatusPill value={client.status} />
        </div>
      </div>
      <div className="adapter-detail-list">
        <KeyValue label="Adapter" value={configured ? client.adapter_name : 'Generation pending'} />
        <KeyValue label="Origin" value={client.allowed_origin || client.store_url || '-'} />
        <KeyValue label="Vertical" value={client.vertical_label || vertical.label} />
        <KeyValue label="Indexed records" value={number(client.catalog.active_products)} />
      </div>
      {!configured ? (
        <AdapterGenerationConsole stages={stageStates} />
      ) : null}
      {client.status === 'available' ? (
        <div className="adapter-empty-note">
          <strong>Available discovery</strong>
          <span>Review this workspace first. Automation stays locked until the client is moved to Current.</span>
        </div>
      ) : null}
      <div className="adapter-actions">
        <Button variant="secondary" size="sm" type="button" onClick={() => onOpenClient(client.site_id, 'adapter')}>
          Open adapter
        </Button>
        <Button variant="secondary" size="sm" type="button" onClick={() => onOpenClient(client.site_id, 'integration')}>
          Setup workspace
        </Button>
        <a className="btn btn-ghost btn-sm" href={client.store_url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Website
        </a>
        <a className="btn btn-ghost btn-sm" href={panelUrl} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Owner panel
        </a>
      </div>
    </article>
  );
}

function AdapterGenerationConsole({
  stages,
}: {
  stages: Array<{ label: string; status: AdapterGenerationStageStatus }>;
}) {
  const completed = stages.filter((stage) => stage.status === 'complete').length;
  const running = stages.find((stage) => stage.status === 'running');
  const progress = Math.max(12, Math.min(92, Math.round(((completed + (running ? 0.5 : 0)) / stages.length) * 100)));
  return (
    <div className="adapter-generation-console" aria-label="Adapter generation progress">
      <div className="adapter-generation-head">
        <div>
          <strong>{running ? running.label : 'Waiting for adapter generation'}</strong>
          <span>Open the site once with the installer loaded, then run setup to validate generated actions.</span>
        </div>
        <em>{number(progress)}%</em>
      </div>
      <div className="adapter-generation-progress" aria-label={`${progress}% ready`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <ol className="adapter-generation-stages">
        {stages.map((stage) => (
          <li key={stage.label} className={stage.status}>
            <span aria-hidden="true" />
            <strong>{stage.label}</strong>
          </li>
        ))}
      </ol>
    </div>
  );
}

function adapterGenerationStages(client: Client, configured: boolean): Array<{ label: string; status: AdapterGenerationStageStatus }> {
  const completed = new Set<string>();
  if (client.store_url || client.allowed_origin) completed.add('Installer connected');
  if (client.site_id) completed.add('Runtime identity received');
  if (client.vertical_key || client.vertical_label) completed.add('Domain profile selected');
  if (configured) {
    ADAPTER_GENERATION_STAGES.forEach((stage) => completed.add(stage));
  }
  const firstPending = ADAPTER_GENERATION_STAGES.find((stage) => !completed.has(stage));
  return ADAPTER_GENERATION_STAGES.map((label) => ({
    label,
    status: completed.has(label) ? 'complete' : label === firstPending ? 'running' : 'pending',
  }));
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}
