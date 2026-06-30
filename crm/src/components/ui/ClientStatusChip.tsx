interface ClientStatusChipProps {
  status: string;
}

const STATUS_STYLES: Record<string, string> = {
  live: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  online: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  current: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  available: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
  offline: 'border-slate-700 bg-slate-800/50 text-slate-400',
  disabled: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  degraded: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  configured: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
};

export function ClientStatusChip({ status }: ClientStatusChipProps) {
  const normalized = String(status || 'unknown').toLowerCase();
  const className = STATUS_STYLES[normalized] || 'border-slate-700 bg-slate-800/50 text-slate-400';
  return (
    <span className={`inline-flex h-5 items-center rounded-full border px-2 text-[10px] font-medium uppercase tracking-wide ${className}`}>
      {readableStatus(normalized)}
    </span>
  );
}

function readableStatus(status: string) {
  if (!status) return 'Unknown';
  return status.replace(/[_-]+/g, ' ');
}
