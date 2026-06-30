import {
  LayoutDashboard,
  Users,
  Database,
  Activity,
  MessageSquare,
  BarChart3,
  Plug,
  Settings,
  HeartPulse,
  KeyRound,
  ExternalLink,
  ListTree,
  CheckCircle2,
  Wifi,
  WifiOff,
  Gauge,
  type LucideIcon,
} from 'lucide-react';
import type { View, HealthSnapshot, Client, ClientBoardSection, AnalyticsSectionId } from '../../types';
import { clientPanelHref } from '../../utils/clientLinks';
import { clientWorkspaceTabs } from '../../verticals/workspace';
import type { ClientWorkspaceTabId } from '../../verticals/types';

export interface SidebarProps {
  view: View;
  setView: (view: View) => void;
  health: HealthSnapshot;
  selectedClient: Client | null;
  activeClientTab: ClientWorkspaceTabId;
  clientBoardSection: ClientBoardSection;
  analyticsSection: AnalyticsSectionId;
  open: boolean;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onOpenClientTab: (tabId: ClientWorkspaceTabId) => void;
  onOpenAnalyticsSection: (section: AnalyticsSectionId) => void;
}

const DEFAULT_VIEW: View = 'dashboard';

const NAV_ITEMS: Array<{ view: View; label: string; icon: LucideIcon; section: string }> = [
  { view: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
  { view: 'clients', label: 'Clients', icon: Users, section: 'Overview' },
  { view: 'catalogs', label: 'Data storage', icon: Database, section: 'Data' },
  { view: 'usage', label: 'Usage', icon: Activity, section: 'Data' },
  { view: 'conversations', label: 'Conversations', icon: MessageSquare, section: 'Data' },
  { view: 'analytics', label: 'Analytics', icon: BarChart3, section: 'Data' },
  { view: 'adapters', label: 'Adapters', icon: Plug, section: 'System' },
  { view: 'settings', label: 'Settings', icon: Settings, section: 'System' },
  { view: 'health', label: 'Health', icon: HeartPulse, section: 'System' },
];

const CLIENT_BOARD_ITEMS: Array<{
  id: ClientBoardSection;
  label: string;
  icon: LucideIcon;
}> = [
  { id: 'all', label: 'All clients', icon: ListTree },
  { id: 'current', label: 'Current clients', icon: CheckCircle2 },
  { id: 'available', label: 'Available installs', icon: Users },
  { id: 'online', label: 'Online installs', icon: Wifi },
  { id: 'offline', label: 'Offline installs', icon: WifiOff },
];

const ANALYTICS_ITEMS: Array<{
  id: AnalyticsSectionId;
  label: string;
  icon: LucideIcon;
}> = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'quality', label: 'Quality & health', icon: Gauge },
  { id: 'details', label: 'Details', icon: BarChart3 },
];

function groupNavItems() {
  return NAV_ITEMS.reduce<Record<string, typeof NAV_ITEMS>>((groups, item) => {
    groups[item.section] = groups[item.section] || [];
    groups[item.section].push(item);
    return groups;
  }, {});
}

