import { useMemo, useState } from 'react';
import { Plus, CheckCircle2, Users, Search, X, Wifi, WifiOff, Trash2 } from 'lucide-react';
import type { Client, ClientBoardSection } from '../../types';
import { Button, IconButton } from '../../components/ui/Button';
import { Panel } from '../../components/ui/Panel';
import { Table } from '../../components/ui/Table';
import { StatusPill } from '../../components/ui/Badge';
import { ClientActionMenu } from '../../components/shared/ActionMenu';
import { CrawlButton } from '../../components/shared/ClientActions';
import { UniversalInstallerPanel } from '../../components/shared/UniversalInstallerPanel';
import { number } from '../../utils/format';
import { clientRuntimeStatus } from '../../utils/clientStatus';
import { getCrmVertical } from '../../verticals/registry';
import { ClientBoardFocus } from './ClientBoardFocus';
import { clientBoardSectionLabel } from './clientBoardModel';
import { AvailableClientGroup, ClientCard } from './ClientCards';
import { PaginationControl } from '../../components/shared/controls/PaginationControl';
import { usePagination } from '../../hooks/usePagination';

const CLIENT_PAGE_SIZE = 8;
const AVAILABLE_CLIENT_PAGE_SIZE = 6;

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
  const availableOnlineClients = availableClients.filter((client) => clientRuntimeStatus(client) === 'online');
  const availableOfflineClients = availableClients.filter((client) => clientRuntimeStatus(client) !== 'online');
  const showCurrentSection = clientBoardSection === 'all' || clientBoardSection === 'current';
  const showAvailableSection = clientBoardSection === 'all' || clientBoardSection === 'available' || clientBoardSection === 'online' || clientBoardSection === 'offline';
  const showOnlineGroup = clientBoardSection === 'all' || clientBoardSection === 'available' || clientBoardSection === 'online';
  const showOfflineGroup = clientBoardSection === 'all' || clientBoardSection === 'available' || clientBoardSection === 'offline';
  const activeSectionLabel = clientBoardSectionLabel(clientBoardSection);
  const totalCurrent = visibleClients.filter((client) => client.status !== 'available').length;
  const totalAvailable = visibleClients.filter((client) => client.status === 'available').length;
  const totalAvailableOnline = visibleClients.filter((client) => client.status === 'available' && clientRuntimeStatus(client) === 'online').length;
  const totalAvailableOffline = totalAvailable - totalAvailableOnline;
  const useCards = currentClients.length <= 8;
  const paginationResetKey = `${clientBoardSection}|${normalizedQuery}`;
  const currentPagination = usePagination(currentClients, CLIENT_PAGE_SIZE, paginationResetKey);
  const onlinePagination = usePagination(availableOnlineClients, AVAILABLE_CLIENT_PAGE_SIZE, paginationResetKey);
  const offlinePagination = usePagination(availableOfflineClients, AVAILABLE_CLIENT_PAGE_SIZE, paginationResetKey);

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
                {currentPagination.pageItems.map((client, index) => (
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
                    {currentPagination.pageItems.map((client) => (
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
                              disabled={clientRuntimeStatus(client) !== 'online'}
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
            {currentClients.length ? (
              <PaginationControl
                page={currentPagination.page}
                pageCount={currentPagination.pageCount}
                pageSize={CLIENT_PAGE_SIZE}
                totalItems={currentClients.length}
                itemLabel="clients"
                onPageChange={currentPagination.setPage}
              />
            ) : null}
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
                  <div>
                    <AvailableClientGroup
                      title="Online installs"
                      description="Website is reachable now. You can inspect it or move it to Current."
                      icon={Wifi}
                      clients={onlinePagination.pageItems}
                      emptyText="No available installs are online right now."
                      onOpenClient={onOpenClient}
                      onActivateClient={handleActivateClient}
                      busy={busy}
                      activatingSiteId={activatingSiteId}
                      onFilter={setQuery}
                      onRemoveClient={onRemoveClient}
                    />
                    {availableOnlineClients.length ? (
                      <PaginationControl
                        page={onlinePagination.page}
                        pageCount={onlinePagination.pageCount}
                        pageSize={AVAILABLE_CLIENT_PAGE_SIZE}
                        totalItems={availableOnlineClients.length}
                        itemLabel="online installs"
                        onPageChange={onlinePagination.setPage}
                      />
                    ) : null}
                  </div>
                ) : null}
                {showOfflineGroup ? (
                  <div>
                    <AvailableClientGroup
                      title="Offline installs"
                      description="Previously detected, but the website is not reachable from AI Hub right now."
                      icon={WifiOff}
                      clients={offlinePagination.pageItems}
                      emptyText="No offline available installs."
                      onOpenClient={onOpenClient}
                      onActivateClient={handleActivateClient}
                      busy={busy}
                      activatingSiteId={activatingSiteId}
                      onFilter={setQuery}
                      onRemoveClient={onRemoveClient}
                    />
                    {availableOfflineClients.length ? (
                      <PaginationControl
                        page={offlinePagination.page}
                        pageCount={offlinePagination.pageCount}
                        pageSize={AVAILABLE_CLIENT_PAGE_SIZE}
                        totalItems={availableOfflineClients.length}
                        itemLabel="offline installs"
                        onPageChange={offlinePagination.setPage}
                      />
                    ) : null}
                  </div>
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

