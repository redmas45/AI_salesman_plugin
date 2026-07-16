import { Menu, RefreshCw } from 'lucide-react';
import { Button, IconButton } from '../../ui/Button';
import type { HealthSnapshot, Client, View } from '../../../types';
import type { Theme } from '../../../types';
import type { ClientWorkspaceTabId } from '../../../verticals/types';
import { ThemeToggle } from '../controls/ThemeToggle';

export interface TopbarProps {
  title: string;
  view: View;
  health: HealthSnapshot;
  selectedClient: Client | null;
  activeClientTab: ClientWorkspaceTabId;
  busy: boolean;
  authenticated: boolean;
  theme: Theme;
  onToggleSidebar: () => void;
  onToggleTheme: () => void;
  onRefresh: () => void;
  onLogout: () => void;
  onOpenDashboard: () => void;
  onOpenClients: () => void;
  onOpenView: (view: View) => void;
  onOpenClient?: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}

export function Topbar({
  title,
  view,
  health,
  selectedClient,
  activeClientTab,
  busy,
  authenticated,
  theme,
  onToggleSidebar,
  onToggleTheme,
  onRefresh,
  onLogout,
  onOpenDashboard,
  onOpenClients,
  onOpenView,
  onOpenClient,
}: TopbarProps) {
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  const sectionLabel = selectedClient ? 'Clients' : title;
  const openSection = selectedClient || view === 'clients' ? onOpenClients : () => onOpenView(view);
  const sectionIsCurrentPage = !selectedClient && view !== 'clients';
  return (
    <header className="crm-topbar">
      <div className="flex items-center gap-3">
        <button className="btn btn-secondary btn-icon mobile-menu-btn" type="button" aria-label="Open navigation" onClick={onToggleSidebar}>
          <Menu size={17} aria-hidden="true" />
        </button>
        <div className="crm-topbar-title" aria-label={`AI Hub, ${title}${selectedClient ? `, ${selectedClient.site_id}` : ''}`}>
          <button className="topbar-crumb-button topbar-crumb-muted" type="button" onClick={onOpenDashboard}>
            AI Hub
          </button>
          <span className="topbar-crumb-separator">/</span>
          <button
            className={`topbar-crumb-button topbar-crumb-section ${selectedClient || view === 'clients' ? 'topbar-crumb-parent' : ''} ${sectionIsCurrentPage ? 'current' : ''}`}
            type="button"
            aria-label={selectedClient ? 'Open all clients' : `Open ${sectionLabel}`}
            aria-current={sectionIsCurrentPage ? 'page' : undefined}
            title={selectedClient ? 'Open all clients' : `Open ${sectionLabel}`}
            onClick={openSection}
          >
            {sectionLabel}
          </button>
          {selectedClient ? (
            <>
              <span className="topbar-crumb-separator">/</span>
              <button
                className="topbar-crumb-button topbar-crumb-client"
                type="button"
                aria-current="page"
                aria-label={`Open ${selectedClient.name || selectedClient.site_id} overview`}
                title={`Open ${selectedClient.name || selectedClient.site_id} overview`}
                onClick={() => onOpenClient?.(selectedClient.site_id, activeClientTab)}
              >
                {selectedClient.site_id}
              </button>
            </>
          ) : null}
        </div>
      </div>
      <div className="crm-topbar-actions">
        <span className={`topbar-live-badge ${healthy ? '' : 'degraded'}`}>
          <span className="topbar-live-dot" />
          {healthy ? 'Live' : 'Degraded'}
        </span>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        {authenticated ? <IconButton label="Refresh" icon={RefreshCw} onClick={onRefresh} disabled={busy} /> : null}
        {authenticated ? (
          <Button variant="secondary" onClick={onLogout}>
            Logout
          </Button>
        ) : null}
      </div>
    </header>
  );
}
