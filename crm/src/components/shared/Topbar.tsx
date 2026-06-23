import { Menu, RefreshCw, Plus, Sun, Moon } from 'lucide-react';
import { Button, IconButton } from '../ui/Button';
import type { HealthSnapshot, Client, Theme } from '../../types';

export interface TopbarProps {
  title: string;
  health: HealthSnapshot;
  selectedClient: Client | null;
  theme: Theme;
  busy: boolean;
  authenticated: boolean;
  onToggleSidebar: () => void;
  onRefresh: () => void;
  onAddClient: () => void;
  onToggleTheme: () => void;
  onLogout: () => void;
}

export function Topbar({
  title,
  health,
  selectedClient,
  theme,
  busy,
  authenticated,
  onToggleSidebar,
  onRefresh,
  onAddClient,
  onToggleTheme,
  onLogout,
}: TopbarProps) {
  const healthy = Object.values(health).every((value) => value === 'up' || value === 'ready');
  return (
    <header className="crm-topbar">
      <div className="flex items-center gap-3">
        <button className="btn btn-secondary btn-icon mobile-menu-btn" type="button" aria-label="Open navigation" onClick={onToggleSidebar}>
          <Menu size={17} aria-hidden="true" />
        </button>
        <div className="crm-topbar-title" aria-label={`AI Hub, ${title}${selectedClient ? `, ${selectedClient.site_id}` : ''}`}>
          <span className="topbar-crumb-muted">AI Hub</span>
          <span className="topbar-crumb-separator">›</span>
          <span>{title}</span>
          {selectedClient ? (
            <>
              <span className="topbar-crumb-separator">›</span>
              <span className="topbar-crumb-client">{selectedClient.site_id}</span>
            </>
          ) : null}
        </div>
      </div>
      <div className="crm-topbar-actions">
        <span className={`topbar-live-badge ${healthy ? '' : 'degraded'}`}>
          <span className="topbar-live-dot" />
          {healthy ? 'Live' : 'Degraded'}
        </span>
        <IconButton
          label={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          icon={theme === 'dark' ? Sun : Moon}
          onClick={onToggleTheme}
        />
        {authenticated ? <IconButton label="Refresh" icon={RefreshCw} onClick={onRefresh} disabled={busy} /> : null}
        {authenticated ? (
          <Button onClick={onAddClient} icon={Plus}>
            Add client
          </Button>
        ) : null}
        {authenticated ? (
          <Button variant="secondary" onClick={onLogout}>
            Logout
          </Button>
        ) : null}
      </div>
    </header>
  );
}
