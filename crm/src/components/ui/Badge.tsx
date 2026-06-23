import { statusClass } from '../../utils/format';

export interface StatusPillProps {
  value: string;
}

export function StatusPill({ value }: StatusPillProps) {
  return <span className={`status-pill ${statusClass(value)}`}>{value || 'unknown'}</span>;
}
