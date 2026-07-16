import type { CSSProperties } from 'react';
import { ExternalLink, Eye, Loader2, Plus, Trash2, Wifi } from 'lucide-react';
import type { Client } from '../../types';
import { Button } from '../../components/ui/Button';
import { StatusPill } from '../../components/ui/Badge';
import { CrawlButton } from '../../components/shared/ClientActions';
import { clientPanelHref } from '../../utils/clientLinks';
import { number, shortTime } from '../../utils/format';
import { clientRuntimeStatus } from '../../utils/clientStatus';
import { getCrmVertical } from '../../verticals/registry';

interface ClientCardProps {
  client: Client;
  crawling: boolean;
  style?: CSSProperties;
  onOpenClient: (siteId: string) => void;
  onFilter: (query: string) => void;
  busy: boolean;
  toggling: boolean;
  onToggleClient: (siteId: string, enabled: boolean) => void | Promise<void>;
  onRemoveClient: (siteId: string) => void;
  onTriggerCrawl: (siteId: string) => void;
}

interface AvailableClientGroupProps {
  title: string;
  description: string;
  icon: typeof Wifi;
  clients: Client[];
  emptyText: string;
  onOpenClient: (siteId: string) => void;
  onActivateClient: (siteId: string) => void | Promise<void>;
  busy: boolean;
  activatingSiteId: string;
  onFilter: (query: string) => void;
  onRemoveClient: (siteId: string) => void;
}

interface AvailableClientCardProps {
  client: Client;
  style?: CSSProperties;
  onOpenClient: (siteId: string) => void;
  onActivateClient: (siteId: string) => void | Promise<void>;
  busy: boolean;
  activating: boolean;
  onFilter: (query: string) => void;
  onRemoveClient: (siteId: string) => void;
}

export function ClientCard({
  client,
  crawling,
  style,
  onOpenClient,
  onFilter,
  busy,
  toggling,
  onToggleClient,
  onRemoveClient,
  onTriggerCrawl,
}: ClientCardProps) {
  const vertical = getCrmVertical(client.vertical_key);
  const panelUrl = clientPanelHref(client.site_id);
  return (
    <article className="client-card" style={style}>
      <button
        className="client-card-hit-target"
        type="button"
        aria-label={`Open ${client.name} workspace`}
        onClick={() => onOpenClient(client.site_id)}
      />
      <div className="client-card-head">
        <div className="min-w-0">
          <button
            className="client-card-id client-link-button"
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onOpenClient(client.site_id);
            }}
          >
            {client.site_id}
          </button>
          <a
            className="client-card-url"
            href={client.store_url}
            target="_blank"
            rel="noopener noreferrer"
            title={client.store_url}
            onClick={(event) => event.stopPropagation()}
          >
            {client.store_url}
          </a>
        </div>
        <StatusPill value={client.status} />
      </div>
      <div className="client-card-chips" onClick={(event) => event.stopPropagation()}>
        <button className="badge badge-muted badge-button" type="button" onClick={() => onFilter(client.vertical_label || vertical.label)}>
          {client.vertical_label || vertical.label}
        </button>
        <span className="badge badge-muted">
          {number(client.catalog.active_products)} {vertical.entityLabelPlural}
        </span>
        <span className="badge badge-muted">
          {number(client.answer_cache?.hits ?? 0)} cache hits
        </span>
        <RuntimeStatusPill client={client} />
        <StatusPill value={client.last_crawl_status || 'not_started'} />
      </div>
      <div className="client-card-title">
        <button
          className="client-card-name-button"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onOpenClient(client.site_id);
          }}
        >
          {client.name}
        </button>
        <span className="text-muted">Last crawl: {shortTime(client.last_crawl_at)}</span>
        <small className="client-card-state-line">{currentClientStateLine(client)}</small>
      </div>
      <div className="client-card-actions" onClick={(event) => event.stopPropagation()}>
        <Button
          variant="secondary"
          size="sm"
          type="button"
          disabled={busy}
          spinning={toggling}
          onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
        >
          {toggling ? 'Saving...' : client.status === 'live' ? 'Disable' : 'Enable'}
        </Button>
        <CrawlButton
          siteId={client.site_id}
          label="Crawl"
          active={crawling}
          disabled={clientRuntimeStatus(client) !== 'online'}
          onTriggerCrawl={onTriggerCrawl}
          compact
        />
        <Button variant="secondary" size="sm" type="button" icon={Eye} onClick={() => onOpenClient(client.site_id)}>
          View
        </Button>
        <Button
          variant="danger"
          size="sm"
          type="button"
          icon={Trash2}
          disabled={busy}
          onClick={() => onRemoveClient(client.site_id)}
        >
          Remove
        </Button>
        <a className="btn btn-secondary btn-sm" href={client.store_url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Website
        </a>
        <a className="btn btn-secondary btn-sm" href={panelUrl} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Owner panel
        </a>
      </div>
    </article>
  );
}

