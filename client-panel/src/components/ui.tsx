import type { RankRow } from '../types';
import { number, percent } from '../utils';

export function KpiCard({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: string | number;
  tone: 'accent' | 'blue' | 'green' | 'amber';
  icon: string;
}) {
  return (
    <section className={`card kpi-card kpi-${tone}`} data-icon={icon}>
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{typeof value === 'number' ? number(value) : value}</strong>
    </section>
  );
}

export function Metric({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string | number;
  detail: string;
  tone: 'accent' | 'blue' | 'green' | 'ink';
}) {
  return (
    <section className={`panel metric tone-${tone}`}>
      <span>{label}</span>
      <strong>{typeof value === 'number' ? number(value) : value}</strong>
      <small>{detail}</small>
    </section>
  );
}

export function RankPanel({ title, rows }: { title: string; rows: RankRow[] }) {
  return (
    <section className="panel">
      <PanelHeader title={title} detail={`${number(rows.length)} signals`} />
      <MiniRank title="" rows={rows} />
    </section>
  );
}

export function MiniRank({ title, rows }: { title: string; rows: RankRow[] }) {
  const max = Math.max(...rows.map((row) => row.count), 1);

  return (
    <div className="mini-rank">
      {title ? <h3>{title}</h3> : null}
      {rows.map((row) => (
        <div className="rank-row" key={`${title}-${row.label}`}>
          <span>{row.label}</span>
          <div><i style={{ width: `${Math.max(8, percent(row.count, max))}%` }} /></div>
          <b>{number(row.count)}</b>
        </div>
      ))}
      {!rows.length ? <EmptyState title="No data yet" message="Signals will appear here after there is enough customer activity." compact /> : null}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  compact = false,
}: {
  title: string;
  message: string;
  compact?: boolean;
}) {
  return (
    <div className={`empty-state ${compact ? 'compact' : ''}`}>
      <div className="empty-icon-wrap">AI</div>
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}

export function Meter({ label, value, danger = false }: { label: string; value: number; danger?: boolean }) {
  return (
    <div>
      <div className="meter-label">
        <span>{label}</span>
        <strong>{number(value)}%</strong>
      </div>
      <Progress value={value} danger={danger} />
    </div>
  );
}

export function Progress({ value, danger = false }: { value: number; danger?: boolean }) {
  return (
    <div className={`progress ${danger ? 'danger' : ''}`}>
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export function PaginationControl({
  page,
  pageCount,
  pageSize,
  totalItems,
  itemLabel,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  pageSize: number;
  totalItems: number;
  itemLabel: string;
  onPageChange: (page: number) => void;
}) {
  const firstItem = totalItems ? (page - 1) * pageSize + 1 : 0;
  const lastItem = Math.min(page * pageSize, totalItems);
  return (
    <nav className="pagination-control" aria-label={`${itemLabel} pagination`}>
      <span className="pagination-summary">
        {number(firstItem)}-{number(lastItem)} of {number(totalItems)} {itemLabel}
      </span>
      <span className="pagination-page">Page {number(page)} of {number(pageCount)}</span>
      <span className="pagination-actions">
        <button className="btn btn-secondary btn-icon btn-sm" type="button" aria-label="Previous page" title="Previous page" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          <span aria-hidden="true">&larr;</span>
        </button>
        <button className="btn btn-secondary btn-icon btn-sm" type="button" aria-label="Next page" title="Next page" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
          <span aria-hidden="true">&rarr;</span>
        </button>
      </span>
    </nav>
  );
}

export function PanelHeader({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="panel-head">
      <h2>{title}</h2>
      <span>{detail}</span>
    </div>
  );
}

export function KeyLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="key-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function StatusPill({ label }: { label: string }) {
  return <span className={`status-pill ${label.toLowerCase()}`}>{label}</span>;
}

export function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="mini-stat">
      <span>{label}</span>
      <strong>{number(value)}</strong>
    </div>
  );
}

export function LoadingPanel() {
  return (
    <div className="overview-layout">
      <div className="kpi-strip">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="skeleton" style={{ height: 104 }} />
        ))}
      </div>
      <div className="overview-main">
        <div className="skeleton" style={{ height: 260 }} />
        <div className="skeleton" style={{ height: 260 }} />
      </div>
    </div>
  );
}
