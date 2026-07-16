import {
  Activity,
  BarChart3,
  Database,
  HeartPulse,
  LayoutDashboard,
  MessageSquare,
  Plug,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react';
import type { HealthSnapshot, View } from '../../../types';

export interface SidebarProps {
  view: View;
  setView: (view: View) => void;
  health: HealthSnapshot;
  open: boolean;
}

const NAV_ITEMS: Array<{ view: View; label: string; icon: LucideIcon }> = [
  { view: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { view: 'clients', label: 'Clients', icon: Users },
  { view: 'catalogs', label: 'Data storage', icon: Database },
  { view: 'usage', label: 'Usage', icon: Activity },
  { view: 'conversations', label: 'Conversations', icon: MessageSquare },
  { view: 'analytics', label: 'Analytics', icon: BarChart3 },
  { view: 'adapters', label: 'Adapters', icon: Plug },
  { view: 'settings', label: 'Settings', icon: Settings },
  { view: 'health', label: 'Health', icon: HeartPulse },
];

export function Sidebar({ view, setView, health, open }: SidebarProps) {
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  return (
    <aside className={`crm-sidebar ${open ? 'open' : ''}`}>
      <button type="button" className="sidebar-brand" onClick={() => setView('dashboard')}>
        <span className="sidebar-brand-mark">AI</span>
        <span className="sidebar-brand-text">
          <strong>
            AI Hub
            <i className={`health-dot ${healthy ? 'ok' : ''}`} aria-label={healthy ? 'Healthy' : 'Degraded'} />
          </strong>
          <span>Maya operations</span>
        </span>
      </button>
      <nav className="sidebar-nav" aria-label="CRM navigation">
        {NAV_ITEMS.map((item) => {
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
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-footer-note">
          <span>Workspace</span>
          <strong>All clients</strong>
        </div>
      </div>
    </aside>
  );
}
