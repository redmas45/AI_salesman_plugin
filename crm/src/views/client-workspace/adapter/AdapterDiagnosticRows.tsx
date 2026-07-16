import type { ReactNode } from 'react';

export function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }): ReactNode {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}

export function RecordList({
  title,
  rows,
  render,
}: {
  title: string;
  rows: Record<string, unknown>[];
  render: (row: Record<string, unknown>) => ReactNode;
}): ReactNode {
  if (!rows.length) return null;
  return (
    <div className="grid gap-2">
      <strong className="text-sm">{title}</strong>
      <div className="grid gap-2">{rows.map(render)}</div>
    </div>
  );
}
