import { EmptyState } from '../../../components/ui/EmptyState';
import { actionLabel } from './actionLabels';

export function ActionChipGrid({ actions }: { actions: string[] }) {
  if (!actions.length) return <EmptyState text="No UI actions are allowed yet." />;
  return (
    <div className="action-chip-grid">
      {actions.map((action) => (
        <span key={action} className="action-chip">
          {actionLabel(action)}
        </span>
      ))}
    </div>
  );
}
