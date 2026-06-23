import { RANGE_OPTIONS } from '../../utils/range';

export interface RangeControlProps {
  value: string;
  onChange: (value: string) => void;
}

export function RangeControl({ value, onChange }: RangeControlProps) {
  return (
    <label className="grid grid-cols-[auto_160px] items-center gap-2 text-xs font-semibold text-muted">
      <span>Range</span>
      <select value={value} onChange={(event) => onChange(event.currentTarget.value)}>
        {RANGE_OPTIONS.map(([optionValue, label]) => (
          <option key={optionValue} value={optionValue}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}
