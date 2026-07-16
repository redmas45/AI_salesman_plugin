import { number } from '../../../utils/format';

export function MetricCard({
  label,
  value,
  detail,
  onClick,
}: {
  label: string;
  value: string | number;
  detail: string;
  onClick?: () => void;
}) {
  const content = (
    <>
      <span className="text-xs font-semibold text-muted">{label}</span>
      <strong className="mt-2 block truncate text-xl font-semibold">{typeof value === 'number' ? number(value) : value}</strong>
      <small className="mt-1 block text-xs text-muted">{detail}</small>
    </>
  );
  if (onClick) {
    return (
      <button className="card workspace-metric-card interactive text-left" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <div className="card workspace-metric-card">{content}</div>;
}

export function SkeletonCard({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 'var(--radius)' }} />;
}

export function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}

export function Meter({ label, value, tone }: { label: string; value: number; tone: 'accent' | 'danger' }) {
  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-muted">{label}</span>
        <strong>{number(value)}%</strong>
      </div>
      <div className={`meter meter-${tone}`}>
        <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}
