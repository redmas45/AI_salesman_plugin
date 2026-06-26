import type { CSSProperties } from 'react';
import { Plus, CheckCircle2, Eye, Users } from 'lucide-react';
import type { Client } from '../types';
import { Button, IconButton } from '../components/ui/Button';
import { Panel } from '../components/ui/Panel';
import { Table } from '../components/ui/Table';
import { StatusPill } from '../components/ui/Badge';
import { ClientActionMenu } from '../components/shared/ActionMenu';
import { CrawlButton } from '../components/shared/ClientActions';
import { number, shortTime } from '../utils/format';
import { getCrmVertical } from '../verticals/registry';

export interface ClientsViewProps {
  clients: Client[];
  crawlingSites: Set<string>;
  onAddClient: () => void;
  onOpenClient: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onTriggerCrawl: (siteId: string) => void;
  onOpenPasswordDialog: (client: Client) => void;
}

export function ClientsView({
  clients,
  crawlingSites,
  onAddClient,
  onOpenClient,
  onRemoveClient,
  onToggleClient,
  onTriggerCrawl,
  onOpenPasswordDialog,
}: ClientsViewProps) {
  const useCards = clients.length <= 8;
  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Clients</h2>
          <p>Manage tenants, crawler state, catalog coverage, and client panel access.</p>
        </div>
        <Button icon={Plus} type="button" onClick={onAddClient}>
          Add client
        </Button>
      </div>
      {!clients.length ? (
        <div className="card">
          <div className="empty-state">
            <Users size={48} className="empty-icon" aria-hidden="true" />
            <h3>No clients yet</h3>
            <p>Add your first client to start crawling and serving the AI widget.</p>
            <Button icon={Plus} type="button" onClick={onAddClient}>
              Add client
            </Button>
          </div>
        </div>
      ) : useCards ? (
        <div className="client-grid">
          {clients.map((client, index) => (
            <ClientCard
              key={client.site_id}
              client={client}
              crawling={crawlingSites.has(client.site_id)}
              style={{ animationDelay: `${index * 40}ms` }}
              onOpenClient={onOpenClient}
              onToggleClient={onToggleClient}
              onTriggerCrawl={onTriggerCrawl}
            />
          ))}
        </div>
      ) : (
        <Panel title="Client directory">
          <Table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Site ID</th>
                <th>Vertical</th>
                <th>Status</th>
                <th>Indexed</th>
                <th>Turns</th>
                <th>Tokens</th>
                <th>Crawler</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((client) => (
                <tr key={client.site_id} className="clickable-row" onClick={() => onOpenClient(client.site_id)}>
                  <td>
                    <strong>{client.name}</strong>
                    <span className="mt-1 block text-xs text-muted truncate-text" title={client.store_url}>
                      {client.store_url}
                    </span>
                  </td>
                  <td>
                    <code>{client.site_id}</code>
                  </td>
                  <td>{client.vertical_label || getCrmVertical(client.vertical_key).label}</td>
                  <td>
                    <StatusPill value={client.status} />
                  </td>
                  <td>{number(client.catalog.active_products)}</td>
                  <td>{number(client.usage.total_turns)}</td>
                  <td>{number(client.usage.tokens_estimated)}</td>
                  <td>
                    <StatusPill value={client.last_crawl_status || 'not_started'} />
                  </td>
                  <td>
                    <div className="flex gap-2" onClick={(event) => event.stopPropagation()}>
                      <CrawlButton
                        siteId={client.site_id}
                        label="Crawl"
                        active={crawlingSites.has(client.site_id)}
                        onTriggerCrawl={onTriggerCrawl}
                        compact
                      />
                      <IconButton
                        label={client.status === 'live' ? 'Disable' : 'Enable'}
                        icon={CheckCircle2}
                        onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
                      />
                      <ClientActionMenu
                        client={client}
                        onOpenClient={onOpenClient}
                        onOpenPasswordDialog={onOpenPasswordDialog}
                        onRemoveClient={onRemoveClient}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Panel>
      )}
    </div>
  );
}

function ClientCard({
  client,
  crawling,
  style,
  onOpenClient,
  onToggleClient,
  onTriggerCrawl,
}: {
  client: Client;
  crawling: boolean;
  style?: CSSProperties;
  onOpenClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onTriggerCrawl: (siteId: string) => void;
}) {
  const vertical = getCrmVertical(client.vertical_key);
  return (
    <article className="client-card" style={style} role="button" tabIndex={0} onClick={() => onOpenClient(client.site_id)} onKeyDown={(event) => {
      if (event.key === 'Enter' || event.key === ' ') onOpenClient(client.site_id);
    }}>
      <div className="client-card-head">
        <div className="min-w-0">
          <div className="client-card-id">{client.site_id}</div>
          <div className="client-card-url" title={client.store_url}>{client.store_url}</div>
        </div>
        <StatusPill value={client.status} />
      </div>
      <div className="client-card-chips">
        <span className="badge badge-muted">{client.vertical_label || vertical.label}</span>
        <span className="badge badge-muted">
          {number(client.catalog.active_products)} {vertical.entityLabelPlural}
        </span>
        <StatusPill value={client.last_crawl_status || 'not_started'} />
      </div>
      <div className="grid gap-1 text-sm">
        <strong>{client.name}</strong>
        <span className="text-muted">Last crawl: {shortTime(client.last_crawl_at)}</span>
      </div>
      <div className="client-card-actions" onClick={(event) => event.stopPropagation()}>
        <Button
          variant="secondary"
          size="sm"
          type="button"
          onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
        >
          {client.status === 'live' ? 'Disable' : 'Enable'}
        </Button>
        <CrawlButton
          siteId={client.site_id}
          label="Crawl"
          active={crawling}
          onTriggerCrawl={onTriggerCrawl}
          compact
        />
        <Button variant="secondary" size="sm" type="button" icon={Eye} onClick={() => onOpenClient(client.site_id)}>
          View
        </Button>
      </div>
    </article>
  );
}
