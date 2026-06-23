import { LayoutDashboard, Users, Database, Activity, MessageSquare, BarChart3, Plug, Settings, HeartPulse } from 'lucide-react';
import type { View, HealthSnapshot, Client } from '../../types';

export interface SidebarProps {
  view: View;
  setView: (view: View) => void;
  health: HealthSnapshot;
  selectedClient: Client | null;
  open: boolean;
}

const DEFAULT_VIEW: View = 'dashboard';

const NAV_ITEMS: Array<{ view: View; label: string; icon: typeof LayoutDashboard; section: string }> = [
  { view: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
  { view: 'clients', label: 'Clients', icon: Users, section: 'Overview' },
  { view: 'catalogs', label: 'Catalogs', icon: Database, section: 'Data' },
  { view: 'usage', label: 'Usage', icon: Activity, section: 'Data' },
  { view: 'conversations', label: 'Conversations', icon: MessageSquare, section: 'Data' },
  { view: 'analytics', label: 'Analytics', icon: BarChart3, section: 'Data' },
  { view: 'adapters', label: 'Adapters', icon: Plug, section: 'System' },
  { view: 'settings', label: 'Settings', icon: Settings, section: 'System' },
  { view: 'health', label: 'Health', icon: HeartPulse, section: 'System' },
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
  open,
}: SidebarProps) {
  const grouped = groupNavItems();
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  return (
    <aside className={`crm-sidebar ${open ? 'open' : ''}`}>
      <button
        type="button"
        className="sidebar-brand"
        onClick={() => setView(DEFAULT_VIEW)}
      >
        <span className="sidebar-brand-mark">AK</span>
        <span className="sidebar-brand-text">
          <strong>
            AI Hub CRM
            <i className={`health-dot ${healthy ? 'ok' : ''}`} aria-label={healthy ? 'Healthy' : 'Degraded'} />
          </strong>
          <span>crawler and AI ops</span>
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
                <button
                  key={item.view}
                  type="button"
                  className={`sidebar-item ${active ? 'active' : ''}`}
                  onClick={() => setView(item.view)}
                >
                  <Icon className="sidebar-item-icon" aria-hidden="true" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        {selectedClient ? (
          <div className="sidebar-client-pin">
            <div className="sidebar-client-pin-label">Current client</div>
            <div className="sidebar-client-pin-id">{selectedClient.site_id}</div>
            <div className="sidebar-client-pin-url" title={selectedClient.store_url}>
              {selectedClient.store_url}
            </div>
          </div>
        ) : (
          <div className="sidebar-client-card">
            <span>Workspace</span>
            <strong>All clients</strong>
            <span>Admin overview</span>
          </div>
        )}
      </div>
    </aside>
  );
}
