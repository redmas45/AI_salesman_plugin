import { useMemo, useState, type CSSProperties } from 'react';
import { Plus, CheckCircle2, Eye, Users, Search, X, ExternalLink, Wifi, WifiOff, Loader2, Trash2 } from 'lucide-react';
import type { Client, ClientBoardSection } from '../types';
import { Button, IconButton } from '../components/ui/Button';
import { Panel } from '../components/ui/Panel';
import { Table } from '../components/ui/Table';
import { StatusPill } from '../components/ui/Badge';
import { ClientActionMenu } from '../components/shared/ActionMenu';
import { CrawlButton } from '../components/shared/ClientActions';
import { UniversalInstallerPanel } from '../components/shared/UniversalInstallerPanel';
import { clientPanelHref } from '../utils/clientLinks';
import { number, shortTime } from '../utils/format';
import { getCrmVertical } from '../verticals/registry';

export interface ClientsViewProps {
  clients: Client[];
  clientBoardSection: ClientBoardSection;
  busy: boolean;
  crawlingSites: Set<string>;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onAddClient: () => void;
  onOpenClient: (siteId: string) => void;
  onActivateClient: (siteId: string) => void | Promise<void>;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void | Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onOpenPasswordDialog: (client: Client) => void;
}

export function ClientsView({
  clients,
  clientBoardSection,
  busy,
  crawlingSites,
  onOpenClientBoardSection,
  onAddClient,
  onOpenClient,
  onActivateClient,
  onRemoveClient,
  onToggleClient,
  onTriggerCrawl,
  onOpenPasswordDialog,
}: ClientsViewProps) {
  const [query, setQuery] = useState('');
  const [activatingSiteId, setActivatingSiteId] = useState('');
  const [togglingSiteId, setTogglingSiteId] = useState('');
  const normalizedQuery = query.trim().toLowerCase();
  const visibleClients = useMemo(() => {
    const normalizeOrigin = (urlStr: string) => {
      try {
        const url = new URL(urlStr);
        let hostname = url.hostname;
        if (hostname === '127.0.0.1' || hostname === 'localhost' || hostname === 'host.docker.internal') {
           hostname = 'localhost';
        }
        return `${url.protocol}//${hostname}:${url.port}`;
      } catch {
        return urlStr;
      }
    };
    
    const explicitOrigins = new Set(
      clients.filter(c => !c.site_id.startsWith('auto_')).map(c => normalizeOrigin(c.store_url || ''))
    );
    
    return clients.filter(client => {
      if (client.status === 'available' && client.site_id.startsWith('auto_')) {
        const origin = normalizeOrigin(client.store_url || '');
        if (explicitOrigins.has(origin)) {
          return false;
        }
      }
      return true;
    });
  }, [clients]);

  const searchedClients = useMemo(() => {
    if (!normalizedQuery) return visibleClients;
    return visibleClients.filter((client) => {
      const vertical = getCrmVertical(client.vertical_key);
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
  }, [visibleClients, normalizedQuery]);
  const currentClients = searchedClients.filter((client) => client.status !== 'available');
  const availableClients = searchedClients.filter((client) => client.status === 'available');
  const availableOnlineClients = availableClients.filter((client) => runtimeStatus(client) === 'online');
  const availableOfflineClients = availableClients.filter((client) => runtimeStatus(client) !== 'online');
  const showCurrentSection = clientBoardSection === 'all' || clientBoardSection === 'current';
  const showAvailableSection = clientBoardSection === 'all' || clientBoardSection === 'available' || clientBoardSection === 'online' || clientBoardSection === 'offline';
  const showOnlineGroup = clientBoardSection === 'all' || clientBoardSection === 'available' || clientBoardSection === 'online';
  const showOfflineGroup = clientBoardSection === 'all' || clientBoardSection === 'available' || clientBoardSection === 'offline';
  const activeSectionLabel = clientBoardSectionLabel(clientBoardSection);
  const totalCurrent = visibleClients.filter((client) => client.status !== 'available').length;
  const totalAvailable = visibleClients.filter((client) => client.status === 'available').length;
  const totalAvailableOnline = visibleClients.filter((client) => client.status === 'available' && runtimeStatus(client) === 'online').length;
  const totalAvailableOffline = totalAvailable - totalAvailableOnline;
  const useCards = currentClients.length <= 8;

  async function handleActivateClient(siteId: string) {
    setActivatingSiteId(siteId);
    try {
      await onActivateClient(siteId);
    } finally {
      setActivatingSiteId((current) => (current === siteId ? '' : current));
    }
  }

  async function handleToggleClient(siteId: string, enabled: boolean) {
    setTogglingSiteId(siteId);
    try {
      await onToggleClient(siteId, enabled);
    } finally {
      setTogglingSiteId((current) => (current === siteId ? '' : current));
    }
  }

  return (
    <div className="grid gap-4">
      <div className="page-header">
        <div>
          <h2>Clients</h2>
          <p>Detected installs stay available until you explicitly activate them for Maya.</p>
        </div>
        <Button icon={Plus} variant="secondary" type="button" onClick={onAddClient} disabled={busy}>
          Manual client
        </Button>
      </div>
      <UniversalInstallerPanel compact />
      <section className="client-board-toolbar" aria-label="Client list controls">
        <label className="client-search">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search clients</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search clients, URLs, verticals, or status"
          />
          {query ? (
            <button type="button" aria-label="Clear client search" onClick={() => setQuery('')}>
              <X size={14} aria-hidden="true" />
            </button>
          ) : null}
        </label>
        <div className="client-board-counts" aria-label="Client board shortcuts">
          <button
            type="button"
            className={clientBoardSection === 'current' ? 'active' : undefined}
            aria-pressed={clientBoardSection === 'current'}
            onClick={() => onOpenClientBoardSection('current')}
          >
            {number(totalCurrent)} current
          </button>
          <button
            type="button"
            className={clientBoardSection === 'available' ? 'active' : undefined}
            aria-pressed={clientBoardSection === 'available'}
            onClick={() => onOpenClientBoardSection('available')}
          >
            {number(totalAvailable)} available
          </button>
          <button
            type="button"
            className={clientBoardSection === 'online' ? 'active' : undefined}
            aria-pressed={clientBoardSection === 'online'}
            onClick={() => onOpenClientBoardSection('online')}
          >
            {number(totalAvailableOnline)} online
          </button>
          <button
            type="button"
            className={clientBoardSection === 'offline' ? 'active' : undefined}
            aria-pressed={clientBoardSection === 'offline'}
            onClick={() => onOpenClientBoardSection('offline')}
          >
            {number(totalAvailableOffline)} offline
          </button>
          <button
            type="button"
            className={clientBoardSection === 'all' ? 'active' : undefined}
            aria-pressed={clientBoardSection === 'all'}
            onClick={() => onOpenClientBoardSection('all')}
          >
            {number(visibleClients.length)} total
          </button>
        </div>
      </section>
      <ClientBoardFocus
        section={clientBoardSection}
        label={activeSectionLabel}
        query={normalizedQuery ? query.trim() : ''}
        counts={{
          current: totalCurrent,
          available: totalAvailable,
          online: totalAvailableOnline,
          offline: totalAvailableOffline,
        }}
        onOpenSection={onOpenClientBoardSection}
      />
      {!visibleClients.length ? (
        <div className="card">
          <div className="empty-state">
            <Users size={48} className="empty-icon" aria-hidden="true" />
            <h3>No clients detected yet</h3>
            <p>Paste the universal installer into an independent website, open that site once, then refresh AI Hub.</p>
            <Button icon={Plus} variant="secondary" type="button" onClick={onAddClient} disabled={busy}>
              Manual fallback
            </Button>
          </div>
        </div>
      ) : (
        <>
          {showCurrentSection ? (
          <section className="client-section" id="client-board-current">
            <div className="client-section-heading">
              <div>
                <h3>Current clients</h3>
                <p>Activated tenants Maya can serve. Crawls and setup runs only from explicit actions.</p>
              </div>
              <span className="badge badge-muted">{number(currentClients.length)} current</span>
            </div>
            {!currentClients.length ? (
              <div className="card client-empty-card">
                <h3>No current clients</h3>
                <p>{normalizedQuery ? 'No current clients match this search.' : 'Move a discovered install from Available clients when you are ready to manage it.'}</p>
              </div>
            ) : useCards ? (
              <div className="client-grid">
                {currentClients.map((client, index) => (
                  <ClientCard
                    key={client.site_id}
                    client={client}
                    crawling={crawlingSites.has(client.site_id)}
                    style={{ animationDelay: `${index * 40}ms` }}
                    onOpenClient={onOpenClient}
                    onFilter={setQuery}
                    busy={busy}
                    toggling={togglingSiteId === client.site_id}
                    onToggleClient={handleToggleClient}
                    onRemoveClient={onRemoveClient}
                    onTriggerCrawl={onTriggerCrawl}
                  />
                ))}
              </div>
            ) : (
              <Panel title="Current client directory">
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
                    {currentClients.map((client) => (
                      <tr key={client.site_id} className="clickable-row" onClick={() => onOpenClient(client.site_id)}>
                        <td>
                          <strong className="client-table-name">{client.name}</strong>
                          <a
                            className="client-table-url mt-1"
                            href={client.store_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={client.store_url}
                            onClick={(event) => event.stopPropagation()}
                          >
                            {client.store_url}
                          </a>
                        </td>
                        <td>
                          <code className="breakable-code">{client.site_id}</code>
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
                          <div className="client-table-actions" onClick={(event) => event.stopPropagation()}>
                            <CrawlButton
                              siteId={client.site_id}
                              label="Crawl"
                              active={crawlingSites.has(client.site_id)}
                              disabled={runtimeStatus(client) !== 'online'}
                              onTriggerCrawl={onTriggerCrawl}
                              compact
                            />
                            <IconButton
                              label={client.status === 'live' ? 'Disable' : 'Enable'}
                              icon={CheckCircle2}
                              disabled={busy}
                              onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
                            />
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
          </section>
          ) : null}
          {showAvailableSection ? (
          <section className="client-section" id="client-board-available">
            <div className="client-section-heading">
              <div>
                <h3>Available clients</h3>
                <p>Script-detected sites waiting for admin approval before Maya controls or crawls them.</p>
              </div>
              <span className="badge badge-muted">{number(availableClients.length)} available</span>
            </div>
            {!availableClients.length ? (
              <div className="card client-empty-card">
                <h3>No available clients</h3>
                <p>{normalizedQuery ? 'No available clients match this search.' : 'When a new website loads the universal installer, it will appear here first.'}</p>
              </div>
            ) : (
              <div className="available-client-groups">
                {showOnlineGroup ? (
                  <AvailableClientGroup
                    title="Online installs"
                    description="Website is reachable now. You can inspect it or move it to Current."
                    icon={Wifi}
                    clients={availableOnlineClients}
                    emptyText="No available installs are online right now."
                    onOpenClient={onOpenClient}
                    onActivateClient={handleActivateClient}
                    busy={busy}
                    activatingSiteId={activatingSiteId}
                    onFilter={setQuery}
                    onRemoveClient={onRemoveClient}
                  />
                ) : null}
                {showOfflineGroup ? (
                  <AvailableClientGroup
                    title="Offline installs"
                    description="Previously detected, but the website is not reachable from AI Hub right now."
                    icon={WifiOff}
                    clients={availableOfflineClients}
                    emptyText="No offline available installs."
                    onOpenClient={onOpenClient}
                    onActivateClient={handleActivateClient}
                    busy={busy}
                    activatingSiteId={activatingSiteId}
                    onFilter={setQuery}
                    onRemoveClient={onRemoveClient}
                  />
                ) : null}
              </div>
            )}
          </section>
          ) : null}
        </>
      )}
    </div>
  );
}

function clientBoardSectionLabel(section: ClientBoardSection) {
  if (section === 'current') return 'Current clients';
  if (section === 'available') return 'Available installs';
  if (section === 'online') return 'Online installs';
  if (section === 'offline') return 'Offline installs';
  return 'All clients';
}

function ClientBoardFocus({
  section,
  label,
  query,
  counts,
  onOpenSection,
}: {
  section: ClientBoardSection;
  label: string;
  query: string;
  counts: { current: number; available: number; online: number; offline: number };
  onOpenSection: (section: ClientBoardSection) => void;
}) {
  const next = clientBoardNextStep(section, counts);
  const target = clientBoardRecommendedSection(section, counts);
  return (
    <section className="client-board-focus" aria-label="Active client board section">
      <div className="client-board-focus-copy">
        <span>Viewing</span>
        <strong>{label}</strong>
        <small>
          {query
            ? `Filtered by "${query}"`
            : `${number(counts.current)} current / ${number(counts.available)} available / ${number(counts.online)} online / ${number(counts.offline)} offline`}
        </small>
      </div>
      <button className="client-board-next-step" type="button" onClick={() => onOpenSection(target)}>
        <span>Next step</span>
        <strong>{next}</strong>
        <small>{clientBoardRecommendedLabel(target)}</small>
      </button>
    </section>
  );
}

function clientBoardNextStep(section: ClientBoardSection, counts: { current: number; available: number; online: number; offline: number }) {
  if (section === 'current') {
    if (!counts.current) return 'Move an online available install to Current before running setup or crawl.';
    return 'Open a client workspace, then run setup, readiness, or crawl only when you explicitly choose it.';
  }
  if (section === 'online') {
    if (!counts.online) return 'Start the test website and refresh AI Hub; online installs will appear here.';
    return 'Inspect the website and owner panel, then add the install to Current if it should be managed.';
  }
  if (section === 'offline') {
    if (!counts.offline) return 'No detected installs are unreachable right now.';
    return 'These installs were detected before, but the source website is not reachable from AI Hub right now.';
  }
  if (section === 'available') {
    if (!counts.available) return 'Install the script on a website and open that site once to create an Available install.';
    return 'Use Online installs for active testing; Offline installs are visible for traceability only.';
  }
  return 'Use Current for managed clients and Available for detected installs awaiting approval.';
}

function clientBoardRecommendedSection(section: ClientBoardSection, counts: { current: number; available: number; online: number; offline: number }): ClientBoardSection {
  if (section === 'current' && !counts.current) return counts.online ? 'online' : 'available';
  if (section === 'available') return counts.online ? 'online' : counts.offline ? 'offline' : 'all';
  if (section === 'online' && !counts.online) return counts.available ? 'available' : 'all';
  if (section === 'offline' && !counts.offline) return counts.available ? 'available' : 'all';
  return section;
}

function clientBoardRecommendedLabel(section: ClientBoardSection) {
  if (section === 'current') return 'Open current clients';
  if (section === 'available') return 'Open available installs';
  if (section === 'online') return 'Open online installs';
  if (section === 'offline') return 'Open offline installs';
  return 'Open all clients';
}

function ClientCard({
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
}: {
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
}) {
  const vertical = getCrmVertical(client.vertical_key);
  const panelUrl = clientPanelHref(client.site_id);
  return (
    <article
      className="client-card"
      style={style}
    >
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
          disabled={runtimeStatus(client) !== 'online'}
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

function AvailableClientGroup({
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
}: {
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
}) {
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
}: {
  client: Client;
  style?: CSSProperties;
  onOpenClient: (siteId: string) => void;
  onActivateClient: (siteId: string) => void | Promise<void>;
  busy: boolean;
  activating: boolean;
  onFilter: (query: string) => void;
  onRemoveClient: (siteId: string) => void;
}) {
  const vertical = getCrmVertical(client.vertical_key);
  const panelUrl = clientPanelHref(client.site_id);
  return (
    <article
      className="client-card client-card-available"
      style={style}
    >
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
  const status = runtimeStatus(client);
  return <span className={`status-pill runtime-${status}`}>{status}</span>;
}

function runtimeStatus(client: Client) {
  return String(client.runtime_status?.status || 'unknown').toLowerCase();
}

function currentClientStateLine(client: Client) {
  const runtime = runtimeStatus(client);
  if (runtime === 'online') return 'Website is reachable. Crawl and setup still run only from explicit actions.';
  if (runtime === 'offline') return 'Website is currently offline from AI Hub; widget controls remain visible for review.';
  return 'Runtime has not reported a fresh online/offline state yet.';
}

function availableClientStateLine(client: Client) {
  const runtime = runtimeStatus(client);
  if (runtime === 'online') return 'Online now: safe to inspect and move to Current. Activation will not crawl.';
  if (runtime === 'offline') return 'Offline now: keep visible for traceability; start the website before setup or crawl.';
  return 'Reachability is unknown; open the website before moving it to Current.';
}
