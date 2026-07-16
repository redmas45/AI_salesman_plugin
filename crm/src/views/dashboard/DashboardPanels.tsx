import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Users,
  Wifi,
  WifiOff,
  type LucideIcon,
} from 'lucide-react';
import type { AnalyticsResponse, Client, ClientBoardSection, HealthSnapshot, UsageEvent } from '../../types';
import { ActivityList } from '../../components/shared/ActivityList';
import { PaginationControl } from '../../components/shared/controls/PaginationControl';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { StatusPill } from '../../components/ui/Badge';
import { healthState, labelize, number } from '../../utils/format';
import { clientRuntimeStatus } from '../../utils/clientStatus';
import { rangeLabel } from '../../utils/range';
import { getCrmVertical } from '../../verticals/registry';
import { usePagination } from '../../hooks/usePagination';

const DASHBOARD_ACTIVITY_PAGE_SIZE = 3;

export function DashboardTrendChart({
  analytics,
  range,
  onOpenAnalytics,
}: {
  analytics: AnalyticsResponse | null;
  range: string;
  onOpenAnalytics: () => void;
}) {
  const visibleRows = (analytics?.series ?? []).slice(-14);
  const maxTurns = Math.max(...visibleRows.map((row) => row.turns), 1);
  const chart = buildDemandLineChart(visibleRows, maxTurns);
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Demand trend</h2>
          <span className="card-meta">{rangeLabel(range)}</span>
        </div>
        <Button variant="ghost" type="button" onClick={onOpenAnalytics}>
          View analytics
        </Button>
      </div>
      {visibleRows.length ? (
        <div className="demand-line-chart">
          <svg className="demand-line-svg" viewBox="0 0 720 220" preserveAspectRatio="none" role="img" aria-label={`Demand trend for ${rangeLabel(range)}`}>
            <defs>
              <linearGradient id="demand-line-fill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#5d5fef" stopOpacity="0.26" />
                <stop offset="100%" stopColor="#20c8ee" stopOpacity="0.02" />
              </linearGradient>
              <linearGradient id="demand-line-stroke" x1="0" x2="1" y1="0" y2="0">
                <stop offset="0%" stopColor="#20c8ee" />
                <stop offset="55%" stopColor="#5d5fef" />
                <stop offset="100%" stopColor="#b067ff" />
              </linearGradient>
            </defs>
            {[0, 1, 2, 3].map((line) => (
              <line key={line} x1="34" x2="696" y1={24 + line * 40} y2={24 + line * 40} className="demand-line-grid" />
            ))}
            <path d={chart.areaPath} className="demand-line-area" />
            <path d={chart.linePath} className="demand-line-path" />
            {chart.points.map((point) => (
              <g key={point.date}>
                <circle cx={point.x} cy={point.y} r="4.5" className="demand-line-dot-halo" />
                <circle cx={point.x} cy={point.y} r="2.7" className="demand-line-dot">
                  <title>{`${point.date}: ${number(point.turns)} turns, ${number(point.tokens)} tokens`}</title>
                </circle>
              </g>
            ))}
          </svg>
          <div className="demand-line-axis" aria-hidden="true">
            {chart.points.map((point) => (
              <span key={point.date}>{point.date.slice(5)}</span>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState text="No trend data yet." />
      )}
    </>
  );
}

function buildDemandLineChart(rows: AnalyticsResponse['series'], maxTurns: number) {
  const width = 720;
  const height = 220;
  const padding = { top: 24, right: 24, bottom: 30, left: 34 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const denominator = Math.max(rows.length - 1, 1);
  const baseline = height - padding.bottom;
  const points = rows.map((row, index) => {
    const x = rows.length === 1 ? padding.left + plotWidth / 2 : padding.left + (index / denominator) * plotWidth;
    const y = padding.top + plotHeight - (row.turns / maxTurns) * plotHeight;
    return { ...row, x, y };
  });
  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
  const areaPath = points.length
    ? `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${baseline} L ${points[0].x.toFixed(1)} ${baseline} Z`
    : '';
  return { points, linePath, areaPath };
}

export function ClientRegistryPanel({
  clients,
  onOpenClient,
  onOpenSection,
}: {
  clients: Client[];
  onOpenClient: (siteId: string) => void;
  onOpenSection: (section: ClientBoardSection) => void;
}) {
  const currentClients = clients.filter((client) => client.status !== 'available').length;
  const availableClients = clients.length - currentClients;
  const currentClientRows = clients.filter((client) => client.status !== 'available').slice(0, 4);
  const availableRows = clients.filter((client) => client.status === 'available');
  const onlineInstalls = availableRows.filter((client) => clientRuntimeStatus(client) === 'online');
  const offlineInstalls = availableRows.length - onlineInstalls.length;
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Client registry</h2>
          <span className="card-meta">
            {number(currentClients)} current / {number(availableClients)} available
          </span>
        </div>
        <Button variant="ghost" type="button" onClick={() => onOpenSection('all')}>
          Open all
        </Button>
      </div>
      {clients.length ? (
        <div className="client-registry-panel">
          <div className="client-registry-section">
            <div className="client-registry-section-head">
              <span>
                <CheckCircle2 size={14} aria-hidden="true" />
                Current clients
              </span>
              <button type="button" onClick={() => onOpenSection('current')}>
                {number(currentClients)} open
              </button>
            </div>
            {currentClientRows.length ? (
              <div className="client-mini-list">
                {currentClientRows.map((client, index) => (
                  <ClientMiniRow
                    key={client.site_id}
                    client={client}
                    index={index}
                    onOpenClient={onOpenClient}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No current clients"
                message="Approve an available install before Maya crawls, runs setup, or controls a website."
                action={
                  <Button variant="secondary" size="sm" type="button" onClick={() => onOpenSection('available')}>
                    Open available installs
                  </Button>
                }
              />
            )}
          </div>
          <div className="client-registry-section">
            <div className="client-registry-section-head">
              <span>
                <Users size={14} aria-hidden="true" />
                Available installs
              </span>
              <button type="button" onClick={() => onOpenSection('available')}>
                {number(availableClients)} review
              </button>
            </div>
            <div className="install-status-grid">
              <InstallStatusButton
                icon={Wifi}
                label="Online"
                count={onlineInstalls.length}
                detail="Reachable now"
                tone="online"
                onClick={() => onOpenSection('online')}
              />
              <InstallStatusButton
                icon={WifiOff}
                label="Offline"
                count={offlineInstalls}
                detail="Detected earlier"
                tone="offline"
                onClick={() => onOpenSection('offline')}
              />
            </div>
          </div>
        </div>
      ) : (
        <EmptyState title="No clients yet" message="Detected installs and current clients will appear here after the AI Hub script reports in." />
      )}
    </>
  );
}

function ClientMiniRow({
  client,
  index,
  onOpenClient,
}: {
  client: Client;
  index: number;
  onOpenClient: (siteId: string) => void;
}) {
  const vertical = getCrmVertical(client.vertical_key);
  const runtime = clientRuntimeStatus(client);
  return (
    <button
      className="client-mini-row"
      type="button"
      onClick={() => onOpenClient(client.site_id)}
      style={{ animationDelay: `${index * 30}ms` }}
    >
      <span className="client-mini-avatar">{client.site_id.slice(0, 2).toUpperCase()}</span>
      <div className="client-mini-copy">
        <strong title={client.name}>{client.name}</strong>
        <span title={client.store_url}>{number(client.catalog.active_products)} active {vertical.entityLabelPlural}</span>
        <a
          className="client-mini-url"
          href={client.store_url}
          target="_blank"
          rel="noopener noreferrer"
          title={client.store_url}
          onClick={(event) => event.stopPropagation()}
        >
          {client.store_url}
          <ExternalLink size={11} aria-hidden="true" />
        </a>
      </div>
      <span className="client-mini-statuses">
        <StatusPill value={client.status} />
        <span className={`status-pill runtime-${runtime}`}>{runtime}</span>
      </span>
      <ArrowRight size={14} aria-hidden="true" className="client-mini-arrow" />
    </button>
  );
}

function InstallStatusButton({
  icon: Icon,
  label,
  count,
  detail,
  tone,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  count: number;
  detail: string;
  tone: 'online' | 'offline';
  onClick: () => void;
}) {
  return (
    <button className={`install-status-button ${tone}`} type="button" onClick={onClick}>
      <span className="install-status-icon">
        <Icon size={16} aria-hidden="true" />
      </span>
      <span>
        <strong>{number(count)}</strong>
        <small>{label}</small>
      </span>
      <em>{detail}</em>
    </button>
  );
}

export function RecentActivityFeed({ items, onOpen }: { items: UsageEvent[]; onOpen: () => void }) {
  const pagination = usePagination(items, DASHBOARD_ACTIVITY_PAGE_SIZE);
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Recent activity</h2>
          <span className="card-meta">Latest {number(items.length)} events</span>
        </div>
        <Button variant="ghost" type="button" onClick={onOpen}>
          Open conversations
        </Button>
      </div>
      <ActivityList items={pagination.pageItems} />
      <PaginationControl
        page={pagination.page}
        pageCount={pagination.pageCount}
        pageSize={DASHBOARD_ACTIVITY_PAGE_SIZE}
        totalItems={items.length}
        itemLabel="events"
        onPageChange={pagination.setPage}
      />
    </>
  );
}

export function HealthStatusPanel({ health, onOpenHealth }: { health: HealthSnapshot; onOpenHealth: () => void }) {
  const entries = Object.entries(health);
  return (
    <>
      <div className="card-header">
        <div>
          <h2>Quick health</h2>
          <span className="card-meta">{number(entries.length)} checks</span>
        </div>
        <Button variant="ghost" type="button" onClick={onOpenHealth}>
          Open health
        </Button>
      </div>
      {entries.length ? (
        <div className="health-compact-list">
          {entries.map(([key, value]) => {
            const state = healthState(value);
            return (
              <button key={key} className={`health-compact-row ${state}`} type="button" onClick={onOpenHealth}>
                <span className="health-compact-name">{labelize(key)}</span>
                <span className="health-compact-status">
                  <StatusPill value={value || 'unknown'} />
                </span>
                <ArrowRight size={14} aria-hidden="true" />
              </button>
            );
          })}
        </div>
      ) : (
        <EmptyState text="No health checks returned." />
      )}
    </>
  );
}
