import type { ReactNode } from 'react';
import { PackageOpen, type LucideIcon } from 'lucide-react';

export interface EmptyStateProps {
  text?: string;
  title?: string;
  message?: string;
  action?: ReactNode;
  icon?: LucideIcon;
}

export function EmptyState({
  text,
  title,
  message,
  action,
  icon: Icon = PackageOpen,
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-icon-wrap">
        <Icon size={30} aria-hidden="true" />
      </div>
      <h3>{title || text || 'Nothing here yet'}</h3>
      {message ? <p>{message}</p> : text && title ? <p>{text}</p> : null}
      {action}
    </div>
  );
}
