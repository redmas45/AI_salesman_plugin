import { number } from '../../../utils/format';

export function MiniMetric({ label, value, onClick }: { label: string; value: number; onClick?: () => void }) {
  const content = (
    <>
      <span className="text-xs text-muted">{label}</span>
      <strong className="mt-1 block text-xl">{number(value)}</strong>
    </>
  );
  if (onClick) {
    return (
      <button className="mini-metric interactive" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return (
    <div className="mini-metric">
      {content}
    </div>
  );
}
