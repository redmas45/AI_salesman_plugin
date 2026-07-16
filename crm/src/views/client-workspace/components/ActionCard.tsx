import type { ReactNode } from 'react';
import { ArrowRight, Loader2, WifiOff, type LucideIcon } from 'lucide-react';

interface ActionCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  variant: 'primary' | 'secondary';
  disabled: boolean;
  running: boolean;
  offline?: boolean;
  onClick: () => void;
  buttonLabel: string;
}

export function ActionCard({
  icon: Icon,
  title,
  description,
  variant,
  disabled,
  running,
  offline = false,
  onClick,
  buttonLabel,
}: ActionCardProps): ReactNode {
  const primary = variant === 'primary';
  return (
    <div
      className={cx(
        'flex min-w-0 flex-col gap-3 rounded-md border p-4',
        primary ? 'border-[#93b4fd] bg-[#eef4ff]' : 'border-[#dce6f5] bg-white',
        disabled && !running ? 'opacity-60' : '',
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        <Icon size={16} className={cx('mt-0.5 shrink-0', primary ? 'text-[#3b6ef8]' : 'text-[#64748b]')} aria-hidden="true" />
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-sm font-semibold leading-tight text-[#172033]">{title}</span>
          <span className="text-xs leading-relaxed text-[#64748b]">{description}</span>
        </div>
      </div>

      {offline ? (
        <div className="flex items-center gap-1.5 text-xs text-[#64748b]">
          <WifiOff size={11} aria-hidden="true" />
          <span>Source offline</span>
        </div>
      ) : (
        <button
          type="button"
          disabled={disabled}
          onClick={onClick}
          className={cx(
            'inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-md px-3 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-40',
            primary
              ? 'bg-[#172033] text-white shadow-[0_10px_24px_rgba(23,32,51,0.18)] hover:-translate-y-0.5 hover:bg-[#263247] hover:shadow-[0_14px_30px_rgba(23,32,51,0.2)]'
              : 'border border-[#dce6f5] bg-white text-[#172033] hover:border-[#93b4fd] hover:bg-[#f8fbff] hover:text-[#3b6ef8]',
          )}
        >
          {running ? (
            <>
              <Loader2 size={12} className="animate-spin" aria-hidden="true" />
              Running...
            </>
          ) : (
            <>
              <span>{buttonLabel}</span>
              {primary ? <ArrowRight size={14} aria-hidden="true" /> : null}
            </>
          )}
        </button>
      )}
    </div>
  );
}

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}