export function Sidebar({
  view,
  setView,
  health,
  selectedClient,
  activeClientTab,
  clientBoardSection,
  analyticsSection,
  open,
  onOpenClientBoardSection,
  onOpenClientTab,
  onOpenAnalyticsSection,
}: SidebarProps) {
  const grouped = groupNavItems();
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  const clientWorkspaceItems = selectedClient ? clientWorkspaceTabs(selectedClient) : [];
  return (
    <aside className={`crm-sidebar ${open ? 'open' : ''}`}>
      <button
        type="button"
        className="sidebar-brand"
        onClick={() => setView(DEFAULT_VIEW)}
      >
        <span className="sidebar-brand-mark">AI</span>
        <span className="sidebar-brand-text">
          <strong>
            AI Hub CRM
            <i className={`health-dot ${healthy ? 'ok' : ''}`} aria-label={healthy ? 'Healthy' : 'Degraded'} />
          </strong>
          <span>Maya operations center</span>
        </span>
      </button>
      <nav className="sidebar-nav" aria-label="CRM navigation">
        {Object.entries(grouped).map(([section, items]) => (
          <div key={section}>
            <div className="sidebar-section-label">{section}</div>
            {items.map((item) => {
              const Icon = item.icon;
              const active = view === item.view || (view === 'client-detail' && item.view === 'clients');
              return (
                <div key={item.view}>
                  <button
                    type="button"
                    className={`sidebar-item ${active ? 'active' : ''}`}
                    onClick={() => {
                      if (item.view === 'clients') {
                        onOpenClientBoardSection('all');
                        return;
                      }
                      setView(item.view);
                    }}
                  >
                    <Icon className="sidebar-item-icon" aria-hidden="true" />
                    <span>{item.label}</span>
                  </button>
                  {item.view === 'clients' && selectedClient && view === 'client-detail' ? (
                    <div className="sidebar-client-tree sidebar-clients-tree" aria-label={`Client workspace for ${selectedClient.site_id}`}>
                      <div className="sidebar-subnav-label">Selected client</div>
                      <button
                        type="button"
                        className="sidebar-current-client"
                        onClick={() => onOpenClientTab('overview')}
                      >
                        <span className={`sidebar-client-status ${runtimeStatus(selectedClient)}`} aria-hidden="true" />
                        <span className="sidebar-client-node-copy">
                          <strong>{selectedClient.name || selectedClient.site_id}</strong>
                          <small>{selectedClient.site_id}</small>
                        </span>
                      </button>
                      <div className="sidebar-subnav-label">Workspace</div>
                      {clientWorkspaceItems.map((subItem) => {
                        const SubIcon = subItem.icon;
                        const activeSubItem = view === 'client-detail' && activeClientTab === subItem.id;
                        return (
                          <button
                            key={subItem.id}
                            type="button"
                            className={`sidebar-subitem ${activeSubItem ? 'active' : ''}`}
                            onClick={() => onOpenClientTab(subItem.id)}
                          >
                            <SubIcon aria-hidden="true" />
                            <span>{subItem.label}</span>
                          </button>
                        );
                      })}
                      <div className="sidebar-subnav-label">Client board</div>
                      {CLIENT_BOARD_ITEMS.map((boardItem) => {
                        const BoardIcon = boardItem.icon;
                        return (
                          <button
                            key={boardItem.id}
                            type="button"
                            className="sidebar-subitem"
                            onClick={() => onOpenClientBoardSection(boardItem.id)}
                          >
                            <BoardIcon aria-hidden="true" />
                            <span>{boardItem.label}</span>
                          </button>
                        );
                      })}
                      <div className="sidebar-subnav-group">
                        <div className="sidebar-subnav-label">Open</div>
                        <a className="sidebar-subitem sidebar-subitem-link" href={selectedClient.store_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink aria-hidden="true" />
                          <span>Website</span>
                        </a>
                        <a className="sidebar-subitem sidebar-subitem-link" href={clientPanelHref(selectedClient.site_id)} target="_blank" rel="noopener noreferrer">
                          <KeyRound aria-hidden="true" />
                          <span>Owner panel</span>
                        </a>
                      </div>
                    </div>
                  ) : null}
                  {item.view === 'clients' && view !== 'client-detail' ? (
                    <div className="sidebar-board-tree" aria-label="Client board shortcuts">
                      <div className="sidebar-subnav-label">Client board</div>
                      {CLIENT_BOARD_ITEMS.map((boardItem) => {
                        const BoardIcon = boardItem.icon;
                        const activeBoardItem = view === 'clients' && clientBoardSection === boardItem.id;
                        return (
                          <button
                            key={boardItem.id}
                            type="button"
                            className={`sidebar-subitem ${activeBoardItem ? 'active' : ''}`}
                            onClick={() => onOpenClientBoardSection(boardItem.id)}
                          >
                            <BoardIcon aria-hidden="true" />
                            <span>{boardItem.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                  {item.view === 'analytics' && view === 'analytics' ? (
                    <div className="sidebar-board-tree" aria-label="Analytics sections">
                      <div className="sidebar-subnav-label">Analytics sections</div>
                      {ANALYTICS_ITEMS.map((analyticsItem) => {
                        const AnalyticsIcon = analyticsItem.icon;
                        const activeAnalyticsItem = analyticsSection === analyticsItem.id;
                        return (
                          <button
                            key={analyticsItem.id}
                            type="button"
                            className={`sidebar-subitem ${activeAnalyticsItem ? 'active' : ''}`}
                            onClick={() => onOpenAnalyticsSection(analyticsItem.id)}
                          >
                            <AnalyticsIcon aria-hidden="true" />
                            <span>{analyticsItem.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-footer-note">
          <span>Workspace</span>
          <strong>{selectedClient ? selectedClient.site_id : 'All clients'}</strong>
        </div>
      </div>
    </aside>
  );
}

function runtimeStatus(client: Client) {
  return String(client.runtime_status?.status || 'unknown').toLowerCase();
}
