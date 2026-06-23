import type { ReactNode } from 'react';

export interface TableProps {
  children: ReactNode;
  compact?: boolean;
}

export function Table({ children, compact = false }: TableProps) {
  return (
    <div className="overflow-x-auto">
      <table className={compact ? 'table-compact' : ''}>{children}</table>
    </div>
  );
}
