import { useMemo, useState } from 'react';
import { ExternalLink, Search, X } from 'lucide-react';
import type { Client } from '../types';
import { Button } from '../components/ui/Button';
import { StatusPill } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { MiniMetric } from './ClientDetailView';
import { clientPanelHref } from '../utils/clientLinks';
import { getCrmVertical } from '../verticals/registry';
import { number } from '../utils/format';
import type { ClientWorkspaceTabId } from '../verticals/types';

export interface CatalogsViewProps {
  clients: Client[];
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}

export function CatalogsView({
  clients,
  onOpenClient,
}: CatalogsViewProps) {
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
        client.vertical_key,
        client.vertical_label,
        vertical.label,
      ].some((value) => String(value || '').toLowerCase().includes(normalizedQuery));
    });
  }, [clients, normalizedQuery, statusFilter]);
  const totalCurrent = clients.filter((client) => client.status !== 'available').length;
  const totalAvailable = clients.filter((client) => client.status === 'available').length;
  return (
    <div className="stack">
      <section className="section-header">
        <div>
          <h2>Data storage</h2>
          <p>Source-backed records, vectors, and crawl freshness for every independent client website.</p>
        </div>
      </section>
      <section className="client-board-toolbar" aria-label="Data storage filters">
        <label className="client-search">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search data clients</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            placeholder="Search clients, URLs, verticals, or status"
          />
          {query ? (
            <button type="button" aria-label="Clear data client search" onClick={() => setQuery('')}>
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
          <span>{number(filteredClients.length)} shown</span>
        </div>
      </section>
      {!clients.length ? (
        <EmptyState
          title="No data clients yet"
          message="Install the universal script on an independent website to create an Available client first."
        />
      ) : !filteredClients.length ? (
        <EmptyState title="No matching clients" message="Clear the search or change the status filter." />
      ) : null}
      <div className="grid gap-4 xl:grid-cols-2">
        {filteredClients.map((client) => {
          return (
            <DataClientCard
              key={client.site_id}
              client={client}
              onOpenClient={onOpenClient}
            />
          );
        })}
      </div>
    </div>
  );
}

function DataClientCard({
  client,
  onOpenClient,
}: {
  client: Client;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  const vertical = getCrmVertical(client.vertical_key);
  const entityLabel = titleCase(vertical.entityLabelPlural);
  const automationLocked = client.status === 'available';
  const panelUrl = clientPanelHref(client.site_id);
  return (
    <article className="data-client-card">
      <button
        className="data-client-card-hit-target"
        type="button"
        aria-label={`Open ${client.name} data workspace`}
        onClick={() => onOpenClient(client.site_id, 'catalog')}
      />
      <div className="data-client-card-head">
        <div className="min-w-0">
          <h3>{client.name}</h3>
          <div className="data-client-meta">
            <button type="button" onClick={() => onOpenClient(client.site_id, 'overview')}>
              {client.site_id}
            </button>
            <a href={client.store_url} target="_blank" rel="noopener noreferrer">
              {client.store_url}
              <ExternalLink size={12} aria-hidden="true" />
            </a>
          </div>
        </div>
        <div className="data-client-badges">
          <span className="badge badge-muted">{vertical.label}</span>
          <StatusPill value={client.status} />
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <MiniMetric label={entityLabel} value={client.catalog.active_products} onClick={() => onOpenClient(client.site_id, 'catalog')} />
        <MiniMetric label="Groups" value={client.catalog.categories ?? 0} onClick={() => onOpenClient(client.site_id, 'catalog')} />
        <MiniMetric label="Missing vectors" value={client.catalog.missing_embeddings} onClick={() => onOpenClient(client.site_id, 'catalog')} />
      </div>
      <div className="data-client-note">
        {automationLocked
          ? 'Available clients can be inspected here, but crawls and setup stay locked until the client is moved to Current.'
          : `${number(client.catalog.active_products)} active ${vertical.entityLabelPlural} are available to Maya for source-backed answers.`}
      </div>
      <div className="data-client-card-actions">
        <Button onClick={() => onOpenClient(client.site_id, 'catalog')}>
          Open data
        </Button>
        <Button variant="secondary" onClick={() => onOpenClient(client.site_id, 'integration')}>
          Setup workspace
        </Button>
        <Button variant="secondary" onClick={() => onOpenClient(client.site_id, 'crawl')}>
          Crawl workspace
        </Button>
        <a className="btn btn-secondary" href={client.store_url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Website
        </a>
        <a className="btn btn-secondary" href={panelUrl} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Owner panel
        </a>
        {automationLocked ? (
          <Button variant="ghost" onClick={() => onOpenClient(client.site_id, 'overview')}>
            Review activation
          </Button>
        ) : null}
      </div>
    </article>
  );
}

function titleCase(value: string) {
  return value
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
