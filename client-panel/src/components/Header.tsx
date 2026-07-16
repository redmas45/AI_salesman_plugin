import { RANGE_OPTIONS } from '../constants';
import type { Theme } from '../theme';
import { ThemeToggle } from './ThemeToggle';

export function Header({
  clientName,
  range,
  busy,
  theme,
  onRangeChange,
  onRefresh,
  onToggleTheme,
  onLogout,
}: {
  clientName: string;
  range: string;
  busy: boolean;
  theme: Theme;
  onRangeChange: (range: string) => void;
  onRefresh: () => void;
  onToggleTheme: () => void;
  onLogout: () => void;
}) {
  return (
    <header className="client-header">
      <div className="brand-lockup">
        <span className="brand-mark">AI</span>
        <div>
          <p>AI Hub client</p>
          <strong>{clientName}</strong>
        </div>
      </div>
      <div className="header-actions">
        <select className="header-range-select" value={range} onChange={(event) => onRangeChange(event.currentTarget.value)} aria-label="Analytics range">
          {RANGE_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <button className="btn btn-secondary" type="button" onClick={onRefresh} disabled={busy}>Refresh</button>
        <button className="btn btn-ghost" type="button" onClick={onLogout}>Logout</button>
      </div>
    </header>
  );
}