export function AvailableClientGroup({
  title,
  description,
  icon: Icon,
  clients,
  emptyText,
  onOpenClient,
  onActivateClient,
  busy,
  activatingSiteId,
  onFilter,
  onRemoveClient,
}: AvailableClientGroupProps) {
  return (
    <section className="available-client-group">
      <div className="available-client-group-head">
        <div>
          <h4><Icon size={16} aria-hidden="true" /> {title}</h4>
          <p>{description}</p>
        </div>
        <span className="badge badge-muted">{number(clients.length)}</span>
      </div>
      {clients.length ? (
        <div className="client-grid">
          {clients.map((client, index) => (
            <AvailableClientCard
              key={client.site_id}
              client={client}
              style={{ animationDelay: `${index * 40}ms` }}
              onOpenClient={onOpenClient}
              onActivateClient={onActivateClient}
              busy={busy}
              activating={activatingSiteId === client.site_id}
              onFilter={onFilter}
              onRemoveClient={onRemoveClient}
            />
          ))}
        </div>
      ) : (
        <div className="client-empty-card subtle">{emptyText}</div>
      )}
    </section>
  );
}

function AvailableClientCard({
  client,
  style,
  onOpenClient,
  onActivateClient,
  busy,
  activating,
  onFilter,
  onRemoveClient,
}: AvailableClientCardProps) {
  const vertical = getCrmVertical(client.vertical_key);
  const panelUrl = clientPanelHref(client.site_id);
  return (
    <article className="client-card client-card-available" style={style}>
      <button
        className="client-card-hit-target"
        type="button"
        aria-label={`Open ${client.name} discovery workspace`}
        onClick={() => onOpenClient(client.site_id)}
      />
      <div className="client-card-head">
        <div className="min-w-0">
          <button
            className="client-card-id client-link-button"
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onOpenClient(client.site_id);
            }}
          >
            {client.site_id}
          </button>
          <a
            className="client-card-url"
            href={client.store_url}
            target="_blank"
            rel="noopener noreferrer"
            title={client.store_url}
            onClick={(event) => event.stopPropagation()}
          >
            {client.store_url}
          </a>
        </div>
        <StatusPill value="available" />
      </div>
      <div className="client-card-chips" onClick={(event) => event.stopPropagation()}>
        <button className="badge badge-muted badge-button" type="button" onClick={() => onFilter(client.vertical_label || vertical.label)}>
          {client.vertical_label || vertical.label}
        </button>
        <span className="badge badge-muted">
          {number(client.catalog.active_products)} {vertical.entityLabelPlural}
        </span>
        <RuntimeStatusPill client={client} />
        <StatusPill value={client.last_crawl_status || 'not_started'} />
      </div>
      <div className="client-card-title">
        <button
          className="client-card-name-button"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onOpenClient(client.site_id);
          }}
        >
          {client.name}
        </button>
        <span className="text-muted">Detected install. Moving it to Current will not start crawling.</span>
        <small className="client-card-state-line">{availableClientStateLine(client)}</small>
      </div>
      <div className="client-card-actions" onClick={(event) => event.stopPropagation()}>
        <Button
          variant="primary"
          size="sm"
          type="button"
          icon={activating ? Loader2 : Plus}
          spinning={activating}
          disabled={busy}
          onClick={() => onActivateClient(client.site_id)}
        >
          {activating ? 'Adding...' : 'Add to current'}
        </Button>
        <Button variant="secondary" size="sm" type="button" icon={Eye} onClick={() => onOpenClient(client.site_id)}>
          View discovery
        </Button>
        <a className="btn btn-secondary btn-sm" href={client.store_url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Website
        </a>
        <a className="btn btn-secondary btn-sm" href={panelUrl} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={14} aria-hidden="true" /> Owner panel
        </a>
        <Button
          variant="danger"
          size="sm"
          type="button"
          icon={Trash2}
          disabled={busy || activating}
          onClick={() => onRemoveClient(client.site_id)}
        >
          Remove
        </Button>
      </div>
    </article>
  );
}

function RuntimeStatusPill({ client }: { client: Client }) {
  const status = clientRuntimeStatus(client);
  return <span className={`status-pill runtime-${status}`}>{status}</span>;
}

function currentClientStateLine(client: Client) {
  const runtime = clientRuntimeStatus(client);
  if (runtime === 'online') return 'Website is reachable. Crawl and setup still run only from explicit actions.';
  if (runtime === 'offline') return 'Website is currently offline from AI Hub; widget controls remain visible for review.';
  return 'Runtime has not reported a fresh online/offline state yet.';
}

function availableClientStateLine(client: Client) {
  const runtime = clientRuntimeStatus(client);
  if (runtime === 'online') return 'Online now: safe to inspect and move to Current. Activation will not crawl.';
  if (runtime === 'offline') return 'Offline now: keep visible for traceability; start the website before setup or crawl.';
  return 'Reachability is unknown; open the website before moving it to Current.';
}
