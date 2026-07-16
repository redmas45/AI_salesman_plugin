import { useState, useEffect, useRef } from 'react';
import { EllipsisVertical, Eye, KeyRound, Trash2, type LucideIcon } from 'lucide-react';
import type { Client } from '../../../types';

export interface ActionMenuItem {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
  danger?: boolean;
}

export interface ActionMenuProps {
  items: ActionMenuItem[];
}

export function ActionMenu({ items }: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handle(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  return (
    <div ref={ref} className="action-menu-wrapper" role="menu">
      <button
        className="btn btn-secondary btn-icon"
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <EllipsisVertical size={16} aria-hidden="true" />
      </button>
      {open ? (
        <div className="action-menu-panel">
          {items.map(({ label, icon: Icon, onClick, danger }) => (
            <button
              key={label}
              className={`action-menu-item ${danger ? 'danger' : ''}`}
              type="button"
              onClick={() => {
                onClick();
                setOpen(false);
              }}
            >
              <Icon size={15} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export interface ClientActionMenuProps {
  client: Client;
  onOpenClient: (siteId: string) => void;
  onOpenPasswordDialog: (client: Client) => void;
  onRemoveClient: (siteId: string) => void;
}

export function ClientActionMenu({
  client,
  onOpenClient,
  onOpenPasswordDialog,
  onRemoveClient,
}: ClientActionMenuProps) {
  return (
    <ActionMenu
      items={[
        { label: 'Open client', icon: Eye, onClick: () => onOpenClient(client.site_id) },
        { label: 'Panel password', icon: KeyRound, onClick: () => onOpenPasswordDialog(client) },
        { label: 'Remove client', icon: Trash2, onClick: () => onRemoveClient(client.site_id), danger: true },
      ]}
    />
  );
}
